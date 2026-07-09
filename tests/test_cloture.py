"""Tests Phase 6b — Clôture d'exercice."""

from __future__ import annotations

import hashlib

import pytest

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.cloture import (
    add_exercice,
    cloturer_exercice,
    decloturer_exercice,
    get_all_exercices,
    get_exercice_by_id,
    get_log_exercice,
    get_stats_exercice,
    is_periode_cloturee,
)
from db.models.securite import (
    changer_mot_de_passe_decloture,
    hash_password,
    reset_mot_de_passe_via_master,
    verifier_code_master,
    verifier_mot_de_passe_decloture,
)
from db.models.tresorerie import (
    add_operation,
    get_all_categories,
    get_all_comptes,
    get_operation_by_id,
)
from core.cloture import (
    calculer_solde_cloture,
    generer_nom_exercice,
    verifier_chevauchement,
    valider_cloture,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _setup(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()


def _compte_principal_id() -> int:
    comptes = get_all_comptes()
    return int(next(c for c in comptes if int(c.get("est_principal") or 0) == 1)["id"])


def _categorie_recette_id() -> int:
    return int(get_all_categories("recette")[0]["id"])


def _categorie_depense_id() -> int:
    return int(get_all_categories("depense")[0]["id"])


def _add_op(compte_id, type_op, libelle, montant, date_op, cat_id, statut="valide"):
    return add_operation(
        compte_id, type_op, libelle, montant, date_op,
        cat_id, "especes", None, None, None, statut, 0, None, None, None,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_creation_exercice(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025-2026", "scolaire", "2025-09-01", "2026-08-31", 500.0, "Test")
    assert ex_id > 0
    ex = get_exercice_by_id(ex_id)
    assert ex is not None
    assert ex["nom"] == "2025-2026"
    assert ex["type_exercice"] == "scolaire"
    assert ex["statut"] == "ouvert"
    assert float(ex["solde_ouverture"]) == 500.0
    set_db_file("")


def test_cloture_exercice_calcul_solde(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()
    cat_d = _categorie_depense_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 200.0)
    _add_op(compte_id, "recette", "Recette A", 1000.0, "2025-03-15", cat_r)
    _add_op(compte_id, "depense", "Dépense B", 300.0, "2025-06-01", cat_d)

    solde = calculer_solde_cloture(ex_id)
    # solde_ouverture(200) + recettes(1000) - dépenses(300) = 900
    assert abs(solde - 900.0) < 0.01

    ok = cloturer_exercice(ex_id, solde)
    assert ok is True

    ex = get_exercice_by_id(ex_id)
    assert ex["statut"] == "cloture"
    assert abs(float(ex["solde_cloture"]) - 900.0) < 0.01
    assert ex["date_cloture"] is not None
    set_db_file("")


def test_operations_gelees_apres_cloture(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    op_id = _add_op(compte_id, "recette", "Op test", 500.0, "2025-05-01", cat_r)

    cloturer_exercice(ex_id, 500.0)

    op = get_operation_by_id(op_id)
    assert op is not None
    assert op["statut"] == "rapproche", f"Statut attendu 'rapproche', obtenu '{op['statut']}'"
    set_db_file("")


def test_operations_degelees_apres_decloture(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    op_id = _add_op(compte_id, "recette", "Op test", 500.0, "2025-05-01", cat_r)

    cloturer_exercice(ex_id, 500.0)
    op = get_operation_by_id(op_id)
    assert op["statut"] == "rapproche"

    decloturer_exercice(ex_id)
    op = get_operation_by_id(op_id)
    assert op is not None
    assert op["statut"] == "valide", f"Statut attendu 'valide', obtenu '{op['statut']}'"
    set_db_file("")


def test_decloture_mot_de_passe_correct(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)

    ok = decloturer_exercice(ex_id)
    assert ok is True
    ex = get_exercice_by_id(ex_id)
    assert ex["statut"] == "ouvert"
    set_db_file("")


def test_decloture_mot_de_passe_incorrect(tmp_db):
    _setup(tmp_db)
    # Le mot de passe par défaut est asso2024
    assert verifier_mot_de_passe_decloture("mauvais_mdp") is False
    assert verifier_mot_de_passe_decloture("asso2024") is True
    set_db_file("")


def test_decloture_code_master(tmp_db):
    _setup(tmp_db)
    assert verifier_code_master("INTERACTIFS-2024-MASTER") is True
    assert verifier_code_master("mauvais_code") is False
    set_db_file("")


def test_reset_mdp_via_code_master(tmp_db):
    _setup(tmp_db)
    # D'abord changer le mot de passe
    ok, _ = changer_mot_de_passe_decloture("asso2024", "nouveau_mdp")
    assert ok is True
    # Vérifier que le nouveau mot de passe fonctionne
    assert verifier_mot_de_passe_decloture("nouveau_mdp") is True
    # Reset via code master
    ok, msg = reset_mot_de_passe_via_master("INTERACTIFS-2024-MASTER")
    assert ok is True
    # Après reset, le mot de passe par défaut doit refonctionner
    assert verifier_mot_de_passe_decloture("asso2024") is True
    set_db_file("")


def test_changer_mot_de_passe(tmp_db):
    _setup(tmp_db)
    # Changement avec ancien mot de passe correct
    ok, msg = changer_mot_de_passe_decloture("asso2024", "nouveauMDP123")
    assert ok is True
    assert verifier_mot_de_passe_decloture("nouveauMDP123") is True

    # Changement avec mauvais ancien mot de passe
    ok, msg = changer_mot_de_passe_decloture("faux_mdp", "autremdp")
    assert ok is False
    assert msg

    # Changement avec code master à la place de l'ancien mot de passe
    ok, msg = changer_mot_de_passe_decloture("INTERACTIFS-2024-MASTER", "mdp_via_master")
    assert ok is True
    assert verifier_mot_de_passe_decloture("mdp_via_master") is True
    set_db_file("")


def test_is_periode_cloturee(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2024", "civile", "2024-01-01", "2024-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)

    assert is_periode_cloturee("2024-06-15") is True
    assert is_periode_cloturee("2025-01-01") is False
    set_db_file("")


def test_chevauchement_exercices(tmp_db):
    _setup(tmp_db)
    add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)

    # Chevauchement → doit retourner True
    assert verifier_chevauchement("2025-06-01", "2026-05-31", "civile") is True
    # Pas de chevauchement sur un autre type
    assert verifier_chevauchement("2025-06-01", "2026-05-31", "scolaire") is False
    # Période strictement après → pas de chevauchement
    assert verifier_chevauchement("2026-01-01", "2026-12-31", "civile") is False
    set_db_file("")


def test_log_cloture_decloture(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)
    decloturer_exercice(ex_id)

    logs = get_log_exercice(ex_id)
    assert len(logs) == 2
    actions = [log["action"] for log in logs]
    assert "cloture" in actions
    assert "decloture" in actions
    set_db_file("")


def test_stats_exercice(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()
    cat_d = _categorie_depense_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 100.0)
    _add_op(compte_id, "recette", "R1", 500.0, "2025-02-01", cat_r)
    _add_op(compte_id, "recette", "R2", 200.0, "2025-07-15", cat_r)
    _add_op(compte_id, "depense", "D1", 150.0, "2025-04-10", cat_d)

    stats = get_stats_exercice(ex_id)
    assert abs(stats["total_recettes"] - 700.0) < 0.01
    assert abs(stats["total_depenses"] - 150.0) < 0.01
    # solde_ouverture(100) + recettes(700) - dépenses(150) = 650
    assert abs(stats["solde_final"] - 650.0) < 0.01
    assert stats["nb_operations"] == 3
    set_db_file("")


def test_hash_password():
    """Le hash SHA-256 est correct."""
    expected = hashlib.sha256("asso2024".encode()).hexdigest()
    assert hash_password("asso2024") == expected


def test_generer_nom_exercice():
    assert generer_nom_exercice("scolaire", "2025-09-01") == "2025-2026"
    assert generer_nom_exercice("civile", "2025-01-01") == "2025"
    assert generer_nom_exercice("scolaire", "2024-09-01") == "2024-2025"
