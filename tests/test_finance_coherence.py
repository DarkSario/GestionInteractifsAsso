"""Tests PR7 : règles financières partagées et cohérence des totaux."""

from __future__ import annotations

import csv
from datetime import date

import pytest

from utils.finance_rules import (
    est_source_comptable,
    formater_montant_eur,
    montant_signe,
    sql_filtre_comptable,
    totaux_operations,
)


# ── Règles pures ──────────────────────────────────────────────────────────────


def test_regles_comptable_vs_tracabilite():
    assert est_source_comptable(None)
    assert est_source_comptable("cotisation")
    assert not est_source_comptable("remise_cheque")
    assert not est_source_comptable("depot_especes")
    assert sql_filtre_comptable("o").startswith("(o.source_module IS NULL")


def test_montant_signe_et_totaux():
    ops = [
        {"type_operation": "recette", "montant": 100, "statut": "valide"},
        {"type_operation": "depense", "montant": 30, "statut": "valide"},
        {"type_operation": "recette", "montant": 50, "statut": "annule"},
        {"type_operation": "recette", "montant": 70, "statut": "valide", "source_module": "remise_cheque"},
        {"type_operation": "recette", "montant": 20, "statut": "valide", "source_module": "depot_especes"},
    ]
    assert [montant_signe(o) for o in ops] == [100, -30, 0, 0, 0]
    assert totaux_operations(ops) == {"total_recettes": 100.0, "total_depenses": 30.0, "solde": 70.0}


def test_formater_montant_eur():
    assert formater_montant_eur(1234.5) == "1 234,50 EUR"
    assert formater_montant_eur(-3) == "-3,00 EUR"
    assert formater_montant_eur(0.999) == "1,00 EUR"
    assert formater_montant_eur("abc") == "—"


# ── Flux automatiques ─────────────────────────────────────────────────────────


@pytest.fixture
def db_fin(tmp_db):
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    db_module.set_db_file(str(tmp_db))
    run_migrations()
    conn = db_module.get_connection()
    conn.execute("INSERT INTO membres (nom, prenom, statut, statut_archive) VALUES ('Dupont', 'Alice', 'Actif', 0)")
    conn.commit()
    conn.close()
    yield db_module
    db_module.set_db_file("")


def _ops(source: str | None = None, source_id: int | None = None) -> list[dict]:
    from db.models.tresorerie import get_operations

    return [
        o for o in get_operations()
        if (source is None or o["source_module"] == source)
        and (source_id is None or o["source_id"] == source_id)
    ]


def _membre_id(db_fin) -> int:
    conn = db_fin.get_connection()
    try:
        return conn.execute("SELECT id FROM membres LIMIT 1").fetchone()["id"]
    finally:
        conn.close()


def test_cotisation_payee_offerte_en_attente(db_fin):
    from db.models.cotisations import add_cotisation, update_cotisation

    mid = _membre_id(db_fin)
    payee = add_cotisation(mid, 2026, 20.0, "payee", date_paiement="2026-01-10", mode_paiement="especes")
    offerte = add_cotisation(mid, 2027, 0.0, "offerte")
    attente = add_cotisation(mid, 2028, 20.0, "en_attente")

    assert len(_ops("cotisation", payee)) == 1
    assert _ops("cotisation", offerte) == []
    assert _ops("cotisation", attente) == []

    # Idempotence : ré-enregistrer ne duplique pas l'écriture
    update_cotisation(payee, montant=25.0)
    update_cotisation(payee, montant=25.0)
    ops = _ops("cotisation", payee)
    assert len(ops) == 1 and ops[0]["montant"] == 25.0 and ops[0]["statut"] == "valide"

    # Repassée en attente : écriture annulée, donc plus comptabilisée
    update_cotisation(payee, statut="en_attente")
    assert [o["statut"] for o in _ops("cotisation", payee)] == ["annule"]


def test_don_argent_une_seule_ecriture_meme_avec_creer_recette(db_fin):
    from core.dons import creer_recette_tresorerie
    from db.models.dons import add_don, get_don_by_id, update_don

    don_id = add_don(donateur_nom="Martin", donateur_prenom="Bob", nature_don="argent", montant=40.0,
                     date_don="2026-02-01", mode_versement="especes")
    creer_recette_tresorerie(don_id)
    creer_recette_tresorerie(don_id)
    update_don(don_id, montant=45.0)
    ops = _ops("don", don_id)
    assert len(ops) == 1 and ops[0]["montant"] == 45.0
    assert get_don_by_id(don_id)["tresorerie_id"] == ops[0]["id"]


