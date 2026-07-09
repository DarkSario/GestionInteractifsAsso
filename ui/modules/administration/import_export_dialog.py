"""Dialogues d'import/export de la base de données."""

from __future__ import annotations

import os
from datetime import datetime
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from db.models.parametres_globaux import get_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.backup import (
    exporter_base_complete,
    importer_base,
    redemarrer_application,
    verifier_integrite_base,
)


class ExportBaseDialog(ctk.CTkToplevel):
    """Fenêtre d'export de la base active."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("📤 Exporter la base de données")
        self.geometry("620x300")
        self.resizable(False, False)
        self.transient(parent)

        self._format_var = ctk.StringVar(value="zip")
        self._dossier_var = ctk.StringVar(
            value=get_parametre("export_dossier_defaut", "") or os.path.expanduser("~")
        )
        self._nom_var = ctk.StringVar()

        self._mettre_nom_par_defaut()
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="📤 Exporter la base de données",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 10))

        frame_format = ctk.CTkFrame(self)
        frame_format.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_format, text="Format", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )
        ctk.CTkRadioButton(
            frame_format,
            text="Fichier .db (base seule)",
            variable=self._format_var,
            value="db",
            command=self._mettre_nom_par_defaut,
        ).pack(anchor="w", padx=16, pady=2)
        ctk.CTkRadioButton(
            frame_format,
            text="Archive .zip (base + configuration)",
            variable=self._format_var,
            value="zip",
            command=self._mettre_nom_par_defaut,
        ).pack(anchor="w", padx=16, pady=(2, 10))

        frame_dest = ctk.CTkFrame(self)
        frame_dest.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_dest, text="Destination", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        row_dossier = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_dossier.pack(fill="x", padx=12, pady=4)
        ctk.CTkEntry(row_dossier, textvariable=self._dossier_var, width=420).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            row_dossier,
            text="📁 Choisir",
            width=110,
            command=self._choisir_dossier,
        ).pack(side="left", padx=(8, 0))

        row_nom = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_nom.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_nom, text="Nom", width=110, anchor="w").pack(side="left")
        ctk.CTkEntry(row_nom, textvariable=self._nom_var).pack(
            side="left", fill="x", expand=True
        )

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=110,
            fg_color="grey",
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn,
            text="📤 Exporter",
            width=130,
            command=self._exporter,
        ).pack(side="right")

    def _mettre_nom_par_defaut(self) -> None:
        extension = ".zip" if self._format_var.get() == "zip" else ".db"
        self._nom_var.set(
            f"asso_interactifs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
        )

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _exporter(self) -> None:
        dossier = self._dossier_var.get().strip()
        nom = self._nom_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier valide.")
            return
        if not nom:
            afficher_erreur(self, "Nom manquant", "Veuillez renseigner un nom de fichier.")
            return

        chemin = os.path.join(dossier, nom)
        resultat = exporter_base_complete(chemin)
        if not resultat["succes"]:
            afficher_erreur(self, "Échec de l'export", resultat["message"])
            return

        afficher_info(self, "Export réussi", f"Export créé :\n{resultat['chemin']}")
        self.destroy()


class ImportBaseDialog(ctk.CTkToplevel):
    """Fenêtre d'import de base de données."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("📥 Importer une base de données")
        self.geometry("620x300")
        self.resizable(False, False)
        self.transient(parent)

        self._fichier_var = ctk.StringVar()
        self._verification_var = ctk.StringVar(value="Vérification : en attente…")
        self._source_valide = False

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="📥 Importer une base de données",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 10))

        ctk.CTkLabel(
            self,
            text="⚠️ Remplacera toutes les données actuelles",
            font=fonts.get("normal"),
            text_color="#d97706",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame, text="Fichier", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkEntry(row, textvariable=self._fichier_var, width=420).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            row,
            text="📁 Choisir",
            width=110,
            command=self._choisir_fichier,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            frame,
            text="Formats acceptés : .db, .zip",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=12)

        self._verification_label = ctk.CTkLabel(
            frame,
            textvariable=self._verification_var,
            font=fonts.get("normal"),
        )
        self._verification_label.pack(anchor="w", padx=12, pady=(8, 12))

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=110,
            fg_color="grey",
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn,
            text="📥 Importer",
            width=130,
            command=self._importer,
        ).pack(side="right")

    def _choisir_fichier(self) -> None:
        chemin = filedialog.askopenfilename(
            parent=self,
            title="Choisir une base à importer",
            filetypes=[
                ("Base SQLite ou archive", "*.db *.zip"),
                ("Base SQLite", "*.db"),
                ("Archive ZIP", "*.zip"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not chemin:
            return
        self._fichier_var.set(chemin)
        self._verifier()

    def _verifier(self) -> None:
        chemin = self._fichier_var.get().strip()
        if not chemin:
            self._source_valide = False
            self._verification_var.set("Vérification : en attente…")
            self._verification_label.configure(text_color=None)
            return

        resultat = verifier_integrite_base(chemin)
        self._source_valide = bool(resultat["valide"])
        prefixe = "✅" if self._source_valide else "❌"
        couleur = "#15803d" if self._source_valide else "#b91c1c"
        self._verification_var.set(f"Vérification : {prefixe} {resultat['message']}")
        self._verification_label.configure(text_color=couleur)

    def _importer(self) -> None:
        chemin = self._fichier_var.get().strip()
        if not chemin:
            afficher_erreur(self, "Fichier manquant", "Veuillez sélectionner un fichier à importer.")
            return
        if not self._source_valide:
            self._verifier()
            if not self._source_valide:
                afficher_erreur(self, "Import impossible", "Le fichier sélectionné n'est pas valide.")
                return

        if not demander_confirmation(
            self,
            "Confirmer l'import",
            "Cette opération remplacera toutes les données actuelles.\n"
            "Une sauvegarde de sécurité sera créée automatiquement.\n\n"
            "Souhaitez-vous continuer ?",
        ):
            return

        resultat = importer_base(chemin)
        if not resultat["succes"]:
            afficher_erreur(self, "Échec de l'import", resultat["message"])
            return

        if demander_confirmation(
            self,
            "Import réussi",
            "L'import a réussi.\n\nL'application doit redémarrer pour appliquer les changements.\n"
            "Redémarrer maintenant ?",
        ):
            redemarrer_application()
            return

        afficher_info(self, "Import réussi", "L'application devra être redémarrée manuellement.")
        self.destroy()
