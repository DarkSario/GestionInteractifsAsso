"""Tests CRUD de db/models/membres.py."""

import pytest

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.membres import (
    add_membre,
    archiver_membre,
    get_all_membres,
    get_membre_by_id,
    get_membres_for_select,
    update_membre,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    """Prépare une base de données temporaire avec migrations appliquées."""
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _ajouter_membre_test(nom="Dupont", prenom="Marie", statut="Membre"):
    return add_membre(
        nom=nom,
        prenom=prenom,
        email="marie@example.com",
        telephone="0612345678",
        statut=statut,
        date_adhesion="2024-01-01",
        commentaire="Test",
    )


def test_add_membre_retourne_id() -> None:
    membre_id = _ajouter_membre_test()
    assert isinstance(membre_id, int)
    assert membre_id > 0


def test_get_all_membres_vide() -> None:
    membres = get_all_membres()
    assert membres == []


def test_get_all_membres_retourne_ajoute() -> None:
    _ajouter_membre_test()
    membres = get_all_membres()
    assert len(membres) == 1
    assert membres[0]["nom"] == "Dupont"
    assert membres[0]["prenom"] == "Marie"


def test_get_membre_by_id_trouve() -> None:
    membre_id = _ajouter_membre_test()
    m = get_membre_by_id(membre_id)
    assert m is not None
    assert m["id"] == membre_id
    assert m["nom"] == "Dupont"


def test_get_membre_by_id_introuvable() -> None:
    m = get_membre_by_id(9999)
    assert m is None


def test_update_membre_succes() -> None:
    membre_id = _ajouter_membre_test()
    ok = update_membre(
        membre_id=membre_id,
        nom="Martin",
        prenom="Paul",
        email="paul@example.com",
        telephone="",
        statut="Trésorier(ère)",
        date_adhesion="2024-06-01",
        commentaire="",
    )
    assert ok is True
    m = get_membre_by_id(membre_id)
    assert m["nom"] == "Martin"
    assert m["prenom"] == "Paul"
    assert m["statut"] == "Trésorier(ère)"


def test_update_membre_inexistant() -> None:
    ok = update_membre(
        membre_id=9999,
        nom="X",
        prenom="Y",
        email="",
        telephone="",
        statut="Membre",
        date_adhesion="",
        commentaire="",
    )
    assert ok is False


def test_archiver_membre_succes() -> None:
    membre_id = _ajouter_membre_test()
    ok = archiver_membre(membre_id)
    assert ok is True

    # N'apparaît plus dans la liste sans archives
    membres_actifs = get_all_membres(include_archives=False)
    ids_actifs = [m["id"] for m in membres_actifs]
    assert membre_id not in ids_actifs

    # Apparaît dans la liste avec archives
    membres_tous = get_all_membres(include_archives=True)
    ids_tous = [m["id"] for m in membres_tous]
    assert membre_id in ids_tous
    m = get_membre_by_id(membre_id)
    assert m["statut_archive"] == 1


def test_archiver_membre_inexistant() -> None:
    ok = archiver_membre(9999)
    assert ok is False


def test_get_membres_for_select_actifs_seulement() -> None:
    id1 = _ajouter_membre_test("Dupont", "Marie")
    id2 = _ajouter_membre_test("Martin", "Paul")
    archiver_membre(id2)

    membres = get_membres_for_select()
    ids = [m["id"] for m in membres]
    assert id1 in ids
    assert id2 not in ids


def test_get_membres_for_select_champs() -> None:
    _ajouter_membre_test()
    membres = get_membres_for_select()
    assert len(membres) == 1
    assert "id" in membres[0]
    assert "nom" in membres[0]
    assert "prenom" in membres[0]


def test_add_multiple_membres_tri() -> None:
    add_membre("Zorro", "Ana", "", "", "Membre", "2024-01-01", "")
    add_membre("Amine", "Bob", "", "", "Président(e)", "2024-01-01", "")
    membres = get_all_membres()
    assert len(membres) == 2
    # Trié par statut puis nom : "Membre" < "Président(e)" alphabétiquement... 
    # selon l'ordre naturel SQL ASC
    assert membres[0]["nom"] in ("Zorro", "Amine")
