from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.budget_evenement import (
    get_bilan_annuel_buvette,
    get_bilan_reel,
    get_seuil_rentabilite,
    sauvegarder_budget,
)
from core.inventaire import (
    calculer_cout_buvette_evenement,
    creer_inventaire,
    get_lignes_inventaire,
    saisir_ligne_inventaire,
    valider_inventaire,
)
from core.stock_v2 import (
    add_lot,
    add_tag,
    archiver_lots_perimes,
    calculer_cout_fifo,
    consommer_stock_fifo,
    get_article_tags,
    get_articles_peremption_proche,
    get_articles_perimes,
    get_lots_fifo,
    get_stock_theorique,
    get_tags,
    set_article_tags,
)
from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import add_depense, add_evenement, add_tarif, add_vente, add_vente_ligne
from db.models.stock import add_article


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _create_article(nom: str = "Champagne") -> int:
    return add_article(
        nom=nom,
        categorie_id=None,
        unite_id=None,
        fournisseur_habituel_id=None,
        quantite=0,
        seuil_alerte=0,
        prix_achat=0.0,
        lot=None,
        commentaire=None,
    )


def _add_lot(
    article_id: int,
    quantite: int,
    prix_ttc: float,
    date_achat: str,
    date_peremption: str | None = None,
) -> int:
    return add_lot(
        article_id=article_id,
        quantite=quantite,
        prix_ht=round(prix_ttc / 1.2, 2),
        prix_ttc=prix_ttc,
        tva_taux=20,
        fournisseur_id=None,
        numero_facture=None,
        numero_lot=None,
        date_achat=date_achat,
        date_peremption=date_peremption,
        commentaire=None,
        tag_ids=[],
    )


def test_fifo_ordre_correct():
    article_id = _create_article()
    _add_lot(article_id, 2, 10.0, "2026-01-01")
    _add_lot(article_id, 2, 12.0, "2026-02-01")

    lots = get_lots_fifo(article_id)
    assert [l["date_achat"] for l in lots] == ["2026-01-01", "2026-02-01"]


def test_fifo_lot_multiple():
    article_id = _create_article()
    _add_lot(article_id, 1, 10.0, "2026-01-01")
    _add_lot(article_id, 1, 11.0, "2026-01-02")
    _add_lot(article_id, 1, 12.0, "2026-01-03")

    lots = get_lots_fifo(article_id)
    assert len(lots) == 3


def test_consommer_stock_fifo():
    article_id = _create_article()
    _add_lot(article_id, 2, 10.0, "2026-01-01")
    _add_lot(article_id, 4, 12.0, "2026-02-01")

    detail = consommer_stock_fifo(article_id, 3)
    assert detail[0]["qte_consommee"] == 2
    assert detail[1]["qte_consommee"] == 1


def test_calculer_cout_fifo():
    article_id = _create_article()
    _add_lot(article_id, 2, 10.0, "2026-01-01")
    _add_lot(article_id, 2, 12.0, "2026-02-01")

    assert calculer_cout_fifo(article_id, 3) == 32.0


def test_stock_theorique():
    article_id = _create_article()
    _add_lot(article_id, 2, 10.0, "2026-01-01")
    _add_lot(article_id, 4, 12.0, "2026-02-01")

    assert get_stock_theorique(article_id) == 6


def test_articles_peremption_proche():
    article_id = _create_article()
    proche = (date.today() + timedelta(days=5)).isoformat()
    _add_lot(article_id, 1, 10.0, date.today().isoformat(), proche)

    rows = get_articles_peremption_proche(10)
    assert any(r["article_id"] == article_id for r in rows)


def test_articles_perimes():
    article_id = _create_article()
    perime = (date.today() - timedelta(days=1)).isoformat()
    _add_lot(article_id, 1, 10.0, date.today().isoformat(), perime)

    rows = get_articles_perimes()
    assert any(r["article_id"] == article_id for r in rows)


def test_archiver_lots_perimes():
    article_id = _create_article()
    perime = (date.today() - timedelta(days=1)).isoformat()
    lot_id = _add_lot(article_id, 1, 10.0, date.today().isoformat(), perime)

    nb = archiver_lots_perimes()
    assert nb >= 1

    conn = get_connection()
    try:
        row = conn.execute("SELECT statut FROM stock_lots WHERE id = ?", (lot_id,)).fetchone()
    finally:
        conn.close()
    assert row["statut"] == "expire"


def test_creer_inventaire_prefilled():
    article_id = _create_article()
    _add_lot(article_id, 3, 10.0, "2026-01-01")
    inventaire_id = creer_inventaire(None, "ponctuel")

    lignes = get_lignes_inventaire(inventaire_id)
    assert len(lignes) == 1
    assert lignes[0]["qte_theorique"] == 3


def test_saisir_ligne_inventaire():
    article_id = _create_article()
    lot_id = _add_lot(article_id, 3, 10.0, "2026-01-01")
    inventaire_id = creer_inventaire(None, "ponctuel")

    saisir_ligne_inventaire(inventaire_id, article_id, lot_id, 2)
    lignes = get_lignes_inventaire(inventaire_id)
    assert lignes[0]["qte_reelle"] == 2


