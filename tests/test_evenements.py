"""Tests pour le module Événements (Phase 5a)."""

from __future__ import annotations

import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import (
    add_benevole,
    add_billet,
    add_depense,
    add_evenement,
    add_tarif,
    add_vente,
    add_vente_ligne,
    annuler_vente,
    delete_benevole,
    delete_tarif,
    get_all_evenements,
    get_benevoles_evenement,
    get_depenses_evenement,
    get_evenement_by_id,
    get_lignes_vente,
    get_parametre,
    get_stats_benevoles,
    get_stats_billetterie,
    get_tarifs_evenement,
    get_ventes_evenement,
    set_parametre,
    update_evenement,
    update_tarif,
)
from core.evenements import (
    calculer_bilan_evenement,
    calculer_frais_sumup,
    calculer_montant_net,
    generer_numero_billet,
    valider_evenement,
    valider_tarif,
    valider_vente,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


# ── test_creation_evenement ───────────────────────────────────────────────────


def test_creation_evenement():
    evt_id = add_evenement(
        nom="Fête de l'école",
        type_="Fête",
        description="Une belle fête.",
        date_debut="2026-06-14",
        date_fin=None,
        statut="planifie",
        budget_previsionnel=500.0,
    )
    assert evt_id is not None and evt_id > 0

    evt = get_evenement_by_id(evt_id)
    assert evt is not None
    assert evt["nom"] == "Fête de l'école"
    assert evt["type"] == "Fête"
    assert evt["statut"] == "planifie"
    assert evt["budget_previsionnel"] == 500.0

    all_evts = get_all_evenements()
    assert any(e["id"] == evt_id for e in all_evts)

    # Filtrage par statut
    planifies = get_all_evenements(statut="planifie")
    assert any(e["id"] == evt_id for e in planifies)

    termines = get_all_evenements(statut="termine")
    assert not any(e["id"] == evt_id for e in termines)

    # Update
    update_evenement(evt_id, statut="en_cours")
    evt_upd = get_evenement_by_id(evt_id)
    assert evt_upd["statut"] == "en_cours"


def test_valider_evenement():
    # Cas valide
    erreurs = valider_evenement("Fête", "2026-06-14", "2026-06-15")
    assert erreurs == []

    # Nom manquant
    erreurs = valider_evenement("", "2026-06-14", None)
    assert any("nom" in e.lower() for e in erreurs)

    # Date de début manquante
    erreurs = valider_evenement("Fête", "", None)
    assert any("date" in e.lower() for e in erreurs)

    # Date fin avant date début
    erreurs = valider_evenement("Fête", "2026-06-14", "2026-06-10")
    assert any("fin" in e.lower() for e in erreurs)


# ── test_tarifs_evenement_crud ────────────────────────────────────────────────


def test_tarifs_evenement_crud():
    evt_id = add_evenement("Loto", None, None, "2026-12-12", None, "planifie", None)

    t_id = add_tarif(evt_id, "Adulte", 5.0, 0, 0)
    assert t_id > 0

    tarifs = get_tarifs_evenement(evt_id)
    assert len(tarifs) == 1
    assert tarifs[0]["nom"] == "Adulte"
    assert tarifs[0]["prix"] == 5.0
    assert tarifs[0]["est_gratuit"] == 0

    # Ajout tarif gratuit
    add_tarif(evt_id, "Gratuit", 0.0, 1, 1)
    tarifs = get_tarifs_evenement(evt_id)
    assert len(tarifs) == 2

    # Update
    update_tarif(t_id, prix=6.0)
    tarifs = get_tarifs_evenement(evt_id)
    adulte = next(t for t in tarifs if t["id"] == t_id)
    assert adulte["prix"] == 6.0

    # Delete
    delete_tarif(t_id)
    tarifs = get_tarifs_evenement(evt_id)
    assert not any(t["id"] == t_id for t in tarifs)

    # Validation
    assert valider_tarif("Enfant", "3.00") == []
    assert valider_tarif("", "3.00") != []
    assert valider_tarif("Enfant", "-1") != []


# ── test_vente_multi_tarifs ───────────────────────────────────────────────────


def test_vente_multi_tarifs():
    evt_id = add_evenement("Kermesse", None, None, "2026-06-01", None, "planifie", None)
    t_adulte = add_tarif(evt_id, "Adulte", 5.0, 0, 0)
    t_enfant = add_tarif(evt_id, "Enfant", 3.0, 0, 1)

    vente_id = add_vente(
        evenement_id=evt_id,
        date="2026-06-01",
        canal="sur_place",
        mode_paiement="especes",
        nom_tireur=None,
        montant_total=16.0,
        frais_sumup=0.0,
        montant_net=16.0,
        commentaire=None,
    )
    assert vente_id > 0

    ligne_a = add_vente_ligne(vente_id, t_adulte, 2, 5.0)
    ligne_e = add_vente_ligne(vente_id, t_enfant, 2, 3.0)

    lignes = get_lignes_vente(vente_id)
    assert len(lignes) == 2
    totaux = {l["tarif_nom"]: l["sous_total"] for l in lignes}
    assert totaux["Adulte"] == 10.0
    assert totaux["Enfant"] == 6.0

    # Billets
    add_billet(ligne_a, "A001", t_adulte)
    add_billet(ligne_a, "A002", t_adulte)
    add_billet(ligne_e, "E001", t_enfant)
    add_billet(ligne_e, "E002", t_enfant)

    ventes = get_ventes_evenement(evt_id)
    assert len(ventes) == 1
    assert ventes[0]["montant_total"] == 16.0


# ── test_calcul_frais_sumup ───────────────────────────────────────────────────


def test_calcul_frais_sumup():
    frais = calculer_frais_sumup(100.0, 1.75)
    assert frais == 1.75

    frais = calculer_frais_sumup(50.0, 1.75)
    assert frais == 0.88

    # Montant net espèces = montant brut
    net = calculer_montant_net(100.0, "especes", 1.75)
    assert net == 100.0

    # Montant net SumUp = montant brut - frais
    net = calculer_montant_net(100.0, "sumup", 1.75)
    assert net == 98.25


# ── test_annulation_vente ─────────────────────────────────────────────────────


def test_annulation_vente():
    evt_id = add_evenement("Concert", None, None, "2026-09-01", None, "planifie", None)
    t_id = add_tarif(evt_id, "Adulte", 10.0, 0, 0)

    vente_id = add_vente(evt_id, "2026-09-01", "sur_place", "especes",
                         None, 10.0, 0.0, 10.0, None)
    add_vente_ligne(vente_id, t_id, 1, 10.0)

    ok = annuler_vente(vente_id, "Erreur de saisie")
    assert ok

    ventes = get_ventes_evenement(evt_id)
    v = next(v for v in ventes if v["id"] == vente_id)
    assert v["statut"] == "annule"
    assert v["motif_annulation"] == "Erreur de saisie"


# ── test_benevoles_crud ───────────────────────────────────────────────────────


def test_benevoles_crud():
    evt_id = add_evenement("Festival", None, None, "2026-07-10", None, "planifie", None)

    # Bénévole externe
    b_id = add_benevole(
        evenement_id=evt_id,
        membre_id=None,
        nom_externe="Dupont",
        prenom_externe="Jean",
        role="Caisse",
        heure_debut="14:00",
        heure_fin="18:00",
        statut="confirme",
    )
    assert b_id > 0

    benevoles = get_benevoles_evenement(evt_id)
    assert len(benevoles) == 1
    assert benevoles[0]["nom_externe"] == "Dupont"
    assert benevoles[0]["role"] == "Caisse"

    # Bénévole désisté
    add_benevole(
        evenement_id=evt_id,
        membre_id=None,
        nom_externe="Martin",
        prenom_externe="Marie",
        role="Buvette",
        heure_debut=None,
        heure_fin=None,
        statut="desiste",
    )

    stats = get_stats_benevoles(evt_id)
    assert stats["total"] == 2
    assert stats["confirmes"] == 1
    assert stats["desistes"] == 1
    assert stats["total_heures"] == 4.0

    # Suppression
    delete_benevole(b_id)
    benevoles = get_benevoles_evenement(evt_id)
    assert len(benevoles) == 1


# ── test_stats_billetterie ────────────────────────────────────────────────────


def test_stats_billetterie():
    evt_id = add_evenement("Bal", None, None, "2026-08-15", None, "planifie", None)
    t_a = add_tarif(evt_id, "Adulte", 5.0, 0, 0)
    t_e = add_tarif(evt_id, "Enfant", 3.0, 0, 1)

    # Vente 1 — espèces
    v1 = add_vente(evt_id, "2026-08-15", "sur_place", "especes", None, 11.0, 0.0, 11.0, None)
    l1 = add_vente_ligne(v1, t_a, 1, 5.0)
    l2 = add_vente_ligne(v1, t_e, 2, 3.0)
    add_billet(l1, "A001", t_a)
    add_billet(l2, "E001", t_e)
    add_billet(l2, "E002", t_e)

    # Vente 2 — SumUp
    v2 = add_vente(evt_id, "2026-08-15", "prevente", "sumup", None, 10.0, 0.18, 9.82, None)
    l3 = add_vente_ligne(v2, t_a, 2, 5.0)
    add_billet(l3, "A002", t_a)
    add_billet(l3, "A003", t_a)

    stats = get_stats_billetterie(evt_id)
    assert stats["total_billets"] == 5
    assert stats["total_recette"] == 21.0
    assert len(stats["par_tarif"]) == 2
    assert any(t["tarif_nom"] == "Adulte" for t in stats["par_tarif"])
    assert len(stats["par_canal"]) == 2
    assert len(stats["par_mode_paiement"]) == 2

    # Vente annulée ne compte pas
    annuler_vente(v2, "test")
    stats = get_stats_billetterie(evt_id)
    assert stats["total_billets"] == 3
    assert stats["total_recette"] == 11.0


# ── test_bilan_evenement ──────────────────────────────────────────────────────


def test_bilan_evenement():
    evt_id = add_evenement("Marché", None, None, "2026-11-01", None, "planifie", None)
    t_id = add_tarif(evt_id, "Adulte", 5.0, 0, 0)

    v1 = add_vente(evt_id, "2026-11-01", "sur_place", "especes", None, 15.0, 0.0, 15.0, None)
    add_vente_ligne(v1, t_id, 3, 5.0)

    add_depense(evt_id, "Location salle", 50.0, "2026-10-01", "Salle",
                None, "virement", None)
    add_depense(evt_id, "Sono", 30.0, "2026-10-15", "Sono",
                None, "especes", None)

    bilan = calculer_bilan_evenement(evt_id)
    assert bilan["recettes_total"] == 15.0
    assert bilan["depenses_total"] == 80.0
    assert bilan["benefice"] == -65.0


# ── test_parametres ───────────────────────────────────────────────────────────


def test_parametres():
    # Taux SumUp par défaut créé par la migration
    taux = get_parametre("taux_sumup")
    assert taux == "1.75"

    # Modification
    set_parametre("taux_sumup", "2.00")
    assert get_parametre("taux_sumup") == "2.00"

    # Nouveau paramètre
    set_parametre("ma_cle", "ma_valeur")
    assert get_parametre("ma_cle") == "ma_valeur"

    # Clé inexistante
    assert get_parametre("inexistant") is None


# ── test_generer_numero_billet ────────────────────────────────────────────────


def test_generer_numero_billet():
    assert generer_numero_billet(1, "Adulte", 1) == "A001"
    assert generer_numero_billet(1, "Enfant", 42) == "E042"
    assert generer_numero_billet(1, "Réduit", 100) == "R100"
    assert generer_numero_billet(1, "", 1) == "X001"
