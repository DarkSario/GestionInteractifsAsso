from __future__ import annotations

from datetime import datetime

import pytest

from core.evenements import calculer_montant_net
from core.parametres import valider_nom_liste
from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.dashboard import get_bilan_dernier_evenement, get_recettes_depenses_mois
from db.models.evenements import add_evenement, add_tarif, add_vente
from db.models.stands import add_stand, finaliser_location_stand
from db.models.tableaux import add_colonne, add_tableau, get_colonnes_tableau
from db.models.tombola import (
    add_lot,
    get_config_tombola_evenement,
    get_lots_evenement,
    update_config_tombola_evenement,
    update_lot,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _event_id(statut: str = "planifie") -> int:
    return add_evenement("Événement test", "Fête", None, "2026-07-10", None, statut, None)


def test_classe_avec_slash():
    assert valider_nom_liste("CM1/CM2") == []


def test_frais_sumup_carte():
    assert calculer_montant_net(100.0, "carte", 1.75) == 98.25


def test_frais_sumup_lien():
    assert calculer_montant_net(100.0, "sumup", 1.75) == 98.25


def test_dashboard_recettes_non_zero():
    evt_id = _event_id()
    add_vente(evt_id, "2026-07-10", "sur_place", "carte", None, 100.0, 1.75, 98.25, None)
    result = get_recettes_depenses_mois(2026, 7)
    assert result["total_recettes"] > 0


def test_tombola_prix_ticket():
    evt_id = _event_id()
    assert update_config_tombola_evenement(evt_id, 2.0, 20.0)
    cfg = get_config_tombola_evenement(evt_id)
    assert cfg["prix_ticket"] == 2.0
    assert cfg["prix_carnet"] == 20.0


def test_tombola_valeur_lot():
    evt_id = _event_id()
    lot_id = add_lot(evt_id, 1, "Panier", 35.0, 35.0, "achete", None, None, None)
    lot = next(l for l in get_lots_evenement(evt_id) if l["id"] == lot_id)
    assert float(lot["valeur_lot"]) == 35.0


def test_tombola_modifier_statut():
    evt_id = _event_id()
    lot_id = add_lot(evt_id, 1, "Panier", 20.0, 20.0, "achete", None, None, None)
    assert update_lot(lot_id, statut="remis")
    lot = next(l for l in get_lots_evenement(evt_id) if l["id"] == lot_id)
    assert lot["statut"] == "remis"


def test_stand_type_recette():
    evt_id = _event_id()
    stand_id = add_stand(evt_id, "A1", "Stand recette", "location", None, None, 50.0, "recette", 0, None)
    assert finaliser_location_stand(stand_id)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM tresorerie_operations WHERE source_module = 'stands' AND evenement_id = ?",
            (evt_id,),
        ).fetchone()
    finally:
        conn.close()
    assert int(row["n"]) == 1


def test_stand_type_depense():
    evt_id = _event_id()
    stand_id = add_stand(evt_id, "A2", "Stand dépense", "location", None, None, 40.0, "depense", 0, None)
    assert finaliser_location_stand(stand_id)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM evenement_depenses WHERE evenement_id = ?",
            (evt_id,),
        ).fetchone()
    finally:
        conn.close()
    assert int(row["n"]) == 1


def test_tableau_type_colonne_valide():
    evt_id = _event_id()
    tableau_id = add_tableau(evt_id, "Tableau", None, 0)
    add_colonne(tableau_id, "Paiement", "  LISTE_PAIEMENT ", None, 0, 0, 120)
    colonnes = get_colonnes_tableau(tableau_id)
    assert colonnes[0]["type_colonne"] == "liste_paiement"


def test_dashboard_colonne_montant():
    evt_id = _event_id("termine")
    tarif_id = add_tarif(evt_id, "Entrée", 10.0, 0, 0)
    _ = tarif_id
    add_vente(evt_id, datetime.now().strftime("%Y-%m-%d"), "sur_place", "sumup", None, 10.0, 0.18, 9.82, None)
    bilan = get_bilan_dernier_evenement()
    assert bilan is not None
    assert bilan["recettes_nettes"] > 0
