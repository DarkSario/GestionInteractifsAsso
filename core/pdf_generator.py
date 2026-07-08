"""Générateurs PDF pour les exports d'événements.

Utilise reportlab (SimpleDocTemplate, Paragraph, Table, TableStyle).
Aucun import tkinter/customtkinter.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.logger import get_logger

if TYPE_CHECKING:
    from core.exports import ConfigAsso

logger = get_logger(__name__)

# ── Constantes de style ───────────────────────────────────────────────────────

COULEUR_ENTETE = colors.HexColor("#1f6aa5")
COULEUR_ENTETE_TEXTE = colors.white
COULEUR_TOTAL = colors.HexColor("#d0e4f7")
COULEUR_GRIS = colors.HexColor("#f5f5f5")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2 * cm

_styles = getSampleStyleSheet()

STYLE_TITRE = ParagraphStyle(
    "Titre",
    parent=_styles["Heading1"],
    fontSize=16,
    textColor=COULEUR_ENTETE,
    spaceAfter=6,
)
STYLE_SOUS_TITRE = ParagraphStyle(
    "SousTitre",
    parent=_styles["Heading2"],
    fontSize=13,
    textColor=COULEUR_ENTETE,
    spaceBefore=12,
    spaceAfter=4,
)
STYLE_NORMAL = _styles["Normal"]
STYLE_SMALL = ParagraphStyle("Small", parent=_styles["Normal"], fontSize=9)
STYLE_BOLD = ParagraphStyle("Bold", parent=_styles["Normal"], fontName="Helvetica-Bold")
STYLE_ITALIC = ParagraphStyle("Italic", parent=_styles["Normal"], fontName="Helvetica-Oblique")


def _style_table(en_tetes: bool = True) -> TableStyle:
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, COULEUR_GRIS]),
    ]
    if en_tetes:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), COULEUR_ENTETE),
            ("TEXTCOLOR", (0, 0), (-1, 0), COULEUR_ENTETE_TEXTE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COULEUR_GRIS]),
        ]
    return TableStyle(cmds)


def _formater_montant(v) -> str:
    try:
        return f"{float(v):,.2f} €".replace(",", "\u202f").replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _formater_date(v: str | None) -> str:
    if not v:
        return "—"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return str(v)


# ── En-tête association ───────────────────────────────────────────────────────


def _construire_entete_asso(config: "ConfigAsso", story: list) -> None:
    """Ajoute l'en-tête asso (logo + infos) au story."""
    elements_entete: list = []

    # Logo
    if config.logo_path and os.path.isfile(config.logo_path):
        try:
            img = Image(config.logo_path, width=3 * cm, height=3 * cm, kind="proportional")
            elements_entete.append(img)
        except Exception as exc:
            logger.warning("Logo non chargeable : %s", exc)

    # Nom + coordonnées
    infos: list[str] = []
    if config.nom:
        infos.append(f"<b>{config.nom}</b>")
    if config.adresse:
        infos.append(config.adresse)
    if config.telephone:
        infos.append(f"Tél : {config.telephone}")
    if config.email:
        infos.append(f"Email : {config.email}")

    if infos:
        story.append(Paragraph("<br/>".join(infos), STYLE_NORMAL))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Spacer(1, 0.2 * cm))


