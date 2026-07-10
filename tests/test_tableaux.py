"""Tests du module Tableaux personnalisés (Phase 5b)."""

from __future__ import annotations

import pytest

from core.tableaux import get_valeurs_liste
from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import add_evenement, set_parametre
from db.models.tableaux import (
    add_colonne,
    add_ligne,
    add_tableau,
    apply_template,
    calculer_totaux,
    dupliquer_tableau,
    get_colonnes_tableau,
    get_lignes_tableau,
    save_template,
    set_cellule,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _event_id(name: str = "Prévente") -> int:
    return add_evenement(name, "Fête", None, "2026-10-01", None, "planifie", None)


def test_tableau_creation_colonnes():
    evt_id = _event_id()
    tableau_id = add_tableau(evt_id, "Prévente billets", "", 0)
    assert tableau_id > 0

    add_colonne(tableau_id, "Nom", "texte", None, 0, 0, 180)
    add_colonne(tableau_id, "Nb billets", "nombre", None, 1, 1, 100)

    colonnes = get_colonnes_tableau(tableau_id)
    assert [c["nom"] for c in colonnes] == ["Nom", "Nb billets"]
    assert colonnes[1]["afficher_total"] == 1


def test_ajout_lignes_cellules():
    evt_id = _event_id()
    tableau_id = add_tableau(evt_id, "Prévente", None, 0)
    c_nom = add_colonne(tableau_id, "Nom", "texte", None, 0, 0, 150)
    c_nb = add_colonne(tableau_id, "Nb", "nombre", None, 1, 1, 90)

    ligne_id = add_ligne(tableau_id, None, "normal", 0)
    assert set_cellule(ligne_id, c_nom, "Dupont Jean")
    assert set_cellule(ligne_id, c_nb, "4")

    lignes = get_lignes_tableau(tableau_id)
    assert len(lignes) == 1
    assert lignes[0]["cellules"][str(c_nom)] == "Dupont Jean"
    assert lignes[0]["cellules"][str(c_nb)] == "4"


def test_totaux_automatiques():
    evt_id = _event_id()
    tableau_id = add_tableau(evt_id, "Ventes", None, 0)
    c_nb = add_colonne(tableau_id, "Nb billets", "nombre", None, 1, 0, 90)
    c_montant = add_colonne(tableau_id, "Montant", "montant", None, 1, 1, 110)

    l1 = add_ligne(tableau_id, None, "normal", 0)
    l2 = add_ligne(tableau_id, None, "normal", 1)
    set_cellule(l1, c_nb, "4")
    set_cellule(l2, c_nb, "5")
    set_cellule(l1, c_montant, "20,00")
    set_cellule(l2, c_montant, "25")

    totaux = calculer_totaux(tableau_id)
    assert totaux[c_nb] == 9.0
    assert totaux[c_montant] == 45.0


def test_save_and_apply_template():
    evt_id = _event_id("Event A")
    tableau_id = add_tableau(evt_id, "Planning bénévoles", None, 0)
    add_colonne(tableau_id, "Nom", "texte", None, 0, 0, 150)
    add_colonne(tableau_id, "Paiement", "liste_paiement", None, 0, 1, 150)

    template_id = save_template("Template planning", "", tableau_id)
    assert template_id > 0

    evt_2 = _event_id("Event B")
    tableau_applique = apply_template(template_id, evt_2)
    assert tableau_applique > 0

    colonnes = get_colonnes_tableau(tableau_applique)
    assert len(colonnes) == 2
    assert [c["nom"] for c in colonnes] == ["Nom", "Paiement"]


def test_dupliquer_tableau():
    evt_id = _event_id()
    tableau_id = add_tableau(evt_id, "Prévente", None, 0)
    add_colonne(tableau_id, "Nom", "texte", None, 0, 0, 150)
    add_colonne(tableau_id, "Montant", "montant", None, 1, 1, 110)

    ligne_id = add_ligne(tableau_id, None, "normal", 0)
    set_cellule(ligne_id, get_colonnes_tableau(tableau_id)[0]["id"], "Dupont")

    copie_id = dupliquer_tableau(tableau_id, evt_id)
    assert copie_id > 0

    assert len(get_colonnes_tableau(copie_id)) == 2
    assert len(get_lignes_tableau(copie_id)) == 0


def test_get_valeurs_liste():
    set_parametre("classes_scolaires", '["CP","CE1"]')
    set_parametre("statuts_perso", '["En attente","Payé"]')

    assert get_valeurs_liste("liste_paiement", "") == ["Espèces", "Carte", "Chèque", "SumUp", "Virement"]
    assert get_valeurs_liste("liste_classes", "") == ["CP", "CE1"]
    assert get_valeurs_liste("liste_statut", "") == ["En attente", "Payé"]
    assert get_valeurs_liste("liste_perso", "A;B; C") == ["A", "B", "C"]
