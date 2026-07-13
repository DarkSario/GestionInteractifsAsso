"""Fenêtre Dossier de Demande de Subvention — Phase 21."""

from __future__ import annotations

import os
import threading
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from db.connection import get_connection
from db.models.parametres_globaux import get_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info
from utils.logger import get_logger

logger = get_logger(__name__)


class DossierSubventionDialog(ctk.CTkToplevel):
    """Fenêtre de génération du Dossier de Demande de Subvention."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("📂 Dossier de Demande de Subvention")
        self.geometry("820x780")
        self.minsize(800, 700)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        annee_en_cours = datetime.now().year

        # Variables de formulaire
        self._organisateur_var = ctk.StringVar()
        self._objet_var = ctk.StringVar()
        self._montant_var = ctk.StringVar(value="0")
        self._type_periode_var = ctk.StringVar(value="civile")
        self._annee_civile_var = ctk.StringVar(value=str(annee_en_cours))
        self._annee_scolaire_var = ctk.StringVar(value=f"{annee_en_cours - 1}-{annee_en_cours}")

        dossier_defaut = get_parametre("export_dossier_defaut", "") or os.path.expanduser("~")
        self._dossier_var = ctk.StringVar(value=dossier_defaut)
        self._nom_fichier_var = ctk.StringVar(
            value=f"dossier_subvention_{annee_en_cours}.pdf"
        )

        # Sections
        self._sections_vars: dict[str, ctk.BooleanVar] = {
            "page_garde": ctk.BooleanVar(value=True),
            "table_matieres": ctk.BooleanVar(value=True),
            "presentation": ctk.BooleanVar(value=True),
            "mot_president": ctk.BooleanVar(value=True),
            "adherents": ctk.BooleanVar(value=True),
            "evenements": ctk.BooleanVar(value=True),
            "benevoles": ctk.BooleanVar(value=True),
            "buvette": ctk.BooleanVar(value=True),
            "resume_financier": ctk.BooleanVar(value=True),
            "tresorerie_detail": ctk.BooleanVar(value=True),
            "soldes_comptes": ctk.BooleanVar(value=True),
            "subventions_recues": ctk.BooleanVar(value=True),
            "dons_recus": ctk.BooleanVar(value=True),
            "remboursements": ctk.BooleanVar(value=False),
            "projet": ctk.BooleanVar(value=True),
            "budget_projet": ctk.BooleanVar(value=True),
            "objectifs": ctk.BooleanVar(value=True),
            "signatures": ctk.BooleanVar(value=True),
            "statuts": ctk.BooleanVar(value=False),
            "membres_bureau": ctk.BooleanVar(value=False),
            "inclure_graphiques": ctk.BooleanVar(value=True),
            "numerotation": ctk.BooleanVar(value=True),
            "entete_pied": ctk.BooleanVar(value=True),
        }

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        # Titre
        ctk.CTkLabel(
            self, text="📂 Dossier de Demande de Subvention", font=fonts.get("title")
        ).pack(anchor="w", padx=20, pady=(16, 8))

        # Zone principale scrollable
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_infos_generales(scroll, fonts)
        self._build_periode(scroll, fonts)
        self._build_destination(scroll, fonts)
        self._build_sections(scroll, fonts)

        # Boutons
        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(4, 16), side="bottom")
        ctk.CTkButton(
            frame_btn, text="❌ Annuler", width=110, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn, text="📊 Générer Excel", width=160, command=self._generer_excel
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            frame_btn, text="📄 Générer PDF", width=160, command=self._generer_pdf
        ).pack(side="right")

    def _build_infos_generales(self, parent, fonts) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame, text="Informations de la demande", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        champs = [
            ("Organisme destinataire", self._organisateur_var),
            ("Objet de la demande", self._objet_var),
        ]
        for label, var in champs:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=3)
            ctk.CTkLabel(row, text=label, width=200, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=400).pack(side="left", fill="x", expand=True)

        row_montant = ctk.CTkFrame(frame, fg_color="transparent")
        row_montant.pack(fill="x", padx=12, pady=(3, 12))
        ctk.CTkLabel(row_montant, text="Montant demandé (€)", width=200, anchor="w").pack(side="left")
        ctk.CTkEntry(row_montant, textvariable=self._montant_var, width=160).pack(side="left")

    def _build_periode(self, parent, fonts) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame, text="Période de référence", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        annees_civiles = [str(y) for y in range(datetime.now().year - 3, datetime.now().year + 2)]
        annees_scolaires = [f"{y}-{y + 1}" for y in range(datetime.now().year - 4, datetime.now().year + 2)]

        row_civile = ctk.CTkFrame(frame, fg_color="transparent")
        row_civile.pack(fill="x", padx=12, pady=2)
        ctk.CTkRadioButton(
            row_civile, text="Année civile",
            variable=self._type_periode_var, value="civile", width=160,
        ).pack(side="left")
        ctk.CTkOptionMenu(
            row_civile, values=annees_civiles, variable=self._annee_civile_var, width=140
        ).pack(side="left", padx=(8, 0))

        row_scolaire = ctk.CTkFrame(frame, fg_color="transparent")
        row_scolaire.pack(fill="x", padx=12, pady=(2, 12))
        ctk.CTkRadioButton(
            row_scolaire, text="Année scolaire",
            variable=self._type_periode_var, value="scolaire", width=160,
        ).pack(side="left")
        ctk.CTkOptionMenu(
            row_scolaire, values=annees_scolaires, variable=self._annee_scolaire_var, width=140
        ).pack(side="left", padx=(8, 0))

        # Nom fichier (mise à jour selon la période sélectionnée)
        row_nom = ctk.CTkFrame(frame, fg_color="transparent")
        row_nom.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(row_nom, text="Nom du fichier PDF", width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(row_nom, textvariable=self._nom_fichier_var, width=360).pack(
            side="left", fill="x", expand=True
        )

    def _build_destination(self, parent, fonts) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame, text="Dossier de destination", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkEntry(row, textvariable=self._dossier_var, width=400).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(row, text="📁 Choisir", width=110, command=self._choisir_dossier).pack(
            side="left", padx=(8, 0)
        )

    def _build_sections(self, parent, fonts) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame, text="📋 Sections à inclure", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        def _section_header(texte: str) -> None:
            ctk.CTkLabel(
                frame, text=f"── {texte} ──",
                font=fonts.get("small"),
                text_color="grey",
            ).pack(anchor="w", padx=16, pady=(6, 2))

        def _checkbox(cle: str, texte: str, avec_editeur: bool = False) -> None:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkCheckBox(row, text=texte, variable=self._sections_vars[cle]).pack(side="left")
            if avec_editeur:
                ctk.CTkButton(
                    row, text="✏️ Éditer", width=80, height=24,
                    command=lambda k=cle: self._editer_template(k),
                ).pack(side="left", padx=(8, 0))

        # Présentation
        _section_header("Présentation")
        _checkbox("page_garde", "Page de garde")
        _checkbox("table_matieres", "Table des matières")
        _checkbox("presentation", "Présentation de l'association", avec_editeur=True)
        _checkbox("mot_president", "Mot du Président", avec_editeur=True)

        # Vie associative
        _section_header("Vie associative")
        _checkbox("adherents", "Statistiques adhérents")
        _checkbox("evenements", "Liste des événements")
        _checkbox("benevoles", "Bénévoles")
        _checkbox("buvette", "Bilan buvette / animations")

        # Financier
        _section_header("Financier")
        _checkbox("resume_financier", "Résumé financier (recettes/dépenses/solde)")
        _checkbox("tresorerie_detail", "Trésorerie détaillée par catégorie")
        _checkbox("soldes_comptes", "Soldes des comptes")
        _checkbox("subventions_recues", "Subventions reçues")
        _checkbox("dons_recus", "Dons reçus")
        _checkbox("remboursements", "Remboursements en attente")

        # Projet
        _section_header("Projet")
        _checkbox("projet", "Description du projet", avec_editeur=True)
        _checkbox("budget_projet", "Budget prévisionnel projet", avec_editeur=True)
        _checkbox("objectifs", "Objectifs & indicateurs", avec_editeur=True)

        # Annexes
        _section_header("Annexes")
        _checkbox("signatures", "Zone signatures (Président, Trésorier, Secrétaire)")
        _checkbox("statuts", "Statuts de l'association", avec_editeur=True)
        _checkbox("membres_bureau", "Membres du bureau")

        # Mise en forme
        _section_header("Mise en forme")
        _checkbox("inclure_graphiques", "Inclure les graphiques")
        _checkbox("numerotation", "Numérotation des pages")
        _checkbox("entete_pied", "En-tête et pied de page")

        ctk.CTkFrame(frame, height=8, fg_color="transparent").pack()

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _editer_template(self, cle: str) -> None:
        """Ouvre l'éditeur de template pour la section donnée."""
        from pathlib import Path

        _BASE_DIR = Path(__file__).parent.parent.parent.parent
        _CONFIG_DIR = _BASE_DIR / "config"

        noms_fichiers = {
            "presentation": "dossier_subvention_presentation.md",
            "mot_president": "dossier_subvention_mot_president.md",
            "projet": "dossier_subvention_projet.md",
            "budget_projet": "dossier_subvention_budget_projet.md",
            "objectifs": "dossier_subvention_objectifs.md",
            "statuts": "dossier_subvention_statuts.md",
        }
        nom = noms_fichiers.get(cle)
        if not nom:
            return

        chemin = _CONFIG_DIR / nom
        chemin_defaut = _CONFIG_DIR / nom.replace(".md", ".default.md")

        # Contenu initial
        contenu = ""
        if chemin.exists():
            try:
                contenu = chemin.read_text(encoding="utf-8")
            except Exception:
                pass
        elif chemin_defaut.exists():
            try:
                contenu = chemin_defaut.read_text(encoding="utf-8")
            except Exception:
                pass

        titres = {
            "presentation": "✏️ Présentation de l'association",
            "mot_president": "✏️ Mot du Président",
            "projet": "✏️ Description du projet",
            "budget_projet": "✏️ Budget prévisionnel",
            "objectifs": "✏️ Objectifs & indicateurs",
            "statuts": "✏️ Statuts de l'association",
        }

        _EditeurTemplateSubvention(
            self,
            titre=titres.get(cle, "✏️ Éditer le template"),
            contenu=contenu,
            chemin_sauvegarde=str(chemin),
            chemin_defaut=str(chemin_defaut),
        )

    def _get_periode(self) -> tuple[str, str]:
        """Retourne (période, type_periode)."""
        type_p = self._type_periode_var.get()
        if type_p == "civile":
            return self._annee_civile_var.get(), "civile"
        return self._annee_scolaire_var.get(), "scolaire"

    def _valider_formulaire(self) -> bool:
        dossier = self._dossier_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier valide.")
            return False
        nom = self._nom_fichier_var.get().strip()
        if not nom:
            afficher_erreur(self, "Nom manquant", "Veuillez renseigner un nom de fichier.")
            return False
        try:
            montant = float(self._montant_var.get().replace(",", ".").replace(" ", ""))
            if montant < 0:
                raise ValueError
        except ValueError:
            afficher_erreur(self, "Montant invalide", "Le montant doit être un nombre positif.")
            return False
        return True

    def _generer_pdf(self) -> None:
        if not self._valider_formulaire():
            return

        periode, type_periode = self._get_periode()
        dossier = self._dossier_var.get().strip()
        nom_fichier = self._nom_fichier_var.get().strip()
        if not nom_fichier.endswith(".pdf"):
            nom_fichier += ".pdf"
        chemin = os.path.join(dossier, nom_fichier)

        montant = float(self._montant_var.get().replace(",", ".").replace(" ", "") or 0)
        sections = {cle: var.get() for cle, var in self._sections_vars.items()}

        progress = ctk.CTkProgressBar(self)
        progress.pack(fill="x", padx=20, pady=(0, 4), side="bottom")
        progress.configure(mode="indeterminate")
        progress.start()

        def _run():
            try:
                from core.pdf_dossier_subvention import PdfDossierSubvention

                gen = PdfDossierSubvention(
                    periode=periode,
                    type_periode=type_periode,
                    organisateur=self._organisateur_var.get().strip(),
                    objet=self._objet_var.get().strip(),
                    montant_demande=montant,
                    sections=sections,
                )
                ok = gen.generer(chemin)
                self.after(0, lambda: self._fin_generation(ok, chemin, progress))
            except Exception as exc:
                logger.exception("_generer_pdf: %s", exc)
                self.after(0, lambda: self._fin_generation(False, chemin, progress))

        threading.Thread(target=_run, daemon=True).start()

    def _generer_excel(self) -> None:
        if not self._valider_formulaire():
            return

        periode, type_periode = self._get_periode()
        dossier = self._dossier_var.get().strip()
        nom_fichier = self._nom_fichier_var.get().strip()
        nom_excel = nom_fichier.replace(".pdf", "").replace(".xlsx", "") + ".xlsx"
        chemin = os.path.join(dossier, nom_excel)

        montant = float(self._montant_var.get().replace(",", ".").replace(" ", "") or 0)
        sections = {cle: var.get() for cle, var in self._sections_vars.items()}

        progress = ctk.CTkProgressBar(self)
        progress.pack(fill="x", padx=20, pady=(0, 4), side="bottom")
        progress.configure(mode="indeterminate")
        progress.start()

        def _run():
            try:
                from core.excel_dossier_subvention import ExcelDossierSubvention

                gen = ExcelDossierSubvention(
                    periode=periode,
                    type_periode=type_periode,
                    organisateur=self._organisateur_var.get().strip(),
                    objet=self._objet_var.get().strip(),
                    montant_demande=montant,
                    sections=sections,
                )
                ok = gen.generer(chemin)
                self.after(0, lambda: self._fin_generation(ok, chemin, progress))
            except Exception as exc:
                logger.exception("_generer_excel: %s", exc)
                self.after(0, lambda: self._fin_generation(False, chemin, progress))

        threading.Thread(target=_run, daemon=True).start()

    def _fin_generation(self, ok: bool, chemin: str, progress) -> None:
        try:
            progress.stop()
            progress.destroy()
        except Exception:
            pass
        if ok:
            afficher_info(self, "Génération réussie", f"Le fichier a été généré :\n{chemin}")
        else:
            afficher_erreur(self, "Échec", "La génération a échoué.\nVérifiez les logs pour plus de détails.")


