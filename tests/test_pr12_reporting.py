"""Tests PR12 : totaux événement, comptes du Bilan AG, schéma de référence."""

from __future__ import annotations

import pytest


@pytest.fixture
def db_fin(tmp_db):
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    db_module.set_db_file(str(tmp_db))
    run_migrations()
    yield db_module
    db_module.set_db_file("")


def test_bilan_ag_affiche_comptes_bancaires(db_fin):
    from core.bilan_ag import collecter_donnees_bilan

    conn = db_fin.get_connection()
    conn.execute("INSERT INTO comptes_bancaires (nom, solde_initial, actif) VALUES ('Compte Test PR12', 123.5, 1)")
    conn.commit()
    conn.close()
    tableau = collecter_donnees_bilan(1)["tableau_comptes"]
    assert "Compte Test PR12" in tableau
    assert "123,50" in tableau


def test_bilan_ag_erreur_distincte_de_aucune_donnee(db_fin, monkeypatch):
    import db.models.tresorerie as treso
    from core.bilan_ag import collecter_donnees_bilan

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(treso, "get_all_comptes", boom)
    tableau = collecter_donnees_bilan(1)["tableau_comptes"]
    assert "erreur" in tableau
    assert "Aucun compte" not in tableau


def test_totaux_evenement_liste_alignes_sur_fiche(db_fin):
    from core.caisses_evenement import calculer_bilan_complet_evenement
    from db.models.evenements import get_all_evenements

    conn = db_fin.get_connection()
    conn.execute("INSERT INTO evenements (id, nom, date_debut) VALUES (1, 'Fete', '2026-05-01')")
    conn.execute(
        "INSERT INTO evenement_stands (evenement_id, nom_stand, type_stand, montant_location, statut)"
        " VALUES (1, 'S1', 'location', 40, 'confirme')"
    )
    conn.commit()
    conn.close()
    bilan = calculer_bilan_complet_evenement(1)
    ev = [e for e in get_all_evenements() if e["id"] == 1][0]
    assert ev["total_recettes"] == bilan["total_recettes"] == 40.0
    assert ev["total_depenses"] == bilan["total_depenses"]


def test_dashboard_explicite_son_perimetre(db_fin):
    from db.models.dashboard import PERIMETRE_RECETTES_MENSUELLES, get_recettes_depenses_mois

    assert get_recettes_depenses_mois(2026, 5)["perimetre_recettes"] == PERIMETRE_RECETTES_MENSUELLES


def test_schema_reference_aligne_sur_migration(db_fin):
    from db.schema import TABLES

    conn = db_fin.get_connection()
    try:
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'tresorerie_operations'"
        ).fetchone()["sql"]
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert "rapproche" in sql
    assert any("rapproche" in c for c in TABLES["tresorerie_operations"])
    assert "comptes_bancaires" in TABLES and "comptes_bancaires" in tables
    assert "tresorerie_comptes" not in tables
