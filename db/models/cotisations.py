"""CRUD pour la table cotisations (Phase 16)."""

from __future__ import annotations

from datetime import date

from db.connection import get_connection
from db.models import _build_nom_complet
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_nom_membre(adherent_id: int) -> str:
    """Retourne 'Prenom Nom' d'un adhérent."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT nom, prenom FROM membres WHERE id = ?", (adherent_id,)
        ).fetchone()
        if row:
            return _build_nom_complet(row['prenom'], row['nom'], defaut=f"Adhérent #{adherent_id}")
        return f"Adhérent #{adherent_id}"
    except Exception:
        return f"Adhérent #{adherent_id}"
    finally:
        conn.close()


def _sync_operation_tresorerie(conn, cotisation_id: int, adherent_id: int, annee: int,
                                montant: float, statut: str,
                                date_paiement: str | None, mode_paiement: str | None) -> None:
    """Crée, met à jour ou annule l'opération trésorerie liée à une cotisation.

    Utilise la connexion fournie sans commit : la cotisation et son écriture sont
    enregistrées dans la même transaction. Toute erreur est propagée à l'appelant.

    - statut='payee' et montant>0 : crée ou met à jour l'opération en 'valide'
    - statut='offerte' ou 'en_attente' : annule l'opération si elle existe
    """
    from db.models.tresorerie import (
        annuler_operations_auto,
        get_categorie_id_par_mot,
        upsert_operation_auto,
    )

    if statut == "payee" and float(montant or 0) > 0:
        upsert_operation_auto(
            conn,
            "cotisation",
            cotisation_id,
            type_operation="recette",
            libelle=f"Cotisation {annee} — {_get_nom_membre(adherent_id)}",
            montant=float(montant),
            date_operation=date_paiement or date.today().isoformat(),
            categorie_id=get_categorie_id_par_mot(conn, "recette", "cotisation"),
            mode_paiement=mode_paiement or "autre",
            commentaire=f"Cotisation automatique exercice {annee}",
        )
    else:
        annuler_operations_auto(conn, "cotisation", cotisation_id)


# ── Lecture ───────────────────────────────────────────────────────────────────


def get_cotisations_adherent(adherent_id: int) -> list[dict]:
    """Retourne toutes les cotisations d'un adhérent, triées par année décroissante."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.adherent_id, c.exercice_id, c.annee, c.montant,
                   c.statut, c.date_paiement, c.mode_paiement, c.commentaire,
                   c.created_at, c.updated_at
            FROM cotisations c
            WHERE c.adherent_id = ?
            ORDER BY c.annee DESC
            """,
            (adherent_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.exception("get_cotisations_adherent(%s): %s", adherent_id, exc)
        return []
    finally:
        conn.close()


def get_cotisations_exercice(annee: int) -> list[dict]:
    """Retourne toutes les cotisations pour une année donnée."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.adherent_id, c.annee, c.montant, c.statut,
                   c.date_paiement, c.mode_paiement, c.commentaire,
                   m.nom, m.prenom
            FROM cotisations c
            JOIN membres m ON m.id = c.adherent_id
            WHERE c.annee = ?
            ORDER BY m.nom, m.prenom
            """,
            (annee,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.exception("get_cotisations_exercice(%s): %s", annee, exc)
        return []
    finally:
        conn.close()


def get_cotisation_by_id(cotisation_id: int) -> dict | None:
    """Retourne une cotisation par son identifiant."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM cotisations WHERE id = ?",
            (cotisation_id,),
        ).fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.exception("get_cotisation_by_id(%s): %s", cotisation_id, exc)
        return None
    finally:
        conn.close()


# ── Écriture ──────────────────────────────────────────────────────────────────


def add_cotisation(
    adherent_id: int,
    annee: int,
    montant: float = 0.0,
    statut: str = "offerte",
    exercice_id: int | None = None,
    date_paiement: str | None = None,
    mode_paiement: str | None = None,
    commentaire: str | None = None,
) -> int:
    """Ajoute une cotisation et retourne son identifiant.

    Si le montant est 0, le statut est automatiquement forcé à 'offerte'.
    """
    if montant == 0.0:
        statut = "offerte"

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO cotisations
                (adherent_id, exercice_id, annee, montant, statut,
                 date_paiement, mode_paiement, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adherent_id,
                exercice_id,
                annee,
                montant,
                statut,
                date_paiement,
                mode_paiement,
                commentaire,
            ),
        )
        cotisation_id = cursor.lastrowid or 0
        if cotisation_id:
            _sync_operation_tresorerie(
                conn, cotisation_id, adherent_id, annee, montant, statut,
                date_paiement, mode_paiement,
            )
        conn.commit()
        return cotisation_id
    except Exception as exc:
        logger.exception("add_cotisation: %s", exc)
        conn.rollback()
        return 0
    finally:
        conn.close()


