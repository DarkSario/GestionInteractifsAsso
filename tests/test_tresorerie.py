"""Tests Trésorerie Phase 6a."""

from __future__ import annotations

from core.tresorerie import slug_reference_remise
from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.tresorerie import (
    accorder_subvention,
    add_cheque_detail,
    add_compte,
    add_operation,
    add_remise_cheque,
    add_subvention,
    add_virement_interne,
    annuler_operation,
    delete_categorie,
    finaliser_remise,
    get_all_categories,
    get_all_comptes,
    get_all_subventions,
    get_evolution_solde,
    get_operation_by_id,
    get_operations,
    get_remises,
    get_solde_compte,
    get_stats_tresorerie,
    set_compte_principal,
)


def _categorie_id(type_categorie: str) -> int:
    categories = get_all_categories(type_categorie)
    assert categories
    return int(categories[0]["id"])


def _compte_principal_id() -> int:
    comptes = get_all_comptes()
    principal = next(c for c in comptes if int(c.get("est_principal") or 0) == 1)
    return int(principal["id"])


def _compte_caisse_id() -> int:
    comptes = get_all_comptes(actif_only=False)
    caisse = next(c for c in comptes if int(c.get("est_caisse") or 0) == 1)
    return int(caisse["id"])

def test_creation_compte(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    compte_id = add_compte("Livret A", "livret", 1000, 0, 0, None, "Banque Test", 3)
    comptes = get_all_comptes(actif_only=False)

    assert compte_id > 0
    assert any(c["nom"] == "Livret A" for c in comptes)

    set_db_file("")


def test_solde_compte_calcule(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    compte_id = _compte_principal_id()
    cat_recette = _categorie_id("recette")
    cat_depense = _categorie_id("depense")

    add_operation(
        compte_id,
        "recette",
        "Recette test",
        150,
        "2026-06-01",
        cat_recette,
        "especes",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )
    add_operation(
        compte_id,
        "depense",
        "Dépense test",
        40,
        "2026-06-02",
        cat_depense,
        "carte",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )
    add_operation(
        compte_id,
        "depense",
        "Dépense annulée",
        20,
        "2026-06-03",
        cat_depense,
        "carte",
        None,
        None,
        None,
        "annule",
        0,
        None,
        None,
        None,
    )

    assert get_solde_compte(compte_id) == 110.0
    set_db_file("")


def test_set_compte_principal(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    nouveau = add_compte("Deuxième compte", "bancaire", 0, 0, 0, None, None, 5)
    assert set_compte_principal(nouveau) is True

    comptes = get_all_comptes(actif_only=False)
    principals = [c for c in comptes if int(c.get("est_principal") or 0) == 1]
    assert len(principals) == 1
    assert int(principals[0]["id"]) == nouveau

    set_db_file("")


def test_add_operation_recette(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    operation_id = add_operation(
        _compte_principal_id(),
        "recette",
        "Don",
        75,
        "2026-04-01",
        _categorie_id("recette"),
        "cheque",
        "F-001",
        None,
        None,
        "valide",
        0,
        None,
        None,
        "Test",
    )

    operation = get_operation_by_id(operation_id)
    assert operation is not None
    assert operation["type_operation"] == "recette"

    set_db_file("")


def test_add_operation_depense(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    operation_id = add_operation(
        _compte_principal_id(),
        "depense",
        "Achat",
        25,
        "2026-04-02",
        _categorie_id("depense"),
        "carte",
        "F-002",
        None,
        None,
        "valide",
        0,
        None,
        None,
        "Test",
    )

    operation = get_operation_by_id(operation_id)
    assert operation is not None
    assert operation["type_operation"] == "depense"

    set_db_file("")


def test_annuler_operation(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    op_id = add_operation(
        _compte_principal_id(),
        "depense",
        "Annulable",
        10,
        "2026-04-02",
        _categorie_id("depense"),
        "carte",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )
    assert annuler_operation(op_id) is True
    assert get_operation_by_id(op_id)["statut"] == "annule"

    set_db_file("")


def test_virement_interne(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    source = _compte_principal_id()
    destination = _compte_caisse_id()
    sortie_id, entree_id = add_virement_interne(
        source,
        destination,
        50,
        "2026-04-03",
        "Transfert caisse",
        None,
    )

    assert sortie_id > 0
    assert entree_id > 0
    assert get_operation_by_id(sortie_id)["type_operation"] == "virement_interne"
    assert get_operation_by_id(entree_id)["type_operation"] == "virement_interne"
    assert get_solde_compte(source) == -50.0
    assert get_solde_compte(destination) == 50.0

    set_db_file("")


def test_remise_cheque_workflow(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    remise_id = add_remise_cheque(_compte_principal_id(), "2026-04-10", "REM-001", "Kermesse")
    add_cheque_detail(remise_id, "Dupont", 20, None, None)
    add_cheque_detail(remise_id, "Martin", 30, None, None)

    assert finaliser_remise(remise_id) is True

    remise = get_remises()[0]
    assert remise["statut"] == "remis"
    assert remise["montant_total"] == 50.0

    operations = get_operations(statut="valide")
    remise_ops = [op for op in operations if op.get("source_module") == "remise_cheque"]
    assert len(remise_ops) == 1
    assert remise_ops[0]["montant"] == 50.0

    set_db_file("")


def test_subvention_accordee_cree_recette(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    subvention_id = add_subvention(
        "Mairie",
        "mairie",
        2026,
        "Projet kermesse",
        500,
        "2026-01-10",
        None,
    )
    compte_id = _compte_principal_id()

    assert accorder_subvention(
        subvention_id,
        400,
        "2026-03-01",
        "2026-03-10",
        compte_id,
    ) is True

    subvention = get_all_subventions(statut="accordee")[0]
    assert subvention["montant_obtenu"] == 400.0
    assert subvention["operation_id"] is not None

    op = get_operation_by_id(int(subvention["operation_id"]))
    assert op is not None
    assert op["type_operation"] == "recette"
    assert op["est_automatique"] == 1

    set_db_file("")


def test_categories_predefinies_non_supprimables(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    categorie_systeme = next(c for c in get_all_categories() if int(c.get("est_systeme") or 0) == 1)
    assert delete_categorie(int(categorie_systeme["id"])) is False

    set_db_file("")


def test_stats_tresorerie(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    compte_id = _compte_principal_id()
    cat_recette = _categorie_id("recette")
    cat_depense = _categorie_id("depense")

    add_operation(
        compte_id,
        "recette",
        "R1",
        200,
        "2026-01-01",
        cat_recette,
        "especes",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )
    add_operation(
        compte_id,
        "depense",
        "D1",
        80,
        "2026-01-02",
        cat_depense,
        "carte",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )

    stats = get_stats_tresorerie(compte_id=compte_id)
    assert stats["total_recettes"] == 200.0
    assert stats["total_depenses"] == 80.0
    assert stats["solde"] == 120.0

    set_db_file("")


def test_get_evolution_solde(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    compte_id = _compte_principal_id()
    cat_recette = _categorie_id("recette")

    add_operation(
        compte_id,
        "recette",
        "R récent",
        90,
        "2026-06-01",
        cat_recette,
        "especes",
        None,
        None,
        None,
        "valide",
        0,
        None,
        None,
        None,
    )

    evolution = get_evolution_solde(compte_id, nb_mois=3)
    assert len(evolution) == 3
    assert all("mois" in item and "solde_fin_mois" in item for item in evolution)

    set_db_file("")


def test_slug_reference_remise():
    slug = slug_reference_remise("2026-06-15", "Compte courant")
    assert slug == "Remise_Compteco_2026-06-15"
