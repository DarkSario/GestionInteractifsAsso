"""PDF Bilan Assemblée Générale."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from core.pdf_base import BasePDF
from utils.logger import get_logger

logger = get_logger(__name__)

_SECTIONS_PAR_DEFAUT = {
    "resume_financier": True,
    "tresorerie_detail": True,
    "subventions": True,
    "evenements": True,
    "buvette": True,
    "adherents": True,
    "dons": True,
    "remboursements": False,
    "signatures": True,
}


class PdfBilanAG(BasePDF):
    """Export PDF du bilan pour l'assemblée générale."""

    def __init__(
        self,
        exercice: str,
        sections: dict | None = None,
        avec_graphiques: bool = False,
        orientation: str = "portrait",
    ):
        super().__init__("Bilan Assemblée Générale", orientation=orientation, avec_page_garde=True)
        self.exercice = exercice or self.exercice
        self._sections = dict(_SECTIONS_PAR_DEFAUT)
        if sections:
            self._sections.update(sections)
        self._avec_graphiques = bool(avec_graphiques)
        self._annee = self._extraire_annee(self.exercice)

    @staticmethod
    def _extraire_annee(exercice: str) -> int | None:
        chiffres = "".join(c for c in str(exercice or "") if c.isdigit())
        if len(chiffres) >= 4:
            return int(chiffres[:4])
        return None

    def _periode(self) -> tuple[str, str]:
        if not self._annee:
            return "", ""
        return f"{self._annee}-01-01", f"{self._annee}-12-31"

    def _construire_contenu(self) -> list:
        elements: list = [Paragraph(self.titre, self._style_titre)]
        if self.exercice:
            elements.append(Paragraph(f"Exercice : {self.exercice}", self._style_normal))
        if self._avec_graphiques:
            elements.append(Paragraph("Option graphiques activée.", self._style_small))
        elements.append(Spacer(1, 0.2 * cm))

        try:
            if self._sections.get("resume_financier"):
                elements.extend(self._section_resume_financier())
            if self._sections.get("tresorerie_detail"):
                elements.extend(self._section_tresorerie_detail())
            if self._sections.get("subventions"):
                elements.extend(self._section_subventions())
            if self._sections.get("evenements"):
                elements.extend(self._section_evenements())
            if self._sections.get("buvette"):
                elements.extend(self._section_buvette())
            if self._sections.get("adherents"):
                elements.extend(self._section_adherents())
            if self._sections.get("dons"):
                elements.extend(self._section_dons())
            if self._sections.get("remboursements"):
                elements.extend(self._section_remboursements())
            if self._sections.get("signatures"):
                elements.extend(self._section_signatures())
            return elements
        except Exception as exc:
            logger.exception("PdfBilanAG._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]

    def _section_resume_financier(self) -> list:
        from db.models.tresorerie import get_all_comptes, get_stats_tresorerie

        date_debut, date_fin = self._periode()
        elements = self._titre_section("Résumé financier")
        comptes = get_all_comptes(actif_only=False)
        stats = get_stats_tresorerie(date_debut=date_debut or None, date_fin=date_fin or None)

        if not comptes:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Compte", "Type", "Solde"]]
        for compte in comptes:
            donnees.append(
                [
                    compte.get("nom") or "—",
                    compte.get("type_compte") or "—",
                    self._formater_montant(compte.get("solde_actuel")),
                ]
            )
        donnees.append(["Total", "", self._formater_montant(sum(float(c.get("solde_actuel") or 0) for c in comptes))])
        elements.append(self._creer_tableau(donnees, col_widths=[7 * cm, 4 * cm, 4 * cm], avec_total=True))
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(
            self._creer_tableau(
                [
                    ["Indicateur", "Montant"],
                    ["Recettes", self._formater_montant(stats.get("total_recettes"))],
                    ["Dépenses", self._formater_montant(stats.get("total_depenses"))],
                    ["Solde", self._formater_montant(stats.get("solde"))],
                ],
                col_widths=[7 * cm, 4 * cm],
                avec_total=True,
            )
        )
        return elements

    def _section_tresorerie_detail(self) -> list:
        from db.models.tresorerie import get_stats_tresorerie

        date_debut, date_fin = self._periode()
        elements = self._titre_section("Trésorerie par catégorie")
        stats = get_stats_tresorerie(date_debut=date_debut or None, date_fin=date_fin or None)
        categories = stats.get("par_categorie") or {}
        if not categories:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Catégorie", "Montant"]]
        for nom, montant in sorted(categories.items(), key=lambda item: item[0].lower()):
            donnees.append([nom, self._formater_montant(montant)])
        donnees.append(["Solde total", self._formater_montant(stats.get("solde"))])
        elements.append(self._creer_tableau(donnees, col_widths=[9 * cm, 4 * cm], avec_total=True))
        return elements

    def _section_subventions(self) -> list:
        from db.models.tresorerie import get_all_subventions

        elements = self._titre_section("Subventions de l'exercice")
        subventions = get_all_subventions(annee=self._annee)
        if not subventions:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Organisme", "Demandé", "Obtenu", "Statut", "Date"]]
        total_demande = 0.0
        total_obtenu = 0.0
        for subvention in subventions:
            montant_demande = float(subvention.get("montant_demande") or 0)
            montant_obtenu = float(subvention.get("montant_obtenu") or 0)
            total_demande += montant_demande
            total_obtenu += montant_obtenu
            donnees.append(
                [
                    subvention.get("organisme") or "—",
                    self._formater_montant(montant_demande),
                    self._formater_montant(montant_obtenu),
                    subvention.get("statut") or "—",
                    self._formater_date(subvention.get("date_decision") or subvention.get("date_demande")),
                ]
            )
        donnees.append(["Total", self._formater_montant(total_demande), self._formater_montant(total_obtenu), "", ""])
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[5 * cm, 3 * cm, 3 * cm, 2.5 * cm, 2.5 * cm],
                avec_total=True,
            )
        )
        return elements

    def _section_evenements(self) -> list:
        from db.connection import get_connection

        elements = self._titre_section("Événements")
        conn = get_connection()
        try:
            if self._annee:
                rows = conn.execute(
                    """
                    SELECT nom, type, date_debut, date_fin, statut, budget_previsionnel
                    FROM evenements
                    WHERE substr(COALESCE(date_debut, date_fin, ''), 1, 4) = ?
                       OR substr(COALESCE(date_fin, date_debut, ''), 1, 4) = ?
                    ORDER BY date_debut DESC, id DESC
                    """,
                    (str(self._annee), str(self._annee)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT nom, type, date_debut, date_fin, statut, budget_previsionnel FROM evenements ORDER BY date_debut DESC, id DESC"
                ).fetchall()
            evenements = [dict(row) for row in rows]
        finally:
            conn.close()

        if not evenements:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Nom", "Type", "Date", "Statut", "Budget"]]
        for evenement in evenements:
            date_label = self._formater_date(evenement.get("date_debut"))
            if evenement.get("date_fin") and evenement.get("date_fin") != evenement.get("date_debut"):
                date_label = f"{date_label} → {self._formater_date(evenement.get('date_fin'))}"
            donnees.append(
                [
                    evenement.get("nom") or "—",
                    evenement.get("type") or "—",
                    date_label,
                    evenement.get("statut") or "—",
                    self._formater_montant(evenement.get("budget_previsionnel")),
                ]
            )
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[5 * cm, 3 * cm, 4 * cm, 2.5 * cm, 2.5 * cm],
            )
        )
        return elements

    def _section_buvette(self) -> list:
        from db.models.buvette import get_all_articles_buvette, get_recettes_buvette

        elements = self._titre_section("Bilan buvette")
        articles = get_all_articles_buvette(include_archives=False)
        recettes = get_recettes_buvette(limit=1000)
        if self._annee:
            recettes = [r for r in recettes if str(r.get("date") or "").startswith(str(self._annee))]

        if not articles and not recettes:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Indicateur", "Valeur"]]
        donnees.append(["Articles suivis", str(len(articles))])
        donnees.append(["Recettes enregistrées", str(len(recettes))])
        donnees.append(["Total brut", self._formater_montant(sum(float(r.get("total_brut") or 0) for r in recettes))])
        donnees.append(["Fond de caisse", self._formater_montant(sum(float(r.get("total_fond_caisse") or 0) for r in recettes))])
        donnees.append(["Recette nette", self._formater_montant(sum(float(r.get("recette_nette") or 0) for r in recettes))])
        elements.append(self._creer_tableau(donnees, col_widths=[8 * cm, 5 * cm], avec_total=True))
        return elements

    def _section_adherents(self) -> list:
        from db.models.membres import get_all_membres

        elements = self._titre_section("Statistiques adhérents")
        membres = get_all_membres(include_archives=True)
        if self._annee:
            membres = [
                m for m in membres
                if not m.get("date_adhesion") or str(m.get("date_adhesion")).startswith(str(self._annee))
            ]
        if not membres:
            return elements + [self._message_aucune_donnee()]

        par_statut: dict[str, int] = {}
        archives = 0
        for membre in membres:
            statut = membre.get("statut") or "Sans statut"
            par_statut[statut] = par_statut.get(statut, 0) + 1
            if int(membre.get("statut_archive") or 0) == 1:
                archives += 1

        donnees = [["Statut", "Effectif"]]
        for statut, nb in sorted(par_statut.items(), key=lambda item: item[0].lower()):
            donnees.append([statut, str(nb)])
        donnees.append(["Archivés", str(archives)])
        donnees.append(["Total", str(len(membres))])
        elements.append(self._creer_tableau(donnees, col_widths=[8 * cm, 4 * cm], avec_total=True))
        return elements

    def _section_dons(self) -> list:
        elements = self._titre_section("Dons reçus")
        try:
            from db.models.dons import get_all_dons

            filtres: dict = {}
            if self._annee:
                filtres["exercice_annee"] = self._annee
            dons = get_all_dons(filtres) if filtres else get_all_dons()
        except Exception:
            dons = []

        if not dons:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Date", "Donateur", "Nature", "Montant", "N° Reçu"]]
        total = 0.0
        for don in dons:
            montant = float(don.get("montant") or don.get("valeur_estimee") or 0)
            total += montant
            donateur = (don.get("donateur_nom") or "").strip()
            prenom = (don.get("donateur_prenom") or "").strip()
            if prenom:
                donateur = f"{donateur} {prenom}".strip()
            nature = "Nature" if don.get("nature_don") == "nature" else "Argent"
            donnees.append(
                [
                    self._formater_date(don.get("date_don")),
                    donateur or "—",
                    nature,
                    self._formater_montant(montant),
                    don.get("num_recu") or "—",
                ]
            )
        donnees.append(["Total", "", "", self._formater_montant(total), ""])
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[2.5 * cm, 5 * cm, 2.5 * cm, 2.5 * cm, 3.5 * cm],
                avec_total=True,
            )
        )
        return elements

    def _section_remboursements(self) -> list:
        elements = self._titre_section("Remboursements en attente")
        try:
            from db.models.remboursements import get_remboursements_en_attente

            lignes = get_remboursements_en_attente()
        except Exception:
            lignes = []

        if not lignes:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Bénéficiaire", "Description", "Montant", "Source"]]
        total = 0.0
        for ligne in lignes:
            montant = float(ligne.get("montant") or 0)
            total += montant
            donnees.append(
                [
                    ligne.get("beneficiaire") or "—",
                    ligne.get("description") or "—",
                    self._formater_montant(montant),
                    ligne.get("source") or "—",
                ]
            )
        donnees.append(["Total en attente", "", self._formater_montant(total), ""])
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[4 * cm, 6 * cm, 2.5 * cm, 3.5 * cm],
                avec_total=True,
            )
        )
        return elements

    def _section_signatures(self) -> list:
        elements = self._titre_section("Signatures")
        contenu = [
            [
                Paragraph("........................................<br/><br/>Président", self._style_center),
                Paragraph("........................................<br/><br/>Trésorier(e)", self._style_center),
                Paragraph("........................................<br/><br/>Secrétaire", self._style_center),
            ]
        ]
        tableau = Table(contenu, colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm])
        tableau.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ]
            )
        )
        return elements + [tableau]