def test_valider_inventaire_maj_stock():
    article_id = _create_article()
    lot_id = _add_lot(article_id, 3, 10.0, "2026-01-01")
    inventaire_id = creer_inventaire(None, "ponctuel")

    saisir_ligne_inventaire(inventaire_id, article_id, lot_id, 1)
    result = valider_inventaire(inventaire_id)
    assert result["nb_lignes"] == 1
    assert get_stock_theorique(article_id) == 1


def test_calculer_cout_buvette_fifo():
    article_id = _create_article()
    lot_id = _add_lot(article_id, 10, 5.0, "2026-01-01")
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "termine", None)

    inv_avant = creer_inventaire(event_id, "avant_evenement")
    saisir_ligne_inventaire(inv_avant, article_id, lot_id, 10)
    valider_inventaire(inv_avant)

    inv_apres = creer_inventaire(event_id, "apres_evenement")
    saisir_ligne_inventaire(inv_apres, article_id, lot_id, 6)
    valider_inventaire(inv_apres)

    couts = calculer_cout_buvette_evenement(event_id)
    assert couts["cout_ttc"] == 20.0


def test_sauvegarder_budget():
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "planifie", None)
    assert sauvegarder_budget(event_id, 800, 500, 100, 100, 5)


def test_bilan_reel_vs_previsionnel():
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "termine", None)
    sauvegarder_budget(event_id, 800, 500, 100, 100, 5)
    add_depense(event_id, "Sono", 120, "2026-06-01", None, None, None, None)
    add_vente(event_id, "2026-06-01", "sur_place", "especes", None, 300, 0, 300, None)

    bilan = get_bilan_reel(event_id)
    assert bilan["recettes_reelles"] == 300.0
    assert bilan["depenses_reelles"] == 120.0


def test_seuil_rentabilite_calcul():
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "planifie", None)
    sauvegarder_budget(event_id, 0, 500, 100, 0, 5)

    seuil = get_seuil_rentabilite(event_id)
    assert seuil["seuil_prevu"] == 120


def test_seuil_rentabilite_atteint():
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "termine", None)
    sauvegarder_budget(event_id, 0, 200, 100, 0, 5)
    tarif_id = add_tarif(event_id, "Entrée", 5.0, 0, 0)
    vente_id = add_vente(event_id, "2026-06-01", "sur_place", "especes", None, 300, 0, 300, None)
    add_vente_ligne(vente_id, tarif_id, 60, 5.0)

    seuil = get_seuil_rentabilite(event_id)
    assert seuil["atteint"] is True


def test_seuil_rentabilite_non_atteint():
    event_id = add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "termine", None)
    sauvegarder_budget(event_id, 0, 200, 100, 0, 5)
    tarif_id = add_tarif(event_id, "Entrée", 5.0, 0, 0)
    vente_id = add_vente(event_id, "2026-06-01", "sur_place", "especes", None, 50, 0, 50, None)
    add_vente_ligne(vente_id, tarif_id, 10, 5.0)

    seuil = get_seuil_rentabilite(event_id)
    assert seuil["atteint"] is False
    assert seuil["manque"] > 0


def test_bilan_annuel_buvette():
    article_id = _create_article()
    buvette_tag = next((t for t in get_tags() if t["nom"] == "Buvette"), None)
    assert buvette_tag is not None
    add_lot(
        article_id=article_id,
        quantite=10,
        prix_ht=2.0,
        prix_ttc=2.4,
        tva_taux=20,
        fournisseur_id=None,
        numero_facture="F-1",
        numero_lot="L-1",
        date_achat="2026-01-01",
        date_peremption=None,
        commentaire=None,
        tag_ids=[buvette_tag["id"]],
    )

    event_id = add_evenement("Spectacle", "Fête", None, "2026-01-10", None, "termine", None)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO buvette_couts_evenement (evenement_id, cout_total_ttc, detail_json)
            VALUES (?, 30, '[]')
            """,
            (event_id,),
        )
        conn.execute(
            """
            INSERT INTO evenement_ventes (evenement_id, date, canal, mode_paiement, montant_total, frais_sumup, montant_net)
            VALUES (?, '2026-01-10', 'sur_place', 'especes', 60, 0, 60)
            """,
            (event_id,),
        )
        conn.commit()
    finally:
        conn.close()

    bilan = get_bilan_annuel_buvette("2025/2026")
    assert bilan["total_achats"] > 0
    assert len(bilan["par_evenement"]) >= 1


def test_tags_multi_article():
    article_id = _create_article()
    tags = get_tags()
    set_article_tags(article_id, [tags[0]["id"], tags[1]["id"]])

    article_tags = get_article_tags(article_id)
    assert len(article_tags) == 2


def test_add_tag_libre():
    tag_id = add_tag("Promo", "#FFFFFF")
    tags = get_tags()
    assert any(t["id"] == tag_id and t["nom"] == "Promo" for t in tags)
