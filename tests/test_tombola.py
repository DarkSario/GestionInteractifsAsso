"""Tests du module Tombola (Phase 5b)."""

from __future__ import annotations

import pytest

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import add_evenement
from db.models.tombola import (
    add_carnet,
    add_lot,
    enregistrer_gagnant,
    get_carnets_evenement,
    get_lots_evenement,
    get_stats_tombola,
    update_carnet,
    update_lot,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _event_id() -> int:
    return add_evenement("Kermesse", "Fête", None, "2026-06-01", None, "planifie", None)


def test_lots_crud():
    evt_id = _event_id()
    lot_id = add_lot(evt_id, 1, "Panier garni", 30.0, 30.0, "achete", None, None, None)
    assert lot_id > 0

    lots = get_lots_evenement(evt_id)
    assert len(lots) == 1
    assert lots[0]["description"] == "Panier garni"

    assert update_lot(lot_id, description="Panier premium", statut="gagne")
    lots = get_lots_evenement(evt_id)
    assert lots[0]["description"] == "Panier premium"
    assert lots[0]["statut"] == "gagne"


def test_carnets_crud():
    evt_id = _event_id()
    carnet_id = add_carnet(evt_id, 1, 50, 2.0, None, "Jean", "2026-06-01")
    assert carnet_id > 0

    carnets = get_carnets_evenement(evt_id)
    assert len(carnets) == 1
    assert carnets[0]["numero_debut"] == 1

    assert update_carnet(carnet_id, statut="vendu", montant_encaisse=100.0)
    carnets = get_carnets_evenement(evt_id)
    assert carnets[0]["statut"] == "vendu"
    assert carnets[0]["montant_encaisse"] == 100.0


def test_enregistrer_gagnant():
    evt_id = _event_id()
    lot_id = add_lot(evt_id, 7, "Coffret", 45.0, 45.0, "sponsorise", None, "Sponsor X", None)

    assert enregistrer_gagnant(lot_id, "042")
    lot = get_lots_evenement(evt_id)[0]
    assert lot["numero_gagnant"] == "042"
    assert lot["statut"] == "gagne"


def test_stats_tombola():
    evt_id = _event_id()
    c1 = add_carnet(evt_id, 1, 50, 2.0, None, None, None)
    c2 = add_carnet(evt_id, 51, 100, 2.0, None, None, None)
    update_carnet(c1, statut="vendu", montant_encaisse=100.0)
    update_carnet(c2, statut="perdu", montant_encaisse=0.0)

    add_lot(evt_id, 1, "Bon d'achat", 50.0, 50.0, "achete", None, None, None)
    l2 = add_lot(evt_id, 2, "Panier", 25.0, 25.0, "achete", None, None, None)
    update_lot(l2, statut="gagne")

    stats = get_stats_tombola(evt_id)
    assert stats["total_carnets"] == 100
    assert stats["vendus"] == 50
    assert stats["perdus"] == 50
    assert stats["montant_total"] == 100.0
    assert stats["lots_attribues"] == 1
