"""Gestion des templates Cerfa, attestation simple et remboursement."""

from __future__ import annotations

import re
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent / 'config'

_TEMPLATE_FILES = {
    'cerfa': ('cerfa_11580_template.md', 'cerfa_11580_template.default.md'),
    'attestation': ('attestation_don_template.md', 'attestation_don_template.default.md'),
    'remboursement': ('remboursement_frais_template.md', 'remboursement_frais_template.default.md'),
}

VARIABLES_TEMPLATE_CERFA = [
    ('nom_asso', "Nom de l'association"),
    ('adresse_asso', "Adresse complète de l'association"),
    ('num_habilitation', 'Numéro d’habilitation fiscale'),
    ('num_recu', 'Numéro du reçu'),
    ('date_don', 'Date du don'),
    ('date_emission', 'Date d’émission du reçu'),
    ('exercice', 'Exercice concerné'),
    ('donateur_nom', 'Nom du donateur'),
    ('donateur_prenom', 'Prénom du donateur'),
    ('donateur_adresse', 'Adresse du donateur'),
    ('donateur_cp', 'Code postal du donateur'),
    ('donateur_ville', 'Ville du donateur'),
    ('donateur_siret', 'SIRET du donateur entreprise'),
    ('montant', 'Montant du don en argent'),
    ('nature_don', 'Nature du don'),
    ('description_don', 'Description du don'),
    ('valeur_estimee', 'Valeur estimée'),
    ('mode_versement', 'Mode de versement'),
    ('mention_fiscale', 'Mention fiscale libre'),
    ('taux_deduction', 'Taux de déduction affiché'),
    ('si_entreprise', 'Bloc conditionnel entreprise'),
    ('si_nature', 'Bloc conditionnel don en nature'),
]

VARIABLES_TEMPLATE_ATTESTATION = [
    ('nom_asso', "Nom de l'association"),
    ('adresse_asso', "Adresse complète de l'association"),
    ('num_recu', 'Numéro du reçu'),
    ('date_don', 'Date du don'),
    ('date_emission', 'Date d’émission'),
    ('exercice', 'Exercice concerné'),
    ('donateur_nom', 'Nom du donateur'),
    ('donateur_prenom', 'Prénom du donateur'),
    ('donateur_adresse', 'Adresse du donateur'),
    ('donateur_cp', 'Code postal du donateur'),
    ('donateur_ville', 'Ville du donateur'),
    ('montant', 'Montant du don'),
    ('nature_don', 'Nature du don'),
    ('description_don', 'Description du don'),
    ('valeur_estimee', 'Valeur estimée'),
    ('mode_versement', 'Mode de versement'),
    ('mention_fiscale', 'Mention complémentaire'),
]

VARIABLES_TEMPLATE_REMBOURSEMENT = [
    ('nom_asso', "Nom de l'association"),
    ('adresse_asso', "Adresse de l'association"),
    ('date_emission', 'Date d’émission'),
    ('nom_evenement', 'Nom de l’événement ou contexte'),
    ('date_evenement', 'Date de l’événement'),
    ('beneficiaire_civilite', 'Civilité du bénéficiaire'),
    ('beneficiaire_nom', 'Nom du bénéficiaire'),
    ('beneficiaire_prenom', 'Prénom du bénéficiaire'),
    ('tableau_frais', 'Tableau markdown des frais'),
    ('montant_total', 'Montant total'),
    ('mode_remboursement', 'Mode de remboursement'),
    ('reference', 'Référence du remboursement'),
    ('texte_certification', 'Texte de certification'),
]


def _paths(kind: str) -> tuple[Path, Path]:
    courant, defaut = _TEMPLATE_FILES[kind]
    return _BASE_DIR / courant, _BASE_DIR / defaut


def _get_template(kind: str) -> str:
    courant, defaut = _paths(kind)
    try:
        return courant.read_text(encoding='utf-8')
    except FileNotFoundError:
        return defaut.read_text(encoding='utf-8')


def _save_template(kind: str, contenu: str) -> None:
    courant, _ = _paths(kind)
    courant.write_text(contenu, encoding='utf-8')


def _reset_template(kind: str) -> None:
    courant, defaut = _paths(kind)
    courant.write_text(defaut.read_text(encoding='utf-8'), encoding='utf-8')


def get_template_cerfa() -> str:
    return _get_template('cerfa')


