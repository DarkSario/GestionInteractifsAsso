"""Fenêtre Bilan AG — Phase 9."""

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
        self.geometry("620x560")
        self.resizable(False, False)
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

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        ctk.CTkLabel(self, text="📋 Bilan AG", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        frame_exercice = ctk.CTkFrame(self)
        frame_exercice.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_exercice, text="Exercice", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        ctk.CTkOptionMenu(
            frame_exercice,
            values=[self._exercice],
            variable=self._exercice_var,
            width=240,
        ).pack(anchor="w", padx=12, pady=(0, 10))

        frame_sections = ctk.CTkFrame(self)
        frame_sections.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_sections, text="Sections du bilan", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        labels = [
            ("☑ Résumé financier", "resume_financier"),
            ("☑ Trésorerie détaillée", "tresorerie_detail"),
            ("☑ Subventions", "subventions"),
            ("☑ Événements (récapitulatif)", "evenements"),
            ("☑ Buvette", "buvette"),
            ("☑ Adhérents", "adherents"),
            ("☑ Dons reçus", "dons"),
            ("☐ Remboursements en attente", "remboursements"),
            ("☑ Zone signatures", "signatures"),
        ]
        for text, key in labels:
            ctk.CTkCheckBox(frame_sections, text=text, variable=self._sections_vars[key]).pack(
                anchor="w", padx=16, pady=3
            )

        ctk.CTkCheckBox(self, text="Inclure les graphiques", variable=self._graphiques_var).pack(
            anchor="w", padx=34, pady=(0, 12)
        )

        frame_dest = ctk.CTkFrame(self)
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

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(6, 16), side="bottom")
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

        sections = {cle: var.get() for cle, var in self._sections_vars.items()}
        chemin = os.path.join(dossier, nom_fichier)
        ok = export_bilan_ag_pdf(
            self._exercice_var.get(),
            chemin,
            sections=sections,
            avec_graphiques=self._graphiques_var.get(),
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
