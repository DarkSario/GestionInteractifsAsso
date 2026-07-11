from __future__ import annotations

from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.evenements import (
    add_evenement,
    get_evenement_by_id,
    get_modules_actifs_evenement,
    serialiser_modules_actifs,
    update_evenement,
)
from db.models.stands import get_stands_evenement
from db.models.tombola import effectuer_tirage_tombola_solidaire, get_lots_evenement, get_participations_solidaires
from db.models.tresorerie import get_all_categories, get_all_comptes, get_all_subventions, get_operation_by_id, get_remises
from ui.modules.evenements.stands import enregistrer_stand_depuis_formulaire
from ui.modules.evenements.tombola import (
    enregistrer_lot_depuis_formulaire,
    enregistrer_participation_solidaire_depuis_formulaire,
)
from ui.modules.tresorerie.operations import enregistrer_operation_depuis_formulaire
from ui.modules.tresorerie.remises import enregistrer_remise_depuis_formulaire
from ui.modules.tresorerie.subventions import enregistrer_subvention_depuis_formulaire



def _event_id(nom: str = "Événement Phase 13-bis") -> int:
    return add_evenement(nom, "Fête", None, "2026-07-11", None, "planifie", None)



def _compte_id() -> int:
    return int(get_all_comptes()[0]["id"])



def _categorie_id(type_categorie: str) -> int:
    return int(get_all_categories(type_categorie)[0]["id"])



