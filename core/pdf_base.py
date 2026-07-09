"""Classe de base PDF pour tous les exports Phase 9.

Aucun import tkinter/customtkinter.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
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

COULEUR_NOIR = colors.HexColor("#000000")
COULEUR_GRIS = colors.HexColor("#808080")
COULEUR_BORDURE = colors.HexColor("#333333")
COULEUR_ENTETE_TABLEAU = colors.HexColor("#F0F0F0")
COULEUR_LIGNE_ALTERNEE = colors.HexColor("#FAFAFA")
COULEUR_TOTAL = colors.HexColor("#E0E0E0")
MARGE = 2 * cm
MARGE_BASSE = 2.5 * cm

_STYLES = getSampleStyleSheet()

_POLICES_BOLD_STANDARD = {
    "Helvetica": "Helvetica-Bold",
    "Times-Roman": "Times-Bold",
    "Courier": "Courier-Bold",
}
_POLICES_ITALIC_STANDARD = {
    "Helvetica": "Helvetica-Oblique",
    "Times-Roman": "Times-Italic",
    "Courier": "Courier-Oblique",
}


class BasePDF:
    """Classe commune à tous les exports PDF Phase 9."""

    def __init__(self, titre: str, orientation: str = "portrait", avec_page_garde: bool = False):
        from core.exports import get_config_asso
        from db.models.parametres_globaux import get_parametre

        self.titre = titre
        self.orientation = orientation or "portrait"
        self.avec_page_garde = bool(avec_page_garde)
        self.config_asso: ConfigAsso = get_config_asso()
        self.exercice = get_parametre("exercice_courant", "")
        self.date_export = datetime.now()
        self.pagesize = landscape(A4) if self.orientation in {"paysage", "landscape"} else A4
        self._police_titre = "Helvetica"
        self._police_titre_bold = "Helvetica-Bold"
        self._police_corps = "Helvetica"
        self._police_corps_bold = "Helvetica-Bold"
        self._police_corps_italic = "Helvetica-Oblique"
        self._taille_base = 11
        self._couleur_accent = COULEUR_NOIR
        self._style_normal = _STYLES["Normal"]
        self._style_bold = _STYLES["BodyText"]
        self._style_small = _STYLES["BodyText"]
        self._style_titre = _STYLES["Heading1"]
        self._style_titre_couverture = _STYLES["Heading1"]
        self._style_nom_asso_couverture = _STYLES["Heading1"]
        self._style_section = _STYLES["Heading2"]
        self._style_message = _STYLES["Italic"]
        self._style_center = _STYLES["BodyText"]
        self._charger_styles()

    def _charger_styles(self) -> None:
        """Charge les styles reportlab à partir de la base."""
        try:
            from db.models.parametres_globaux import get_parametre
            from db.models.polices import get_police_by_nom

            police_titre = get_parametre("pdf_police_titre", "Helvetica") or "Helvetica"
            police_corps = get_parametre("pdf_police_corps", "Helvetica") or "Helvetica"
            taille_base_raw = get_parametre("pdf_taille_base", "11") or "11"
            couleur_accent_raw = get_parametre("pdf_couleur_accent", "#000000") or "#000000"

            self._taille_base = max(8, min(72, int(float(taille_base_raw))))
            try:
                self._couleur_accent = colors.HexColor(couleur_accent_raw)
            except Exception:
                self._couleur_accent = COULEUR_NOIR

            self._police_titre, self._police_titre_bold, _ = self._resoudre_police(police_titre, get_police_by_nom)
            self._police_corps, self._police_corps_bold, self._police_corps_italic = self._resoudre_police(
                police_corps,
                get_police_by_nom,
            )
        except Exception as exc:
            logger.error("BasePDF._charger_styles: %s", exc)
            self._police_titre = "Helvetica"
            self._police_titre_bold = "Helvetica-Bold"
            self._police_corps = "Helvetica"
            self._police_corps_bold = "Helvetica-Bold"
            self._police_corps_italic = "Helvetica-Oblique"
            self._taille_base = 11
            self._couleur_accent = COULEUR_NOIR

        self._style_normal = ParagraphStyle(
            "Phase9Normal",
            parent=_STYLES["Normal"],
            fontName=self._police_corps,
            fontSize=self._taille_base,
            leading=self._taille_base + 3,
            textColor=COULEUR_NOIR,
            spaceAfter=4,
        )
        self._style_bold = ParagraphStyle(
            "Phase9Bold",
            parent=self._style_normal,
            fontName=self._police_corps_bold,
        )
        self._style_small = ParagraphStyle(
            "Phase9Small",
            parent=self._style_normal,
            fontSize=8,
            leading=10,
            textColor=COULEUR_GRIS,
        )
        self._style_titre = ParagraphStyle(
            "Phase9Titre",
            parent=_STYLES["Heading1"],
            fontName=self._police_titre_bold,
            fontSize=self._taille_base + 5,
            leading=self._taille_base + 8,
            textColor=COULEUR_NOIR,
            spaceAfter=8,
        )
        self._style_titre_couverture = ParagraphStyle(
            "Phase9TitreCouverture",
            parent=self._style_titre,
            alignment=1,
            fontSize=16,
        )
        self._style_nom_asso_couverture = ParagraphStyle(
            "Phase9NomAssoCouverture",
            parent=self._style_titre,
            alignment=1,
            fontSize=20,
        )
        self._style_section = ParagraphStyle(
            "Phase9Section",
            parent=_STYLES["Heading2"],
            fontName=self._police_titre_bold,
            fontSize=self._taille_base + 2,
            leading=self._taille_base + 5,
            textColor=COULEUR_NOIR,
            spaceBefore=10,
            spaceAfter=4,
        )
        self._style_message = ParagraphStyle(
            "Phase9Message",
            parent=self._style_normal,
            fontName=self._police_corps_italic,
            textColor=COULEUR_NOIR,
        )
        self._style_center = ParagraphStyle(
            "Phase9Center",
            parent=self._style_normal,
            alignment=1,
        )

    def _resoudre_police(self, nom: str, get_police_by_nom_fn) -> tuple[str, str, str]:
        if nom in _POLICES_BOLD_STANDARD:
            return nom, _POLICES_BOLD_STANDARD[nom], _POLICES_ITALIC_STANDARD.get(nom, nom)

        police = get_police_by_nom_fn(nom)
        if not police or int(police.get("actif") or 0) != 1:
            return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

        base_name = str(police.get("nom") or "Helvetica").strip()
        normal_name = self._enregistrer_police(base_name, police.get("fichier_ttf")) or "Helvetica"
        bold_name = self._enregistrer_police(f"{base_name}-Bold", police.get("fichier_ttf_bold"))
        italic_name = self._enregistrer_police(f"{base_name}-Italic", police.get("fichier_ttf_italic"))
        return (
            normal_name,
            bold_name or normal_name,
            italic_name or normal_name,
        )

    @staticmethod
    def _enregistrer_police(nom_police: str, chemin_fichier: str | None) -> str | None:
        if not chemin_fichier:
            return None
        chemin = str(chemin_fichier).strip()
        if not chemin or not os.path.isfile(chemin):
            return None
        try:
            if nom_police not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(nom_police, chemin))
            return nom_police
        except Exception as exc:
            logger.error("BasePDF._enregistrer_police(%s): %s", nom_police, exc)
            return None

    def _en_tete(self, canvas, doc) -> None:
        """Dessine l'en-tête standard du document."""
        if self.avec_page_garde and doc.page == 1:
            return

        canvas.saveState()
        largeur, hauteur = doc.pagesize
        y = hauteur - 1.5 * cm
        x = doc.leftMargin
        largeur_logo = 0.0

        if self.config_asso.logo_path and os.path.isfile(self.config_asso.logo_path):
            try:
                largeur_logo = 1.8 * cm
                canvas.drawImage(
                    self.config_asso.logo_path,
                    x,
                    y - 0.9 * cm,
                    width=largeur_logo,
                    height=largeur_logo,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception as exc:
                logger.error("BasePDF._en_tete logo: %s", exc)
                largeur_logo = 0.0

        texte_x = x + largeur_logo + (0.4 * cm if largeur_logo else 0)
        canvas.setFillColor(COULEUR_NOIR)
        canvas.setFont(self._police_titre_bold, self._taille_base + 1)
        canvas.drawString(texte_x, y, self.config_asso.nom or "Association")
        canvas.setFont(self._police_corps_bold, self._taille_base + 3)
        canvas.drawString(texte_x, y - 0.55 * cm, self.titre)
        canvas.setStrokeColor(self._couleur_accent)
        canvas.setLineWidth(0.7)
        canvas.line(doc.leftMargin, y - 1.0 * cm, largeur - doc.rightMargin, y - 1.0 * cm)
        canvas.restoreState()

    def _pied_de_page(self, canvas, doc) -> None:
        """Dessine le pied de page standard du document."""
        canvas.saveState()
        largeur, _ = doc.pagesize
        footer_y = 1.2 * cm
        canvas.setFont(self._police_corps, 8)
        canvas.setFillColor(COULEUR_GRIS)

        gauche = self.config_asso.nom or "Association"
        if self.exercice:
            gauche = f"{gauche} • {self.exercice}"
        centre = self.date_export.strftime("%d/%m/%Y %H:%M")
        droite = f"Page {doc.page}"

        canvas.drawString(doc.leftMargin, footer_y, gauche)
        canvas.drawCentredString(largeur / 2, footer_y, centre)
        canvas.drawRightString(largeur - doc.rightMargin, footer_y, droite)
        canvas.restoreState()

    def _page_garde(self) -> list:
        """Construit la page de garde."""
        elements: list = [Spacer(1, 4 * cm)]

        if self.config_asso.logo_path and os.path.isfile(self.config_asso.logo_path):
            try:
                image = Image(self.config_asso.logo_path, width=5 * cm, height=5 * cm, kind="proportional")
                image.hAlign = "CENTER"
                elements.extend([image, Spacer(1, 1 * cm)])
            except Exception as exc:
                logger.error("BasePDF._page_garde logo: %s", exc)

        elements.append(Paragraph(self.config_asso.nom or "Association", self._style_nom_asso_couverture))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(self.titre, self._style_titre_couverture))
        elements.append(Spacer(1, 0.4 * cm))
        elements.append(
            Paragraph(
                self.exercice or "Exercice non défini",
                ParagraphStyle("Phase9ExerciceCouverture", parent=self._style_center, fontSize=12),
            )
        )
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(
            Paragraph(
                self.date_export.strftime("%d/%m/%Y %H:%M"),
                ParagraphStyle("Phase9DateCouverture", parent=self._style_small, alignment=1, fontSize=10),
            )
        )
        return elements

    def _style_tableau(self, nb_colonnes: int = 0, avec_total: bool = False) -> TableStyle:
        """Retourne le style commun des tableaux."""
        commandes = [
            ("GRID", (0, 0), (-1, -1), 0.5, COULEUR_BORDURE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, -1), self._police_corps),
            ("FONTSIZE", (0, 0), (-1, -1), self._taille_base - 1),
            ("TEXTCOLOR", (0, 0), (-1, -1), COULEUR_NOIR),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, 0), COULEUR_ENTETE_TABLEAU),
            ("FONTNAME", (0, 0), (-1, 0), self._police_corps_bold),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COULEUR_LIGNE_ALTERNEE]),
        ]
        if avec_total:
            commandes.extend(
                [
                    ("BACKGROUND", (0, -1), (-1, -1), COULEUR_TOTAL),
                    ("FONTNAME", (0, -1), (-1, -1), self._police_corps_bold),
                ]
            )
        return TableStyle(commandes)

    def _titre_section(self, texte: str) -> list:
        """Retourne les flowables pour un titre de section."""
        return [
            Paragraph(texte, self._style_section),
            HRFlowable(width="100%", thickness=0.8, color=self._couleur_accent, spaceBefore=2, spaceAfter=6),
        ]

    def _formater_montant(self, v) -> str:
        """Formate un montant en euros."""
        try:
            return f"{float(v):,.2f} €".replace(",", "\u202f").replace(".", ",")
        except (TypeError, ValueError):
            return "—"

    def _formater_date(self, v: str | None) -> str:
        """Formate une date brute en format JJ/MM/AAAA."""
        if not v:
            return "—"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return str(v)

    def _creer_tableau(
        self,
        donnees: list,
        col_widths: list[float] | None = None,
        avec_total: bool = False,
        alignements: dict[int, str] | None = None,
    ) -> Table:
        tableau = Table(donnees, colWidths=col_widths, repeatRows=1 if donnees else 0)
        style = self._style_tableau(len(donnees[0]) if donnees else 0, avec_total=avec_total)
        if alignements:
            for index_colonne, alignement in alignements.items():
                style.add("ALIGN", (index_colonne, 1), (index_colonne, -1), alignement)
        tableau.setStyle(style)
        return tableau

    def _message_aucune_donnee(self) -> Paragraph:
        return Paragraph("Aucune donnée disponible.", self._style_message)

    def generer(self, chemin_sortie: str) -> bool:
        """Construit puis enregistre le document PDF."""
        try:
            doc = SimpleDocTemplate(
                chemin_sortie,
                pagesize=self.pagesize,
                leftMargin=MARGE,
                rightMargin=MARGE,
                topMargin=MARGE,
                bottomMargin=MARGE_BASSE,
            )
            story: list = []
            if self.avec_page_garde:
                story.extend(self._page_garde())
                story.append(PageBreak())
            story.extend(self._construire_contenu())
            doc.build(story, onFirstPage=self._dessiner_page, onLaterPages=self._dessiner_page)
            return True
        except Exception as exc:
            logger.error("%s.generer: %s", self.__class__.__name__, exc)
            return False

    def _dessiner_page(self, canvas, doc) -> None:
        self._en_tete(canvas, doc)
        self._pied_de_page(canvas, doc)

    def _construire_contenu(self) -> list:
        """Construit le corps du document."""
        raise NotImplementedError
