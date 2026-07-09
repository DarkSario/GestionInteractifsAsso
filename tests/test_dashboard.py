"""Tests pour le tableau de bord — Phase 8."""

from __future__ import annotations

from datetime import date

import pytest

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.dashboard import (
    get_alertes_stock,
    get_bilan_dernier_evenement,
    get_cheques_en_attente,
    get_comparatif_mois,
    get_evenement_en_cours,
    get_evolution_tresorerie,
    get_info_derniere_sauvegarde,
    get_prochains_evenements,
    get_recettes_depenses_mois,
    get_solde_global,
    get_stats_adherents_dashboard,
    get_stats_subventions_dashboard,
    get_toutes_alertes,
)
from core.dashboard import (
    calculer_progression_subventions,
    formater_variation,
    get_donnees_dashboard,
    get_resume_mois_courant,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def db_vide(tmp_db):
    """Prépare une base vide avec toutes les migrations."""
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


# ── Tests couche données ──────────────────────────────────────────────────────


def test_get_solde_global():
    result = get_solde_global()
    assert "solde_total" in result
    assert "solde_bancaire" in result
    assert "solde_caisse" in result
    assert "par_compte" in result
    assert isinstance(result["par_compte"], list)
    assert isinstance(result["solde_total"], float)


def test_get_recettes_depenses_mois():
    result = get_recettes_depenses_mois(2026, 6)
    assert "total_recettes" in result
    assert "total_depenses" in result
    assert "solde_net" in result
    assert result["total_recettes"] >= 0
    assert result["total_depenses"] >= 0
    assert result["solde_net"] == round(
        result["total_recettes"] - result["total_depenses"], 2
    )


def test_get_comparatif_mois():
    result = get_comparatif_mois(2026, 6)
    assert "mois_actuel" in result
    assert "mois_precedent" in result
    assert "variation_recettes_pct" in result
    assert "variation_depenses_pct" in result
    assert "recettes" in result["mois_actuel"]
    assert "depenses" in result["mois_actuel"]


def test_get_evolution_tresorerie():
    result = get_evolution_tresorerie(12)
    assert isinstance(result, list)
    assert len(result) == 12
    for item in result:
        assert "mois_label" in item
        assert "solde_fin_mois" in item
        assert isinstance(item["solde_fin_mois"], float)


def test_get_evolution_tresorerie_nb_mois_reduit():
    result = get_evolution_tresorerie(3)
    assert len(result) == 3


def test_get_top_categories_depenses():
    from db.models.dashboard import get_top_categories_depenses
    result = get_top_categories_depenses(2026, 6, top_n=3)
    assert isinstance(result, list)
    assert len(result) <= 3


def test_get_cheques_en_attente():
    result = get_cheques_en_attente()
    assert "nb_remises" in result
    assert "montant_total" in result
    assert "details" in result
    assert result["nb_remises"] == 0
    assert isinstance(result["details"], list)


def test_get_stats_subventions_dashboard():
    result = get_stats_subventions_dashboard()
    assert "montant_demande" in result
    assert "montant_obtenu" in result
    assert "nb_en_attente" in result
    assert "progression_pct" in result
    assert 0.0 <= result["progression_pct"] <= 100.0


def test_get_prochains_evenements():
    result = get_prochains_evenements(3)
    assert isinstance(result, list)
    assert len(result) <= 3


def test_get_evenement_en_cours():
    result = get_evenement_en_cours()
    # Base vide — aucun événement
    assert result is None


def test_get_bilan_dernier_evenement():
    result = get_bilan_dernier_evenement()
    # Base vide — aucun événement terminé
    assert result is None


def test_get_stats_adherents_dashboard():
    result = get_stats_adherents_dashboard()
    assert "nb_total" in result
    assert "nb_actifs" in result
    assert "nb_cotisation_non_reglee" in result
    assert "montant_cotisations_dues" in result
    assert "nb_nouveaux_ce_mois" in result
    assert result["nb_total"] == 0
    assert result["nb_actifs"] == 0


def test_get_alertes_stock():
    result = get_alertes_stock()
    assert "critique" in result
    assert "faible" in result
    assert isinstance(result["critique"], list)
    assert isinstance(result["faible"], list)


def test_get_toutes_alertes_vide():
    """Sur une base vide, les alertes liées aux données doivent être absentes."""
    alertes = get_toutes_alertes()
    assert isinstance(alertes, list)
    # Pas de stock, donc pas d'alertes critique/faible
    niveaux = {a["niveau"] for a in alertes}
    assert niveaux.issubset({"rouge", "orange", "bleu"})


def test_get_toutes_alertes_avec_donnees(tmp_db):
    """Injecte des données et vérifie la génération d'alertes."""
    from db.connection import get_connection

    conn = get_connection()
    try:
        # Ajouter un article en rupture de stock
        conn.execute(
            """
            INSERT INTO stock (nom, quantite, seuil_alerte, statut_archive)
            VALUES ('Gobelets', 0, 10, 0)
            """
        )
        # Ajouter un article en stock faible
        conn.execute(
            """
            INSERT INTO stock (nom, quantite, seuil_alerte, statut_archive)
            VALUES ('Sodas', 3, 10, 0)
            """
        )
        conn.commit()
    finally:
        conn.close()

    alertes = get_toutes_alertes()
    assert isinstance(alertes, list)
    niveaux = {a["niveau"] for a in alertes}
    # Au moins une alerte rouge (rupture stock)
    assert "rouge" in niveaux
    # Au moins une alerte orange (stock faible)
    assert "orange" in niveaux


def test_get_info_derniere_sauvegarde():
    result = get_info_derniere_sauvegarde()
    assert "date" in result
    assert "nb_jours_depuis" in result
    assert "chemin" in result


# ── Tests couche métier ───────────────────────────────────────────────────────


def test_get_donnees_dashboard_complet():
    result = get_donnees_dashboard()
    cles_attendues = [
        "periode", "solde_global", "recettes_depenses", "comparatif",
        "evolution", "cheques", "subventions", "prochains_evenements",
        "evenement_en_cours", "bilan_dernier_evenement", "nb_benevoles",
        "adherents", "stock", "alertes", "derniere_sauvegarde",
    ]
    for cle in cles_attendues:
        assert cle in result, f"Clé manquante dans get_donnees_dashboard : {cle}"


def test_formater_variation_hausse():
    result = formater_variation(120.0, 100.0)
    assert result["sens"] == "hausse"
    assert result["variation_pct"] == 20.0
    assert result["couleur"] == "green"


def test_formater_variation_baisse():
    result = formater_variation(80.0, 100.0)
    assert result["sens"] == "baisse"
    assert result["variation_pct"] == 20.0
    assert result["couleur"] == "red"


def test_formater_variation_stable():
    result = formater_variation(100.0, 100.0)
    assert result["sens"] == "stable"
    assert result["variation_pct"] == 0.0


def test_formater_variation_precedent_zero():
    result = formater_variation(50.0, 0.0)
    assert result["sens"] == "stable"
    assert result["variation_pct"] == 0.0


def test_calculer_progression_subventions():
    assert calculer_progression_subventions(1000.0, 400.0) == 40.0
    assert calculer_progression_subventions(0.0, 0.0) == 0.0
    assert calculer_progression_subventions(100.0, 150.0) == 100.0  # plafonné à 100


def test_get_resume_mois_courant():
    result = get_resume_mois_courant()
    today = date.today()
    assert str(today.year) in result
    # Vérifier que c'est une chaîne non vide
    assert len(result) > 4