def save_template_cerfa(contenu: str) -> None:
    _save_template('cerfa', contenu)


def reset_template_cerfa() -> None:
    _reset_template('cerfa')


def get_template_attestation() -> str:
    return _get_template('attestation')


def save_template_attestation(contenu: str) -> None:
    _save_template('attestation', contenu)


def reset_template_attestation() -> None:
    _reset_template('attestation')


def get_template_remboursement() -> str:
    return _get_template('remboursement')


def save_template_remboursement(contenu: str) -> None:
    _save_template('remboursement', contenu)


def reset_template_remboursement() -> None:
    _reset_template('remboursement')


def render_template(template: str, donnees: dict) -> str:
    def replace_block(match: re.Match[str]) -> str:
        cle = match.group(1).strip()
        contenu = match.group(2)
        return contenu if cle in donnees and bool(donnees[cle]) else ''

    rendu = re.sub(r'\{\{#([^}]+)\}\}(.*?)\{\{/\1\}\}', replace_block, template, flags=re.DOTALL)

    def replace_var(match: re.Match[str]) -> str:
        cle = match.group(1).strip()
        return str(donnees.get(cle, ''))

    return re.sub(r'\{\{([^}]+)\}\}', replace_var, rendu)


def generer_pdf_markdown(contenu_md: str, chemin_destination: str) -> dict:
    try:
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover - dépendance externe
        return {'succes': False, 'chemin': chemin_destination, 'message': f'Dépendance manquante : {exc}'}

    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle('H1Doc', parent=styles['Heading1'], fontSize=16, spaceAfter=12)
    style_h2 = ParagraphStyle('H2Doc', parent=styles['Heading2'], fontSize=13, spaceAfter=8, spaceBefore=12)
    style_h3 = ParagraphStyle('H3Doc', parent=styles['Heading3'], fontSize=11, spaceAfter=6, spaceBefore=8)
    style_normal = styles['Normal']
    style_normal.fontSize = 10
    style_normal.spaceAfter = 4

    def render_inline(texte: str) -> str:
        texte = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', texte)
        texte = re.sub(r'\*(.+?)\*', r'<i>\1</i>', texte)
        return texte

    def parse_table(lines: list[str]) -> Table | None:
        rows: list[list[str]] = []
        for line in lines:
            cellules = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if cellules and all(set(cell.replace(':', '').replace('-', '').strip()) == set() for cell in cellules):
                continue
            rows.append(cellules)
        if not rows:
            return None
        table = Table(rows, hAlign='LEFT')
        table.setStyle(
            TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1f6aa5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#c7d2e0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.whitesmoke, rl_colors.HexColor('#f8fafc')]),
            ])
        )
        return table

    try:
        doc = SimpleDocTemplate(
            chemin_destination,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        elements: list = []
        lignes = contenu_md.splitlines()
        i = 0
        while i < len(lignes):
            ligne = lignes[i].rstrip()
            strip = ligne.strip()
            if strip.startswith('|'):
                bloc = []
                while i < len(lignes) and lignes[i].strip().startswith('|'):
                    bloc.append(lignes[i])
                    i += 1
                table = parse_table(bloc)
                if table is not None:
                    elements.append(table)
                    elements.append(Spacer(1, 0.25 * cm))
                continue
            if not strip:
                elements.append(Spacer(1, 0.25 * cm))
            elif strip.startswith('# '):
                elements.append(Paragraph(render_inline(strip[2:]), style_h1))
            elif strip.startswith('## '):
                elements.append(Paragraph(render_inline(strip[3:]), style_h2))
            elif strip.startswith('### '):
                elements.append(Paragraph(render_inline(strip[4:]), style_h3))
            elif strip.startswith('---'):
                elements.append(Spacer(1, 0.2 * cm))
            elif strip.startswith('- '):
                elements.append(Paragraph(f'• {render_inline(strip[2:])}', style_normal))
            else:
                elements.append(Paragraph(render_inline(strip), style_normal))
            i += 1
        doc.build(elements)
        return {'succes': True, 'chemin': chemin_destination, 'message': 'PDF généré avec succès.'}
    except Exception as exc:  # noqa: BLE001
        logger.exception('generer_pdf_markdown: %s', exc)
        return {'succes': False, 'chemin': chemin_destination, 'message': str(exc)}
