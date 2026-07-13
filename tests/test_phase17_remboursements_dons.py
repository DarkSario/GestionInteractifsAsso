from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def db_phase17(tmp_db: Path):
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    db_module.set_db_file(str(tmp_db))
    run_migrations()
    conn = db_module.get_connection()
    conn.execute(
        """
        INSERT INTO membres (nom, prenom, statut, date_adhesion, statut_archive)
        VALUES ('Dupont', 'Alice', 'Actif', '2024-09-01', 0),
               ('Martin', 'Bob', 'Bénévole', '2024-09-01', 0)
        """
    )
    conn.commit()
    yield conn
    conn.close()
    db_module.set_db_file('')


def _creer_compte() -> int:
    from db.models.tresorerie import add_compte

    return add_compte('Compte principal', 'bancaire', 0, 1, 0, '', '', 1)


def _creer_evenement() -> int:
    from db.models.evenements import add_evenement

    return add_evenement('Fête des écoles', 'Fête', 'Test', '2026-05-10', '2026-05-10', 'planifie', 1000.0)


def test_migration_phase17_cree_table_dons_et_colonnes(db_phase17):
    colonnes_depenses = {row['name'] for row in db_phase17.execute("PRAGMA table_info(evenement_depenses)").fetchall()}
    colonnes_treso = {row['name'] for row in db_phase17.execute("PRAGMA table_info(tresorerie_operations)").fetchall()}
    tables = {row['name'] for row in db_phase17.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}

    assert 'dons' in tables
    assert {'avance_par_membre_id', 'remboursement_statut', 'remboursement_date', 'remboursement_mode', 'remboursement_reference'}.issubset(colonnes_depenses)
    assert {'avance_par_membre_id', 'remboursement_statut', 'remboursement_date', 'remboursement_mode', 'remboursement_reference'}.issubset(colonnes_treso)


def test_remboursements_evenement_et_tresorerie(db_phase17):
    from db.models.evenements import add_depense
    from db.models.remboursements import get_remboursements_all, get_stats_remboursements, marquer_rembourse
    from ui.modules.tresorerie.operations import enregistrer_operation_depuis_formulaire

    membre_id = db_phase17.execute("SELECT id FROM membres WHERE nom = 'Dupont'").fetchone()['id']
    evenement_id = _creer_evenement()
    depense_id = add_depense(
        evenement_id=evenement_id,
        libelle='Achat matériel',
        montant=42.5,
        date='2026-05-01',
        categorie='Matériel',
        fournisseur_id=None,
        mode_paiement='cheque',
        commentaire='Avance bénévole',
        avance_par_membre_id=membre_id,
        remboursement_statut='en_attente',
    )
    _creer_compte()
    operation_id = enregistrer_operation_depuis_formulaire({
        'type_operation': 'depense',
        'libelle': 'Fournitures bureau',
        'montant': '18,90',
        'date_operation': '2026-05-03',
        'mode_paiement': 'cb',
        'statut': 'valide',
        'avance_par_membre_id': membre_id,
        'remboursement_statut': 'en_attente',
        'commentaire': 'Papeterie',
    })

    lignes = get_remboursements_all({'statut': 'en_attente'})
    assert {ligne['source'] for ligne in lignes} == {'evenement', 'tresorerie'}
    assert any(ligne['source_id'] == depense_id for ligne in lignes)
    assert any(ligne['source_id'] == operation_id for ligne in lignes)

    stats = get_stats_remboursements()
    assert stats['nb_remboursements'] == 2
    assert stats['total_en_attente'] == pytest.approx(61.4)

    assert marquer_rembourse('evenement', depense_id, 'Chèque', 'CHK-01', '2026-05-15', 'Remboursé en caisse') is True
    maj = db_phase17.execute(
        'SELECT remboursement_statut, remboursement_reference, commentaire FROM evenement_depenses WHERE id = ?',
        (depense_id,),
    ).fetchone()
    assert maj['remboursement_statut'] == 'rembourse'
    assert maj['remboursement_reference'] == 'CHK-01'
    assert maj['commentaire'] == 'Remboursé en caisse'


