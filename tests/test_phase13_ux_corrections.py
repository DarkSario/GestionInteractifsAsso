from __future__ import annotations

from pathlib import Path

import pytest

from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import (
    MODULES_EVENEMENT_DISPONIBLES,
    add_evenement,
    get_evenement_by_id,
    get_modules_actifs_evenement,
    modules_actifs_depuis_json,
    serialiser_modules_actifs,
)
from core.budget_evenement import get_or_create_budget
from db.models.stands import add_stand, get_stands_evenement
from db.models.stock import add_article, add_mouvement, get_article_by_id
from db.models.tableaux import (
    add_colonne,
    add_ligne,
    add_tableau,
    get_cellules_ligne,
    update_ligne,
)
from db.models.tombola import (
    add_participation_solidaire,
    effectuer_tirage_tombola_solidaire,
    get_participations_solidaires,
    get_total_dons_tombola_solidaire,
)
from db.models.tresorerie import (
    add_operation,
    add_subvention,
    get_all_categories,
    get_all_comptes,
    get_all_subventions,
    get_operation_by_id,
    update_subvention,
)
from utils.backup import backup_db


@pytest.fixture(autouse=True)
def setup_db(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    yield
    set_db_file("")


def _event_id(nom: str = "Événement Phase 13") -> int:
    return add_evenement(nom, "Fête", None, "2026-07-11", None, "planifie", None)


def _article_id(nom: str = "Bière Blonde", quantite: int = 50) -> int:
    return add_article(
        nom=nom,
        categorie_id=None,
        unite_id=None,
        fournisseur_habituel_id=None,
        quantite=quantite,
        seuil_alerte=0,
        prix_achat=0,
        lot=None,
        commentaire=None,
    )


def _categorie_id(type_categorie: str) -> int:
    return int(get_all_categories(type_categorie)[0]["id"])


def _compte_id() -> int:
    return int(get_all_comptes()[0]["id"])


def test_sauvegarde_sans_permission_error(tmp_db: Path):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO config (nom_asso) VALUES (?)", ("Asso test",))
        conn.commit()
        backup_path = backup_db(tmp_db, tmp_db.parent)
    finally:
        conn.close()
    assert backup_path.exists()
    assert backup_path.read_bytes().startswith(b"SQLite format 3")


def test_stock_calcul_avec_sorties():
    article_id = _article_id()
    add_mouvement(article_id, "2026-07-11", "Entrée marchandise", 50, 1.0, None, None, None, None)
    add_mouvement(article_id, "2026-07-11", "Sortie buvette", 26, None, None, None, None, None)

    article = get_article_by_id(article_id)
    assert article is not None
    assert int(article["quantite"]) == 24


def test_stock_entree_puis_sortie():
    article_id = _article_id(quantite=0)
    add_mouvement(article_id, "2026-07-11", "Entrée marchandise", 12, 1.0, None, None, None, None)
    add_mouvement(article_id, "2026-07-11", "Sortie buvette", 5, None, None, None, None, None)

    article = get_article_by_id(article_id)
    assert article is not None
    assert int(article["quantite"]) == 7


def test_budget_evenement_id_valide():
    evenement_id = _event_id()
    budget = get_or_create_budget(evenement_id)

    assert int(budget["evenement_id"]) == evenement_id


def test_tableau_modifier_ligne():
    evenement_id = _event_id()
    tableau_id = add_tableau(evenement_id, "Participants", None, 0)
    nom_id = add_colonne(tableau_id, "Nom", "texte", None, 0, 0, 150)
    montant_id = add_colonne(tableau_id, "Montant", "montant", None, 0, 1, 120)
    ligne_id = add_ligne(tableau_id, None, "normal", 0)

    assert update_ligne(ligne_id, {nom_id: "Alice", montant_id: "12,50"})

    cellules = get_cellules_ligne(ligne_id)
    assert cellules[nom_id] == "Alice"
    assert cellules[montant_id] == "12,50"


def test_tombola_solidaire_ajout_participant():
    evenement_id = _event_id()
    participation_id = add_participation_solidaire(
        evenement_id, "Durand", "Camille", "06 12 34 56 78", 10.0, "Merci"
    )

    participations = get_participations_solidaires(evenement_id)
    assert any(p["id"] == participation_id for p in participations)


def test_tombola_solidaire_tirage():
    evenement_id = _event_id()
    add_participation_solidaire(evenement_id, "Durand", "Camille", None, 10.0, None)
    add_participation_solidaire(evenement_id, "Martin", "Léa", None, 15.0, None)

    gagnant = effectuer_tirage_tombola_solidaire(evenement_id, seed=7)

    participations = get_participations_solidaires(evenement_id)
    assert gagnant is not None
    assert sum(int(p["est_gagnant"]) for p in participations) == 1


def test_tombola_solidaire_total_dons():
    evenement_id = _event_id()
    add_participation_solidaire(evenement_id, "A", "B", None, 10.0, None)
    add_participation_solidaire(evenement_id, "C", "D", None, 15.5, None)

    assert get_total_dons_tombola_solidaire(evenement_id) == 25.5


def test_stand_avec_responsable():
    evenement_id = _event_id()
    add_stand(
        evenement_id,
        "A1",
        "Stand pêche",
        "location",
        None,
        "Mme Dupont",
        50.0,
        "recette",
        0,
        "Test",
        responsable="Mme Dupont",
        telephone="06 00 00 00 00",
        emplacement="Allée B - N°3",
    )

    stand = get_stands_evenement(evenement_id)[0]
    assert stand["responsable"] == "Mme Dupont"
    assert stand["telephone"] == "06 00 00 00 00"
    assert stand["emplacement"] == "Allée B - N°3"


def test_evenement_modules_actifs():
    evenement_id = add_evenement(
        "Modules",
        "Fête",
        None,
        "2026-07-11",
        None,
        "planifie",
        None,
        serialiser_modules_actifs(["billetterie", "stands"]),
    )

    evenement = get_evenement_by_id(evenement_id)
    assert evenement is not None
    assert get_modules_actifs_evenement(evenement_id) == ["billetterie", "stands"]


def test_evenement_modules_filtres_onglets():
    assert modules_actifs_depuis_json(None) == list(MODULES_EVENEMENT_DISPONIBLES)
    assert modules_actifs_depuis_json('["depenses","budget_previsionnel"]') == [
        "depenses",
        "budget_previsionnel",
    ]


def test_subvention_montant_obtenu():
    subvention_id = add_subvention(
        "Mairie",
        "mairie",
        2026,
        "Projet été",
        500.0,
        "2026-03-01",
        None,
    )
    assert update_subvention(subvention_id, montant_obtenu=350.0)

    subvention = next(s for s in get_all_subventions() if s["id"] == subvention_id)
    assert float(subvention["montant_obtenu"]) == 350.0


def test_subvention_modifier_statut():
    subvention_id = add_subvention(
        "Département",
        "departement",
        2026,
        "Projet hiver",
        800.0,
        "2026-02-01",
        None,
    )
    assert update_subvention(subvention_id, statut="partielle")

    subvention = next(s for s in get_all_subventions() if s["id"] == subvention_id)
    assert subvention["statut"] == "partielle"


def test_operation_avec_moyen_paiement():
    operation_id = add_operation(
        _compte_id(),
        "depense",
        "Achat matériel",
        250.0,
        "2026-07-11",
        _categorie_id("depense"),
        "virement",
        None,
        None,
        None,
        "valide",
        0,
        "manuel",
        None,
        None,
    )

    operation = get_operation_by_id(operation_id)
    assert operation is not None
    assert operation["mode_paiement"] == "virement"


def test_operation_avec_categorie():
    categorie_id = _categorie_id("depense")
    operation_id = add_operation(
        _compte_id(),
        "depense",
        "Achat sono",
        125.0,
        "2026-07-11",
        categorie_id,
        "carte",
        None,
        None,
        None,
        "valide",
        0,
        "manuel",
        None,
        None,
    )

    operation = get_operation_by_id(operation_id)
    assert operation is not None
    assert int(operation["categorie_id"]) == categorie_id
