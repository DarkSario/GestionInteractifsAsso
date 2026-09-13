"""Tests des caisses événement (tables détaillées + intégration bilan)."""

from __future__ import annotations

import pytest

from core.caisses_evenement import calculer_bilan_complet_evenement
from core.evenements import calculer_bilan_evenement
from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.caisse_designations import (
    creer_designation_caisse,
    definir_activation_designation_caisse,
    lister_designations_caisse,
    reinitialiser_designations_caisses,
    supprimer_designation_caisse,
)
from db.models.evenement_caisses import (
    ajouter_ligne_caisse,
    creer_caisse,
    get_caisse,
    get_total_recettes_caisses_evenement,
    lister_caisses_evenement,
    modifier_ligne_caisse,
)
from db.models.evenements import (
    add_depense,
    add_evenement,
    add_tarif,
    add_vente,
    add_vente_ligne,
)
from db.models.tableaux import add_colonne, add_ligne, add_tableau, set_cellule


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def test_caisse_lignes_debut_fin_et_recette() -> None:
    evenement_id = add_evenement(
        "Fête", None, None, "2026-06-10", None, "planifie", None
    )
    caisse_id = creer_caisse(evenement_id, "Billetterie")

    ajouter_ligne_caisse(caisse_id, "debut", "Pièces 1€", 1.0, 15)
    ajouter_ligne_caisse(caisse_id, "debut", "Billets 20€", 20.0, 2)
    ajouter_ligne_caisse(caisse_id, "fin", "Pièces 1€", 1.0, 25)
    ajouter_ligne_caisse(caisse_id, "fin", "Billets 20€", 20.0, 3)

    caisse = get_caisse(caisse_id)
    assert caisse is not None
    assert caisse["total_debut"] == 55.0
    assert caisse["total_fin"] == 85.0
    assert caisse["recette"] == 30.0

    caisses = lister_caisses_evenement(evenement_id)
    assert len(caisses) == 1
    assert caisses[0]["nom"] == "Billetterie"
    assert caisses[0]["recette"] == 30.0
    assert get_total_recettes_caisses_evenement(evenement_id) == 30.0


