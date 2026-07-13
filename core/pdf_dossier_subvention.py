"""Génération PDF du Dossier de Demande de Subvention — Phase 21."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from core.pdf_base_pro import PdfBasePro, COULEUR_GRIS, COULEUR_NOIR, MARGE
from utils.logger import get_logger

logger = get_logger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_CONFIG_DIR = _BASE_DIR / "config"

_TEMPLATES = {
    "presentation": "dossier_subvention_presentation.md",
    "mot_president": "dossier_subvention_mot_president.md",
    "projet": "dossier_subvention_projet.md",
    "objectifs": "dossier_subvention_objectifs.md",
    "statuts": "dossier_subvention_statuts.md",
    "budget_projet": "dossier_subvention_budget_projet.md",
}

_SECTIONS_PAR_DEFAUT = {
    "page_garde": True,
    "table_matieres": True,
    "presentation": True,
    "mot_president": True,
    "adherents": True,
    "evenements": True,
    "benevoles": True,
    "buvette": True,
    "resume_financier": True,
    "tresorerie_detail": True,
    "soldes_comptes": True,
    "subventions_recues": True,
    "dons_recus": True,
    "remboursements": False,
    "projet": True,
    "budget_projet": True,
    "objectifs": True,
    "signatures": True,
    "statuts": False,
    "membres_bureau": False,
    "inclure_graphiques": True,
    "numerotation": True,
    "entete_pied": True,
}


class PdfDossierSubvention(PdfBasePro):
    """Export PDF complet du Dossier de Demande de Subvention."""

    def __init__(
        self,
        periode: str,
        type_periode: str = "scolaire",
        organisateur: str = "",
        objet: str = "",
        montant_demande: float = 0.0,
        sections: dict | None = None,
    ):
        super().__init__(
            "Dossier de Demande de Subvention",
            orientation="portrait",
            avec_page_garde=True,
        )
        self._periode = periode
        self._type_periode = type_periode or "scolaire"
        self._organisateur = organisateur
        self._objet = objet
        self._montant_demande = float(montant_demande or 0)
        self._sections_config = dict(_SECTIONS_PAR_DEFAUT)
        if sections:
            self._sections_config.update(sections)

        self.exercice = periode
        self._date_debut, self._date_fin = self._calcul_periode()
        self._variables = self._charger_variables()

    def _calcul_periode(self) -> tuple[str, str]:
        """Calcule les dates de début/fin selon le type de période."""
        if self._type_periode == "civile":
            try:
                annee = int(self._periode[:4])
                return f"{annee}-01-01", f"{annee}-12-31"
            except (ValueError, TypeError):
                pass
        else:
            try:
                parts = str(self._periode).split("-")
                annee_debut = int(parts[0])
                annee_fin = int(parts[1]) if len(parts) > 1 else annee_debut + 1
                return f"{annee_debut}-09-01", f"{annee_fin}-08-31"
            except (ValueError, IndexError):
                pass
        annee = datetime.now().year
        return f"{annee}-01-01", f"{annee}-12-31"

    def _charger_variables(self) -> dict:
        """Charge les variables de remplacement depuis la DB."""
        variables = {
            "nom_asso": self.config_asso.nom or "",
            "adresse_asso": self.config_asso.adresse or "",
            "exercice": self._periode,
            "date_export": self.date_export.strftime("%d/%m/%Y"),
            "organisme": self._organisateur,
            "objet": self._objet,
            "montant_demande": f"{self._montant_demande:,.2f}".replace(",", " ").replace(".", ","),
            "annee_creation": "",
            "objet_social": "",
            "president_nom": "",
            "nb_adherents": "0",
            "nb_benevoles": "0",
            "nb_evenements": "0",
        }
        try:
            from db.connection import get_connection
            from db.models.parametres_globaux import get_parametre

            variables["annee_creation"] = get_parametre("annee_creation", "") or ""
            variables["objet_social"] = get_parametre("objet_social", "") or ""
            variables["president_nom"] = get_parametre("president_nom", "") or ""

            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) as nb FROM membres WHERE statut = 'actif'"
                ).fetchone()
                variables["nb_adherents"] = str(row["nb"]) if row else "0"

                row = conn.execute(
                    """SELECT COUNT(*) as nb FROM evenements
                       WHERE date_debut >= ? AND date_debut <= ?""",
                    (self._date_debut, self._date_fin),
                ).fetchone()
                variables["nb_evenements"] = str(row["nb"]) if row else "0"

                row = conn.execute(
                    """SELECT COUNT(DISTINCT membre_id) as nb FROM evenement_benevoles
                       WHERE membre_id IS NOT NULL"""
                ).fetchone()
                variables["nb_benevoles"] = str(row["nb"]) if row else "0"
            finally:
                conn.close()
        except Exception as exc:
            logger.error("_charger_variables: %s", exc)
        return variables

    def _remplacer_variables(self, texte: str) -> str:
        """Remplace les {{variables}} dans un texte."""
        for cle, valeur in self._variables.items():
            texte = texte.replace(f"{{{{{cle}}}}}", str(valeur))
        return texte

    def _lire_template(self, cle: str) -> str:
        """Lit le template depuis le fichier config."""
        nom_fichier = _TEMPLATES.get(cle)
        if not nom_fichier:
            return ""
        chemin = _CONFIG_DIR / nom_fichier
        try:
            return chemin.read_text(encoding="utf-8")
        except FileNotFoundError:
            chemin_defaut = _CONFIG_DIR / nom_fichier.replace(".md", ".default.md")
            try:
                return chemin_defaut.read_text(encoding="utf-8")
            except FileNotFoundError:
                return ""
        except Exception as exc:
            logger.error("_lire_template(%s): %s", cle, exc)
            return ""

    # ── Page de garde ─────────────────────────────────────────────────────────

    def _page_garde(self) -> list:
        """Construit la page de garde professionnelle."""
        elements: list = [Spacer(1, 3 * cm)]

        # Logo centré
        if self._logo_pro_path and os.path.isfile(self._logo_pro_path):
            try:
                img = Image(self._logo_pro_path, width=5 * cm, height=3 * cm, kind="proportional")
                img.hAlign = "CENTER"
                elements.append(img)
                elements.append(Spacer(1, 0.8 * cm))
            except Exception as exc:
                logger.error("_page_garde logo: %s", exc)

        # Ligne décorative
        elements.append(HRFlowable(
            width="80%",
            thickness=2,
            color=self._couleur_principale,
            hAlign="CENTER",
        ))
        elements.append(Spacer(1, 0.5 * cm))

        # Nom association
        style_nom = ParagraphStyle(
            "GardeNom",
            parent=self._style_nom_asso_couverture,
            textColor=self._couleur_principale,
            fontSize=20,
            spaceAfter=4,
        )
        elements.append(Paragraph(self.config_asso.nom or "Association", style_nom))

        # Adresse / contact
        if self.config_asso.adresse or self.config_asso.telephone or self.config_asso.email:
            lignes_contact = []
            if self.config_asso.adresse:
                lignes_contact.append(self.config_asso.adresse)
            if self.config_asso.telephone:
                lignes_contact.append(f"Tél. {self.config_asso.telephone}")
            if self.config_asso.email:
                lignes_contact.append(self.config_asso.email)
            style_contact = ParagraphStyle(
                "GardeContact",
                parent=self._style_center,
                textColor=COULEUR_GRIS,
                fontSize=9,
            )
            elements.append(Paragraph(" • ".join(lignes_contact), style_contact))

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
            "GardeTitre",
            parent=self._style_titre_couverture,
            fontSize=18,
            textColor=self._couleur_secondaire,
            spaceAfter=8,
        )
        elements.append(Paragraph("DOSSIER DE DEMANDE DE SUBVENTION", style_titre_garde))
        elements.append(Spacer(1, 0.8 * cm))

        # Informations demande
        style_info = ParagraphStyle(
            "GardeInfo",
            parent=self._style_normal,
            alignment=1,
            fontSize=11,
            spaceAfter=4,
        )
        style_label = ParagraphStyle(
            "GardeLabel",
            parent=style_info,
            textColor=COULEUR_GRIS,
            fontSize=10,
        )

        if self._organisateur:
            elements.append(Paragraph(f"Adressé à : <b>{self._organisateur}</b>", style_info))
        if self._objet:
            elements.append(Paragraph(f"Objet : {self._objet}", style_label))
        if self._montant_demande:
            montant_fmt = f"{self._montant_demande:,.2f} €".replace(",", "\u202f").replace(".", ",")
            elements.append(Paragraph(f"Montant demandé : <b>{montant_fmt}</b>", style_info))

        type_label = "Année civile" if self._type_periode == "civile" else "Exercice"
        elements.append(Paragraph(f"Période : {type_label} {self._periode}", style_label))
        elements.append(Spacer(1, 0.5 * cm))

        _mois_fr = {
            "January": "janvier", "February": "février", "March": "mars",
            "April": "avril", "May": "mai", "June": "juin",
            "July": "juillet", "August": "août", "September": "septembre",
            "October": "octobre", "November": "novembre", "December": "décembre",
        }
        date_str = self.date_export.strftime("%d %B %Y")
        for _en, _fr in _mois_fr.items():
            date_str = date_str.replace(_en, _fr)
        elements.append(Paragraph(f"Généré le {date_str}", style_label))

        return elements

    # ── Sections ──────────────────────────────────────────────────────────────

    def _section_presentation(self) -> list:
        elements = self._titre_section_pro("Présentation de l'association")

        # KPI
        kpis = [
            (self._variables["nb_adherents"], "Adhérents"),
            (self._variables["nb_evenements"], "Événements"),
        ]
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                row = conn.execute(
                    """SELECT COALESCE(SUM(montant), 0) as total FROM tresorerie_operations
                       WHERE date_operation >= ? AND date_operation <= ?""",
                    (self._date_debut, self._date_fin),
                ).fetchone()
                budget = float(row["total"]) if row else 0.0
                budget_fmt = f"{budget:,.0f} €".replace(",", "\u202f")
                kpis.append((budget_fmt, "Budget"))
            finally:
                conn.close()
        except Exception:
            pass

        largeur_page = self.pagesize[0] - 2 * MARGE
        largeur_kpi = min(4 * cm, largeur_page / max(len(kpis), 1))
        encadres = [self._encadre_chiffre_cle(v, l) for v, l in kpis]
        if encadres:
            t = Table([encadres], colWidths=[largeur_kpi] * len(encadres))
            t.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.4 * cm))

        # Texte template
        texte = self._remplacer_variables(self._lire_template("presentation"))
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne:
                elements.append(Spacer(1, 0.2 * cm))
                continue
            if ligne.startswith("## "):
                continue
            if ligne.startswith("**") and ligne.endswith("**"):
                elements.append(Paragraph(ligne[2:-2], self._style_bold))
            else:
                elements.append(Paragraph(ligne, self._style_normal))

        return elements

    def _section_mot_president(self) -> list:
        elements = self._titre_section_pro("Mot du Président")
        texte = self._remplacer_variables(self._lire_template("mot_president"))
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("## "):
                elements.append(Spacer(1, 0.2 * cm))
                continue
            if ligne.startswith("*") and ligne.endswith("*") and not ligne.startswith("**"):
                elements.append(Paragraph(ligne[1:-1], self._style_message))
            else:
                elements.append(Paragraph(ligne, self._style_normal))
        return elements

    def _section_adherents(self) -> list:
        elements = self._titre_section_pro("Statistiques adhérents")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    "SELECT statut, COUNT(*) as nb FROM membres GROUP BY statut ORDER BY statut"
                ).fetchall()
                total = conn.execute("SELECT COUNT(*) as nb FROM membres").fetchone()
            finally:
                conn.close()

            if not rows:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Statut", "Nombre"]]
            for row in rows:
                donnees.append([row["statut"] or "(Inconnu)", str(row["nb"])])
            if total:
                donnees.append(["TOTAL", str(total["nb"])])

            elements.append(self._creer_tableau(
                donnees,
                col_widths=[10 * cm, 5 * cm],
                avec_total=bool(total),
            ))

            if self._sections_config.get("inclure_graphiques") and rows:
                elements.extend(self._graphique_camembert(
                    [(str(r["statut"]), float(r["nb"])) for r in rows],
                    "Répartition des adhérents",
                ))
        except Exception as exc:
            logger.error("_section_adherents: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_evenements(self) -> list:
        elements = self._titre_section_pro("Liste des événements")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT nom, date_debut, lieu, statut
                       FROM evenements
                       WHERE date_debut >= ? AND date_debut <= ?
                       ORDER BY date_debut""",
                    (self._date_debut, self._date_fin),
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Événement", "Date", "Lieu", "Statut"]]
            for row in rows:
                donnees.append([
                    row["nom"] or "",
                    self._formater_date(row["date_debut"]),
                    row["lieu"] or "—",
                    row["statut"] or "—",
                ])
            elements.append(self._creer_tableau(donnees))
        except Exception as exc:
            logger.error("_section_evenements: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_resume_financier(self) -> list:
        elements = self._titre_section_pro("Bilan financier")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rec = conn.execute(
                    """SELECT COALESCE(SUM(montant), 0) as total FROM tresorerie_operations
                       WHERE type_operation = 'recette' AND date_operation >= ? AND date_operation <= ?""",
                    (self._date_debut, self._date_fin),
                ).fetchone()
                dep = conn.execute(
                    """SELECT COALESCE(SUM(montant), 0) as total FROM tresorerie_operations
                       WHERE type_operation = 'depense' AND date_operation >= ? AND date_operation <= ?""",
                    (self._date_debut, self._date_fin),
                ).fetchone()
            finally:
                conn.close()

            recettes = float(rec["total"]) if rec else 0.0
            depenses = float(dep["total"]) if dep else 0.0
            solde = recettes - depenses

            donnees = [
                ["Indicateur", "Montant"],
                ["Recettes", self._formater_montant(recettes)],
                ["Dépenses", self._formater_montant(depenses)],
                ["Solde", self._formater_montant(solde)],
            ]
            elements.append(self._creer_tableau(
                donnees,
                col_widths=[10 * cm, 6 * cm],
                avec_total=True,
            ))

            if self._sections_config.get("inclure_graphiques"):
                elements.extend(self._graphique_camembert(
                    [("Recettes", recettes), ("Dépenses", depenses)],
                    "Répartition recettes / dépenses",
                ))

        except Exception as exc:
            logger.error("_section_resume_financier: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_tresorerie_detail(self) -> list:
        elements = self._titre_section_pro("Trésorerie détaillée par catégorie")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT c.nom as categorie, o.type_operation,
                              COUNT(*) as nb,
                              COALESCE(SUM(o.montant), 0) as total
                       FROM tresorerie_operations o
                       LEFT JOIN tresorerie_categories c ON o.categorie_id = c.id
                       WHERE o.date_operation >= ? AND o.date_operation <= ?
                       GROUP BY c.nom, o.type_operation
                       ORDER BY c.nom, o.type_operation""",
                    (self._date_debut, self._date_fin),
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Catégorie", "Type", "Nb opérations", "Total"]]
            for row in rows:
                donnees.append([
                    row["categorie"] or "(Sans catégorie)",
                    "Recette" if row["type_operation"] == "recette" else "Dépense",
                    str(row["nb"]),
                    self._formater_montant(row["total"]),
                ])
            elements.append(self._creer_tableau(donnees))

            if self._sections_config.get("inclure_graphiques") and rows:
                dep_data = [(r["categorie"] or "?", float(r["total"])) for r in rows if r["type_operation"] == "depense"]
                if dep_data:
                    elements.extend(self._graphique_camembert(dep_data, "Répartition des dépenses par catégorie"))
        except Exception as exc:
            logger.error("_section_tresorerie_detail: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_soldes_comptes(self) -> list:
        elements = self._titre_section_pro("Soldes des comptes")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT c.nom,
                              COALESCE(SUM(CASE WHEN o.type_operation='recette' THEN o.montant ELSE -o.montant END), 0) as solde
                       FROM comptes_bancaires c
                       LEFT JOIN tresorerie_operations o ON o.compte_id = c.id
                       AND o.date_operation >= ? AND o.date_operation <= ?
                       WHERE c.actif = 1
                       GROUP BY c.id, c.nom
                       ORDER BY c.nom""",
                    (self._date_debut, self._date_fin),
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(self._message_aucune_donnee())
                return elements

            donnees = [["Compte", "Solde sur la période"]]
            for row in rows:
                donnees.append([row["nom"], self._formater_montant(row["solde"])])
            elements.append(self._creer_tableau(donnees, col_widths=[12 * cm, 6 * cm]))
        except Exception as exc:
            logger.error("_section_soldes_comptes: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_subventions_recues(self) -> list:
        elements = self._titre_section_pro("Subventions reçues")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT organisme, objet, montant_obtenu, date_demande, statut
                       FROM subventions
                       WHERE date_demande >= ? AND date_demande <= ?
                       AND statut = 'accordee'
                       ORDER BY date_demande""",
                    (self._date_debut, self._date_fin),
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(Paragraph("Aucune subvention reçue sur la période.", self._style_message))
                return elements

            donnees = [["Organisme", "Objet", "Montant accordé", "Date"]]
            for row in rows:
                donnees.append([
                    row["organisme"] or "—",
                    row["objet"] or "—",
                    self._formater_montant(row["montant_obtenu"] or 0),
                    self._formater_date(row["date_demande"]),
                ])
            elements.append(self._creer_tableau(donnees))
        except Exception as exc:
            logger.error("_section_subventions_recues: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_dons_recus(self) -> list:
        elements = self._titre_section_pro("Dons reçus")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT date_don, donateur_nom, montant, nature_don
                       FROM dons
                       WHERE date_don >= ? AND date_don <= ?
                       ORDER BY date_don""",
                    (self._date_debut, self._date_fin),
                ).fetchall()
                total = conn.execute(
                    """SELECT COALESCE(SUM(montant), 0) as total FROM dons
                       WHERE date_don >= ? AND date_don <= ?""",
                    (self._date_debut, self._date_fin),
                ).fetchone()
            finally:
                conn.close()

            if not rows:
                elements.append(Paragraph("Aucun don enregistré sur la période.", self._style_message))
                return elements

            donnees = [["Date", "Donateur", "Montant", "Type"]]
            for row in rows:
                donnees.append([
                    self._formater_date(row["date_don"]),
                    row["donateur_nom"] or "Anonyme",
                    self._formater_montant(row["montant"] or 0),
                    row["nature_don"] or "—",
                ])
            if total:
                donnees.append(["TOTAL", "", self._formater_montant(total["total"]), ""])
            elements.append(self._creer_tableau(donnees, avec_total=bool(total)))
        except Exception as exc:
            logger.error("_section_dons_recus: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_projet(self) -> list:
        elements = self._titre_section_pro("Description du projet")
        texte = self._remplacer_variables(self._lire_template("projet"))
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("## "):
                elements.append(Spacer(1, 0.2 * cm))
                continue
            elements.append(Paragraph(ligne, self._style_normal))
        return elements

    def _section_budget_projet(self) -> list:
        elements = self._titre_section_pro("Budget prévisionnel du projet")
        texte = self._remplacer_variables(self._lire_template("budget_projet"))

        # Parse le tableau Markdown simple
        in_table = False
        table_data = []
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("## "):
                if in_table and table_data:
                    elements.append(self._creer_tableau(table_data))
                    table_data = []
                    in_table = False
                continue
            if ligne.startswith("|"):
                in_table = True
                if "---|" in ligne:
                    continue
                cells = [c.strip() for c in ligne.strip("|").split("|")]
                row = []
                for cell in cells:
                    cell = re.sub(r"\*\*(.+?)\*\*", r"\1", cell)
                    row.append(cell)
                table_data.append(row)
            else:
                if in_table and table_data:
                    elements.append(self._creer_tableau(table_data))
                    table_data = []
                    in_table = False
                elements.append(Paragraph(ligne, self._style_normal))

        if in_table and table_data:
            elements.append(self._creer_tableau(table_data))

        return elements

    def _section_objectifs(self) -> list:
        elements = self._titre_section_pro("Objectifs et indicateurs")
        texte = self._remplacer_variables(self._lire_template("objectifs"))

        table_data = []
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("## "):
                continue
            if ligne.startswith("|"):
                if "---|" in ligne:
                    continue
                cells = [c.strip() for c in ligne.strip("|").split("|")]
                table_data.append(cells)

        if table_data:
            elements.append(self._creer_tableau(table_data))
        return elements

    def _section_statuts(self) -> list:
        elements = self._titre_section_pro("Statuts de l'association")
        texte = self._remplacer_variables(self._lire_template("statuts"))
        for ligne in texte.split("\n"):
            ligne = ligne.strip()
            if not ligne or ligne.startswith("## "):
                continue
            elements.append(Paragraph(ligne, self._style_normal))
        return elements

    def _section_remboursements(self) -> list:
        elements = self._titre_section_pro("Remboursements en attente")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT m.nom, m.prenom, o.libelle AS motif, o.montant, o.date_operation AS date_demande
                       FROM tresorerie_operations o
                       LEFT JOIN membres m ON m.id = o.avance_par_membre_id
                       WHERE o.remboursement_statut = 'en_attente'
                         AND o.avance_par_membre_id IS NOT NULL
                         AND o.type_operation = 'depense'
                       ORDER BY o.date_operation""",
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(Paragraph("Aucun remboursement en attente.", self._style_message))
                return elements

            donnees = [["Membre", "Motif", "Montant", "Date"]]
            for row in rows:
                nom_complet = f"{row['nom'] or ''} {row['prenom'] or ''}".strip()
                donnees.append([
                    nom_complet or "—",
                    row["motif"] or "—",
                    self._formater_montant(row["montant"] or 0),
                    self._formater_date(row["date_demande"]),
                ])
            elements.append(self._creer_tableau(donnees))
        except Exception as exc:
            logger.error("_section_remboursements: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    def _section_benevoles(self) -> list:
        elements = self._titre_section_pro("Bénévoles")
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    """SELECT m.nom, m.prenom, COUNT(DISTINCT eb.evenement_id) as nb_events
                       FROM membres m
                       JOIN evenement_benevoles eb ON eb.membre_id = m.id
                       GROUP BY m.id, m.nom, m.prenom
                       ORDER BY nb_events DESC
                       LIMIT 20""",
                ).fetchall()
            finally:
                conn.close()

            if not rows:
                elements.append(Paragraph("Aucun bénévole enregistré.", self._style_message))
                return elements

            donnees = [["Nom", "Prénom", "Nb événements"]]
            for row in rows:
                donnees.append([row["nom"] or "", row["prenom"] or "", str(row["nb_events"])])
            elements.append(self._creer_tableau(
                donnees,
                col_widths=[7 * cm, 7 * cm, 4 * cm],
            ))
        except Exception as exc:
            logger.error("_section_benevoles: %s", exc)
            elements.append(self._message_aucune_donnee())
        return elements

    # ── Construction du contenu ───────────────────────────────────────────────

    def _construire_contenu(self) -> list:
        elements: list = []
        sec = self._sections_config

        if sec.get("mot_president"):
            elements.extend(self._section_mot_president())
            elements.append(PageBreak())

        if sec.get("presentation"):
            elements.extend(self._section_presentation())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("adherents"):
            elements.extend(self._section_adherents())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("evenements"):
            elements.extend(self._section_evenements())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("benevoles"):
            elements.extend(self._section_benevoles())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("resume_financier"):
            elements.extend(self._section_resume_financier())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("tresorerie_detail"):
            elements.extend(self._section_tresorerie_detail())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("soldes_comptes"):
            elements.extend(self._section_soldes_comptes())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("subventions_recues"):
            elements.extend(self._section_subventions_recues())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("dons_recus"):
            elements.extend(self._section_dons_recus())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("remboursements"):
            elements.extend(self._section_remboursements())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("projet"):
            elements.append(PageBreak())
            elements.extend(self._section_projet())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("budget_projet"):
            elements.extend(self._section_budget_projet())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("objectifs"):
            elements.extend(self._section_objectifs())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("statuts"):
            elements.append(PageBreak())
            elements.extend(self._section_statuts())
            elements.append(Spacer(1, 0.5 * cm))

        if sec.get("signatures"):
            elements.append(PageBreak())
            signataires = ["Le Président", "Le Trésorier", "La Secrétaire"]
            elements.extend(self._zone_signature(signataires))

        return elements
