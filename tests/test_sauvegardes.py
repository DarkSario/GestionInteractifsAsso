"""Tests de la Phase 10 — Sauvegardes & import/export base."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.parametres_globaux import get_parametre, set_parametre


@pytest.fixture
def backup_env(tmp_path: Path, tmp_db: Path, monkeypatch):
    """Prépare un environnement isolé pour les sauvegardes."""
    import utils.backup as backup

    app_root = tmp_path / "app"
    config_dir = app_root / "config"
    fonts_dir = config_dir / "fonts"
    fonts_dir.mkdir(parents=True)
    (config_dir / "theme.json").write_text('{"appearance_mode": "dark"}', encoding="utf-8")
    (fonts_dir / "demo.ttf").write_bytes(b"fake-font")

    set_db_file(str(tmp_db))
    run_migrations()

    monkeypatch.setattr(backup, "APP_ROOT", app_root)
    monkeypatch.setattr(backup, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(backup, "DEFAULT_BACKUP_DIR", app_root / "data" / "sauvegardes")

    yield backup
    set_db_file("")


def _set_nom_asso(valeur: str) -> None:
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS total FROM config").fetchone()["total"]
        if total:
            conn.execute("UPDATE config SET nom_asso = ?", (valeur,))
        else:
            conn.execute("INSERT INTO config (nom_asso) VALUES (?)", (valeur,))
        conn.commit()
    finally:
        conn.close()


def _get_nom_asso() -> str:
    conn = get_connection()
    try:
        row = conn.execute("SELECT nom_asso FROM config LIMIT 1").fetchone()
        return row["nom_asso"] if row else ""
    finally:
        conn.close()


def _patch_noms(monkeypatch, backup_module, noms: list[str]) -> None:
    sequence = iter(noms)
    monkeypatch.setattr(
        backup_module,
        "generer_nom_sauvegarde",
        lambda type_sv="manuelle": next(sequence),
    )


def test_generer_nom_sauvegarde(backup_env):
    set_parametre("sauvegarde_compression", "0")
    nom = backup_env.generer_nom_sauvegarde()
    assert re.fullmatch(r"asso_interactifs_\d{8}_\d{6}_manuelle\.db", nom)


def test_sauvegarder_maintenant_manuelle(backup_env):
    dossier = backup_env.APP_ROOT / "sauvegardes"
    set_parametre("sauvegarde_dossier", str(dossier))
    set_parametre("sauvegarde_compression", "0")

    resultat = backup_env.sauvegarder_maintenant("manuelle")

    assert resultat["succes"] is True
    assert Path(resultat["chemin"]).exists()
    assert resultat["nom_fichier"].endswith(".db")
    assert get_parametre("derniere_sauvegarde") != ""
    historique = backup_env.get_liste_sauvegardes()
    assert historique[0]["type_code"] == "manuelle"


def test_sauvegarder_maintenant_automatique(backup_env):
    dossier = backup_env.APP_ROOT / "sauvegardes_auto"
    set_parametre("sauvegarde_dossier", str(dossier))
    set_parametre("sauvegarde_compression", "1")

    resultat = backup_env.sauvegarder_maintenant("automatique")

    assert resultat["succes"] is True
    archive = Path(resultat["chemin"])
    assert archive.exists()
    assert archive.suffix == ".zip"
    historique = backup_env.get_liste_sauvegardes()
    assert historique[0]["type_code"] == "automatique"


def test_verifier_integrite_base_valide(backup_env, tmp_db: Path):
    resultat = backup_env.verifier_integrite_base(str(tmp_db))
    assert resultat["valide"] is True
    assert resultat["message"] == "Base valide"


def test_verifier_integrite_base_corrompue(backup_env, tmp_path: Path):
    fichier = tmp_path / "corrompue.db"
    fichier.write_text("pas une base sqlite", encoding="utf-8")

    resultat = backup_env.verifier_integrite_base(str(fichier))

    assert resultat["valide"] is False


def test_restaurer_sauvegarde(backup_env):
    set_parametre("sauvegarde_compression", "0")
    _set_nom_asso("Version A")
    resultat_backup = backup_env.sauvegarder_maintenant("manuelle")
    _set_nom_asso("Version B")

    resultat = backup_env.restaurer_sauvegarde(resultat_backup["chemin"])

    assert resultat["succes"] is True
    assert _get_nom_asso() == "Version A"


def test_restauration_cree_sauvegarde_securite(backup_env):
    set_parametre("sauvegarde_compression", "0")
    _set_nom_asso("Avant restauration")
    resultat_backup = backup_env.sauvegarder_maintenant("manuelle")
    _set_nom_asso("Après sauvegarde")

    resultat = backup_env.restaurer_sauvegarde(resultat_backup["chemin"])

    assert resultat["succes"] is True
    assert Path(resultat["chemin_sauvegarde_securite"]).exists()
    assert any(
        item["type_code"] == "avant_restauration"
        for item in backup_env.get_liste_sauvegardes()
    )


def test_get_liste_sauvegardes(backup_env, monkeypatch):
    set_parametre("sauvegarde_compression", "0")
    _patch_noms(
        monkeypatch,
        backup_env,
        [
            "asso_interactifs_20260709_143022_manuelle.db",
            "asso_interactifs_20260710_143022_automatique.db",
        ],
    )

    backup_env.sauvegarder_maintenant("manuelle")
    backup_env.sauvegarder_maintenant("automatique")

    historique = backup_env.get_liste_sauvegardes()

    assert len(historique) == 2
    assert historique[0]["nom_fichier"] == "asso_interactifs_20260710_143022_automatique.db"
    assert {"id", "nom_fichier", "chemin", "taille_formatee", "type", "statut", "date_formatee"}.issubset(
        historique[0]
    )


def test_supprimer_sauvegarde(backup_env):
    set_parametre("sauvegarde_compression", "0")
    resultat = backup_env.sauvegarder_maintenant("manuelle")
    sauvegarde = backup_env.get_liste_sauvegardes()[0]

    ok = backup_env.supprimer_sauvegarde(int(sauvegarde["id"]))

    assert ok is True
    assert not Path(resultat["chemin"]).exists()
    historique = backup_env.get_liste_sauvegardes()
    assert historique[0]["statut"] == "supprimee"


def test_rotation_sauvegardes(backup_env, monkeypatch):
    set_parametre("sauvegarde_compression", "0")
    set_parametre("sauvegarde_rotation_max", "2")
    _patch_noms(
        monkeypatch,
        backup_env,
        [
            "asso_interactifs_20260709_100000_manuelle.db",
            "asso_interactifs_20260709_110000_manuelle.db",
            "asso_interactifs_20260709_120000_manuelle.db",
        ],
    )

    backup_env.sauvegarder_maintenant("manuelle")
    backup_env.sauvegarder_maintenant("manuelle")
    backup_env.sauvegarder_maintenant("manuelle")

    actives = [item for item in backup_env.get_liste_sauvegardes() if item["statut"] != "supprimee"]
    supprimees = [item for item in backup_env.get_liste_sauvegardes() if item["statut"] == "supprimee"]

    assert len(actives) == 2
    assert len(supprimees) == 1


def test_formater_taille(backup_env):
    assert backup_env.formater_taille(345) == "345 octets"
    assert backup_env.formater_taille(2048) == "2 Ko"
    assert backup_env.formater_taille(1258291) == "1,2 Mo"


def test_exporter_base_db(backup_env, tmp_path: Path):
    destination = tmp_path / "export.db"

    resultat = backup_env.exporter_base_complete(str(destination))

    assert resultat["succes"] is True
    assert destination.exists()
    assert destination.read_bytes().startswith(b"SQLite format 3")


def test_exporter_base_zip(backup_env, tmp_path: Path):
    destination = tmp_path / "export.zip"
    set_parametre("sauvegarde_inclure_config", "1")

    resultat = backup_env.exporter_base_complete(str(destination))

    assert resultat["succes"] is True
    with zipfile.ZipFile(destination) as archive:
        noms = archive.namelist()
    assert any(nom.endswith(".db") for nom in noms)
    assert "config/theme.json" in noms
    assert "config/fonts/demo.ttf" in noms


def test_importer_base_valide(backup_env, tmp_path: Path):
    source = tmp_path / "source.db"
    _set_nom_asso("Base importée")
    backup_env.exporter_base_complete(str(source))
    _set_nom_asso("Base courante")

    resultat = backup_env.importer_base(str(source))

    assert resultat["succes"] is True
    assert resultat["necessite_redemarrage"] is True
    assert _get_nom_asso() == "Base importée"


def test_importer_base_invalide(backup_env, tmp_path: Path):
    source = tmp_path / "source.db"
    source.write_text("fichier invalide", encoding="utf-8")

    resultat = backup_env.importer_base(str(source))

    assert resultat["succes"] is False


def test_verifier_sauvegarde_auto_declenchee(backup_env):
    dossier = backup_env.APP_ROOT / "auto"
    set_parametre("sauvegarde_dossier", str(dossier))
    set_parametre("sauvegarde_auto", "1")
    set_parametre("sauvegarde_frequence", "7")
    set_parametre("derniere_sauvegarde", "2020-01-01T00:00:00")

    ok = backup_env.verifier_sauvegarde_auto()

    assert ok is True
    assert any(item["type_code"] == "automatique" for item in backup_env.get_liste_sauvegardes())


def test_verifier_sauvegarde_auto_non_declenchee(backup_env):
    set_parametre("sauvegarde_auto", "1")
    set_parametre("sauvegarde_frequence", "7")
    set_parametre("derniere_sauvegarde", backup_env._now_iso())

    ok = backup_env.verifier_sauvegarde_auto()

    assert ok is False
    assert backup_env.get_liste_sauvegardes() == []
