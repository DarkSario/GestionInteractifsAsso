"""PDF Bilan Assemblée Générale."""

from __future__ import annotations

from datetime import date, timedelta

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import CondPageBreak, HRFlowable, KeepTogether, Paragraph, Spacer, Table, TableStyle

from core.pdf_base_pro import PdfBasePro, COULEUR_GRIS
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


class PdfBilanAG(PdfBasePro):
    """Export PDF du bilan pour l'assemblée générale."""

    def __init__(
        self,
        exercice: str,
        sections: dict | None = None,
        avec_graphiques: bool = False,
        orientation: str = "portrait",
        type_periode: str = "scolaire",
        introduction: str = "",
        conclusion: str = "",
        date_debut: str | None = None,
        date_fin: str | None = None,
    ):
        super().__init__("Bilan Assemblée Générale", orientation=orientation, avec_page_garde=True)
        self.exercice = exercice or self.exercice
        self._sections = dict(_SECTIONS_PAR_DEFAUT)
        if sections:
            self._sections.update(sections)
        self._avec_graphiques = bool(avec_graphiques)
        self._type_periode = type_periode or "scolaire"
        self._annee = self._extraire_annee(self.exercice)
        self._introduction = introduction or ""
        self._conclusion = conclusion or ""
        self._date_debut = date_debut or ""
        self._date_fin = date_fin or ""

    @staticmethod
    def _extraire_annee(exercice: str) -> int | None:
        chiffres = "".join(c for c in str(exercice or "") if c.isdigit())
        if len(chiffres) >= 4:
            return int(chiffres[:4])
        return None

    def _periode(self) -> tuple[str, str]:
        if self._date_debut and self._date_fin:
            return self._date_debut, self._date_fin
        if not self._annee:
            return "", ""
        if self._type_periode == "civile":
            return f"{self._annee}-01-01", f"{self._annee}-12-31"
        # Année scolaire : ex "2025-2026" → sept 2025 à août 2026
        if "-" in str(self.exercice):
            parts = str(self.exercice).split("-")
            try:
                annee_debut = int(parts[0])
                annee_fin = int(parts[1]) if len(parts) > 1 else annee_debut + 1
                return f"{annee_debut}-09-01", f"{annee_fin}-08-31"
            except (ValueError, IndexError):
                pass
        return f"{self._annee}-01-01", f"{self._annee}-12-31"


    def _page_garde(self) -> list:
        """Page de garde professionnelle du Bilan AG."""
        import os

        elements: list = [Spacer(1, 3 * cm)]

        # Logo centré (priorité : logo_pro_path, puis config_asso.logo_path)
        logo_path = self._logo_pro_path or self.config_asso.logo_path or ""
        if logo_path and os.path.isfile(logo_path):
            try:
                from reportlab.platypus import Image as RLImage
                img = RLImage(logo_path, width=5 * cm, height=3 * cm, kind="proportional")
                img.hAlign = "CENTER"
                elements.append(img)
                elements.append(Spacer(1, 0.8 * cm))
            except Exception as exc:
                logger.error("PdfBilanAG._page_garde logo: %s", exc)

        # Ligne décorative
        elements.append(HRFlowable(
            width="80%",
            thickness=2,
            color=self._couleur_principale,
            hAlign="CENTER",
        ))
        elements.append(Spacer(1, 0.5 * cm))

        # Nom de l'association
        nom_asso = self.config_asso.nom or ""
        if not nom_asso:
            try:
                from db.models.parametres_globaux import get_parametre
                nom_asso = get_parametre("nom_asso", "") or get_parametre("asso_nom", "Association")
            except Exception:
                nom_asso = "Association"

        style_nom = ParagraphStyle(
            "BilanGardeNom",
            parent=self._style_nom_asso_couverture,
            textColor=self._couleur_principale,
            fontSize=20,
            spaceAfter=4,
        )
        elements.append(Paragraph(nom_asso, style_nom))

        elements.append(Spacer(1, 0.5 * cm))
        elements.append(HRFlowable(
            width="80%",
            thickness=2,
            color=self._couleur_principale,
            hAlign="CENTER",
        ))
        elements.append(Spacer(1, 1.5 * cm))

        # Titre principal
        style_titre_garde = ParagraphStyle(
            "BilanGardeTitre",
            parent=self._style_titre_couverture,
            fontSize=18,
            textColor=self._couleur_secondaire,
            spaceAfter=8,
        )
        elements.append(Paragraph("BILAN ASSEMBLÉE GÉNÉRALE", style_titre_garde))
        elements.append(Spacer(1, 0.8 * cm))

        # Exercice
        style_info = ParagraphStyle(
            "BilanGardeInfo",
            parent=self._style_normal,
            alignment=1,
            fontSize=11,
            spaceAfter=4,
        )
        style_label = ParagraphStyle(
            "BilanGardeLabel",
            parent=style_info,
            textColor=COULEUR_GRIS,
            fontSize=10,
        )
        if self.exercice:
            elements.append(Paragraph(f"Exercice {self.exercice}", style_info))
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(
            self.date_export.strftime("Généré le %d/%m/%Y"),
            style_label,
        ))

        return elements

    def _construire_contenu(self) -> list:
        elements: list = []
        if self.exercice:
            elements.append(Paragraph(f"Exercice : {self.exercice}", self._style_normal))
        if self._avec_graphiques:
            elements.append(Paragraph("Option graphiques activée.", self._style_small))
        elements.append(Spacer(1, 0.2 * cm))

        # Introduction
        if self._introduction:
            elements.append(Spacer(1, 0.3 * cm))
            import html as _html
            elements.append(Paragraph(_html.escape(self._introduction).replace("\n", "<br/>"), self._style_normal))
            elements.append(Spacer(1, 0.4 * cm))

        try:
            sections = [
                ("resume_financier", self._section_resume_financier),
                ("tresorerie_detail", self._section_tresorerie_detail),
                ("subventions", self._section_subventions),
                ("evenements", self._section_evenements),
                ("buvette", self._section_buvette),
                ("adherents", self._section_adherents),
                ("dons", self._section_dons),
                ("remboursements", self._section_remboursements),
                ("signatures", self._section_signatures),
            ]
            for section_key, section_fn in sections:
                if self._sections.get(section_key):
                    elements.append(CondPageBreak(6 * cm))
                    elements.extend(self._envelopper_section(section_fn()))

            # Conclusion (avant la signature si pas de section signatures)
            if self._conclusion:
                import html as _html
                elements.append(Spacer(1, 0.4 * cm))
                elements.append(Paragraph(_html.escape(self._conclusion).replace("\n", "<br/>"), self._style_normal))
                elements.append(Spacer(1, 0.3 * cm))

            return elements
        except Exception as exc:
            logger.exception("PdfBilanAG._construire_contenu: %s", exc)
            return elements + [self._message_aucune_donnee()]

    def _envelopper_section(self, elements_section: list) -> list:
        """Garde titre + début de section ensemble sur la même page."""
        # Seuil : sections de moins de 15 flowables sont gardées entièrement ensemble
        _SEUIL_SECTION_COURTE = 15
        # Nombre de flowables de "tête" à garder solidaires (titre + spacer + tableau header)
        _NB_ELEMENTS_ENTETE = 4
        if not elements_section:
            return elements_section
        try:
            if len(elements_section) <= _SEUIL_SECTION_COURTE:
                return [KeepTogether(elements_section)]
            # Pour les sections longues, garder au moins l'entête + début du contenu ensemble
            tete = elements_section[:_NB_ELEMENTS_ENTETE]
            suite = elements_section[_NB_ELEMENTS_ENTETE:]
            return [KeepTogether(tete)] + suite
        except Exception:
            return elements_section

    def _section_resume_financier(self) -> list:
        from db.models.tresorerie import get_all_comptes, get_stats_tresorerie

        date_debut, date_fin = self._periode()
        elements = self._titre_section_pro("Résumé financier")
        if date_fin:
            elements.append(Paragraph(f"Soldes des comptes au {self._formater_date(date_fin)}.", self._style_normal))
        comptes = get_all_comptes(actif_only=False, date_fin=date_fin or None)
        stats = get_stats_tresorerie(date_debut=date_debut or None, date_fin=date_fin or None)
        solde_ouverture = None
        if date_debut:
            try:
                veille_periode = (date.fromisoformat(date_debut[:10]) - timedelta(days=1)).isoformat()
                comptes_ouverture = get_all_comptes(actif_only=False, date_fin=veille_periode)
                solde_ouverture = sum(
                    float(compte.get("solde_actuel") or 0) for compte in comptes_ouverture
                )
            except ValueError:
                logger.warning("Date de début invalide pour le solde d'ouverture : %s", date_debut)

        if not comptes:
            return elements + [self._message_aucune_donnee()]

        solde_cloture = sum(float(compte.get("solde_actuel") or 0) for compte in comptes)
        donnees = [["Compte", "Type", "Solde (fin de période)"]]
        for compte in comptes:
            donnees.append(
                [
                    compte.get("nom") or "—",
                    compte.get("type_compte") or "—",
                    self._formater_montant(compte.get("solde_actuel")),
                ]
            )
        donnees.append(["Total", "", self._formater_montant(solde_cloture)])
        elements.append(self._creer_tableau(donnees, col_widths=[7 * cm, 4 * cm, 4 * cm], avec_total=True))
        elements.append(Spacer(1, 0.2 * cm))
        indicateurs = [["Indicateur", "Montant"]]
        if solde_ouverture is not None:
            indicateurs.append(["Solde d'ouverture", self._formater_montant(solde_ouverture)])
        indicateurs.extend(
            [
                ["Recettes", self._formater_montant(stats.get("total_recettes"))],
                ["Dépenses", self._formater_montant(stats.get("total_depenses"))],
                ["Variation nette", self._formater_montant(stats.get("solde"))],
                ["Solde de clôture", self._formater_montant(solde_cloture)],
            ]
        )
        elements.append(
            self._creer_tableau(
                indicateurs,
                col_widths=[7 * cm, 4 * cm],
                avec_total=True,
            )
        )
        return elements

    def _section_tresorerie_detail(self) -> list:
        from db.models.tresorerie import get_stats_tresorerie

        date_debut, date_fin = self._periode()
        elements = self._titre_section_pro("Trésorerie par catégorie")
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

        elements = self._titre_section_pro("Subventions de l'exercice")
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
        from core.caisses_evenement import calculer_bilan_complet_evenement
        from db.connection import get_connection

        date_debut, date_fin = self._periode()
        elements = self._titre_section_pro("Événements")
        conn = get_connection()
        try:
            colonnes = (
                "id, nom, type, date_debut, date_fin, statut, budget_previsionnel"
            )
            if date_debut and date_fin:
                rows = conn.execute(
                    f"""
                    SELECT {colonnes}
                    FROM evenements
                    WHERE substr(COALESCE(NULLIF(date_debut, ''), date_fin, ''), 1, 10) <= ?
                      AND substr(COALESCE(NULLIF(date_fin, ''), date_debut, ''), 1, 10) >= ?
                    ORDER BY date_debut DESC, id DESC
                    """,
                    (date_fin, date_debut),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {colonnes} FROM evenements ORDER BY date_debut DESC, id DESC"
                ).fetchall()
            evenements = [dict(row) for row in rows]
        finally:
            conn.close()

        if not evenements:
            return elements + [self._message_aucune_donnee()]

        donnees = [["Nom", "Date", "Statut", "Budget", "Recettes", "Dépenses"]]
        total_recettes = 0.0
        total_depenses = 0.0
        for evenement in evenements:
            date_label = self._formater_date(evenement.get("date_debut"))
            if evenement.get("date_fin") and evenement.get("date_fin") != evenement.get("date_debut"):
                date_label = f"{date_label} → {self._formater_date(evenement.get('date_fin'))}"
            try:
                bilan = calculer_bilan_complet_evenement(int(evenement["id"]))
            except Exception as exc:
                logger.warning("PdfBilanAG._section_evenements bilan %s: %s", evenement.get("id"), exc)
                bilan = {}
            recettes = float(bilan.get("total_recettes") or 0)
            depenses = float(bilan.get("total_depenses") or 0)
            total_recettes += recettes
            total_depenses += depenses
            donnees.append(
                [
                    evenement.get("nom") or "—",
                    date_label,
                    evenement.get("statut") or "—",
                    self._formater_montant(evenement.get("budget_previsionnel")),
                    self._formater_montant(recettes),
                    self._formater_montant(depenses),
                ]
            )
        donnees.append(
            ["Total", "", "", "", self._formater_montant(total_recettes), self._formater_montant(total_depenses)]
        )
        elements.append(
            self._creer_tableau(
                donnees,
                col_widths=[4.2 * cm, 3.6 * cm, 2 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm],
                avec_total=True,
            )
        )
        elements.append(
            Paragraph(
                "Recettes et dépenses issues du module Événements (billetterie, stands, tombola, "
                "buvette, caisses) : bilan complet de chaque événement, pas uniquement les "
                "opérations de la période. Ces montants sont informatifs et ne s'ajoutent pas "
                "aux totaux de trésorerie.",
                self._style_normal,
            )
        )
        return elements

    def _section_buvette(self) -> list:
        from db.models.buvette import get_all_articles_buvette, get_recettes_buvette

        date_debut, date_fin = self._periode()
        elements = self._titre_section_pro("Bilan buvette")
        articles = get_all_articles_buvette(include_archives=False)
        recettes = get_recettes_buvette(
            limit=None, date_debut=date_debut or None, date_fin=date_fin or None
        )

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

        elements = self._titre_section_pro("Statistiques adhérents")
        membres = get_all_membres(include_archives=True)
        # Ne pas filtrer par année d'adhésion — afficher tous les membres actifs
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
        elements = self._titre_section_pro("Dons reçus")
        try:
            from db.models.dons import get_all_dons

            date_debut, date_fin = self._periode()
            filtres = {}
            if date_debut:
                filtres["date_debut"] = date_debut
            if date_fin:
                filtres["date_fin"] = date_fin
            dons = get_all_dons(filtres)
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
        elements = self._titre_section_pro("Remboursements en attente")
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
        elements = self._titre_section_pro("Signatures")
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
