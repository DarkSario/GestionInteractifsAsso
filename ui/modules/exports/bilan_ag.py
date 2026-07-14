"""Fenêtre Bilan AG — Phase 9 / Phase 21."""

from __future__ import annotations

import os
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from core.exports import export_bilan_ag_pdf
from db.connection import get_connection
from db.models.parametres_globaux import get_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class BilanAGDialog(ctk.CTkToplevel):
    """Fenêtre de génération du Bilan AG."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("📋 Bilan AG")
        self.geometry("700x860")
        self.minsize(700, 760)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._exercice = self._charger_exercice_courant()
        self._exercice_var = ctk.StringVar(value=self._exercice)
        self._graphiques_var = ctk.BooleanVar(value=False)
        self._dossier_var = ctk.StringVar(
            value=get_parametre("export_dossier_defaut", "") or os.path.expanduser("~")
        )
        self._nom_fichier_var = ctk.StringVar(
            value=f"bilan_ag_{self._slug_exercice(self._exercice)}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
        )
        self._sections_vars = {
            "resume_financier": ctk.BooleanVar(value=True),
            "tresorerie_detail": ctk.BooleanVar(value=True),
            "subventions": ctk.BooleanVar(value=True),
            "evenements": ctk.BooleanVar(value=True),
            "buvette": ctk.BooleanVar(value=True),
            "adherents": ctk.BooleanVar(value=True),
            "dons": ctk.BooleanVar(value=True),
            "remboursements": ctk.BooleanVar(value=False),
            "signatures": ctk.BooleanVar(value=True),
        }

        # Période de référence
        self._type_periode_var = ctk.StringVar(value="scolaire")
        annee_en_cours = datetime.now().year
        self._annee_scolaire_var = ctk.StringVar(value=f"{annee_en_cours - 1}-{annee_en_cours}")
        self._annee_civile_var = ctk.StringVar(value=str(annee_en_cours))

        # Zones de texte introduction / conclusion
        self._introduction_widget: ctk.CTkTextbox | None = None
        self._conclusion_widget: ctk.CTkTextbox | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(scroll, text="📋 Bilan AG", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        # ── Période de référence ──────────────────────────────────────────────
        frame_periode = ctk.CTkFrame(scroll)
        frame_periode.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_periode, text="Période de référence", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        annees_scolaires = self._generer_annees_scolaires()
        annees_civiles = [str(y) for y in range(datetime.now().year - 3, datetime.now().year + 2)]

        row_scolaire = ctk.CTkFrame(frame_periode, fg_color="transparent")
        row_scolaire.pack(fill="x", padx=12, pady=2)
        ctk.CTkRadioButton(
            row_scolaire,
            text="Année scolaire",
            variable=self._type_periode_var,
            value="scolaire",
            width=160,
        ).pack(side="left")
        ctk.CTkOptionMenu(
            row_scolaire,
            values=annees_scolaires,
            variable=self._annee_scolaire_var,
            width=140,
        ).pack(side="left", padx=(8, 0))

        row_civile = ctk.CTkFrame(frame_periode, fg_color="transparent")
        row_civile.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkRadioButton(
            row_civile,
            text="Année civile",
            variable=self._type_periode_var,
            value="civile",
            width=160,
        ).pack(side="left")
        ctk.CTkOptionMenu(
            row_civile,
            values=annees_civiles,
            variable=self._annee_civile_var,
            width=140,
        ).pack(side="left", padx=(8, 0))

        # ── Sections du bilan ─────────────────────────────────────────────────
        frame_sections = ctk.CTkFrame(scroll)
        frame_sections.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_sections, text="Sections du bilan", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        labels = [
            ("Résumé financier", "resume_financier"),
            ("Trésorerie détaillée", "tresorerie_detail"),
            ("Subventions", "subventions"),
            ("Événements (récapitulatif)", "evenements"),
            ("Buvette", "buvette"),
            ("Adhérents", "adherents"),
            ("Dons reçus", "dons"),
            ("Remboursements en attente", "remboursements"),
            ("Zone signatures", "signatures"),
        ]
        for text, key in labels:
            ctk.CTkCheckBox(frame_sections, text=text, variable=self._sections_vars[key]).pack(
                anchor="w", padx=16, pady=3
            )

        ctk.CTkCheckBox(scroll, text="Inclure les graphiques", variable=self._graphiques_var).pack(
            anchor="w", padx=34, pady=(0, 12)
        )

        # ── Textes libres — Introduction / Conclusion ──────────────────────────
        frame_textes = ctk.CTkFrame(scroll)
        frame_textes.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_textes, text="Textes du bilan", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        ctk.CTkLabel(
            frame_textes,
            text="Introduction (affiché en début de bilan)",
            anchor="w",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=(4, 2))
        self._introduction_widget = ctk.CTkTextbox(frame_textes, height=70)
        self._introduction_widget.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(
            frame_textes,
            text="Conclusion (affichée en fin de bilan, avant la signature)",
            anchor="w",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=(0, 2))
        self._conclusion_widget = ctk.CTkTextbox(frame_textes, height=70)
        self._conclusion_widget.pack(fill="x", padx=12, pady=(0, 12))

        # ── Destination ───────────────────────────────────────────────────────
        frame_dest = ctk.CTkFrame(scroll)
        frame_dest.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(frame_dest, text="Destination", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        row_dossier = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_dossier.pack(fill="x", padx=12, pady=4)
        ctk.CTkEntry(row_dossier, textvariable=self._dossier_var, width=420).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(row_dossier, text="📁 Choisir", width=110, command=self._choisir_dossier).pack(
            side="left", padx=(8, 0)
        )

        row_nom = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_nom.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_nom, text="Nom du fichier", width=110, anchor="w").pack(side="left")
        ctk.CTkEntry(row_nom, textvariable=self._nom_fichier_var).pack(side="left", fill="x", expand=True)

        # ── Boutons ───────────────────────────────────────────────────────────
        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(6, 16))
        ctk.CTkButton(frame_btn, text="Annuler", width=110, fg_color="grey", command=self.destroy).pack(side="left")
        ctk.CTkButton(frame_btn, text="📋 Générer le bilan", width=180, command=self._generer).pack(side="right")

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _generer(self) -> None:
        dossier = self._dossier_var.get().strip()
        nom_fichier = self._nom_fichier_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier valide.")
            return
        if not nom_fichier:
            afficher_erreur(self, "Nom manquant", "Veuillez renseigner un nom de fichier.")
            return

        type_periode = self._type_periode_var.get()
        if type_periode == "civile":
            periode = self._annee_civile_var.get()
        else:
            periode = self._annee_scolaire_var.get() or self._exercice_var.get()

        introduction = ""
        conclusion = ""
        if self._introduction_widget:
            introduction = self._introduction_widget.get("1.0", "end").strip()
        if self._conclusion_widget:
            conclusion = self._conclusion_widget.get("1.0", "end").strip()

        sections = {cle: var.get() for cle, var in self._sections_vars.items()}
        chemin = os.path.join(dossier, nom_fichier)
        ok = export_bilan_ag_pdf(
            periode,
            chemin,
            sections=sections,
            avec_graphiques=self._graphiques_var.get(),
            type_periode=type_periode,
            introduction=introduction,
            conclusion=conclusion,
        )
        if ok:
            afficher_info(self, "Bilan généré", f"Le bilan AG a été généré :\n{chemin}")
            self.destroy()
        else:
            afficher_erreur(self, "Échec", "Le bilan AG n'a pas pu être généré.")

    @staticmethod
    def _slug_exercice(exercice: str) -> str:
        return (exercice or "exercice").replace("/", "-").replace(" ", "_")

    @staticmethod
    def _generer_annees_scolaires() -> list[str]:
        annee = datetime.now().year
        return [f"{y}-{y + 1}" for y in range(annee - 3, annee + 2)]

    @staticmethod
    def _charger_exercice_courant() -> str:
        try:
            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT exercice, date_debut, date_fin FROM config ORDER BY id ASC LIMIT 1"
                ).fetchone()
                if row and row["exercice"]:
                    return str(row["exercice"])
                row_ex = conn.execute(
                    "SELECT date_debut, date_fin FROM exercices WHERE statut = 'ouvert' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
            if row_ex:
                debut = str(row_ex["date_debut"] or "")[:4]
                fin = str(row_ex["date_fin"] or "")[:4]
                return f"{debut}-{fin}" if debut or fin else "Exercice en cours"
        except Exception:
            pass
        return "Exercice en cours"
