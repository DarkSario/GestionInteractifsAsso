"""Tests Phase 6b — Clôture d'exercice."""

from __future__ import annotations

import hashlib


from db.connection import set_db_file
from db.migrations.runner import run_migrations
from db.models.cloture import (
    add_exercice,
    cloturer_exercice,
    decloturer_exercice,
    get_exercice_by_id,
    get_log_exercice,
    get_stats_exercice,
    is_periode_cloturee,
)
from db.models.securite import (
    _hasher_secret,
    _verifier_secret,
    changer_mot_de_passe_decloture,
    hash_password,
    initialiser_secrets,
    reset_mot_de_passe_via_master,
    verifier_code_master,
    verifier_mot_de_passe_decloture,
)
from db.models.tresorerie import (
    add_operation,
    get_all_categories,
    get_all_comptes,
    get_operation_by_id,
)
from core.cloture import (
    calculer_solde_cloture,
    generer_nom_exercice,
    verifier_chevauchement,
)

# Valeurs de test (non réelles — générées dynamiquement pour chaque suite)
_MDP_TEST = "mdp_de_test_phase14"
_MASTER_TEST = "master_de_test_phase14"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _setup(tmp_db):
    set_db_file(str(tmp_db))
    run_migrations()
    # Initialiser avec des valeurs connues pour les tests
    initialiser_secrets(mdp_initial=_MDP_TEST, code_master_initial=_MASTER_TEST)


def _compte_principal_id() -> int:
    comptes = get_all_comptes()
    return int(next(c for c in comptes if int(c.get("est_principal") or 0) == 1)["id"])


def _categorie_recette_id() -> int:
    return int(get_all_categories("recette")[0]["id"])


def _categorie_depense_id() -> int:
    return int(get_all_categories("depense")[0]["id"])


