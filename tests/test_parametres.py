"""Tests — Phase 7 : Paramètres globaux."""

from __future__ import annotations

import pytest

from db.connection import set_db_file
from db.migrations.runner import run_migrations


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def db_parametres(tmp_db):
    """Base de données temporaire avec toutes les migrations appliquées."""
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


# ── Tests paramètres génériques ───────────────────────────────────────────────


def test_get_set_parametre(db_parametres):
    from db.models.parametres_globaux import get_parametre, set_parametre

    # Clé existante (seed migration 0010)
    assert get_parametre("sauvegarde_auto") == "0"

    # Ecriture et relecture
    assert set_parametre("sauvegarde_auto", "1") is True
    assert get_parametre("sauvegarde_auto") == "1"

    # Clé inexistante → valeur par défaut
    assert get_parametre("cle_inexistante", "defaut") == "defaut"
    assert get_parametre("cle_inexistante") == ""


def test_get_all_parametres(db_parametres):
    from db.models.parametres_globaux import get_all_parametres

    params = get_all_parametres()
    assert isinstance(params, dict)
    assert "sauvegarde_auto" in params
    assert "theme_mode" in params


# ── Tests classes scolaires ───────────────────────────────────────────────────


def test_seed_classes_par_defaut(db_parametres):
    from db.models.parametres_globaux import get_all_classes

    classes = get_all_classes()
    noms = [c["nom"] for c in classes]
    for nom_attendu in ("PS", "MS", "GS", "CP", "CE1", "CM1", "CM2"):
        assert nom_attendu in noms, f"Classe '{nom_attendu}' absente du seed"


def test_classes_scolaires_crud(db_parametres):
    from db.models.parametres_globaux import (
        add_classe,
        delete_classe,
        get_all_classes,
        toggle_classe,
        update_classe,
    )

    # Ajout
    new_id = add_classe("TEST", 99)
    assert new_id > 0

    # Vérification présence
    classes = get_all_classes()
    noms = [c["nom"] for c in classes]
    assert "TEST" in noms

    # Modification
    ok = update_classe(new_id, "TEST2", 88)
    assert ok is True
    classes = get_all_classes()
    noms = [c["nom"] for c in classes]
    assert "TEST2" in noms
    assert "TEST" not in noms

    # Toggle actif
    classe = next(c for c in classes if c["nom"] == "TEST2")
    assert classe["actif"] == 1
    toggle_classe(new_id)
    classes = get_all_classes()
    classe = next(c for c in classes if c["nom"] == "TEST2")
    assert classe["actif"] == 0

    # Suppression
    ok = delete_classe(new_id)
    assert ok is True
    classes = get_all_classes()
    noms = [c["nom"] for c in classes]
    assert "TEST2" not in noms


