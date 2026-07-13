"""Classe de base PDF avancée pour les exports professionnels — Phase 21.

Hérite de BasePDF et ajoute :
- En-tête pro : logo + nom asso + ligne colorée
- Pied de page pro : logo petit + asso + titre + page X/Y
- Table des matières automatique
- Méthodes utilitaires KPI, signatures, sections numérotées, graphiques
"""

from __future__ import annotations

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from core.pdf_base import BasePDF, COULEUR_GRIS, COULEUR_NOIR, MARGE
from utils.logger import get_logger

logger = get_logger(__name__)

# Taille logo en-tête
_LOGO_ENTETE_HAUTEUR = 1.2 * cm
# Taille logo pied de page
_LOGO_PIED_HAUTEUR = 0.6 * cm


class PdfBasePro(BasePDF):
    """Classe de base pour les exports PDF professionnels."""

    def __init__(
        self,
        titre: str,
        orientation: str = "portrait",
        avec_page_garde: bool = True,
    ):
        super().__init__(titre, orientation=orientation, avec_page_garde=avec_page_garde)

        from core.theme_export import get_theme_export
        from core.logo import get_logo_config

        theme = get_theme_export()
        self._couleur_principale_hex = theme.get("couleur_principale", "#1f6aa5")
        self._couleur_secondaire_hex = theme.get("couleur_secondaire", "#144870")
        self._style_tableaux = theme.get("style_tableaux", "moderne")

        try:
            self._couleur_principale = colors.HexColor(self._couleur_principale_hex)
        except Exception:
            self._couleur_principale = colors.HexColor("#1f6aa5")
        try:
            self._couleur_secondaire = colors.HexColor(self._couleur_secondaire_hex)
        except Exception:
            self._couleur_secondaire = colors.HexColor("#144870")

        self._couleur_accent = self._couleur_principale

        logo_config = get_logo_config()
        self._logo_pro_path = logo_config.get("path")
        self._logo_position = logo_config.get("position", "gauche")
        self._logo_taille = logo_config.get("taille", "moyenne")

        self._compteur_section = 0
        self._total_pages: int | None = None

        # Styles pro supplémentaires
        self._style_section_pro = ParagraphStyle(
            "ProSection",
            parent=self._style_section,
            fontSize=self._taille_base + 3,
            textColor=colors.white,
            leading=self._taille_base + 6,
            spaceBefore=14,
            spaceAfter=6,
        )

    # ── En-tête et pied de page ───────────────────────────────────────────────

    def _en_tete(self, canvas, doc) -> None:
        """En-tête pro : logo + nom asso + titre + ligne colorée."""
        if self.avec_page_garde and doc.page == 1:
            return

        canvas.saveState()
        largeur, hauteur = doc.pagesize
        y_haut = hauteur - 1.2 * cm
        x = doc.leftMargin
        x_droite = largeur - doc.rightMargin

        largeur_logo = 0.0
        if self._logo_pro_path and os.path.isfile(self._logo_pro_path):
            try:
                largeur_logo = _LOGO_ENTETE_HAUTEUR * 1.5
                canvas.drawImage(
                    self._logo_pro_path,
                    x,
                    y_haut - _LOGO_ENTETE_HAUTEUR,
                    width=largeur_logo,
                    height=_LOGO_ENTETE_HAUTEUR,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception as exc:
                logger.error("PdfBasePro._en_tete logo: %s", exc)
                largeur_logo = 0.0

        texte_x = x + largeur_logo + (0.4 * cm if largeur_logo else 0)

        canvas.setFillColor(COULEUR_NOIR)
        canvas.setFont(self._police_titre_bold, self._taille_base + 1)
        canvas.drawString(texte_x, y_haut, self.config_asso.nom or "Association")

        canvas.setFont(self._police_corps, self._taille_base - 1)
        canvas.setFillColor(COULEUR_GRIS)
        canvas.drawString(texte_x, y_haut - 0.45 * cm, self.titre)

        # Numéro de page à droite
        canvas.setFont(self._police_corps, self._taille_base - 1)
        canvas.setFillColor(COULEUR_GRIS)
        page_txt = f"Page {doc.page}"
        if self._total_pages:
            page_txt = f"Page {doc.page} / {self._total_pages}"
        canvas.drawRightString(x_droite, y_haut, page_txt)

        # Ligne colorée
        canvas.setStrokeColor(self._couleur_principale)
        canvas.setLineWidth(1.5)
        canvas.line(x, y_haut - 1.0 * cm, x_droite, y_haut - 1.0 * cm)

        canvas.restoreState()

    def _pied_de_page(self, canvas, doc) -> None:
        """Pied de page pro : logo petit + asso + titre + page X/Y."""
        canvas.saveState()
        largeur, _ = doc.pagesize
        footer_y = 0.9 * cm
        x = doc.leftMargin
        x_droite = largeur - doc.rightMargin

        # Ligne fine
        canvas.setStrokeColor(COULEUR_GRIS)
        canvas.setLineWidth(0.4)
        canvas.line(x, footer_y + 0.35 * cm, x_droite, footer_y + 0.35 * cm)

        # Logo petit
        logo_largeur = 0.0
        if self._logo_pro_path and os.path.isfile(self._logo_pro_path):
            try:
                logo_largeur = _LOGO_PIED_HAUTEUR * 1.5
                canvas.drawImage(
                    self._logo_pro_path,
                    x,
                    footer_y - 0.1 * cm,
                    width=logo_largeur,
                    height=_LOGO_PIED_HAUTEUR,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                logo_largeur = 0.0

        texte_x = x + logo_largeur + (0.3 * cm if logo_largeur else 0)

        canvas.setFont(self._police_corps, 7)
        canvas.setFillColor(COULEUR_GRIS)
        nom_asso = self.config_asso.nom or "Association"
        centre_txt = f"{nom_asso} | {self.titre}"
        canvas.drawString(texte_x, footer_y, centre_txt[:80])

        # Date à droite
        date_txt = self.date_export.strftime("%d/%m/%Y")
        canvas.drawRightString(x_droite, footer_y, date_txt)

        canvas.restoreState()

    # ── Méthodes utilitaires ──────────────────────────────────────────────────

    def _titre_section_pro(self, texte: str) -> list:
        """Titre de section avec fond coloré et numérotation automatique."""
        self._compteur_section += 1
        titre_numerate = f"{self._compteur_section}. {texte.upper()}"

        largeur_page = self.pagesize[0] - 2 * MARGE
        donnees = [[titre_numerate]]
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self._couleur_principale),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), self._police_titre_bold),
            ("FONTSIZE", (0, 0), (-1, -1), self._taille_base + 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
        tableau = Table(donnees, colWidths=[largeur_page])
        tableau.setStyle(style)
        return [Spacer(1, 0.3 * cm), tableau, Spacer(1, 0.3 * cm)]

    def _encadre_chiffre_cle(self, valeur: str, label: str, couleur: str | None = None) -> Table:
        """Retourne un encadré coloré pour un KPI.

        Args:
            valeur: La valeur à afficher en grand (ex. '42').
            label: Le libellé sous la valeur (ex. 'Adhérents').
            couleur: Couleur hex du fond, par défaut couleur principale.

        Returns:
            Un objet Table formaté.
        """
        if couleur:
            try:
                bg = colors.HexColor(couleur)
            except Exception:
                bg = self._couleur_principale
        else:
            bg = self._couleur_principale

        style_val = ParagraphStyle(
            "KpiVal",
            parent=self._style_bold,
            fontSize=self._taille_base + 6,
            textColor=colors.white,
            alignment=1,
            leading=self._taille_base + 10,
        )
        style_lbl = ParagraphStyle(
            "KpiLbl",
            parent=self._style_normal,
            fontSize=self._taille_base - 1,
            textColor=colors.white,
            alignment=1,
        )

        donnees = [
            [Paragraph(str(valeur), style_val)],
            [Paragraph(str(label), style_lbl)],
        ]
        tableau = Table(donnees, colWidths=[4 * cm])
        tableau.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tableau

    def _badge_statut(self, texte: str, couleur: str = "#2ecc71") -> Table:
        """Retourne un badge coloré pour afficher dans un tableau.

        Args:
            texte: Texte du badge.
            couleur: Couleur hex du fond.

        Returns:
            Un objet Table formaté.
        """
        try:
            bg = colors.HexColor(couleur)
        except Exception:
            bg = colors.HexColor("#2ecc71")

        style_badge = ParagraphStyle(
            "Badge",
            parent=self._style_normal,
            fontSize=self._taille_base - 2,
            textColor=colors.white,
            alignment=1,
        )
        donnees = [[Paragraph(str(texte), style_badge)]]
        tableau = Table(donnees)
        tableau.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tableau

    def _zone_signature(self, titres: list[str]) -> list:
        """Retourne un bloc de signatures avec lignes et intitulés.

        Args:
            titres: Liste des titres de signataires (ex. ['Le Président', ...]).

        Returns:
            Liste de flowables.
        """
        if not titres:
            return []

        elements = []
        elements.extend(self._titre_section("Signatures"))
        elements.append(Spacer(1, 0.5 * cm))

        n = len(titres)
        largeur_page = self.pagesize[0] - 2 * MARGE
        largeur_col = largeur_page / n

        style_titre_sig = ParagraphStyle(
            "SigTitre",
            parent=self._style_bold,
            fontSize=self._taille_base,
            alignment=1,
        )
        style_nom_sig = ParagraphStyle(
            "SigNom",
            parent=self._style_normal,
            fontSize=self._taille_base - 1,
            textColor=COULEUR_GRIS,
            alignment=1,
        )
        style_ligne_sig = ParagraphStyle(
            "SigLigne",
            parent=self._style_normal,
            fontSize=8,
            textColor=COULEUR_GRIS,
            alignment=1,
        )

        entetes = [[Paragraph(t, style_titre_sig) for t in titres]]
        espaces = [[Spacer(1, 1.5 * cm)] * n]
        lignes = [[Paragraph("_" * 25, style_ligne_sig)] * n]
        sous_lignes = [[Paragraph("Signature", style_nom_sig)] * n]

        for ligne_data in [entetes, espaces, lignes, sous_lignes]:
            t = Table(ligne_data, colWidths=[largeur_col] * n)
            t.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elements.append(t)

        elements.append(Spacer(1, 0.5 * cm))
        elements.append(
            Paragraph(
                f"Fait à _________________________, le _______________________",
                self._style_normal,
            )
        )
        return elements

    def _graphique_camembert(self, donnees: list[tuple[str, float]], titre: str) -> list:
        """Insère un graphique camembert dans le document."""
        try:
            from core.graphiques import graphique_camembert_rl

            drawing = graphique_camembert_rl(donnees, titre, self._couleur_principale_hex)
            return [drawing, Spacer(1, 0.3 * cm)]
        except Exception as exc:
            logger.error("_graphique_camembert: %s", exc)
            return [Paragraph(f"[Graphique : {titre}]", self._style_small)]

    def _graphique_barres(self, donnees: list[tuple[str, float, float]], titre: str,
                          label1: str = "Recettes", label2: str = "Dépenses") -> list:
        """Insère un histogramme dans le document."""
        try:
            from core.graphiques import graphique_barres_rl

            drawing = graphique_barres_rl(donnees, titre, self._couleur_principale_hex,
                                          label1=label1, label2=label2)
            return [drawing, Spacer(1, 0.3 * cm)]
        except Exception as exc:
            logger.error("_graphique_barres: %s", exc)
            return [Paragraph(f"[Graphique : {titre}]", self._style_small)]

    def _construire_contenu(self) -> list:
        """Doit être surchargé par les sous-classes."""
        raise NotImplementedError
