"""Couche métier du module remboursements."""

from __future__ import annotations

from datetime import date

from core.parametres import get_infos_asso
from core.recus_fiscaux import (
    generer_pdf_markdown,
    get_template_remboursement as _get_template_remboursement,
    render_template,
    reset_template_remboursement as _reset_template_remboursement,
    save_template_remboursement as _save_template_remboursement,
)
from db.models.membres import get_membre_by_id
from db.models.remboursements import get_remboursement_by_unified_id


def get_template_remboursement() -> str:
    return _get_template_remboursement()


def save_template_remboursement(contenu: str) -> None:
    _save_template_remboursement(contenu)


def reset_template_remboursement() -> None:
    _reset_template_remboursement()


def collecter_donnees_remboursement(source: str, identifiant: int) -> dict:
    ligne = get_remboursement_by_unified_id(f'{source}:{identifiant}')
    if not ligne:
        raise ValueError('Remboursement introuvable.')

    infos_asso = get_infos_asso()
    membre = get_membre_by_id(int(ligne.get('membre_id') or 0)) if ligne.get('membre_id') else None
    civilite = 'M.'
    if membre:
        statut = (membre.get('statut') or '').lower()
        civilite = 'Mme' if 'madame' in statut or 'mme' in statut else 'M.'

    reference = ligne.get('remboursement_reference') or ''
    mode = ligne.get('remboursement_mode') or 'À préciser'
    texte_certification = (
        f"L'association {infos_asso.get('nom') or 'Association'} reconnaît avoir remboursé les frais avancés "
        'pour son fonctionnement ou ses activités.'
    )
    montant = float(ligne.get('montant') or 0)
    tableau = '\n'.join([
        '| Date facture | Description | Montant |',
        '|---|---|---:|',
        f"| {ligne.get('date_piece') or ''} | {ligne.get('description') or ''} | {montant:.2f} € |",
    ])
    return {
        'nom_asso': infos_asso.get('nom') or 'Association',
        'adresse_asso': infos_asso.get('adresse') or '',
        'date_emission': date.today().strftime('%d/%m/%Y'),
        'nom_evenement': ligne.get('nom_evenement') or 'Fonctionnement association',
        'date_evenement': ligne.get('date_evenement') or (ligne.get('date_piece') or ''),
        'beneficiaire_civilite': civilite,
        'beneficiaire_nom': ligne.get('membre_nom') or '',
        'beneficiaire_prenom': ligne.get('membre_prenom') or '',
        'tableau_frais': tableau,
        'montant_total': f'{montant:.2f} €',
        'mode_remboursement': mode,
        'reference': f'({reference})' if reference else '',
        'texte_certification': texte_certification,
    }


def generer_pdf_remboursement(remboursement_id: str | int, chemin_destination: str) -> dict:
    identifiant = str(remboursement_id)
    if ':' in identifiant:
        source, source_id = identifiant.split(':', 1)
    else:
        ligne = get_remboursement_by_unified_id(identifiant)
        if not ligne:
            raise ValueError('Remboursement introuvable.')
        source, source_id = str(ligne['source']), str(ligne['source_id'])

    donnees = collecter_donnees_remboursement(source, int(source_id))
    contenu = render_template(get_template_remboursement(), donnees)
    return generer_pdf_markdown(contenu, chemin_destination)
