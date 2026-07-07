"""Tests CRUD/flux de db/models/buvette.py."""

import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.buvette import (
    add_article_buvette,
    add_caisse,
    add_ligne_approvisionnement,
    add_ligne_inventaire,
    archiver_article_buvette,
    calculer_recette_evenement,
    create_approvisionnement,
    create_inventaire,
    enregistrer_recette_evenement,
    finaliser_approvisionnement,
    get_all_articles_buvette,
    get_lignes_inventaire,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


@pytest.fixture
def ids_base() -> dict:
    conn = get_connection()
    try:
        cat = conn.execute(
            "SELECT id FROM categories WHERE nom = 'Boissons' ORDER BY id LIMIT 1"
        ).fetchone()
        unite = conn.execute("SELECT id FROM unites ORDER BY id LIMIT 1").fetchone()

        if not cat:
            parent = conn.execute(
                "SELECT id FROM categories WHERE nom = 'Alimentation & Buvette'"
            ).fetchone()
            parent_id = parent["id"] if parent else None
            cur = conn.execute(
                "INSERT INTO categories (nom, parent_id) VALUES ('Boissons', ?)",
                (parent_id,),
            )
            cat_id = cur.lastrowid
        else:
            cat_id = cat["id"]

        if not unite:
            cur = conn.execute("INSERT INTO unites (nom) VALUES ('Pièce')")
            unite_id = cur.lastrowid
        else:
            unite_id = unite["id"]

        stock_id = conn.execute(
            """
            INSERT INTO stock
                (nom, categorie_id, unite_id, quantite, seuil_alerte, prix_achat, statut_archive)
            VALUES ('Pack Coca', ?, ?, 100, 5, 1.0, 0)
            """,
            (cat_id, unite_id),
        ).lastrowid

        fournisseur_id = conn.execute(
            "INSERT INTO fournisseurs (nom) VALUES ('Metro')"
        ).lastrowid

        evenement_id = conn.execute(
            "INSERT INTO evenements (nom, date) VALUES (?, ?)",
            ("Fête de l'école", "2025-09-01"),
        ).lastrowid

        conn.commit()
        return {
            "cat_id": cat_id,
            "unite_id": unite_id,
            "stock_id": stock_id,
            "fournisseur_id": fournisseur_id,
            "evenement_id": evenement_id,
        }
    finally:
        conn.close()


def test_articles_buvette_crud_et_archivage(ids_base: dict) -> None:
    article_id = add_article_buvette(
        nom="Coca 33cL",
        categorie_id=ids_base["cat_id"],
        unite_id=ids_base["unite_id"],
        contenance="33cL",
        prix_vente=1.5,
        prix_achat=0.8,
        stock_id=ids_base["stock_id"],
        commentaire="",
    )

    articles = get_all_articles_buvette(include_archives=False)
    assert any(a["id"] == article_id for a in articles)

    archiver_article_buvette(article_id)
    actifs = get_all_articles_buvette(include_archives=False)
    assert not any(a["id"] == article_id for a in actifs)


def test_inventaire_ecart_calcule_en_python(ids_base: dict) -> None:
    article_id = add_article_buvette(
        nom="Jus 25cL",
        categorie_id=ids_base["cat_id"],
        unite_id=ids_base["unite_id"],
        contenance="25cL",
        prix_vente=1.0,
        prix_achat=0.5,
        stock_id=None,
        commentaire="",
    )

    inventaire_id = create_inventaire("2025-09-01", "hors_evenement", None, "test")
    add_ligne_inventaire(inventaire_id, article_id, quantite_theorique=10, quantite_comptee=7)

    lignes = get_lignes_inventaire(inventaire_id)
    assert len(lignes) == 1
    assert lignes[0]["ecart"] == -3


def test_finaliser_approvisionnement_met_a_jour_stocks_et_tresorerie(ids_base: dict) -> None:
    article_id = add_article_buvette(
        nom="Bière 50cL",
        categorie_id=ids_base["cat_id"],
        unite_id=ids_base["unite_id"],
        contenance="50cL",
        prix_vente=2.0,
        prix_achat=1.0,
        stock_id=ids_base["stock_id"],
        commentaire="",
    )

    appro_id = create_approvisionnement(
        "2025-09-01",
        ids_base["evenement_id"],
        ids_base["fournisseur_id"],
        "réassort",
    )
    add_ligne_approvisionnement(appro_id, article_id, 12, 1.2)

    assert finaliser_approvisionnement(appro_id) is True

    conn = get_connection()
    try:
        stock_buvette = conn.execute(
            "SELECT stock_actuel FROM articles_buvette WHERE id = ?",
            (article_id,),
        ).fetchone()["stock_actuel"]
        stock_general = conn.execute(
            "SELECT quantite FROM stock WHERE id = ?",
            (ids_base["stock_id"],),
        ).fetchone()["quantite"]
        depenses = conn.execute(
            "SELECT COUNT(*) AS n FROM depenses_diverses WHERE categorie = 'Approvisionnement buvette'"
        ).fetchone()["n"]
    finally:
        conn.close()

    assert stock_buvette == 12
    assert stock_general == 88
    assert depenses == 1


def test_recette_evenement_enregistree_une_seule_fois(ids_base: dict) -> None:
    add_caisse(ids_base["evenement_id"], "Caisse Bar", 50, 380, "2025-09-01", "")
    add_caisse(ids_base["evenement_id"], "Caisse Entrée", 30, 210, "2025-09-01", "")

    calcul = calculer_recette_evenement(ids_base["evenement_id"])
    assert calcul["recette_nette"] == 510

    recette_id_1 = enregistrer_recette_evenement(ids_base["evenement_id"])
    recette_id_2 = enregistrer_recette_evenement(ids_base["evenement_id"])
    assert recette_id_1 == recette_id_2

    conn = get_connection()
    try:
        nb_recettes = conn.execute(
            "SELECT COUNT(*) AS n FROM recettes_buvette WHERE evenement_id = ?",
            (ids_base["evenement_id"],),
        ).fetchone()["n"]
        nb_dons = conn.execute(
            "SELECT COUNT(*) AS n FROM dons_subventions WHERE type = 'Recette buvette'"
        ).fetchone()["n"]
    finally:
        conn.close()

    assert nb_recettes == 1
    assert nb_dons == 1