def update_cotisation(cotisation_id: int, **kwargs) -> bool:
    """Modifie une cotisation existante.

    Clés acceptées : annee, montant, statut, exercice_id,
    date_paiement, mode_paiement, commentaire.
    """
    cles_autorisees = {
        "annee", "montant", "statut", "exercice_id",
        "date_paiement", "mode_paiement", "commentaire",
    }
    params = {k: v for k, v in kwargs.items() if k in cles_autorisees}
    if not params:
        return False

    # Si montant est mis à 0, forcer statut offerte
    if "montant" in params and params["montant"] == 0.0:
        params["statut"] = "offerte"

    params["updated_at"] = date.today().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in params)
    values = list(params.values()) + [cotisation_id]

    conn = get_connection()
    try:
        cur = conn.execute(
            f"UPDATE cotisations SET {set_clause} WHERE id = ?",
            values,
        )
        row = conn.execute(
            "SELECT adherent_id, annee, montant, statut, date_paiement, mode_paiement "
            "FROM cotisations WHERE id = ?",
            (cotisation_id,),
        ).fetchone()
        if row:
            _sync_operation_tresorerie(
                conn,
                cotisation_id,
                int(row["adherent_id"] or 0),
                int(row["annee"] or date.today().year),
                float(row["montant"] or 0),
                row["statut"] or "en_attente",
                row["date_paiement"],
                row["mode_paiement"],
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.exception("update_cotisation(%s): %s", cotisation_id, exc)
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_cotisation(cotisation_id: int) -> bool:
    """Supprime une cotisation."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cotisations WHERE id = ?", (cotisation_id,))
        conn.execute(
            "UPDATE tresorerie_operations SET statut = 'annule' "
            "WHERE source_module = 'cotisation' AND source_id = ? AND statut != 'annule'",
            (cotisation_id,),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.exception("delete_cotisation(%s): %s", cotisation_id, exc)
        conn.rollback()
        return False
    finally:
        conn.close()


# ── Opérations de masse ───────────────────────────────────────────────────────


def renouveler_cotisations_masse(
    annee: int,
    montant: float = 0.0,
    statut: str = "offerte",
    exercice_id: int | None = None,
) -> int:
    """Crée une cotisation pour tous les adhérents actifs qui n'en ont pas encore pour l'année.

    Returns:
        Nombre de cotisations créées.
    """
    if montant == 0.0:
        statut = "offerte"

    conn = get_connection()
    try:
        # Adhérents actifs sans cotisation pour cette année
        rows = conn.execute(
            """
            SELECT m.id
            FROM membres m
            WHERE m.statut_archive = 0
              AND m.id NOT IN (
                  SELECT adherent_id FROM cotisations WHERE annee = ?
              )
            """,
            (annee,),
        ).fetchall()

        nb_crees = 0
        for row in rows:
            cur = conn.execute(
                """
                INSERT INTO cotisations
                    (adherent_id, exercice_id, annee, montant, statut)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["id"], exercice_id, annee, montant, statut),
            )
            _sync_operation_tresorerie(
                conn, cur.lastrowid, row["id"], annee, montant, statut, None, None,
            )
            nb_crees += 1

        conn.commit()
        return nb_crees
    except Exception as exc:
        logger.exception("renouveler_cotisations_masse(%s): %s", annee, exc)
        conn.rollback()
        return 0
    finally:
        conn.close()


# ── Statistiques ──────────────────────────────────────────────────────────────


def get_stats_cotisations(annee: int) -> dict:
    """Retourne les statistiques des cotisations pour une année.

    Returns:
        {total, nb_payees, nb_offertes, nb_en_attente,
         montant_total, montant_paye}
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT statut, COUNT(*) as nb, COALESCE(SUM(montant), 0) as montant
            FROM cotisations
            WHERE annee = ?
            GROUP BY statut
            """,
            (annee,),
        ).fetchall()

        stats: dict = {
            "total": 0,
            "nb_payees": 0,
            "nb_offertes": 0,
            "nb_en_attente": 0,
            "montant_total": 0.0,
            "montant_paye": 0.0,
        }
        for row in rows:
            stats["total"] += row["nb"]
            stats["montant_total"] += row["montant"]
            if row["statut"] == "payee":
                stats["nb_payees"] = row["nb"]
                stats["montant_paye"] = row["montant"]
            elif row["statut"] == "offerte":
                stats["nb_offertes"] = row["nb"]
            elif row["statut"] == "en_attente":
                stats["nb_en_attente"] = row["nb"]

        return stats
    except Exception as exc:
        logger.exception("get_stats_cotisations(%s): %s", annee, exc)
        return {
            "total": 0, "nb_payees": 0, "nb_offertes": 0,
            "nb_en_attente": 0, "montant_total": 0.0, "montant_paye": 0.0,
        }
    finally:
        conn.close()


def get_nb_cotisations_en_attente(annee: int) -> int:
    """Retourne le nombre d'adhérents avec une cotisation en attente pour l'année."""
    conn = get_connection()
    try:
        result = conn.execute(
            "SELECT COUNT(*) FROM cotisations WHERE annee = ? AND statut = 'en_attente'",
            (annee,),
        ).fetchone()
        return int(result[0]) if result else 0
    except Exception as exc:
        logger.exception("get_nb_cotisations_en_attente: %s", exc)
        return 0
    finally:
        conn.close()
