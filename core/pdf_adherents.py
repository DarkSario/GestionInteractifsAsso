"""Exports PDF des adhérents."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from core.pdf_base import BasePDF
from utils.logger import get_logger

logger = get_logger(__name__)


class PdfListeAdherents(BasePDF):
    """Export PDF de la liste des adhérents."""

    def __init__(self, filtre_statut: str = "", actif_seulement: bool = True, orientation: str = "portrait"):
        super().__init__("Liste des adhérents", orientation=orientation, avec_page_garde=False)
        self._filtre_statut = (filtre_statut or "").strip()
        self._actif_seulement = bool(actif_seulement)

    def _construire_contenu(self) -> list:
        from db.models.membres import get_all_membres

        elements: list = [Paragraph(self.titre, self._style_titre), Spacer(1, 0.2 * cm)]
        try:
            membres = get_all_membres(include_archives=not self._actif_seulement)
            if self._filtre_statut:
                filtre = self._filtre_statut.casefold()
                membres = [m for m in membres if str(m.get("statut") or "").casefold() == filtre]

            if self._filtre_statut:
                elements.append(Paragraph(f"Filtre statut : {self._filtre_statut}", self._style_normal))
                elements.append(Spacer(1, 0.1 * cm))

            elements.extend(self._titre_section("Coordonnées"))
            if not membres:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Nom", "Prénom", "Statut", "Téléphone", "Email"]]
            for membre in membres:
                donnees.append(
                    [
                        membre.get("nom") or "—",
                        membre.get("prenom") or "—",
                        membre.get("statut") or "—",
                        membre.get("telephone") or "—",
                        membre.get("email") or "—",
                    ]
                )
            donnees.append(["Total", "", str(len(membres)), "", ""])
            elements.append(
                self._creer_tableau(
                    donnees,
                    col_widths=[4 * cm, 4 * cm, 3.5 * cm, 3.5 * cm, 5 * cm],
                    avec_total=True,
                )
            )
            return elements
        except Exception as exc:
            logger.error("PdfListeAdherents._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]


class PdfFicheAdherent(BasePDF):
    """Export PDF de la fiche d'un adhérent."""

    def __init__(self, membre_id: int):
        super().__init__("Fiche adhérent", orientation="portrait", avec_page_garde=False)
        self._membre_id = membre_id

    def _construire_contenu(self) -> list:
        from db.models.membres import get_membre_by_id

        membre = get_membre_by_id(self._membre_id)
        if not membre:
            raise ValueError(f"Adhérent introuvable : id={self._membre_id}")

        nom_complet = f"{membre.get('prenom') or ''} {membre.get('nom') or ''}".strip() or f"Adhérent #{self._membre_id}"
        elements: list = [Paragraph(self.titre, self._style_titre)]
        elements.append(Paragraph(nom_complet, self._style_bold))
        elements.append(Spacer(1, 0.2 * cm))

        elements.extend(self._titre_section("Informations personnelles"))
        infos = [
            ["Champ", "Valeur"],
            ["Nom", membre.get("nom") or "—"],
            ["Prénom", membre.get("prenom") or "—"],
            ["Statut", membre.get("statut") or "—"],
            ["Téléphone", membre.get("telephone") or "—"],
            ["Email", membre.get("email") or "—"],
            ["Date d'adhésion", self._formater_date(membre.get("date_adhesion"))],
        ]
        elements.append(self._creer_tableau(infos, col_widths=[5 * cm, 11 * cm]))

        elements.extend(self._titre_section("Commentaire"))
        commentaire = (membre.get("commentaire") or "").strip()
        elements.append(Paragraph(commentaire.replace("\n", "<br/>"), self._style_normal) if commentaire else self._message_aucune_donnee())
        return elements
