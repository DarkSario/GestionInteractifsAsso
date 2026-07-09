"""Sauvegarde, restauration et import/export de la base SQLite."""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath

from db.connection import get_connection, get_db_file
from db.migrations.runner import MIGRATIONS_DIR, run_migrations
from db.models.parametres_globaux import get_parametre, set_parametre
from utils.logger import get_logger

logger = get_logger(__name__)

APP_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_ROOT / "config"
DEFAULT_BACKUP_DIR = APP_ROOT / "data" / "sauvegardes"
SQLITE_HEADER = b"SQLite format 3\x00"

_TYPE_LABELS = {
    "manuelle": "Manuel",
    "automatique": "Auto",
    "avant_restauration": "Sécurité",
}


def get_chemin_db() -> Path:
    """Retourne le chemin absolu de la base SQLite active."""
    db_file = get_db_file()
    if not db_file:
        raise RuntimeError("Aucune base de données active.")

    db_path = Path(db_file).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")
    return db_path


def get_dossier_sauvegarde() -> Path:
    """Retourne et crée au besoin le dossier des sauvegardes."""
    dossier = get_parametre("sauvegarde_dossier", "").strip()
    if dossier:
        path = Path(dossier).expanduser()
        if not path.is_absolute():
            path = (APP_ROOT / path).resolve()
    else:
        path = DEFAULT_BACKUP_DIR

    path.mkdir(parents=True, exist_ok=True)
    return path


def generer_nom_sauvegarde(type_sv: str = "manuelle") -> str:
    """Génère un nom de sauvegarde horodaté."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = ".zip" if _compression_activee() else ".db"
    return f"asso_interactifs_{horodatage}_{type_sv}{extension}"


def sauvegarder_maintenant(type_sv: str = "manuelle") -> dict:
    """Crée une sauvegarde immédiate et l'enregistre dans l'historique."""
    destination: Path | None = None
    try:
        db_path = get_chemin_db()
        dossier = get_dossier_sauvegarde()
        nom_fichier = generer_nom_sauvegarde(type_sv)
        destination = dossier / nom_fichier

        if destination.suffix.lower() == ".zip":
            _creer_archive_sauvegarde(db_path, destination)
        else:
            _copier_base_sqlite(db_path, destination)

        taille = destination.stat().st_size
        now_iso = _now_iso()
        _enregistrer_sauvegarde(
            nom_fichier=destination.name,
            chemin_complet=str(destination),
            taille_octets=taille,
            type_sauvegarde=type_sv,
            statut="ok",
            message_erreur=None,
            created_at=now_iso,
        )
        set_parametre("derniere_sauvegarde", now_iso)
        appliquer_rotation()

        message = f"Sauvegarde créée : {destination}"
        logger.info(message)
        return {
            "succes": True,
            "chemin": str(destination),
            "nom_fichier": destination.name,
            "taille": taille,
            "message": message,
        }
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        logger.exception("Erreur de sauvegarde : %s", message)
        if destination and destination.exists():
            try:
                destination.unlink()
            except OSError:
                logger.warning("Impossible de supprimer la sauvegarde incomplète : %s", destination)
        _tenter_enregistrement_erreur(destination, type_sv, message)
        return {
            "succes": False,
            "chemin": str(destination) if destination else "",
            "nom_fichier": destination.name if destination else "",
            "taille": 0,
            "message": message,
        }


def verifier_sauvegarde_auto() -> bool:
    """Déclenche une sauvegarde automatique silencieuse si nécessaire."""
    try:
        if get_parametre("sauvegarde_auto", "0") != "1":
            return False

        frequence = _get_param_int("sauvegarde_frequence", 7, minimum=1)
        derniere = _parse_datetime(get_parametre("derniere_sauvegarde", ""))
        if derniere and (datetime.now() - derniere) < timedelta(days=frequence):
            return False

        resultat = sauvegarder_maintenant("automatique")
        if not resultat["succes"]:
            logger.error("Échec de la sauvegarde automatique : %s", resultat["message"])
            return False
        logger.info("Sauvegarde automatique effectuée : %s", resultat["chemin"])
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur lors de la vérification de sauvegarde auto : %s", exc)
        return False


def verifier_integrite_base(chemin_db: str) -> dict:
    """Vérifie l'intégrité d'une base SQLite ou d'une archive de sauvegarde."""
    try:
        with _chemin_db_temporaire(Path(chemin_db)) as db_path:
            if not _est_fichier_sqlite(db_path):
                return {"valide": False, "message": "Le fichier n'est pas une base SQLite valide."}

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                row = conn.execute("PRAGMA integrity_check;").fetchone()
            finally:
                conn.close()

            if row and str(row[0]).lower() == "ok":
                return {"valide": True, "message": "Base valide"}
            return {"valide": False, "message": row[0] if row else "Intégrité invalide."}
    except zipfile.BadZipFile:
        return {"valide": False, "message": "Archive ZIP invalide."}
    except Exception as exc:  # noqa: BLE001
        return {"valide": False, "message": str(exc)}


