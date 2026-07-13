"""Tests Phase 16 : cotisations, alertes, bilan AG template."""

from __future__ import annotations

from pathlib import Path

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db_cotisations(tmp_db: Path):
    """Base de données avec migrations complètes pour les tests cotisations."""
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    db_module.set_db_file(str(tmp_db))
    run_migrations()
    conn = db_module.get_connection()
    # Créer deux membres de test
    conn.execute(
        """
        INSERT INTO membres (nom, prenom, statut, date_adhesion, statut_archive)
        VALUES ('Dupont', 'Alice', 'Actif', '2024-09-01', 0),
               ('Martin', 'Bob', 'Bénévole', '2023-09-01', 0),
               ('Archive', 'Carl', 'Inactif', '2022-09-01', 1)
        """
    )
    conn.commit()
    yield conn
    conn.close()
    db_module.set_db_file("")


# ── Tests modèle cotisations ──────────────────────────────────────────────────


def test_add_cotisation_offerte(db_cotisations):
    """Ajouter une cotisation à 0 € force le statut 'offerte'."""
    from db.models.cotisations import add_cotisation, get_cotisations_adherent

    adherent_id = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    new_id = add_cotisation(adherent_id=adherent_id, annee=2026, montant=0.0, statut="en_attente")
    assert new_id > 0

    cotisations = get_cotisations_adherent(adherent_id)
    assert len(cotisations) == 1
    # Statut doit être forcé à 'offerte' car montant = 0
    assert cotisations[0]["statut"] == "offerte"


def test_add_cotisation_payee(db_cotisations):
    """Ajouter une cotisation payée."""
    from db.models.cotisations import add_cotisation, get_cotisations_adherent

    adherent_id = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Martin'"
    ).fetchone()["id"]

    new_id = add_cotisation(
        adherent_id=adherent_id,
        annee=2026,
        montant=15.0,
        statut="payee",
        date_paiement="2026-01-15",
        mode_paiement="espèces",
    )
    assert new_id > 0

    cotisations = get_cotisations_adherent(adherent_id)
    assert len(cotisations) == 1
    assert cotisations[0]["statut"] == "payee"
    assert cotisations[0]["montant"] == 15.0
    assert cotisations[0]["date_paiement"] == "2026-01-15"


def test_update_cotisation(db_cotisations):
    """Modifier une cotisation existante."""
    from db.models.cotisations import add_cotisation, get_cotisation_by_id, update_cotisation

    adherent_id = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    cot_id = add_cotisation(adherent_id=adherent_id, annee=2026, montant=10.0, statut="en_attente")
    ok = update_cotisation(cot_id, statut="payee", date_paiement="2026-02-01")
    assert ok is True

    cot = get_cotisation_by_id(cot_id)
    assert cot["statut"] == "payee"
    assert cot["date_paiement"] == "2026-02-01"


def test_update_cotisation_montant_zero_force_offerte(db_cotisations):
    """Mettre le montant à 0 lors d'une mise à jour force le statut offerte."""
    from db.models.cotisations import add_cotisation, get_cotisation_by_id, update_cotisation

    adherent_id = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    cot_id = add_cotisation(adherent_id=adherent_id, annee=2026, montant=15.0, statut="payee")
    update_cotisation(cot_id, montant=0.0)
    cot = get_cotisation_by_id(cot_id)
    assert cot["statut"] == "offerte"


def test_delete_cotisation(db_cotisations):
    """Supprimer une cotisation."""
    from db.models.cotisations import add_cotisation, delete_cotisation, get_cotisation_by_id

    adherent_id = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    cot_id = add_cotisation(adherent_id=adherent_id, annee=2026, montant=0.0)
    ok = delete_cotisation(cot_id)
    assert ok is True
    assert get_cotisation_by_id(cot_id) is None