def test_don_en_nature_sans_ecriture(db_fin):
    from db.models.dons import add_don

    don_id = add_don(donateur_nom="Martin", nature_don="nature", montant=0, valeur_estimee=50.0)
    assert _ops("don", don_id) == []


def test_remboursement_tombola_idempotent(db_fin):
    from db.models.remboursements import _creer_operation_remboursement_tombola

    lot = {"id": 7, "montant_avance": 12.0, "description": "Lot", "membre_nom": "A", "membre_prenom": "B"}
    _creer_operation_remboursement_tombola(lot, "especes", "2026-03-01")
    _creer_operation_remboursement_tombola(lot, "especes", "2026-03-01")
    assert len(_ops("tombola_remboursement", 7)) == 1


# ── Cohérence des totaux ──────────────────────────────────────────────────────


@pytest.fixture
def dataset(db_fin):
    """Recettes/dépenses comptables + remise de chèques + dépôt d'espèces (traçabilité)."""
    from db.models.tresorerie import add_operation, get_all_comptes

    conn = db_fin.get_connection()
    conn.execute(
        "INSERT INTO exercices (id, nom, date_debut, date_fin, statut) VALUES (900, 'Test', '2026-01-01', '2026-12-31', 'ouvert')"
    )
    conn.commit()
    conn.close()
    compte_id = get_all_comptes()[0]["id"]

    def op(type_op, montant, source, statut="valide"):
        oid = add_operation(
            compte_id=compte_id, type_operation=type_op, libelle=f"{type_op} {source}", montant=montant,
            date_operation="2026-05-10", categorie_id=None, mode_paiement="especes", numero_facture=None,
            evenement_id=None, fournisseur_id=None, statut=statut, est_automatique=0,
            source_module=source, source_id=None, commentaire=None,
        )
        return oid

    op("recette", 200.0, "manuel")
    op("depense", 50.0, "manuel")
    op("recette", 80.0, "remise_cheque")
    op("recette", 60.0, "depot_especes")
    return compte_id


def test_totaux_alignes_dashboard_bilan_exports(dataset):
    from core.bilan_ag import collecter_donnees_bilan
    from core.exports import montant_signe_operation
    from db.models.dashboard import get_recettes_depenses_mois
    from db.models.tresorerie import get_operations, get_solde_compte, get_stats_tresorerie

    stats = get_stats_tresorerie()
    assert (stats["total_recettes"], stats["total_depenses"], stats["solde"]) == (200.0, 50.0, 150.0)

    dash = get_recettes_depenses_mois(2026, 5)
    assert dash["total_recettes"] == 200.0 and dash["total_depenses"] == 50.0

    bilan = collecter_donnees_bilan(900)
    assert bilan["total_recettes"] == formater_montant_eur(200.0)
    assert bilan["total_depenses"] == formater_montant_eur(50.0)
    assert bilan["solde"] == formater_montant_eur(150.0)

    toutes = get_operations()
    assert round(sum(montant_signe_operation(o) for o in toutes), 2) == 150.0
    assert totaux_operations(toutes)["solde"] == stats["solde"]

    from db.models.tresorerie import get_compte_principal

    compte = get_compte_principal() or {"id": dataset}
    solde_initial = float(compte.get("solde_initial") or 0)
    assert get_solde_compte(dataset) == round(solde_initial + 150.0, 2)


def test_excel_dossier_subvention_exclut_tracabilite(dataset):
    from core.excel_dossier_subvention import ExcelDossierSubvention

    gen = ExcelDossierSubvention("2026")
    gen._date_debut, gen._date_fin = "2026-01-01", "2026-12-31"
    kpis = dict(gen._charger_kpis())
    assert kpis["Total recettes"] == 200.0
    assert kpis["Total dépenses"] == 50.0
    assert kpis["Solde"] == 150.0


def test_export_csv_exclut_tracabilite(dataset, tmp_path):
    pytest.importorskip("tkinter")
    from db.models.tresorerie import get_operations
    from ui.modules.exports.export_csv_tresorerie import _ecrire_csv

    toutes = get_operations()
    fichier = tmp_path / "t.csv"
    _ecrire_csv(toutes, str(fichier))
    with open(fichier, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.reader(f, delimiter=";"))[1:]
    assert len(lignes) == 2