def restaurer_sauvegarde(chemin_sauvegarde: str) -> dict:
    """Restaure la base courante depuis une sauvegarde .db ou .zip."""
    source = Path(chemin_sauvegarde).expanduser()
    if not source.exists():
        return {
            "succes": False,
            "message": "Le fichier de sauvegarde est introuvable.",
            "chemin_sauvegarde_securite": "",
        }

    integrite = verifier_integrite_base(str(source))
    if not integrite["valide"]:
        return {
            "succes": False,
            "message": f"Restauration impossible : {integrite['message']}",
            "chemin_sauvegarde_securite": "",
        }

    securite = sauvegarder_maintenant("avant_restauration")
    if not securite["succes"]:
        return {
            "succes": False,
            "message": "Impossible de créer la sauvegarde de sécurité avant restauration.",
            "chemin_sauvegarde_securite": "",
        }

    try:
        with _chemin_db_temporaire(source) as db_path:
            _remplacer_base_active(db_path)
        if source.suffix.lower() == ".zip":
            _restaurer_config_depuis_archive(source)
        run_migrations()
        _restaurer_trace_sauvegarde_securite(securite["chemin"])
        return {
            "succes": True,
            "message": "Restauration réussie. Redémarrage requis.",
            "chemin_sauvegarde_securite": securite["chemin"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur de restauration : %s", exc)
        return {
            "succes": False,
            "message": str(exc),
            "chemin_sauvegarde_securite": securite["chemin"],
        }


def get_liste_sauvegardes() -> list[dict]:
    """Retourne l'historique des sauvegardes trié par date décroissante."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom_fichier, chemin_complet, taille_octets, type_sauvegarde,
                   statut, message_erreur, created_at
            FROM sauvegardes
            ORDER BY datetime(created_at) DESC, id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    resultats: list[dict] = []
    for row in rows:
        created_at = row["created_at"] or ""
        resultats.append(
            {
                "id": row["id"],
                "nom_fichier": row["nom_fichier"],
                "chemin": row["chemin_complet"],
                "taille_octets": row["taille_octets"] or 0,
                "taille_formatee": formater_taille(row["taille_octets"] or 0),
                "type": _TYPE_LABELS.get(row["type_sauvegarde"], row["type_sauvegarde"]),
                "type_code": row["type_sauvegarde"],
                "statut": row["statut"],
                "message_erreur": row["message_erreur"] or "",
                "date": created_at,
                "date_formatee": _formater_datetime(created_at),
            }
        )
    return resultats


def supprimer_sauvegarde(sauvegarde_id: int) -> bool:
    """Supprime le fichier de sauvegarde et marque l'entrée comme supprimée."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT chemin_complet FROM sauvegardes WHERE id = ?",
            (sauvegarde_id,),
        ).fetchone()
        if not row:
            return False

        chemin = Path(row["chemin_complet"])
        if chemin.exists():
            chemin.unlink()

        conn.execute(
            "UPDATE sauvegardes SET statut = 'supprimee' WHERE id = ?",
            (sauvegarde_id,),
        )
        conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur suppression sauvegarde #%s : %s", sauvegarde_id, exc)
        return False
    finally:
        conn.close()


def appliquer_rotation(max_sauvegardes: int | None = None) -> int:
    """Supprime les sauvegardes les plus anciennes au-delà de la limite."""
    limite = max_sauvegardes or _get_param_int("sauvegarde_rotation_max", 10, minimum=1)
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, chemin_complet
            FROM sauvegardes
            WHERE statut != 'supprimee'
            ORDER BY datetime(created_at) DESC, id DESC
            """
        ).fetchall()

        if len(rows) <= limite:
            return 0

        a_supprimer = rows[limite:]
        total = 0
        for row in a_supprimer:
            chemin = Path(row["chemin_complet"])
            if chemin.exists():
                try:
                    chemin.unlink()
                except OSError as exc:
                    logger.warning("Impossible de supprimer %s : %s", chemin, exc)
                    continue
            conn.execute(
                "UPDATE sauvegardes SET statut = 'supprimee' WHERE id = ?",
                (row["id"],),
            )
            total += 1

        conn.commit()
        return total
    finally:
        conn.close()


def formater_taille(octets: int) -> str:
    """Formate une taille en unité lisible."""
    valeur = max(int(octets or 0), 0)
    if valeur < 1024:
        return f"{valeur} octets"

    unites = ["Ko", "Mo", "Go", "To"]
    taille = float(valeur)
    for unite in unites:
        taille /= 1024.0
        if taille < 1024 or unite == unites[-1]:
            if taille >= 100:
                texte = f"{taille:.0f}"
            else:
                texte = f"{taille:.1f}".rstrip("0").rstrip(".")
            return f"{texte.replace('.', ',')} {unite}"
    return f"{valeur} octets"


def exporter_base_complete(chemin_destination: str) -> dict:
    """Exporte la base active en .db ou .zip."""
    destination = Path(chemin_destination).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        db_path = get_chemin_db()
        if destination.suffix.lower() == ".zip":
            _creer_archive_export(db_path, destination)
        else:
            if destination.suffix.lower() != ".db":
                destination = destination.with_suffix(".db")
            _copier_base_sqlite(db_path, destination)

        taille = destination.stat().st_size
        return {
            "succes": True,
            "chemin": str(destination),
            "taille": taille,
            "message": f"Export réalisé : {destination}",
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur export base : %s", exc)
        return {
            "succes": False,
            "chemin": str(destination),
            "taille": 0,
            "message": str(exc),
        }


def importer_base(chemin_source: str) -> dict:
    """Importe une base externe après vérifications et sauvegarde de sécurité."""
    source = Path(chemin_source).expanduser()
    if not source.exists():
        return {
            "succes": False,
            "message": "Le fichier à importer est introuvable.",
            "necessite_redemarrage": False,
            "chemin_sauvegarde_securite": "",
        }

    integrite = verifier_integrite_base(str(source))
    if not integrite["valide"]:
        return {
            "succes": False,
            "message": integrite["message"],
            "necessite_redemarrage": False,
            "chemin_sauvegarde_securite": "",
        }

    try:
        with _chemin_db_temporaire(source) as db_path:
            compatible = _verifier_schema_compatible(db_path)
            if not compatible["valide"]:
                return {
                    "succes": False,
                    "message": compatible["message"],
                    "necessite_redemarrage": False,
                    "chemin_sauvegarde_securite": "",
                }
    except Exception as exc:  # noqa: BLE001
        return {
            "succes": False,
            "message": str(exc),
            "necessite_redemarrage": False,
            "chemin_sauvegarde_securite": "",
        }

    securite = sauvegarder_maintenant("avant_restauration")
    if not securite["succes"]:
        return {
            "succes": False,
            "message": "Impossible de créer la sauvegarde de sécurité avant import.",
            "necessite_redemarrage": False,
            "chemin_sauvegarde_securite": "",
        }

    try:
        with _chemin_db_temporaire(source) as db_path:
            _remplacer_base_active(db_path)
        if source.suffix.lower() == ".zip":
            _restaurer_config_depuis_archive(source)
        run_migrations()
        _restaurer_trace_sauvegarde_securite(securite["chemin"])
        return {
            "succes": True,
            "message": "Import réussi. Redémarrage requis.",
            "necessite_redemarrage": True,
            "chemin_sauvegarde_securite": securite["chemin"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Erreur import base : %s", exc)
        return {
            "succes": False,
            "message": str(exc),
            "necessite_redemarrage": False,
            "chemin_sauvegarde_securite": securite["chemin"],
        }


def redemarrer_application() -> None:
    """Redémarre l'application courante."""
    os.execv(sys.executable, [sys.executable] + sys.argv)


def backup_db(db_path: Path, backup_dir: Path | None = None) -> Path:
    """Compatibilité ascendante : crée une copie .db de la base."""
    if not db_path.exists():
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    destination_dir = (backup_dir or db_path.parent).resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{db_path.stem}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}{db_path.suffix}"
    _copier_base_sqlite(db_path, destination)
    return destination


