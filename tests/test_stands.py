"""Tests du module Stands (Phase 5b)."""

from __future__ import annotations

import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import add_evenement
from db.models.stands import (
    add_attente,
    add_stand,
    finaliser_location_stand,
    get_attente_evenement,
    get_stands_evenement,
    promouvoir_attente,
    update_stand,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _event_id() -> int:
    return add_evenement("Vide-grenier", "Marché", None, "2026-09-10", None, "planifie", None)


def test_stands_crud():
    evt_id = _event_id()
    stand_id = add_stand(evt_id, "A1", "Stand gâteaux", "benevole", None, "Marie", 0, "recette", 0, None)
    assert stand_id > 0

    stands = get_stands_evenement(evt_id)
    assert len(stands) == 1
    assert stands[0]["numero_emplacement"] == "A1"

    assert update_stand(stand_id, numero_emplacement="A2", commentaire="Déplacé")
    stands = get_stands_evenement(evt_id)
    assert stands[0]["numero_emplacement"] == "A2"


def test_liste_attente():
    evt_id = _event_id()
    attente_id = add_attente(evt_id, "Dupont", "Jean", "0612345678", "")
    assert attente_id > 0

    attente = get_attente_evenement(evt_id)
    assert len(attente) == 1

    assert promouvoir_attente(attente_id)
    assert get_attente_evenement(evt_id) == []
    stands = get_stands_evenement(evt_id)
    assert len(stands) == 1
    assert stands[0]["type_stand"] == "benevole"


def test_finaliser_location_stand():
    evt_id = _event_id()
    stand_id = add_stand(evt_id, "B3", "Emplacement VG", "location", None, "M. Durand", 15.0, "recette", 1, None)

    assert finaliser_location_stand(stand_id)

    stands = get_stands_evenement(evt_id)
    assert stands[0]["tresorerie_id"] is not None

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT type_operation, montant, source_module FROM tresorerie_operations WHERE source_module = 'stands'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["type_operation"] == "recette"
    assert rows[0]["montant"] == 15.0