class _EditeurTemplateSubvention(ctk.CTkToplevel):
    """Éditeur de template Markdown pour les sections du dossier de subvention."""

    def __init__(
        self,
        parent,
        titre: str,
        contenu: str,
        chemin_sauvegarde: str,
        chemin_defaut: str,
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("720x580")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._chemin = chemin_sauvegarde
        self._chemin_defaut = chemin_defaut

        fonts = app_theme.FONTS

        ctk.CTkLabel(self, text=titre, font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 8)
        )

        self._textbox = ctk.CTkTextbox(self, wrap="word")
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        self._textbox.insert("1.0", contenu)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(
            frame_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn,
            text="🔄 Restaurer défaut",
            width=160,
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._restaurer_defaut,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            frame_btn, text="💾 Enregistrer", width=140, command=self._enregistrer
        ).pack(side="right")

    def _enregistrer(self) -> None:
        contenu = self._textbox.get("1.0", "end-1c")
        try:
            from pathlib import Path
            Path(self._chemin).parent.mkdir(parents=True, exist_ok=True)
            Path(self._chemin).write_text(contenu, encoding="utf-8")
            afficher_info(self, "Succès", "Le template a été enregistré.")
            self.destroy()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer : {exc}")

    def _restaurer_defaut(self) -> None:
        from ui.components.dialogs import demander_confirmation
        if not demander_confirmation(
            self,
            "Restaurer le défaut",
            "Toutes vos modifications seront perdues. Continuer ?",
        ):
            return
        try:
            from pathlib import Path
            contenu = Path(self._chemin_defaut).read_text(encoding="utf-8")
            self._textbox.delete("1.0", "end")
            self._textbox.insert("1.0", contenu)
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de restaurer : {exc}")