def _add_op(compte_id, type_op, libelle, montant, date_op, cat_id, statut="valide"):
    return add_operation(
        compte_id, type_op, libelle, montant, date_op,
        cat_id, "especes", None, None, None, statut, 0, None, None, None,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_creation_exercice(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025-2026", "scolaire", "2025-09-01", "2026-08-31", 500.0, "Test")
    assert ex_id > 0
    ex = get_exercice_by_id(ex_id)
    assert ex is not None
    assert ex["nom"] == "2025-2026"
    assert ex["type_exercice"] == "scolaire"
    assert ex["statut"] == "ouvert"
    assert float(ex["solde_ouverture"]) == 500.0
    set_db_file("")


def test_cloture_exercice_calcul_solde(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()
    cat_d = _categorie_depense_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 200.0)
    _add_op(compte_id, "recette", "Recette A", 1000.0, "2025-03-15", cat_r)
    _add_op(compte_id, "depense", "Dépense B", 300.0, "2025-06-01", cat_d)

    solde = calculer_solde_cloture(ex_id)
    # solde_ouverture(200) + recettes(1000) - dépenses(300) = 900
    assert abs(solde - 900.0) < 0.01

    ok = cloturer_exercice(ex_id, solde)
    assert ok is True

    ex = get_exercice_by_id(ex_id)
    assert ex["statut"] == "cloture"
    assert abs(float(ex["solde_cloture"]) - 900.0) < 0.01
    assert ex["date_cloture"] is not None
    set_db_file("")


def test_operations_gelees_apres_cloture(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    op_id = _add_op(compte_id, "recette", "Op test", 500.0, "2025-05-01", cat_r)

    cloturer_exercice(ex_id, 500.0)

    op = get_operation_by_id(op_id)
    assert op is not None
    assert op["statut"] == "rapproche", f"Statut attendu 'rapproche', obtenu '{op['statut']}'"
    set_db_file("")


def test_operations_degelees_apres_decloture(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    op_id = _add_op(compte_id, "recette", "Op test", 500.0, "2025-05-01", cat_r)

    cloturer_exercice(ex_id, 500.0)
    op = get_operation_by_id(op_id)
    assert op["statut"] == "rapproche"

    decloturer_exercice(ex_id)
    op = get_operation_by_id(op_id)
    assert op is not None
    assert op["statut"] == "valide", f"Statut attendu 'valide', obtenu '{op['statut']}'"
    set_db_file("")


def test_decloture_mot_de_passe_correct(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)

    ok = decloturer_exercice(ex_id)
    assert ok is True
    ex = get_exercice_by_id(ex_id)
    assert ex["statut"] == "ouvert"
    set_db_file("")


def test_decloture_mot_de_passe_incorrect(tmp_db):
    _setup(tmp_db)
    assert verifier_mot_de_passe_decloture("mauvais_mdp") is False
    assert verifier_mot_de_passe_decloture(_MDP_TEST) is True
    set_db_file("")


def test_decloture_code_master(tmp_db):
    _setup(tmp_db)
    assert verifier_code_master(_MASTER_TEST) is True
    assert verifier_code_master("mauvais_code") is False
    set_db_file("")


def test_reset_mdp_via_code_master(tmp_db):
    _setup(tmp_db)
    # D'abord changer le mot de passe
    ok, _ = changer_mot_de_passe_decloture(_MDP_TEST, "nouveau_mdp")
    assert ok is True
    # Vérifier que le nouveau mot de passe fonctionne
    assert verifier_mot_de_passe_decloture("nouveau_mdp") is True
    # Reset via code master
    ok, nouveau_mdp = reset_mot_de_passe_via_master(_MASTER_TEST)
    assert ok is True
    assert nouveau_mdp  # Un nouveau mot de passe aléatoire a été généré
    # Après reset, le nouveau mot de passe généré doit fonctionner
    assert verifier_mot_de_passe_decloture(nouveau_mdp) is True
    set_db_file("")


def test_changer_mot_de_passe(tmp_db):
    _setup(tmp_db)
    # Changement avec ancien mot de passe correct
    ok, msg = changer_mot_de_passe_decloture(_MDP_TEST, "nouveauMDP123")
    assert ok is True
    assert verifier_mot_de_passe_decloture("nouveauMDP123") is True

    # Changement avec mauvais ancien mot de passe
    ok, msg = changer_mot_de_passe_decloture("faux_mdp", "autremdp")
    assert ok is False
    assert msg

    # Changement avec code master à la place de l'ancien mot de passe
    ok, msg = changer_mot_de_passe_decloture(_MASTER_TEST, "mdp_via_master")
    assert ok is True
    assert verifier_mot_de_passe_decloture("mdp_via_master") is True
    set_db_file("")


def test_is_periode_cloturee(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2024", "civile", "2024-01-01", "2024-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)

    assert is_periode_cloturee("2024-06-15") is True
    assert is_periode_cloturee("2025-01-01") is False
    set_db_file("")


def test_chevauchement_exercices(tmp_db):
    _setup(tmp_db)
    add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)

    # Chevauchement → doit retourner True
    assert verifier_chevauchement("2025-06-01", "2026-05-31", "civile") is True
    # Pas de chevauchement sur un autre type
    assert verifier_chevauchement("2025-06-01", "2026-05-31", "scolaire") is False
    # Période strictement après → pas de chevauchement
    assert verifier_chevauchement("2026-01-01", "2026-12-31", "civile") is False
    set_db_file("")


def test_log_cloture_decloture(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    cloturer_exercice(ex_id, 0.0)
    decloturer_exercice(ex_id)

    logs = get_log_exercice(ex_id)
    assert len(logs) == 2
    actions = [log["action"] for log in logs]
    assert "cloture" in actions
    assert "decloture" in actions
    set_db_file("")


def test_stats_exercice(tmp_db):
    _setup(tmp_db)
    compte_id = _compte_principal_id()
    cat_r = _categorie_recette_id()
    cat_d = _categorie_depense_id()

    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 100.0)
    _add_op(compte_id, "recette", "R1", 500.0, "2025-02-01", cat_r)
    _add_op(compte_id, "recette", "R2", 200.0, "2025-07-15", cat_r)
    _add_op(compte_id, "depense", "D1", 150.0, "2025-04-10", cat_d)

    stats = get_stats_exercice(ex_id)
    assert abs(stats["total_recettes"] - 700.0) < 0.01
    assert abs(stats["total_depenses"] - 150.0) < 0.01
    # solde_ouverture(100) + recettes(700) - dépenses(150) = 650
    assert abs(stats["solde_final"] - 650.0) < 0.01
    assert stats["nb_operations"] == 3
    set_db_file("")


def test_generer_nom_exercice():
    assert generer_nom_exercice("scolaire", "2025-09-01") == "2025-2026"
    assert generer_nom_exercice("civile", "2025-01-01") == "2025"
    assert generer_nom_exercice("scolaire", "2024-09-01") == "2024-2025"


# ── Tests des nouvelles fonctions de hachage (Phase 14) ──────────────────────


def test_hasher_secret_avec_sel():
    """Le hash scrypt inclut bien un sel (format sel_hex$hash_hex)."""
    h1 = _hasher_secret("mon_secret")
    h2 = _hasher_secret("mon_secret")
    assert "$" in h1
    assert "$" in h2
    # Deux hashes du même secret sont différents (sel aléatoire)
    assert h1 != h2


def test_verifier_secret_correct():
    """La vérification scrypt retourne True pour un secret correct."""
    secret = "test_verif_correct"
    stocke = _hasher_secret(secret)
    assert _verifier_secret(secret, stocke) is True


def test_verifier_secret_incorrect():
    """La vérification scrypt retourne False pour un secret incorrect."""
    stocke = _hasher_secret("bon_secret")
    assert _verifier_secret("mauvais_secret", stocke) is False


def test_retrocompat_sha256():
    """La vérification accepte les anciens hashes SHA-256 (sans sel)."""
    secret = "ancien_secret_sha256"
    hash_sha256 = hashlib.sha256(secret.encode()).hexdigest()
    # Doit fonctionner (format héritage : pas de $ dans le hash)
    assert "$" not in hash_sha256
    assert _verifier_secret(secret, hash_sha256) is True
    assert _verifier_secret("mauvais", hash_sha256) is False


def test_hash_password_format_scrypt():
    """hash_password retourne désormais un hash scrypt (contient '$')."""
    h = hash_password("test_mdp")
    assert "$" in h


def test_initialiser_secrets_idempotent(tmp_db):
    """initialiser_secrets n'écrase pas les valeurs déjà stockées."""
    set_db_file(str(tmp_db))
    run_migrations()
    initialiser_secrets(mdp_initial="premier_mdp", code_master_initial="premier_master")
    # Second appel avec d'autres valeurs : ne doit pas écraser
    initialiser_secrets(mdp_initial="autre_mdp", code_master_initial="autre_master")
    assert verifier_mot_de_passe_decloture("premier_mdp") is True
    assert verifier_mot_de_passe_decloture("autre_mdp") is False
    set_db_file("")


# ── PR10 : verrouillage des périodes clôturées ───────────────────────────────


def _ctx():
    return _compte_principal_id(), _categorie_recette_id()


def test_decloture_ne_touche_pas_rapprochements_preexistants(tmp_db):
    _setup(tmp_db)
    compte, cat = _ctx()
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    deja = _add_op(compte, "recette", "Déjà rapprochée", 10.0, "2025-02-01", cat, "rapproche")
    valide = _add_op(compte, "recette", "Valide", 20.0, "2025-03-01", cat)

    assert cloturer_exercice(ex_id, 30.0)
    assert decloturer_exercice(ex_id)

    assert get_operation_by_id(deja)["statut"] == "rapproche"
    assert get_operation_by_id(valide)["statut"] == "valide"


def test_exercices_chevauchants_statuts_preserves(tmp_db):
    _setup(tmp_db)
    compte, cat = _ctx()
    a = add_exercice("A", "civile", "2025-01-01", "2025-12-31", 0.0)
    b = add_exercice("B", "scolaire", "2025-09-01", "2026-08-31", 0.0)
    commun = _add_op(compte, "recette", "Commun", 10.0, "2025-10-01", cat)
    seul_b = _add_op(compte, "recette", "Seul B", 10.0, "2026-02-01", cat)

    assert cloturer_exercice(a, 10.0)
    assert cloturer_exercice(b, 20.0)
    # Réouvrir A : l'opération commune reste verrouillée par B
    assert decloturer_exercice(a)
    assert get_operation_by_id(commun)["statut"] == "rapproche"
    assert get_operation_by_id(seul_b)["statut"] == "rapproche"
    # Réouvrir B : tout revient à l'état d'origine
    assert decloturer_exercice(b)
    assert get_operation_by_id(commun)["statut"] == "valide"
    assert get_operation_by_id(seul_b)["statut"] == "valide"


def test_ecritures_refusees_en_periode_cloturee(tmp_db):
    import pytest

    from db.models.cloture import PeriodeClotureeError
    from db.models.tresorerie import (
        annuler_operation,
        delete_operation,
        update_operation,
        upsert_operation_auto,
    )
    from db.connection import get_connection

    _setup(tmp_db)
    compte, cat = _ctx()
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    op = _add_op(compte, "recette", "Op", 10.0, "2025-05-01", cat)
    hors = _add_op(compte, "recette", "Hors", 10.0, "2026-05-01", cat)
    conn = get_connection()
    upsert_operation_auto(
        conn, "don", 1, type_operation="recette", libelle="Don", montant=5.0,
        date_operation="2025-06-01", categorie_id=cat, mode_paiement="especes",
        commentaire=None,
    )
    conn.commit()
    conn.close()
    assert cloturer_exercice(ex_id, 15.0)

    with pytest.raises(PeriodeClotureeError):
        _add_op(compte, "recette", "Nouvelle", 1.0, "2025-07-01", cat)
    assert update_operation(op, montant=99.0) is False
    assert update_operation(hors, date_operation="2025-07-01") is False
    assert annuler_operation(op) is False
    assert delete_operation(op) is False
    assert float(get_operation_by_id(op)["montant"]) == 10.0

    conn = get_connection()
    try:
        with pytest.raises(PeriodeClotureeError):
            upsert_operation_auto(
                conn, "don", 1, type_operation="recette", libelle="Don", montant=500.0,
                date_operation="2025-06-01", categorie_id=cat, mode_paiement="especes",
                commentaire=None,
            )
        with pytest.raises(PeriodeClotureeError):
            upsert_operation_auto(
                conn, "don", 2, type_operation="recette", libelle="Don2", montant=1.0,
                date_operation="2025-08-01", categorie_id=cat, mode_paiement="especes",
                commentaire=None,
            )
    finally:
        conn.close()
    # Hors période : toujours modifiable
    assert update_operation(hors, montant=11.0) is True
    # Après réouverture : modifiable
    assert decloturer_exercice(ex_id)
    assert update_operation(op, montant=99.0) is True


def test_commentaire_cloture_journalise(tmp_db):
    _setup(tmp_db)
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    assert cloturer_exercice(ex_id, 0.0, "Validé en AG")
    logs = get_log_exercice(ex_id)
    assert logs[0]["action"] == "cloture"
    assert logs[0]["commentaire"] == "Validé en AG"


def test_cloture_refusee_avec_operations_en_attente(tmp_db):
    _setup(tmp_db)
    compte, cat = _ctx()
    ex_id = add_exercice("2025", "civile", "2025-01-01", "2025-12-31", 0.0)
    _add_op(compte, "recette", "Attente", 1.0, "2025-02-01", cat, "en_attente")
    assert cloturer_exercice(ex_id, 0.0) is False
    assert get_exercice_by_id(ex_id)["statut"] == "ouvert"