def test_get_cotisations_exercice(db_cotisations):
    """Lister les cotisations d'une année."""
    from db.models.cotisations import add_cotisation, get_cotisations_exercice

    ids = [
        db_cotisations.execute(
            "SELECT id FROM membres WHERE nom = ?",(nom,)
        ).fetchone()["id"]
        for nom in ("Dupont", "Martin")
    ]
    for adh_id in ids:
        add_cotisation(adherent_id=adh_id, annee=2026, montant=0.0)

    cotisations = get_cotisations_exercice(2026)
    assert len(cotisations) == 2


def test_get_stats_cotisations(db_cotisations):
    """Statistiques des cotisations."""
    from db.models.cotisations import add_cotisation, get_stats_cotisations

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]
    id_bob = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Martin'"
    ).fetchone()["id"]

    add_cotisation(adherent_id=id_alice, annee=2026, montant=0.0, statut="offerte")
    add_cotisation(adherent_id=id_bob, annee=2026, montant=15.0, statut="payee")

    stats = get_stats_cotisations(2026)
    assert stats["total"] == 2
    assert stats["nb_offertes"] == 1
    assert stats["nb_payees"] == 1
    assert stats["montant_paye"] == 15.0


def test_renouveler_cotisations_masse(db_cotisations):
    """Renouvellement en masse pour les adhérents actifs."""
    from db.models.cotisations import renouveler_cotisations_masse, get_cotisations_exercice

    # Seuls les 2 membres non archivés doivent être créés
    nb = renouveler_cotisations_masse(annee=2026, montant=0.0, statut="offerte")
    assert nb == 2

    cotisations = get_cotisations_exercice(2026)
    assert len(cotisations) == 2

    # Un deuxième appel ne doit pas créer de doublons
    nb2 = renouveler_cotisations_masse(annee=2026, montant=0.0)
    assert nb2 == 0


def test_get_nb_cotisations_en_attente(db_cotisations):
    """Compter les cotisations en attente."""
    from db.models.cotisations import add_cotisation, get_nb_cotisations_en_attente

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]
    id_bob = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Martin'"
    ).fetchone()["id"]

    add_cotisation(adherent_id=id_alice, annee=2026, montant=10.0, statut="en_attente")
    add_cotisation(adherent_id=id_bob, annee=2026, montant=0.0, statut="offerte")

    assert get_nb_cotisations_en_attente(2026) == 1


# ── Tests core cotisations ────────────────────────────────────────────────────


def test_cotisation_est_a_jour_sans_cotisation(db_cotisations):
    """Un adhérent sans cotisation est considéré à jour."""
    from core.cotisations import cotisation_est_a_jour

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    assert cotisation_est_a_jour(id_alice, 2026) is True


def test_cotisation_est_a_jour_offerte(db_cotisations):
    """Une cotisation offerte est à jour."""
    from db.models.cotisations import add_cotisation
    from core.cotisations import cotisation_est_a_jour

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    add_cotisation(adherent_id=id_alice, annee=2026, montant=0.0, statut="offerte")
    assert cotisation_est_a_jour(id_alice, 2026) is True


def test_cotisation_est_a_jour_en_attente(db_cotisations):
    """Une cotisation en attente n'est pas à jour."""
    from db.models.cotisations import add_cotisation
    from core.cotisations import cotisation_est_a_jour

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    add_cotisation(adherent_id=id_alice, annee=2026, montant=15.0, statut="en_attente")
    assert cotisation_est_a_jour(id_alice, 2026) is False


def test_get_montant_cotisation_defaut(db_cotisations):
    """Le montant par défaut est 0.0 si non configuré."""
    from core.cotisations import get_montant_cotisation_defaut

    assert get_montant_cotisation_defaut() == 0.0


def test_set_montant_cotisation_defaut(db_cotisations):
    """Enregistrer et relire le montant par défaut."""
    from core.cotisations import get_montant_cotisation_defaut, set_montant_cotisation_defaut

    set_montant_cotisation_defaut(12.50)
    assert get_montant_cotisation_defaut() == 12.50


# ── Tests core alertes ────────────────────────────────────────────────────────


def test_get_alertes_retourne_liste(db_cotisations):
    """get_alertes() retourne toujours une liste."""
    from core.alertes import get_alertes

    alertes = get_alertes()
    assert isinstance(alertes, list)
    for a in alertes:
        assert "niveau" in a
        assert "message" in a


