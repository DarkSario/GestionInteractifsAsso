"""Dialogue de configuration des informations de l'association.

Accessible depuis le menu Administration et le dialogue d'export.
"""

from __future__ import annotations

import os
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from db.models.evenements import get_parametre, set_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class ConfigAssoDialog(ctk.CTkToplevel):
    """Fenêtre modale de configuration des informations de l'association."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("⚙️ Informations de l'association")
        self.geometry("520x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._champs: dict[str, ctk.CTkEntry] = {}
        self._logo_path_var = ctk.StringVar()

        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="⚙️ Informations de l'association",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 8))

        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        champs_config = [
            ("asso_nom", "Nom *"),
            ("asso_adresse", "Adresse"),
            ("asso_telephone", "Téléphone"),
            ("asso_email", "Email"),
        ]
        for cle, label in champs_config:
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=140, anchor="ne").pack(
                side="left", padx=(0, 8), pady=2
            )
            entry = ctk.CTkEntry(f, width=300)
            entry.pack(side="left", fill="x", expand=True)
            self._champs[cle] = entry

        # Logo
        f_logo = ctk.CTkFrame(frame, fg_color="transparent")
        f_logo.pack(fill="x", pady=3)
        ctk.CTkLabel(f_logo, text="Logo", width=140, anchor="ne").pack(
            side="left", padx=(0, 8), pady=2
        )
        entry_logo = ctk.CTkEntry(f_logo, textvariable=self._logo_path_var, width=230)
        entry_logo.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            f_logo,
            text="📁",
            width=40,
            command=self._choisir_logo,
        ).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            frame,
            text="PNG ou JPG, max 2 Mo",
            font=app_theme.FONTS.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=(148, 0))

        # Boutons
        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(f_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy).pack(
            side="left"
        )
        ctk.CTkButton(f_btn, text="💾 Enregistrer", width=140, command=self._enregistrer).pack(
            side="right"
        )

    def _charger(self) -> None:
        """Charge les valeurs depuis la DB."""
        for cle, entry in self._champs.items():
            val = get_parametre(cle) or ""
            entry.delete(0, "end")
            entry.insert(0, val)
        logo = get_parametre("asso_logo_path") or ""
        self._logo_path_var.set(logo)

    def _choisir_logo(self) -> None:
        """Ouvre un sélecteur de fichier pour le logo."""
        chemin = filedialog.askopenfilename(
            parent=self,
            title="Choisir le logo de l'association",
            filetypes=[("Images", "*.png *.jpg *.jpeg"), ("Tous les fichiers", "*.*")],
        )
        if chemin:
            # Vérification taille (max 2 Mo)
            try:
                taille = os.path.getsize(chemin)
                if taille > 2 * 1024 * 1024:
                    afficher_erreur(self, "Fichier trop grand", "Le logo ne doit pas dépasser 2 Mo.")
                    return
            except OSError:
                pass
            self._logo_path_var.set(chemin)

    def _enregistrer(self) -> None:
        """Enregistre les paramètres en DB."""
        for cle, entry in self._champs.items():
            set_parametre(cle, entry.get().strip())
        set_parametre("asso_logo_path", self._logo_path_var.get().strip())
        afficher_info(self, "Succès", "Les informations de l'association ont été enregistrées.")
        self.destroy()
