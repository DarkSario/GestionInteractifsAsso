"""Couche métier du module Dons."""

from __future__ import annotations

from datetime import date

from core.parametres import get_infos_asso
from core.recus_fiscaux import (
    generer_pdf_markdown,
    get_template_attestation,
    get_template_cerfa,
    render_template,
)
from db.models.dons import get_don_by_id, update_don
from db.models.parametres_globaux import get_parametre
from db.models.tresorerie import add_operation, get_all_categories, get_all_comptes


def _nom_donateur(don: dict) -> str:
    return f"{(don.get('donateur_nom') or '').strip()} {(don.get('donateur_prenom') or '').strip()}".strip()


def _get_compte_recette_defaut() -> int:
    comptes = get_all_comptes(actif_only=True)
    if not comptes:
        return 0
    compte_principal = get_parametre('compte_principal_id', '').strip()
    for compte in comptes:
        try:
            compte_id = int(compte['id'])
        except (TypeError, ValueError, KeyError):
            continue
        if str(compte_id) == compte_principal:
            return compte_id
    for compte in comptes:
        try:
            return int(compte['id'])
        except (TypeError, ValueError, KeyError):
            continue
    return 0


def get_type_recu_defaut() -> str:
    type_recu = get_parametre('type_recu_don', 'cerfa').strip().lower()
    return type_recu if type_recu in {'cerfa', 'simple'} else 'cerfa'


def _mode_versement_libelle(code: str | None) -> str:
    mapping = {
        'cheque': 'Chèque',
        'virement': 'Virement',
        'especes': 'Espèces',
        'cb': 'Carte bancaire',
        'autre': 'Autre',
    }
    return mapping.get((code or '').lower(), code or '—')


def _collecter_donnees_recu(don_id: int) -> dict:
    don = get_don_by_id(don_id)
    if not don:
        raise ValueError('Don introuvable.')

    infos_asso = get_infos_asso()
    type_donateur = (don.get('type_donateur') or 'particulier').lower()
    nature = (don.get('nature_don') or 'argent').lower()
    taux = '60 %' if type_donateur == 'entreprise' else '66 %'
    mention_fiscale = (
        "Le présent reçu ouvre droit à la réduction d'impôt prévue par les articles 200 et 238 bis du CGI."
        if get_type_recu_defaut() == 'cerfa'
        else 'Attestation délivrée à titre de justificatif interne de l’association.'
    )
    montant_affiche = float(don.get('montant') or 0)
    valeur_estimee = float(don.get('valeur_estimee') or 0)

    return {
        'nom_asso': infos_asso.get('nom') or 'Association',
        'adresse_asso': infos_asso.get('adresse') or '',
        'num_habilitation': get_parametre('num_habilitation_fiscale', ''),
        'num_recu': don.get('num_recu') or '',
        'date_don': don.get('date_don') or '',
        'date_emission': don.get('date_emission_recu') or date.today().strftime('%d/%m/%Y'),
        'exercice': str(don.get('exercice_id') or ''),
        'donateur_nom': don.get('donateur_nom') or '',
        'donateur_prenom': don.get('donateur_prenom') or '',
        'donateur_adresse': don.get('donateur_adresse') or '',
        'donateur_cp': don.get('donateur_cp') or '',
        'donateur_ville': don.get('donateur_ville') or '',
        'donateur_siret': don.get('donateur_siret') or '',
        'montant': f'{montant_affiche:.2f}',
        'nature_don': 'Don en nature' if nature == 'nature' else 'Don en argent',
        'description_don': don.get('description_don') or '',
        'valeur_estimee': f'{valeur_estimee:.2f}',
        'mode_versement': _mode_versement_libelle(don.get('mode_versement')),
        'mention_fiscale': mention_fiscale,
        'taux_deduction': taux,
        'si_entreprise': type_donateur == 'entreprise',
        'si_nature': nature == 'nature',
    }


def generer_pdf_recu_don(don_id: int, chemin_destination: str) -> dict:
    donnees = _collecter_donnees_recu(don_id)
    type_recu = get_type_recu_defaut()
    template = get_template_cerfa() if type_recu == 'cerfa' else get_template_attestation()
    rendu = render_template(template, donnees)
    return generer_pdf_markdown(rendu, chemin_destination)


def creer_recette_tresorerie(don_id: int) -> int:
    don = get_don_by_id(don_id)
    if not don or (don.get('nature_don') or 'argent') != 'argent':
        return 0
    if don.get('tresorerie_id'):
        return int(don['tresorerie_id'])

    compte_id = _get_compte_recette_defaut()
    if not compte_id:
        return 0
    categories = get_all_categories('recette')
    categorie_id = int(categories[0]['id']) if categories else None
    montant = float(don.get('montant') or 0)
    if montant <= 0:
        return 0

    operation_id = add_operation(
        compte_id=compte_id,
        type_operation='recette',
        libelle=f"Don - {_nom_donateur(don)}".strip(),
        montant=montant,
        date_operation=don.get('date_don') or date.today().isoformat(),
        categorie_id=categorie_id,
        mode_paiement=don.get('mode_versement') or 'autre',
        numero_facture=don.get('num_recu') or None,
        evenement_id=None,
        fournisseur_id=None,
        statut='valide',
        est_automatique=0,
        source_module='don',
        source_id=don_id,
        commentaire=don.get('commentaire') or None,
    )
    update_don(don_id, tresorerie_id=operation_id)
    return int(operation_id)