def test_alertes_cotisations_en_attente(db_cotisations):
    """Une cotisation en attente génère une alerte orange."""
    from db.models.cotisations import add_cotisation
    from core.cotisations import get_alertes_cotisations
    from datetime import date

    id_alice = db_cotisations.execute(
        "SELECT id FROM membres WHERE nom = 'Dupont'"
    ).fetchone()["id"]

    add_cotisation(adherent_id=id_alice, annee=date.today().year, montant=10.0, statut="en_attente")
    alertes = get_alertes_cotisations()
    assert len(alertes) == 1
    assert alertes[0]["niveau"] == "orange"


# ── Tests core bilan AG ───────────────────────────────────────────────────────


def test_get_template_bilan_retourne_contenu():
    """get_template_bilan() retourne le contenu du template."""
    from core.bilan_ag import get_template_bilan

    contenu = get_template_bilan()
    assert "{{exercice}}" in contenu
    assert "{{nom_asso}}" in contenu


def test_save_and_reload_template(tmp_path):
    """Sauvegarder et recharger un template modifié."""
    from core.bilan_ag import get_template_bilan, save_template_bilan, reset_template_bilan
    from pathlib import Path
    import core.bilan_ag as bilan_module

    # Sauvegarder les chemins originaux
    original_path = bilan_module._TEMPLATE_PATH
    test_path = tmp_path / "bilan_ag_template.md"
    bilan_module._TEMPLATE_PATH = test_path

    try:
        test_content = "# Test\n{{exercice}}\n{{nom_asso}}\n"
        save_template_bilan(test_content)
        rechargé = get_template_bilan()
        assert rechargé == test_content
    finally:
        bilan_module._TEMPLATE_PATH = original_path


def test_reset_template_bilan(tmp_path):
    """Restaurer le template par défaut."""
    import shutil
    import core.bilan_ag as bilan_module

    original_path = bilan_module._TEMPLATE_PATH
    original_default = bilan_module._TEMPLATE_DEFAULT_PATH
    test_path = tmp_path / "bilan_ag_template.md"
    test_default = tmp_path / "bilan_ag_template.default.md"

    # Créer un fichier de défaut pour le test
    default_content = "# Défaut\n{{exercice}}\n"
    test_default.write_text(default_content, encoding="utf-8")
    test_path.write_text("# Modifié\n", encoding="utf-8")

    bilan_module._TEMPLATE_PATH = test_path
    bilan_module._TEMPLATE_DEFAULT_PATH = test_default

    try:
        from core.bilan_ag import reset_template_bilan, get_template_bilan

        reset_template_bilan()
        rechargé = get_template_bilan()
        assert rechargé == default_content
    finally:
        bilan_module._TEMPLATE_PATH = original_path
        bilan_module._TEMPLATE_DEFAULT_PATH = original_default


def test_collecter_donnees_bilan_structure(db_cotisations):
    """collecter_donnees_bilan retourne les clés attendues."""
    from core.bilan_ag import collecter_donnees_bilan, VARIABLES_DISPONIBLES

    # On utilise exercice_id=999 (inexistant) - doit fonctionner sans crash
    donnees = collecter_donnees_bilan(999, "Intro test", "Conclusion test")

    assert isinstance(donnees, dict)
    # Vérifier que toutes les variables du template sont présentes
    for nom, _ in VARIABLES_DISPONIBLES:
        assert nom in donnees, f"Variable manquante : {nom}"

    assert donnees["introduction"] == "Intro test"
    assert donnees["conclusion"] == "Conclusion test"


def test_variables_disponibles_format():
    """VARIABLES_DISPONIBLES contient des tuples (nom, description)."""
    from core.bilan_ag import VARIABLES_DISPONIBLES

    assert len(VARIABLES_DISPONIBLES) > 0
    for item in VARIABLES_DISPONIBLES:
        assert len(item) == 2
        nom, desc = item
        assert isinstance(nom, str)
        assert isinstance(desc, str)
        assert len(nom) > 0
        assert len(desc) > 0