def test_remise_cheque_formulaire_complet(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    remise_id = enregistrer_remise_depuis_formulaire(
        {
            "date_remise": "2026-07-11",
            "compte_id": _compte_id(),
            "nombre_cheques": "3",
            "montant_total": "360,00",
            "numero_bordereau": "BRD-2026-001",
            "commentaire": "Remise fête",
        }
    )

    remise = next(r for r in get_remises() if int(r["id"]) == remise_id)
    assert int(remise["nombre_cheques"]) == 3
    assert float(remise["montant_total"]) == 360.0
    assert remise["numero_bordereau"] == "BRD-2026-001"



def test_subvention_montant_obtenu_sauvegarde(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    subvention_id = enregistrer_subvention_depuis_formulaire(
        {
            "organisme": "Mairie",
            "objet": "Projet été",
            "montant_demande": "500,00",
            "montant_obtenu": "350,00",
            "date_demande": "2026-03-01",
            "date_obtention": "2026-06-15",
            "statut": "obtenue",
            "commentaire": "Accord partiel",
        }
    )

    subvention = next(s for s in get_all_subventions() if int(s["id"]) == subvention_id)
    assert float(subvention["montant_obtenu"]) == 350.0
    assert subvention["date_decision"] == "2026-06-15"



def test_subvention_statut_modifiable(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    subvention_id = enregistrer_subvention_depuis_formulaire(
        {
            "organisme": "Département",
            "objet": "Projet hiver",
            "montant_demande": "800,00",
            "date_demande": "2026-02-01",
            "statut": "en_attente",
        }
    )
    enregistrer_subvention_depuis_formulaire(
        {
            "organisme": "Département",
            "objet": "Projet hiver",
            "montant_demande": "800,00",
            "montant_obtenu": "400,00",
            "date_demande": "2026-02-01",
            "date_obtention": "2026-05-10",
            "statut": "partielle",
        },
        subvention_id=subvention_id,
    )

    subvention = next(s for s in get_all_subventions() if int(s["id"]) == subvention_id)
    assert subvention["statut"] == "partielle"



def test_operation_tous_champs_sauvegardes(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    categorie_id = _categorie_id("depense")
    operation_id = enregistrer_operation_depuis_formulaire(
        {
            "type_operation": "depense",
            "libelle": "Achat matériel",
            "montant": "250,00",
            "date_operation": "2026-07-11",
            "categorie_id": categorie_id,
            "mode_paiement": "virement",
            "statut": "en_attente",
            "compte_id": _compte_id(),
            "commentaire": "Commande sono",
        }
    )

    operation = get_operation_by_id(operation_id)
    assert operation is not None
    assert operation["date_operation"] == "2026-07-11"
    assert int(operation["categorie_id"]) == categorie_id
    assert operation["mode_paiement"] == "virement"
    assert operation["statut"] == "en_attente"
    assert operation["commentaire"] == "Commande sono"



def test_tombola_lot_formulaire_riche(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    lot_id = enregistrer_lot_depuis_formulaire(
        evenement_id,
        {
            "numero": "1",
            "description": "Panier garni",
            "valeur_estimee": "45,00",
            "donateur": "Leclerc",
            "statut": "Disponible",
            "numero_gagnant": "",
            "commentaire": "Lot principal",
        },
    )

    lot = next(l for l in get_lots_evenement(evenement_id) if int(l["id"]) == lot_id)
    assert float(lot["valeur_estimee"]) == 45.0
    assert lot["donateur"] == "Leclerc"



def test_tombola_solidaire_ajout_participant(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    participation_id = enregistrer_participation_solidaire_depuis_formulaire(
        evenement_id,
        {
            "nom": "Dupont",
            "prenom": "Marie",
            "telephone": "06 12 34 56 78",
            "montant_don": "10,00",
            "commentaire": "Merci",
        },
    )

    participations = get_participations_solidaires(evenement_id)
    assert any(int(p["id"]) == participation_id for p in participations)



def test_tombola_solidaire_tirage(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    enregistrer_participation_solidaire_depuis_formulaire(evenement_id, {"nom": "Dupont", "prenom": "Marie", "montant_don": "10,00"})
    enregistrer_participation_solidaire_depuis_formulaire(evenement_id, {"nom": "Martin", "prenom": "Paul", "montant_don": "20,00"})

    gagnant = effectuer_tirage_tombola_solidaire(evenement_id, seed=2)

    participations = get_participations_solidaires(evenement_id)
    assert gagnant is not None
    assert sum(int(p["est_gagnant"]) for p in participations) == 1



def test_tombola_solidaire_tirage_unique(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    enregistrer_participation_solidaire_depuis_formulaire(evenement_id, {"nom": "A", "prenom": "B", "montant_don": "5,00"})
    enregistrer_participation_solidaire_depuis_formulaire(evenement_id, {"nom": "C", "prenom": "D", "montant_don": "7,00"})
    effectuer_tirage_tombola_solidaire(evenement_id, seed=1)
    effectuer_tirage_tombola_solidaire(evenement_id, seed=3)

    participations = get_participations_solidaires(evenement_id)
    assert sum(int(p["est_gagnant"]) for p in participations) == 1



def test_stand_responsable_sauvegarde(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    stand_id = enregistrer_stand_depuis_formulaire(
        evenement_id,
        {
            "nom_stand": "Stand pêche",
            "type_ui": "Location",
            "responsable": "Mme Dupont",
            "telephone": "06 00 00 00 00",
            "emplacement": "Allée B - N°3",
            "type_location": "Recette",
            "montant_location": "50,00",
            "statut": "Confirmé",
            "commentaire": "Test",
        },
    )

    stand = next(s for s in get_stands_evenement(evenement_id) if int(s["id"]) == stand_id)
    assert stand["responsable"] == "Mme Dupont"
    assert stand["telephone"] == "06 00 00 00 00"



def test_evenement_modules_selection_creation(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    modules_json = serialiser_modules_actifs(["billetterie", "depenses", "stands"])
    evenement_id = add_evenement(
        "Modules",
        "Fête",
        None,
        "2026-07-11",
        None,
        "planifie",
        None,
        modules_json,
    )

    evenement = get_evenement_by_id(evenement_id)
    assert evenement is not None
    assert evenement["modules_actifs_json"] == modules_json



def test_evenement_modules_modification(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()

    evenement_id = _event_id()
    modules_json = serialiser_modules_actifs(["depenses", "stands", "tombola_solidaire"])
    assert update_evenement(evenement_id, modules_actifs_json=modules_json)

    assert get_modules_actifs_evenement(evenement_id) == ["depenses", "stands", "tombola_solidaire"]
