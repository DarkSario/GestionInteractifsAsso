"""Exports PDF du stock."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from core.pdf_base import BasePDF
from utils.logger import get_logger

logger = get_logger(__name__)


class PdfListeStock(BasePDF):
    """Export PDF de la liste du stock."""

    def __init__(self, orientation: str = "portrait"):
        super().__init__("Liste du stock", orientation=orientation, avec_page_garde=False)

    def _construire_contenu(self) -> list:
        from db.models.stock import get_all_articles

        elements: list = [Paragraph(self.titre, self._style_titre), Spacer(1, 0.2 * cm)]
        try:
            articles = get_all_articles(include_archives=False)
            elements.extend(self._titre_section("Articles"))
            if not articles:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Désignation", "Catégorie", "Qté", "Unité", "Seuil", "Statut"]]
            for article in articles:
                quantite = int(article.get("quantite") or 0)
                seuil = int(article.get("seuil_alerte") or 0)
                statut = "Sous seuil" if quantite <= seuil else "OK"
                donnees.append(
                    [
                        article.get("nom") or "—",
                        article.get("categorie_nom") or "—",
                        str(quantite),
                        article.get("unite_nom") or "—",
                        str(seuil),
                        statut,
                    ]
                )
            elements.append(
                self._creer_tableau(
                    donnees,
                    col_widths=[5.5 * cm, 4 * cm, 2 * cm, 2.5 * cm, 2 * cm, 3 * cm],
                    alignements={2: "RIGHT", 4: "RIGHT"},
                )
            )
            return elements
        except Exception as exc:
            logger.error("PdfListeStock._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]


class PdfHistoriqueStock(BasePDF):
    """Export PDF de l'historique du stock."""

    def __init__(self, date_debut: str = "", date_fin: str = "", orientation: str = "portrait"):
        super().__init__("Historique du stock", orientation=orientation, avec_page_garde=False)
        self._date_debut = date_debut or ""
        self._date_fin = date_fin or ""

    def _construire_contenu(self) -> list:
        from db.models.stock import get_all_mouvements

        elements: list = [Paragraph(self.titre, self._style_titre), Spacer(1, 0.2 * cm)]
        try:
            mouvements = get_all_mouvements(limit=10000)
            if self._date_debut:
                mouvements = [m for m in mouvements if str(m.get("date") or "") >= self._date_debut]
            if self._date_fin:
                mouvements = [m for m in mouvements if str(m.get("date") or "") <= self._date_fin]

            if self._date_debut or self._date_fin:
                elements.append(
                    Paragraph(
                        f"Période : {self._formater_date(self._date_debut) if self._date_debut else 'Début'}"
                        f" → {self._formater_date(self._date_fin) if self._date_fin else 'Fin'}",
                        self._style_normal,
                    )
                )
                elements.append(Spacer(1, 0.1 * cm))

            elements.extend(self._titre_section("Mouvements"))
            if not mouvements:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Date", "Article", "Type mouvement", "Qté", "Fournisseur"]]
            for mouvement in mouvements:
                donnees.append(
                    [
                        self._formater_date(mouvement.get("date")),
                        mouvement.get("article_nom") or "—",
                        mouvement.get("type") or "—",
                        str(mouvement.get("quantite") or 0),
                        mouvement.get("fournisseur_nom") or "—",
                    ]
                )
            elements.append(
                self._creer_tableau(
                    donnees,
                    col_widths=[3 * cm, 5 * cm, 4.5 * cm, 2 * cm, 5.5 * cm],
                    alignements={3: "RIGHT"},
                )
            )
            return elements
        except Exception as exc:
            logger.error("PdfHistoriqueStock._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]