def test_classe_non_supprimable_si_utilisee(db_parametres):
    """Une classe référencée dans evenement_paiements ne doit pas être supprimable."""
    from db.connection import get_connection
    from db.models.parametres_globaux import add_classe, delete_classe

    new_id = add_classe("CLASSE_UTILISEE", 50)
    assert new_id > 0

    # Simuler une utilisation dans evenement_paiements
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO evenements (nom, type, date_debut, statut)
            VALUES ('Evt test', 'Kermesse', '2026-01-01', 'planifie')
            """
        )
        evt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute(
            """
            INSERT INTO evenement_paiements (evenement_id, classe, montant)
            VALUES (?, 'CLASSE_UTILISEE', 10.0)
            """,
            (evt_id,),
        )
        conn.commit()
    finally:
        conn.close()

    ok = delete_classe(new_id)
    assert ok is False, "La classe utilisée dans evenement_paiements ne devrait pas être supprimable"


def test_get_all_classes_actif_only(db_parametres):
    from db.models.parametres_globaux import add_classe, get_all_classes, toggle_classe

    new_id = add_classe("INACTIVE", 99)
    toggle_classe(new_id)  # désactive la classe

    all_classes = get_all_classes(actif_only=False)
    actives = get_all_classes(actif_only=True)

    noms_all = [c["nom"] for c in all_classes]
    noms_actives = [c["nom"] for c in actives]
    assert "INACTIVE" in noms_all
    assert "INACTIVE" not in noms_actives


# ── Tests types d'événements ──────────────────────────────────────────────────


def test_seed_types_evenements_par_defaut(db_parametres):
    from db.models.parametres_globaux import get_all_types_evenements

    types = get_all_types_evenements()
    noms = [t["nom"] for t in types]
    for nom_attendu in ("Kermesse", "Spectacle", "Sortie scolaire", "Vente", "Repas", "Autre"):
        assert nom_attendu in noms, f"Type '{nom_attendu}' absent du seed"


def test_types_evenements_crud(db_parametres):
    from db.models.parametres_globaux import (
        add_type_evenement,
        delete_type_evenement,
        get_all_types_evenements,
        toggle_type_evenement,
        update_type_evenement,
    )

    # Ajout
    new_id = add_type_evenement("Concours", 10)
    assert new_id > 0

    types = get_all_types_evenements()
    noms = [t["nom"] for t in types]
    assert "Concours" in noms

    # Modification
    ok = update_type_evenement(new_id, "Concours modifié", 11)
    assert ok is True
    types = get_all_types_evenements()
    noms = [t["nom"] for t in types]
    assert "Concours modifié" in noms

    # Toggle
    tp = next(t for t in types if t["nom"] == "Concours modifié")
    assert tp["actif"] == 1
    toggle_type_evenement(new_id)
    types = get_all_types_evenements()
    tp = next(t for t in types if t["nom"] == "Concours modifié")
    assert tp["actif"] == 0

    # Suppression
    ok = delete_type_evenement(new_id)
    assert ok is True
    types = get_all_types_evenements()
    noms = [t["nom"] for t in types]
    assert "Concours modifié" not in noms


# ── Tests modes de paiement ───────────────────────────────────────────────────


def test_modes_paiement_seed(db_parametres):
    from db.models.parametres_globaux import get_all_modes_paiement

    modes = get_all_modes_paiement()
    codes = [m["code"] for m in modes]
    for code in ("especes", "cheque", "carte", "sumup", "virement", "prelevement"):
        assert code in codes, f"Mode '{code}' absent du seed"


def test_modes_paiement_toggle(db_parametres):
    from db.models.parametres_globaux import get_all_modes_paiement, toggle_mode_paiement

    modes = get_all_modes_paiement()
    assert len(modes) >= 2  # besoin d'au moins 2 pour désactiver l'un

    premier = modes[0]
    ok = toggle_mode_paiement(premier["id"])
    assert ok is True

    modes_apres = get_all_modes_paiement()
    mode_apres = next(m for m in modes_apres if m["id"] == premier["id"])
    assert mode_apres["actif"] != premier["actif"]


def test_mode_paiement_impossible_desactiver_dernier(db_parametres):
    """Ne pas pouvoir désactiver le dernier mode de paiement actif."""
    from db.connection import get_connection
    from db.models.parametres_globaux import toggle_mode_paiement

    # Désactiver tous les modes sauf un
    conn = get_connection()
    try:
        conn.execute("UPDATE modes_paiement SET actif = 0")
        conn.execute("UPDATE modes_paiement SET actif = 1 WHERE code = 'especes'")
        conn.commit()
        mode_id = conn.execute(
            "SELECT id FROM modes_paiement WHERE code = 'especes'"
        ).fetchone()["id"]
    finally:
        conn.close()

    # Tenter de désactiver le dernier mode actif
    ok = toggle_mode_paiement(mode_id)
    assert ok is False, "Ne devrait pas pouvoir désactiver le dernier mode actif"


# ── Tests couche métier core/parametres.py ────────────────────────────────────


def test_get_infos_asso(db_parametres):
    from core.parametres import get_infos_asso

    infos = get_infos_asso()
    assert isinstance(infos, dict)
    assert "nom" in infos
    assert "adresse" in infos
    assert "telephone" in infos
    assert "email" in infos
    assert "logo_path" in infos


def test_set_infos_asso_validation(db_parametres):
    from core.parametres import get_infos_asso, set_infos_asso

    # Nom vide → erreur
    erreurs = set_infos_asso("", "", "", "", "")
    assert len(erreurs) > 0

    # Nom valide → succès
    erreurs = set_infos_asso(
        "Les Interactifs des Écoles",
        "12 rue de l'École",
        "0123456789",
        "contact@interactifs.fr",
        "",
    )
    assert erreurs == []

    infos = get_infos_asso()
    assert infos["nom"] == "Les Interactifs des Écoles"
    assert infos["email"] == "contact@interactifs.fr"


def test_get_config_financiere(db_parametres):
    from core.parametres import get_config_financiere, set_config_financiere

    config = get_config_financiere()
    assert "taux_sumup" in config
    assert "compte_principal_id" in config
    assert "compte_caisse_id" in config

    ok = set_config_financiere(taux_sumup="2.5", compte_principal_id="1")
    assert ok is True

    config = get_config_financiere()
    assert config["taux_sumup"] == "2.5"
    assert config["compte_principal_id"] == "1"


def test_config_systeme(db_parametres):
    from core.parametres import get_config_systeme, set_config_systeme

    config = get_config_systeme()
    assert "sauvegarde_auto" in config
    assert "sauvegarde_frequence" in config

    ok = set_config_systeme(sauvegarde_auto="1", sauvegarde_frequence="14")
    assert ok is True

    config = get_config_systeme()
    assert config["sauvegarde_auto"] == "1"
    assert config["sauvegarde_frequence"] == "14"


def test_valider_nom_liste(db_parametres):
    from core.parametres import valider_nom_liste

    # Valide
    assert valider_nom_liste("CE1") == []
    assert valider_nom_liste("Kermesse d'été") == []
    assert valider_nom_liste("Sortie scolaire") == []

    # Invalide : vide
    erreurs = valider_nom_liste("")
    assert len(erreurs) > 0

    # Invalide : trop long
    erreurs = valider_nom_liste("A" * 101)
    assert len(erreurs) > 0