def test_dons_crud_et_numero_recu(db_phase17):
    from db.models.dons import add_don, get_all_dons, get_don_by_id, get_prochain_num_recu, get_stats_dons, marquer_recu_emis, update_don

    membre_id = db_phase17.execute("SELECT id FROM membres WHERE nom = 'Martin'").fetchone()['id']
    don_id = add_don(
        date_don='2026-06-10',
        type_donateur='entreprise',
        membre_id=membre_id,
        donateur_nom='Entreprise Locale',
        donateur_prenom='',
        nature_don='argent',
        montant=500.0,
        mode_versement='virement',
    )
    don = get_don_by_id(don_id)
    assert don is not None
    assert don['num_recu'] == '2026-001'
    assert get_prochain_num_recu(2026) == '2026-002'

    assert update_don(don_id, commentaire='Soutien fête') is True
    assert marquer_recu_emis(don_id) is True
    don = get_don_by_id(don_id)
    assert don['statut_recu'] == 'emis'

    stats = get_stats_dons(None)
    assert stats['montant_total'] == pytest.approx(500.0)
    assert stats['nb_donateurs'] == 1
    assert len(get_all_dons({'statut_recu': 'emis'})) == 1


def test_templates_recus_et_remboursement(tmp_path):
    import core.recus_fiscaux as recus

    original = {
        'cerfa': recus._paths('cerfa'),
        'attestation': recus._paths('attestation'),
        'remboursement': recus._paths('remboursement'),
    }
    try:
        for cle in ('cerfa', 'attestation', 'remboursement'):
            courant = tmp_path / f'{cle}.md'
            defaut = tmp_path / f'{cle}.default.md'
            courant.write_text('# Modifié\n', encoding='utf-8')
            defaut.write_text('# Défaut\n', encoding='utf-8')
            recus._TEMPLATE_FILES[cle] = (courant.name, defaut.name)
        recus._BASE_DIR = tmp_path

        recus.save_template_cerfa('# Cerfa test\n')
        assert recus.get_template_cerfa() == '# Cerfa test\n'
        recus.reset_template_cerfa()
        assert recus.get_template_cerfa() == '# Défaut\n'
        rendu = recus.render_template('{{#si_entreprise}}OK{{/si_entreprise}} {{nom_asso}}', {'si_entreprise': True, 'nom_asso': 'Asso'})
        assert 'OK' in rendu and 'Asso' in rendu
    finally:
        recus._BASE_DIR = original['cerfa'][0].parent
        recus._TEMPLATE_FILES['cerfa'] = (original['cerfa'][0].name, original['cerfa'][1].name)
        recus._TEMPLATE_FILES['attestation'] = (original['attestation'][0].name, original['attestation'][1].name)
        recus._TEMPLATE_FILES['remboursement'] = (original['remboursement'][0].name, original['remboursement'][1].name)


def test_collecter_bilan_inclut_dons(db_phase17):
    from core.bilan_ag import collecter_donnees_bilan
    from db.models.dons import add_don

    db_phase17.execute(
        "INSERT INTO exercices (nom, date_debut, date_fin, statut) VALUES ('2025-2026', '2025-09-01', '2026-08-31', 'ouvert')"
    )
    exercice_id = db_phase17.execute("SELECT id FROM exercices ORDER BY id DESC LIMIT 1").fetchone()['id']
    db_phase17.commit()
    add_don(
        exercice_id=exercice_id,
        date_don='2026-06-10',
        type_donateur='particulier',
        donateur_nom='Durand',
        donateur_prenom='Claire',
        nature_don='argent',
        montant=75.0,
        mode_versement='cheque',
    )
    donnees = collecter_donnees_bilan(exercice_id, 'Intro', 'Conclusion')
    assert 'tableau_dons' in donnees
    assert 'Durand' in donnees['tableau_dons']
    assert donnees['total_dons'] == '75,00 EUR'


def test_alertes_phase17(db_phase17):
    from core.alertes import get_alertes
    from db.models.dons import add_don
    from db.models.evenements import add_depense

    membre_id = db_phase17.execute("SELECT id FROM membres WHERE nom = 'Dupont'").fetchone()['id']
    evenement_id = _creer_evenement()
    add_depense(
        evenement_id=evenement_id,
        libelle='Achat déco',
        montant=15.0,
        date='2026-05-01',
        categorie='Matériel',
        fournisseur_id=None,
        mode_paiement='cheque',
        commentaire='Avance',
        avance_par_membre_id=membre_id,
        remboursement_statut='en_attente',
    )
    add_don(
        date_don='2026-06-10',
        type_donateur='particulier',
        donateur_nom='Durand',
        donateur_prenom='Claire',
        nature_don='argent',
        montant=75.0,
        mode_versement='cheque',
    )
    messages = [alerte['message'] for alerte in get_alertes()]
    assert any('remboursements de frais en attente' in message for message in messages)
    assert any('dons sans reçu émis' in message for message in messages)
