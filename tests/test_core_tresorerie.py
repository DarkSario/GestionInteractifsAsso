"""Tests du module Trésorerie (Phase 6)."""

from __future__ import annotations

import pytest

from core.tresorerie import (
    calculer_bilan,
    valider_depense,
    valider_don,
    valider_mouvement_banque,
    valider_retrocession,
)
from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.tresorerie import (
    add_depot_retrait,
    add_depense_diverse,
    add_depense_reguliere,
    add_don,
    add_retrocession,
    delete_depot_retrait,
    delete_depense_diverse,
    delete_depense_reguliere,
    delete_don,
    get_all_depenses_diverses,
    get_all_depenses_regulieres,
    get_all_depots_retraits,
    get_all_dons,
    get_all_retrocessions,
    get_journal_general,
    update_don,
    update_depense_reguliere,
    update_depot_retrait,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


# ── Validation métier ─────────────────────────────────────────────────────────


def test_valider_don_valide():
    erreurs = valider_don("2026-01-15", "Mairie", "500")
    assert erreurs == []


def test_valider_don_date_manquante():
    erreurs = valider_don("", "Mairie", "500")
    assert any("date" in e.lower() for e in erreurs)


def test_valider_don_source_manquante():
    erreurs = valider_don("2026-01-15", "", "500")
    assert any("source" in e.lower() for e in erreurs)


def test_valider_don_montant_invalide():
    erreurs = valider_don("2026-01-15", "Mairie", "abc")
    assert any("montant" in e.lower() for e in erreurs)


def test_valider_don_montant_nul():
    erreurs = valider_don("2026-01-15", "Mairie", "0")
    assert any("montant" in e.lower() for e in erreurs)


def test_valider_depense_valide():
    erreurs = valider_depense("2026-02-10", "Achats matériel", "120.50")
    assert erreurs == []


def test_valider_depense_categorie_manquante():
    erreurs = valider_depense("2026-02-10", "", "120")
    assert any("catégorie" in e.lower() for e in erreurs)


def test_valider_depense_montant_negatif():
    erreurs = valider_depense("2026-02-10", "Divers", "-10")
    assert any("montant" in e.lower() for e in erreurs)


def test_valider_mouvement_banque_valide():
    erreurs = valider_mouvement_banque("2026-03-01", "dépôt", "1000")
    assert erreurs == []


def test_valider_mouvement_banque_type_invalide():
    erreurs = valider_mouvement_banque("2026-03-01", "virement", "1000")
    assert any("type" in e.lower() for e in erreurs)


def test_valider_retrocession_valide():
    erreurs = valider_retrocession("2026-04-01", "École Pasteur", "300")
    assert erreurs == []


def test_valider_retrocession_ecole_manquante():
    erreurs = valider_retrocession("2026-04-01", "", "300")
    assert any("école" in e.lower() for e in erreurs)


# ── CRUD dons ─────────────────────────────────────────────────────────────────


def test_add_don_retourne_id():
    don_id = add_don("2026-01-15", "Mairie", 500.0, "subvention", None, None)
    assert don_id > 0


def test_get_all_dons_retourne_liste():
    add_don("2026-01-15", "Mairie", 500.0, "subvention", None, None)
    add_don("2026-02-01", "Sponsor ABC", 200.0, "don", None, None)
    dons = get_all_dons()
    assert len(dons) == 2


def test_update_don():
    don_id = add_don("2026-01-15", "Mairie", 500.0, "subvention", None, None)
    ok = update_don(don_id, "2026-01-20", "Mairie (MAJ)", 600.0, "subvention", None, "modifié")
    assert ok
    dons = get_all_dons()
    assert dons[0]["montant"] == 600.0
    assert dons[0]["source"] == "Mairie (MAJ)"


def test_delete_don():
    don_id = add_don("2026-01-15", "Mairie", 500.0, "subvention", None, None)
    ok = delete_don(don_id)
    assert ok
    assert get_all_dons() == []


def test_filtre_exercice_dons():
    add_don("2025-12-01", "Ancien exercice", 100.0, "don", None, None)
    add_don("2026-03-15", "Exercice courant", 200.0, "don", None, None)
    dons_2026 = get_all_dons(exercice="2026")
    assert len(dons_2026) == 1
    assert dons_2026[0]["source"] == "Exercice courant"


# ── CRUD dépenses régulières ──────────────────────────────────────────────────


def test_add_depense_reguliere_retourne_id():
    dep_id = add_depense_reguliere(
        "2026-02-10", "Achats matériel", 120.0,
        "Fournisseur X", "chèque", "000123", "F-001", "réglé", None
    )
    assert dep_id > 0


def test_get_all_depenses_regulieres():
    add_depense_reguliere("2026-02-10", "Achats matériel", 120.0, None, None, None, None, "non réglé", None)
    add_depense_reguliere("2026-03-01", "Communication / impression", 45.0, None, None, None, None, "réglé", None)
    deps = get_all_depenses_regulieres()
    assert len(deps) == 2


def test_update_depense_reguliere():
    dep_id = add_depense_reguliere(
        "2026-02-10", "Divers", 100.0, None, None, None, None, "non réglé", None
    )
    ok = update_depense_reguliere(
        dep_id, "2026-02-15", "Divers", 150.0, None, None, None, None, "réglé", None
    )
    assert ok
    deps = get_all_depenses_regulieres()
    assert deps[0]["montant"] == 150.0


def test_delete_depense_reguliere():
    dep_id = add_depense_reguliere(
        "2026-02-10", "Divers", 100.0, None, None, None, None, "non réglé", None
    )
    ok = delete_depense_reguliere(dep_id)
    assert ok
    assert get_all_depenses_regulieres() == []


# ── CRUD dépenses diverses ────────────────────────────────────────────────────


def test_add_depense_diverse_retourne_id():
    dep_id = add_depense_diverse(
        "2026-04-05", "Locations", 80.0, None, "espèces", None, None, "réglé", None
    )
    assert dep_id > 0


def test_get_all_depenses_diverses():
    add_depense_diverse("2026-04-05", "Locations", 80.0, None, None, None, None, "réglé", None)
    add_depense_diverse("2026-05-10", "Divers", 35.0, None, None, None, None, "non réglé", None)
    assert len(get_all_depenses_diverses()) == 2


def test_delete_depense_diverse():
    dep_id = add_depense_diverse("2026-04-05", "Divers", 50.0, None, None, None, None, "non réglé", None)
    ok = delete_depense_diverse(dep_id)
    assert ok
    assert get_all_depenses_diverses() == []


# ── CRUD dépôts/retraits ──────────────────────────────────────────────────────


def test_add_depot_retourne_id():
    mvt_id = add_depot_retrait("2026-06-01", "dépôt", 1500.0, "REF001", "CIC", 0, None)
    assert mvt_id > 0


def test_get_all_depots_retraits():
    add_depot_retrait("2026-06-01", "dépôt", 1500.0, None, None, 0, None)
    add_depot_retrait("2026-06-15", "retrait", 200.0, None, None, 1, None)
    mvts = get_all_depots_retraits()
    assert len(mvts) == 2


def test_update_depot_retrait():
    mvt_id = add_depot_retrait("2026-06-01", "dépôt", 1500.0, None, None, 0, None)
    ok = update_depot_retrait(mvt_id, "2026-06-02", "dépôt", 1600.0, "REF002", "CIC", 1, None)
    assert ok
    mvts = get_all_depots_retraits()
    assert mvts[0]["montant"] == 1600.0


def test_delete_depot_retrait():
    mvt_id = add_depot_retrait("2026-06-01", "dépôt", 1500.0, None, None, 0, None)
    ok = delete_depot_retrait(mvt_id)
    assert ok
    assert get_all_depots_retraits() == []


# ── CRUD rétrocessions ────────────────────────────────────────────────────────


def test_add_retrocession_retourne_id():
    r_id = add_retrocession("2026-07-01", "École Pasteur", 400.0, None)
    assert r_id > 0


def test_get_all_retrocessions():
    add_retrocession("2026-07-01", "École Pasteur", 400.0, None)
    add_retrocession("2026-07-15", "École Curie", 350.0, "solde")
    retros = get_all_retrocessions()
    assert len(retros) == 2


# ── Journal général ───────────────────────────────────────────────────────────


def test_journal_contient_toutes_operations():
    add_don("2026-01-10", "Mairie", 500.0, "subvention", None, None)
    add_depense_reguliere("2026-02-05", "Divers", 100.0, None, None, None, None, "réglé", None)
    add_depot_retrait("2026-03-01", "dépôt", 1000.0, None, None, 0, None)
    journal = get_journal_general()
    assert len(journal) == 3


def test_journal_filtre_exercice():
    add_don("2025-11-01", "Vieux don", 100.0, "don", None, None)
    add_don("2026-04-01", "Don récent", 200.0, "don", None, None)
    journal_2026 = get_journal_general(exercice="2026")
    assert len(journal_2026) == 1
    assert journal_2026[0]["libelle"] == "Don récent"


# ── Bilan ─────────────────────────────────────────────────────────────────────


def test_calculer_bilan_vide():
    bilan = calculer_bilan()
    assert bilan["total_recettes"] == 0.0
    assert bilan["total_depenses"] == 0.0
    assert bilan["solde_theorique"] == 0.0


def test_calculer_bilan_avec_donnees():
    add_don("2026-01-15", "Mairie", 500.0, "subvention", None, None)
    add_don("2026-02-01", "Sponsor", 200.0, "don", None, None)
    add_depense_reguliere("2026-03-01", "Divers", 150.0, None, None, None, None, "réglé", None)
    add_depense_diverse("2026-04-01", "Locations", 80.0, None, None, None, None, "réglé", None)
    add_retrocession("2026-05-01", "École Pasteur", 120.0, None)
    add_depot_retrait("2026-06-01", "dépôt", 1000.0, None, None, 0, None)
    add_depot_retrait("2026-06-15", "retrait", 200.0, None, None, 0, None)

    bilan = calculer_bilan("2026")
    assert bilan["total_dons"] == 700.0
    assert bilan["total_recettes"] == 700.0
    assert bilan["total_depenses_regulieres"] == 150.0
    assert bilan["total_depenses_diverses"] == 80.0
    assert bilan["total_retrocessions"] == 120.0
    assert bilan["total_depenses"] == 350.0
    assert bilan["solde_theorique"] == 350.0  # 0 + 700 - 350
    assert bilan["total_depots"] == 1000.0
    assert bilan["total_retraits"] == 200.0
    assert bilan["solde_banque"] == 800.0  # 0 + 1000 - 200