def _pied_de_page(canvas, doc) -> None:
    """Dessine le pied de page (date export + numéro de page)."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    date_export = datetime.now().strftime("%d/%m/%Y %H:%M")
    canvas.drawString(MARGIN, 1.2 * cm, f"Exporté le {date_export}")
    canvas.drawRightString(
        PAGE_WIDTH - MARGIN,
        1.2 * cm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


# ── PdfEvenement ─────────────────────────────────────────────────────────────


class PdfEvenement:
    """Génère le bilan PDF complet d'un événement."""

    def __init__(self, evenement_id: int, config_asso: "ConfigAsso") -> None:
        self._evenement_id = evenement_id
        self._config = config_asso

    def generer(self, chemin_sortie: str) -> bool:
        """Génère le PDF et l'enregistre dans chemin_sortie."""
        try:
            from db.models.evenements import (
                get_evenement_by_id,
                get_depenses_evenement,
                get_benevoles_evenement,
            )
            from db.models.tombola import get_lots_evenement, get_carnets_evenement
            from db.models.stands import get_stands_evenement
            from db.models.tableaux import get_tableaux_evenement, get_colonnes_tableau, get_lignes_tableau
            from core.evenements import calculer_bilan_evenement

            evenement = get_evenement_by_id(self._evenement_id)
            if not evenement:
                logger.error("PdfEvenement: événement %s introuvable", self._evenement_id)
                return False

            doc = SimpleDocTemplate(
                chemin_sortie,
                pagesize=A4,
                leftMargin=MARGIN,
                rightMargin=MARGIN,
                topMargin=MARGIN,
                bottomMargin=2 * cm,
            )
            story: list = []

            # 1. En-tête asso
            _construire_entete_asso(self._config, story)

            # 2. Titre
            nom_ev = evenement.get("nom") or f"Événement #{self._evenement_id}"
            story.append(Paragraph(f"Bilan — {nom_ev}", STYLE_TITRE))
            story.append(Spacer(1, 0.3 * cm))

            # 3. Informations générales
            story.append(Paragraph("Informations générales", STYLE_SOUS_TITRE))
            LABELS_STATUT = {
                "planifie": "Planifié",
                "en_cours": "En cours",
                "termine": "Terminé",
                "annule": "Annulé",
            }
            infos_data = [
                ["Champ", "Valeur"],
                ["Type", evenement.get("type") or "—"],
                ["Date début", _formater_date(evenement.get("date_debut"))],
                ["Date fin", _formater_date(evenement.get("date_fin"))],
                ["Statut", LABELS_STATUT.get(evenement.get("statut") or "", evenement.get("statut") or "—")],
                ["Budget prévisionnel", _formater_montant(evenement.get("budget_previsionnel"))],
            ]
            t = Table(infos_data, colWidths=[5 * cm, 12 * cm])
            t.setStyle(_style_table())
            story.append(t)
            story.append(Spacer(1, 0.3 * cm))

            # 4. Description
            desc = (evenement.get("description") or "").strip()
            if desc:
                story.append(Paragraph("Description", STYLE_SOUS_TITRE))
                story.append(Paragraph(desc.replace("\n", "<br/>"), STYLE_NORMAL))
                story.append(Spacer(1, 0.3 * cm))

            # 5. Résumé financier
            bilan = calculer_bilan_evenement(self._evenement_id)
            story.append(Paragraph("Résumé financier", STYLE_SOUS_TITRE))
            fin_data = [
                ["", "Montant"],
                ["Recettes totales", _formater_montant(bilan["recettes_total"])],
                ["Dépenses totales", _formater_montant(bilan["depenses_total"])],
                ["Bénéfice net", _formater_montant(bilan["benefice"])],
            ]
            t_fin = Table(fin_data, colWidths=[10 * cm, 7 * cm])
            style_fin = _style_table()
            style_fin.add("BACKGROUND", (0, 3), (-1, 3), COULEUR_TOTAL)
            style_fin.add("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold")
            t_fin.setStyle(style_fin)
            story.append(t_fin)
            story.append(Spacer(1, 0.3 * cm))

            # 6. Billetterie
            stats_bill = bilan["detail"]["billetterie"]
            story.append(Paragraph("Billetterie", STYLE_SOUS_TITRE))
            bill_summary = [
                ["Indicateur", "Valeur"],
                ["Billets émis", str(stats_bill.get("total_billets", 0))],
                ["Nombre de ventes", str(stats_bill.get("nb_ventes", 0))],
                ["Recette brute", _formater_montant(stats_bill.get("total_recette", 0))],
                ["Frais SumUp", _formater_montant(stats_bill.get("total_frais", 0))],
                ["Recette nette", _formater_montant(stats_bill.get("total_net", 0))],
            ]
            t_bill = Table(bill_summary, colWidths=[10 * cm, 7 * cm])
            t_bill.setStyle(_style_table())
            story.append(t_bill)
            story.append(Spacer(1, 0.2 * cm))

            # Par tarif
            par_tarif = stats_bill.get("par_tarif") or []
            if par_tarif:
                tarif_data = [["Tarif", "Quantité", "Montant"]]
                for r in par_tarif:
                    tarif_data.append([
                        r.get("tarif_nom") or "—",
                        str(r.get("quantite") or 0),
                        _formater_montant(r.get("sous_total") or 0),
                    ])
                t_tarif = Table(tarif_data, colWidths=[9 * cm, 4 * cm, 4 * cm])
                t_tarif.setStyle(_style_table())
                story.append(t_tarif)
                story.append(Spacer(1, 0.2 * cm))

            # 7. Dépenses
            depenses = get_depenses_evenement(self._evenement_id)
            if depenses:
                story.append(Paragraph("Dépenses", STYLE_SOUS_TITRE))
                dep_data = [["Libellé", "Montant", "Fournisseur", "Date"]]
                for d in depenses:
                    dep_data.append([
                        d.get("libelle") or "—",
                        _formater_montant(d.get("montant")),
                        d.get("fournisseur_nom") or "—",
                        _formater_date(d.get("date")),
                    ])
                t_dep = Table(dep_data, colWidths=[7 * cm, 4 * cm, 4.5 * cm, 3 * cm])
                t_dep.setStyle(_style_table())
                story.append(t_dep)
                story.append(Spacer(1, 0.3 * cm))

            # 8. Bénévoles
            benevoles = get_benevoles_evenement(self._evenement_id)
            if benevoles:
                story.append(Paragraph("Bénévoles", STYLE_SOUS_TITRE))
                STATUTS_BEN = {"confirme": "Confirmé", "desiste": "Désisté", "remplace": "Remplacé"}
                ben_data = [["Nom", "Prénom", "Rôle", "Horaires", "Statut"]]
                for b in benevoles:
                    if b.get("membre_id"):
                        nom = b.get("membre_nom") or ""
                        prenom = b.get("membre_prenom") or ""
                    else:
                        nom = b.get("nom_externe") or ""
                        prenom = b.get("prenom_externe") or ""
                    hdebut = b.get("heure_debut") or ""
                    hfin = b.get("heure_fin") or ""
                    horaires = f"{hdebut}–{hfin}" if hdebut and hfin else (hdebut or hfin or "—")
                    ben_data.append([
                        nom,
                        prenom,
                        b.get("role") or "—",
                        horaires,
                        STATUTS_BEN.get(b.get("statut") or "", b.get("statut") or "—"),
                    ])
                t_ben = Table(ben_data, colWidths=[3.5 * cm, 3.5 * cm, 3.5 * cm, 4 * cm, 3 * cm])
                t_ben.setStyle(_style_table())
                story.append(t_ben)
                story.append(Spacer(1, 0.3 * cm))

            # 9. Tombola
            lots = get_lots_evenement(self._evenement_id)
            carnets = get_carnets_evenement(self._evenement_id)
            if lots or carnets:
                story.append(Paragraph("Tombola", STYLE_SOUS_TITRE))
                if carnets:
                    story.append(Paragraph("Carnets", STYLE_BOLD))
                    STATUTS_CARNET = {"emis": "Émis", "vendu": "Vendu", "retourne": "Retourné", "perdu": "Perdu"}
                    carn_data = [["N° début", "N° fin", "Prix carnet", "Vendeur", "Statut", "Encaissé"]]
                    for c in carnets:
                        vendeur = ""
                        if c.get("vendeur_membre_id"):
                            vendeur = f"{c.get('vendeur_prenom') or ''} {c.get('vendeur_nom') or ''}".strip()
                        else:
                            vendeur = c.get("vendeur_nom_externe") or "—"
                        carn_data.append([
                            str(c.get("numero_debut") or ""),
                            str(c.get("numero_fin") or ""),
                            _formater_montant(c.get("prix_carnet")),
                            vendeur or "—",
                            STATUTS_CARNET.get(c.get("statut") or "", c.get("statut") or "—"),
                            _formater_montant(c.get("montant_encaisse")),
                        ])
                    t_carn = Table(carn_data, colWidths=[2.5 * cm, 2.5 * cm, 3 * cm, 4 * cm, 2.5 * cm, 3 * cm])
                    t_carn.setStyle(_style_table())
                    story.append(t_carn)
                    story.append(Spacer(1, 0.2 * cm))

                if lots:
                    story.append(Paragraph("Lots", STYLE_BOLD))
                    STATUTS_LOT = {"en_attente": "En attente", "attribue": "Attribué", "non_reclame": "Non réclamé"}
                    lots_data = [["N°", "Description", "Valeur", "N° gagnant", "Statut"]]
                    for lot in lots:
                        lots_data.append([
                            str(lot.get("numero") or ""),
                            lot.get("description") or "—",
                            _formater_montant(lot.get("valeur_estimee")),
                            lot.get("numero_gagnant") or "—",
                            STATUTS_LOT.get(lot.get("statut") or "", lot.get("statut") or "—"),
                        ])
                    t_lots = Table(lots_data, colWidths=[1.5 * cm, 7 * cm, 3 * cm, 3 * cm, 3 * cm])
                    t_lots.setStyle(_style_table())
                    story.append(t_lots)
                    story.append(Spacer(1, 0.3 * cm))

            # 10. Stands
            stands = get_stands_evenement(self._evenement_id)
            if stands:
                story.append(Paragraph("Stands", STYLE_SOUS_TITRE))
                TYPES_STAND = {"benevole": "Bénévole", "location": "Location"}
                STATUTS_STAND = {"confirme": "Confirmé", "annule": "Annulé"}
                stands_data = [["N° empl.", "Nom stand", "Type", "Responsable", "Montant", "Statut"]]
                for s in stands:
                    if s.get("responsable_membre_id"):
                        resp = f"{s.get('responsable_prenom') or ''} {s.get('responsable_nom') or ''}".strip()
                    else:
                        resp = s.get("responsable_nom_externe") or "—"
                    stands_data.append([
                        s.get("numero_emplacement") or "—",
                        s.get("nom_stand") or "—",
                        TYPES_STAND.get(s.get("type_stand") or "", s.get("type_stand") or "—"),
                        resp or "—",
                        _formater_montant(s.get("montant_location")) if s.get("type_stand") == "location" else "—",
                        STATUTS_STAND.get(s.get("statut") or "", s.get("statut") or "—"),
                    ])
                t_stands = Table(stands_data, colWidths=[2 * cm, 5 * cm, 2.5 * cm, 4 * cm, 2.5 * cm, 2 * cm])
                t_stands.setStyle(_style_table())
                story.append(t_stands)
                story.append(Spacer(1, 0.3 * cm))

            # 11. Tableaux personnalisés
            tableaux = get_tableaux_evenement(self._evenement_id)
            for tableau in tableaux:
                colonnes = get_colonnes_tableau(int(tableau["id"]))
                lignes = get_lignes_tableau(int(tableau["id"]))
                if not colonnes:
                    continue
                story.append(Paragraph(f"Tableau : {tableau.get('nom') or '—'}", STYLE_SOUS_TITRE))
                if tableau.get("description"):
                    story.append(Paragraph(tableau["description"], STYLE_ITALIC))
                    story.append(Spacer(1, 0.1 * cm))

                # En-têtes
                ent = [c.get("nom") or "" for c in colonnes]
                tab_data = [ent]
                for ligne in lignes:
                    cellules = ligne.get("cellules") or {}
                    row = []
                    for col in colonnes:
                        val = cellules.get(str(col["id"])) or ""
                        row.append(val)
                    tab_data.append(row)

                nb_cols = len(colonnes)
                col_w = (PAGE_WIDTH - 2 * MARGIN) / nb_cols if nb_cols > 0 else 3 * cm
                t_tab = Table(tab_data, colWidths=[col_w] * nb_cols)
                t_tab.setStyle(_style_table())
                story.append(t_tab)
                story.append(Spacer(1, 0.3 * cm))

            # 12. Bilan de fin
            bilan_fin = (evenement.get("bilan_fin") or "").strip()
            if bilan_fin:
                story.append(Paragraph("Bilan de fin", STYLE_SOUS_TITRE))
                story.append(Paragraph(bilan_fin.replace("\n", "<br/>"), STYLE_NORMAL))
                story.append(Spacer(1, 0.3 * cm))

            doc.build(story, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
            return True
        except Exception as exc:
            logger.error("PdfEvenement.generer: %s", exc)
            return False


# ── PvTirage ─────────────────────────────────────────────────────────────────


class PvTirage:
    """Génère le PV de tirage tombola en PDF."""

    def __init__(self, evenement_id: int, config_asso: "ConfigAsso") -> None:
        self._evenement_id = evenement_id
        self._config = config_asso

    def generer(self, chemin_sortie: str) -> bool:
        """Génère le PV de tirage et l'enregistre dans chemin_sortie."""
        try:
            from db.models.tombola import generer_pv_tirage

            pv = generer_pv_tirage(self._evenement_id)
            lots = pv.get("lots") or []

            doc = SimpleDocTemplate(
                chemin_sortie,
                pagesize=A4,
                leftMargin=MARGIN,
                rightMargin=MARGIN,
                topMargin=MARGIN,
                bottomMargin=2 * cm,
            )
            story: list = []

            _construire_entete_asso(self._config, story)

            story.append(Paragraph("Procès-Verbal de Tirage au Sort", STYLE_TITRE))
            story.append(Spacer(1, 0.3 * cm))

            ev = pv.get("evenement") or {}
            ev_nom = ev.get("nom") or f"Événement #{self._evenement_id}"
            ev_date = _formater_date(ev.get("date_debut"))
            story.append(Paragraph(f"Événement : {ev_nom}", STYLE_NORMAL))
            story.append(Paragraph(f"Date de l'événement : {ev_date}", STYLE_NORMAL))
            story.append(Paragraph(f"Date du tirage : {pv.get('date_generation') or '—'}", STYLE_NORMAL))
            story.append(Spacer(1, 0.4 * cm))

            STATUTS_LOT = {"en_attente": "En attente", "attribue": "Attribué", "non_reclame": "Non réclamé"}
            lots_data = [["N°", "Description", "Valeur", "N° gagnant", "Statut"]]
            for lot in lots:
                lots_data.append([
                    str(lot.get("numero") or ""),
                    lot.get("description") or "—",
                    _formater_montant(lot.get("valeur_estimee")),
                    lot.get("numero_gagnant") or "—",
                    STATUTS_LOT.get(lot.get("statut") or "", lot.get("statut") or "—"),
                ])
            t_lots = Table(lots_data, colWidths=[1.5 * cm, 8 * cm, 3 * cm, 3 * cm, 3 * cm])
            t_lots.setStyle(_style_table())
            story.append(t_lots)
            story.append(Spacer(1, 1.5 * cm))

            # Zone signature
            story.append(Paragraph("Lu et approuvé :", STYLE_NORMAL))
            story.append(Spacer(1, 0.5 * cm))
            sig_data = [["Signature :", "Signature :"]]
            t_sig = Table(sig_data, colWidths=[9 * cm, 9 * cm])
            t_sig.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("MINROWHEIGHT", (0, 0), (-1, -1), 3 * cm),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t_sig)

            doc.build(story, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
            return True
        except Exception as exc:
            logger.error("PvTirage.generer: %s", exc)
            return False


# ── ListeBenevolesPdf ─────────────────────────────────────────────────────────


class ListeBenevolesPdf:
    """Génère la liste des bénévoles en PDF."""

    def __init__(self, evenement_id: int, config_asso: "ConfigAsso") -> None:
        self._evenement_id = evenement_id
        self._config = config_asso

    def generer(self, chemin_sortie: str) -> bool:
        """Génère la liste des bénévoles et l'enregistre dans chemin_sortie."""
        try:
            from db.models.evenements import get_evenement_by_id, get_benevoles_evenement

            evenement = get_evenement_by_id(self._evenement_id)
            nom_ev = (evenement or {}).get("nom") or f"Événement #{self._evenement_id}"
            benevoles = get_benevoles_evenement(self._evenement_id)

            doc = SimpleDocTemplate(
                chemin_sortie,
                pagesize=A4,
                leftMargin=MARGIN,
                rightMargin=MARGIN,
                topMargin=MARGIN,
                bottomMargin=2 * cm,
            )
            story: list = []

            _construire_entete_asso(self._config, story)

            story.append(Paragraph(f"Liste des Bénévoles — {nom_ev}", STYLE_TITRE))
            story.append(Spacer(1, 0.3 * cm))

            STATUTS_BEN = {"confirme": "Confirmé", "desiste": "Désisté", "remplace": "Remplacé"}
            ben_data = [["Nom", "Prénom", "Rôle", "Horaires", "Statut"]]
            total_minutes = 0
            for b in benevoles:
                if b.get("membre_id"):
                    nom = b.get("membre_nom") or ""
                    prenom = b.get("membre_prenom") or ""
                else:
                    nom = b.get("nom_externe") or ""
                    prenom = b.get("prenom_externe") or ""
                hdebut = b.get("heure_debut") or ""
                hfin = b.get("heure_fin") or ""
                if hdebut and hfin:
                    horaires = f"{hdebut}–{hfin}"
                    try:
                        h1 = datetime.strptime(hdebut, "%H:%M")
                        h2 = datetime.strptime(hfin, "%H:%M")
                        diff = (h2 - h1).seconds // 60
                        if diff > 0 and b.get("statut") == "confirme":
                            total_minutes += diff
                    except ValueError:
                        pass
                else:
                    horaires = hdebut or hfin or "—"
                ben_data.append([
                    nom,
                    prenom,
                    b.get("role") or "—",
                    horaires,
                    STATUTS_BEN.get(b.get("statut") or "", b.get("statut") or "—"),
                ])

            # Ligne totaux
            total_heures = total_minutes / 60
            ben_data.append([
                f"Total : {len(benevoles)} bénévole(s)",
                "",
                "",
                f"{total_heures:.1f} h",
                "",
            ])

            t_ben = Table(ben_data, colWidths=[3.5 * cm, 3.5 * cm, 4 * cm, 4 * cm, 3 * cm])
            style_ben = _style_table()
            # Ligne total en gras
            style_ben.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
            style_ben.add("BACKGROUND", (0, -1), (-1, -1), COULEUR_TOTAL)
            style_ben.add("SPAN", (0, -1), (2, -1))
            t_ben.setStyle(style_ben)
            story.append(t_ben)

            doc.build(story, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
            return True
        except Exception as exc:
            logger.error("ListeBenevolesPdf.generer: %s", exc)
            return False
