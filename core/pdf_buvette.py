"""Exports PDF du module buvette."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from core.pdf_base import BasePDF
from utils.logger import get_logger

logger = get_logger(__name__)


class PdfRapportCaisse(BasePDF):
    """Export PDF d'un rapport de caisse buvette."""

    def __init__(self, session_id: int | None = None):
        super().__init__("Rapport de caisse buvette", orientation="portrait", avec_page_garde=False)
        self._session_id = session_id

    def _construire_contenu(self) -> list:
        from db.models.buvette import get_caisses_by_evenement, get_recettes_buvette
        from db.models.buvette import get_all_articles_buvette

        elements: list = [Paragraph(self.titre, self._style_titre)]
        if self._session_id is not None:
            elements.append(Paragraph(f"Session / événement : {self._session_id}", self._style_normal))
        elements.append(Spacer(1, 0.1 * cm))

        try:
            articles = get_all_articles_buvette(include_archives=False)
            elements.extend(self._titre_section("Articles vendus"))
            if articles:
                donnees_articles = [["Nom", "Qté", "Prix unitaire", "Total"]]
                total_global = 0.0
                for article in articles:
                    quantite = int(article.get("stock_actuel") or 0)
                    prix_unitaire = float(article.get("prix_vente") or 0)
                    total = quantite * prix_unitaire
                    total_global += total
                    donnees_articles.append(
                        [
                            article.get("nom") or "—",
                            str(quantite),
                            self._formater_montant(prix_unitaire),
                            self._formater_montant(total),
                        ]
                    )
                donnees_articles.append(["Total", "", "", self._formater_montant(total_global)])
                elements.append(
                    self._creer_tableau(
                        donnees_articles,
                        col_widths=[7 * cm, 2 * cm, 3.5 * cm, 3.5 * cm],
                        avec_total=True,
                    )
                )
            else:
                elements.append(self._message_aucune_donnee())

            elements.append(Spacer(1, 0.2 * cm))
            elements.extend(self._titre_section("Recettes par mode de paiement"))
            if self._session_id is None:
                recettes = get_recettes_buvette(limit=1000)
                caisses = []
            else:
                recettes = [r for r in get_recettes_buvette(limit=1000) if int(r.get("evenement_id") or 0) == self._session_id]
                caisses = get_caisses_by_evenement(self._session_id)

            if self._session_id is None:
                from db.connection import get_connection

                conn = get_connection()
                try:
                    rows = conn.execute(
                        "SELECT id, evenement_id, nom, fond_de_caisse, total_brut, date, commentaire FROM caisses_buvette ORDER BY date DESC, id DESC"
                    ).fetchall()
                    caisses = [dict(row) for row in rows]
                finally:
                    conn.close()

            if not caisses and not recettes:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees_recettes = [["Mode / Caisse", "Montant brut", "Fond de caisse", "Net"]]
            total_brut = 0.0
            total_fond = 0.0
            total_net = 0.0
            for caisse in caisses:
                brut = float(caisse.get("total_brut") or 0)
                fond = float(caisse.get("fond_de_caisse") or 0)
                net = brut - fond
                total_brut += brut
                total_fond += fond
                total_net += net
                donnees_recettes.append(
                    [
                        caisse.get("nom") or "—",
                        self._formater_montant(brut),
                        self._formater_montant(fond),
                        self._formater_montant(net),
                    ]
                )
            if recettes and not caisses:
                for recette in recettes:
                    brut = float(recette.get("total_brut") or 0)
                    fond = float(recette.get("total_fond_caisse") or 0)
                    net = float(recette.get("recette_nette") or 0)
                    total_brut += brut
                    total_fond += fond
                    total_net += net
                    donnees_recettes.append(
                        [
                            recette.get("evenement_nom") or "Recette",
                            self._formater_montant(brut),
                            self._formater_montant(fond),
                            self._formater_montant(net),
                        ]
                    )
            donnees_recettes.append(
                [
                    "Total",
                    self._formater_montant(total_brut),
                    self._formater_montant(total_fond),
                    self._formater_montant(total_net),
                ]
            )
            elements.append(
                self._creer_tableau(
                    donnees_recettes,
                    col_widths=[7 * cm, 3 * cm, 3 * cm, 3 * cm],
                    avec_total=True,
                )
            )
            return elements
        except Exception as exc:
            logger.error("PdfRapportCaisse._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]