def test_bilan_evenement_integre_recette_caisses() -> None:
    from db.connection import get_connection

    evenement_id = add_evenement(
        "Kermesse", None, None, "2026-07-01", None, "planifie", None
    )

    tarif_id = add_tarif(evenement_id, "Entrée", 5.0, 0, 0)
    vente_id = add_vente(
        evenement_id=evenement_id,
        date="2026-07-01",
        canal="sur_place",
        mode_paiement="especes",
        nom_tireur=None,
        montant_total=10.0,
        frais_sumup=0.0,
        montant_net=10.0,
        commentaire=None,
    )
    add_vente_ligne(vente_id, tarif_id, 2, 5.0)
    add_depense(
        evenement_id,
        "Achat déco",
        4.0,
        "2026-06-30",
        "Décoration",
        None,
        "especes",
        None,
    )

    caisse_id = creer_caisse(evenement_id, "Caisse principale")
    ajouter_ligne_caisse(caisse_id, "debut", "Fond", 1.0, 10)
    ajouter_ligne_caisse(caisse_id, "fin", "Fond", 1.0, 18)

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO tombola_carnets
                (evenement_id, numero_debut, numero_fin, prix_carnet, vendeur_nom_externe, statut, montant_encaisse)
            VALUES (?, 1, 1, 2, 'Élève A', 'vendu', 12)
            """,
            (evenement_id,),
        )
        conn.execute(
            """
            INSERT INTO caisses_buvette
                (evenement_id, nom, fond_de_caisse, total_brut, date, commentaire)
            VALUES (?, 'Bar', 3, 10, '2026-07-01', '')
            """,
            (evenement_id,),
        )
        conn.commit()
    finally:
        conn.close()

    bilan_complet = calculer_bilan_complet_evenement(evenement_id)
    assert bilan_complet["recettes_billetterie"] == 10.0
    assert bilan_complet["recettes_caisses"] == 8.0
    assert bilan_complet["recettes_tombola"] == 12.0
    assert bilan_complet["recettes_buvette"] == 7.0
    assert bilan_complet["total_recettes"] == 37.0
    assert bilan_complet["total_depenses"] == 4.0
    assert bilan_complet["benefice_global"] == 33.0

    bilan_fiche = calculer_bilan_evenement(evenement_id)
    assert bilan_fiche["recettes_total"] == 37.0
    assert bilan_fiche["depenses_total"] == 4.0
    assert bilan_fiche["benefice"] == 33.0


def test_bilan_tableaux_compte_uniquement_colonnes_afficher_total() -> None:
    evenement_id = add_evenement(
        "Expo", None, None, "2026-09-01", None, "planifie", None
    )
    tableau_id = add_tableau(evenement_id, "Recettes stand", None, 0)
    col_comptee = add_colonne(tableau_id, "Ventes", "montant", None, True, 0, 120)
    col_non_comptee = add_colonne(tableau_id, "Acompte", "montant", None, False, 1, 120)
    ligne_id = add_ligne(tableau_id, None, "normal", 0)
    assert set_cellule(ligne_id, col_comptee, "10")
    assert set_cellule(ligne_id, col_non_comptee, "999")

    bilan = calculer_bilan_complet_evenement(evenement_id)
    assert bilan["recettes_tableaux"] == 10.0
    assert bilan["total_recettes"] == 10.0


def test_designations_par_defaut_et_activation() -> None:
    designations = lister_designations_caisse()
    noms = [designation["nom"] for designation in designations]
    assert "Pièces 1€" in noms
    assert "Chèques" in noms

    piece_1 = next(
        designation for designation in designations if designation["nom"] == "Pièces 1€"
    )
    assert piece_1["montant_unitaire"] == 1.0
    assert piece_1["actif"] == 1

    assert definir_activation_designation_caisse(piece_1["id"], False)
    actifs = lister_designations_caisse(actif_only=True)
    assert all(designation["id"] != piece_1["id"] for designation in actifs)

    total = reinitialiser_designations_caisses()
    assert total >= len(designations)
    piece_1_reloaded = next(
        designation
        for designation in lister_designations_caisse(actif_only=True)
        if designation["nom"] == "Pièces 1€"
    )
    assert piece_1_reloaded["actif"] == 1


def test_ligne_caisse_conserve_texte_si_designation_supprimee() -> None:
    evenement_id = add_evenement(
        "Marché", None, None, "2026-10-10", None, "planifie", None
    )
    designation_id = creer_designation_caisse(
        "Jetons", 2.5, "Monnaie interne", 200, True
    )
    caisse_id = creer_caisse(evenement_id, "Accueil")

    ajouter_ligne_caisse(
        caisse_id, "fin", "Jetons", 2.5, 4, designation_id=designation_id
    )
    caisse = get_caisse(caisse_id)
    assert caisse is not None
    assert caisse["lignes_fin"][0]["designation_id"] == designation_id
    assert caisse["lignes_fin"][0]["designation"] == "Jetons"

    assert supprimer_designation_caisse(designation_id)

    caisse_apres = get_caisse(caisse_id)
    assert caisse_apres is not None
    assert caisse_apres["lignes_fin"][0]["designation_id"] is None
    assert caisse_apres["lignes_fin"][0]["designation"] == "Jetons"


def test_modifier_ligne_caisse_conserve_lien_designation_et_texte() -> None:
    evenement_id = add_evenement(
        "Braderie", None, None, "2026-11-15", None, "planifie", None
    )
    designation = next(
        item for item in lister_designations_caisse(actif_only=True) if item["nom"] == "SumUp/CB"
    )
    designation_id = int(designation["id"])
    caisse_id = creer_caisse(evenement_id, "Point CB")

    ligne_id = ajouter_ligne_caisse(
        caisse_id, "fin", "SumUp/CB", 120.0, 1, designation_id=designation_id
    )
    assert modifier_ligne_caisse(
        ligne_id,
        designation="SumUp/CB",
        montant_unitaire=180.5,
        quantite=1,
        designation_id=designation_id,
    )

    caisse = get_caisse(caisse_id)
    assert caisse is not None
    ligne = caisse["lignes_fin"][0]
    assert ligne["designation_id"] == designation_id
    assert ligne["designation"] == "SumUp/CB"
    assert ligne["montant_unitaire"] == 180.5
    assert ligne["total"] == 180.5