def restore_db(backup_path: Path, db_path: Path) -> None:
    """Compatibilité ascendante : restaure un fichier .db sur la base active."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Fichier de sauvegarde introuvable : {backup_path}")
    _copier_base_sqlite(backup_path, db_path)


def list_backups(db_path: Path, backup_dir: Path | None = None) -> list[Path]:
    """Compatibilité ascendante : liste les fichiers de sauvegarde sur disque."""
    search_dir = (backup_dir or db_path.parent).resolve()
    backups = list(search_dir.glob("*.db")) + list(search_dir.glob("*.zip"))
    return sorted(backups, reverse=True)


def _copier_base_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    with sqlite3.connect(source) as src_conn, sqlite3.connect(destination) as dst_conn:
        src_conn.backup(dst_conn)


def _creer_archive_sauvegarde(db_path: Path, destination: Path) -> None:
    _creer_archive_zip(
        db_path=db_path,
        destination=destination,
        nom_db_interne=f"{destination.stem}.db",
        inclure_config=get_parametre("sauvegarde_inclure_config", "1") == "1",
    )


def _creer_archive_export(db_path: Path, destination: Path) -> None:
    _creer_archive_zip(
        db_path=db_path,
        destination=destination,
        nom_db_interne=db_path.name,
        inclure_config=get_parametre("sauvegarde_inclure_config", "1") == "1",
    )


def _creer_archive_zip(
    db_path: Path,
    destination: Path,
    nom_db_interne: str,
    inclure_config: bool,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        snapshot_db = tmp_dir / nom_db_interne
        _copier_base_sqlite(db_path, snapshot_db)

        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_db, arcname=nom_db_interne)
            if inclure_config:
                _ajouter_config_au_zip(archive)


def _ajouter_config_au_zip(archive: zipfile.ZipFile) -> None:
    if not CONFIG_DIR.exists():
        return
    for path in CONFIG_DIR.rglob("*"):
        if path.is_file():
            archive.write(path, arcname=path.relative_to(APP_ROOT).as_posix())


def _restaurer_config_depuis_archive(archive_path: Path) -> None:
    base_dir = CONFIG_DIR.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for nom in archive.namelist():
            rel = PurePosixPath(nom)
            if not rel.parts or rel.parts[0] != "config" or nom.endswith("/"):
                continue
            if rel.is_absolute() or any(part == ".." for part in rel.parts):
                logger.warning("Entrée ZIP ignorée (chemin suspect) : %s", nom)
                continue
            destination = CONFIG_DIR.joinpath(*rel.parts[1:]).resolve()
            try:
                destination.relative_to(base_dir)
            except ValueError:
                logger.warning("Entrée ZIP ignorée (hors config/) : %s", nom)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(nom) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _remplacer_base_active(source_db: Path) -> None:
    db_active = get_chemin_db()
    temp_destination = db_active.parent / f"{db_active.name}.tmp"
    try:
        _copier_base_sqlite(source_db, temp_destination)
        _supprimer_fichiers_sqlite_associes(db_active)
        os.replace(temp_destination, db_active)
    finally:
        if temp_destination.exists():
            try:
                temp_destination.unlink()
            except OSError:
                logger.warning("Impossible de nettoyer le fichier temporaire : %s", temp_destination)


def _supprimer_fichiers_sqlite_associes(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError as exc:
                logger.warning("Impossible de supprimer %s : %s", sidecar, exc)


def _verifier_schema_compatible(chemin_db: Path) -> dict:
    conn = sqlite3.connect(f"file:{chemin_db}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

        if "config" not in tables and "_migrations" not in tables:
            return {
                "valide": False,
                "message": "Cette base ne correspond pas à l'application Gestion Interactifs Asso.",
            }

        if "_migrations" in tables:
            migrations_importees = {
                row[0] for row in conn.execute("SELECT nom FROM _migrations").fetchall()
            }
            migrations_locales = {path.name for path in MIGRATIONS_DIR.glob("*.sql")}
            inconnues = sorted(migrations_importees - migrations_locales)
            if inconnues:
                return {
                    "valide": False,
                    "message": (
                        "La base importée provient d'une version plus récente de l'application."
                    ),
                }

        return {"valide": True, "message": "Schéma compatible."}
    finally:
        conn.close()


@contextmanager
def _chemin_db_temporaire(source: Path):
    source = source.expanduser().resolve()
    if source.suffix.lower() != ".zip":
        yield source
        return

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(source) as archive:
            nom_db = next(
                (nom for nom in archive.namelist() if nom.lower().endswith(".db")),
                None,
            )
            if not nom_db:
                raise ValueError("Aucune base .db n'a été trouvée dans l'archive.")
            destination = tmp_dir / Path(nom_db).name
            with archive.open(nom_db) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)
        yield destination


def _est_fichier_sqlite(path: Path) -> bool:
    try:
        if not path.exists() or path.stat().st_size < len(SQLITE_HEADER):
            return False
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_HEADER)) == SQLITE_HEADER
    except OSError:
        return False


def _enregistrer_sauvegarde(
    nom_fichier: str,
    chemin_complet: str,
    taille_octets: int,
    type_sauvegarde: str,
    statut: str,
    message_erreur: str | None,
    created_at: str,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO sauvegardes (
                nom_fichier, chemin_complet, taille_octets, type_sauvegarde,
                statut, message_erreur, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nom_fichier,
                chemin_complet,
                taille_octets,
                type_sauvegarde,
                statut,
                message_erreur,
                created_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _tenter_enregistrement_erreur(destination: Path | None, type_sv: str, message: str) -> None:
    try:
        if not get_db_file():
            return
        _enregistrer_sauvegarde(
            nom_fichier=destination.name if destination else "",
            chemin_complet=str(destination) if destination else "",
            taille_octets=0,
            type_sauvegarde=type_sv,
            statut="erreur",
            message_erreur=message,
            created_at=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Impossible d'enregistrer l'erreur de sauvegarde : %s", exc)


def _restaurer_trace_sauvegarde_securite(chemin_sauvegarde: str) -> None:
    path = Path(chemin_sauvegarde)
    created_at = _now_iso()
    _enregistrer_sauvegarde(
        nom_fichier=path.name,
        chemin_complet=str(path),
        taille_octets=path.stat().st_size if path.exists() else 0,
        type_sauvegarde="avant_restauration",
        statut="ok",
        message_erreur=None,
        created_at=created_at,
    )
    set_parametre("derniere_sauvegarde", created_at)


def _get_param_int(cle: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(get_parametre(cle, str(default)).strip() or default)
        return max(value, minimum)
    except (TypeError, ValueError):
        return max(default, minimum)


def _compression_activee() -> bool:
    return get_parametre("sauvegarde_compression", "1") == "1"


def _parse_datetime(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None

    formats = (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y à %Hh%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _formater_datetime(value: str) -> str:
    dt = _parse_datetime(value)
    if not dt:
        return value or "—"
    return dt.strftime("%d/%m/%Y à %Hh%M")


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
