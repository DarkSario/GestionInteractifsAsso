"""Dialogue de changement du mot de passe de déclôture (Phase 6b)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from db.models.securite import changer_mot_de_passe_decloture
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class MdpDecloture(ctk.CTkToplevel):
    """Fenêtre de changement du mot de passe de déclôture."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("🔐 Mot de passe de déclôture")
        self.geometry("440x320")
        self.resizable(False, False)
        self.transient(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        ctk.CTkLabel(
            self, text="🔐 Mot de passe de déclôture", font=fonts.get("subtitle")
        ).pack(padx=20, pady=(16, 12))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=20)

        # Mot de passe actuel
        ctk.CTkLabel(form, text="Mot de passe actuel *", font=fonts.get("normal"), anchor="w").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self._ancien_entry = ctk.CTkEntry(form, show="•", placeholder_text="Mot de passe actuel ou code master")
        self._ancien_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Nouveau mot de passe
        ctk.CTkLabel(form, text="Nouveau mot de passe *", font=fonts.get("normal"), anchor="w").grid(
            row=1, column=0, sticky="w", pady=6
        )
        self._nouveau_entry = ctk.CTkEntry(form, show="•", placeholder_text="Nouveau mot de passe")
        self._nouveau_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)

        # Confirmation
        ctk.CTkLabel(form, text="Confirmation *", font=fonts.get("normal"), anchor="w").grid(
            row=2, column=0, sticky="w", pady=6
        )
        self._confirm_entry = ctk.CTkEntry(form, show="•", placeholder_text="Confirmez le mot de passe")
        self._confirm_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=6)

        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="(Vous pouvez saisir le code master à la place du mot de passe actuel)",
            font=fonts.get("small"),
            text_color="gray",
            wraplength=380,
        ).pack(padx=20, pady=(4, 12))

        # Boutons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
            command=self.destroy
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="💾 Enregistrer",
            width=140,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._enregistrer,
        ).pack(side="left", padx=8)

    def _enregistrer(self) -> None:
        ancien = self._ancien_entry.get()
        nouveau = self._nouveau_entry.get()
        confirm = self._confirm_entry.get()

        if not ancien:
            afficher_erreur(self, "Saisie incomplète", "Veuillez saisir le mot de passe actuel.")
            return

        if not nouveau:
            afficher_erreur(self, "Saisie incomplète", "Veuillez saisir un nouveau mot de passe.")
            return

        if nouveau != confirm:
            afficher_erreur(self, "Erreur", "Le nouveau mot de passe et la confirmation ne correspondent pas.")
            return

        ok, message = changer_mot_de_passe_decloture(ancien, nouveau)
        if ok:
            afficher_info(self, "Succès", "Le mot de passe de déclôture a été modifié avec succès.")
            self.destroy()
        else:
            afficher_erreur(self, "Erreur", message or "Impossible de modifier le mot de passe.")
            self._ancien_entry.delete(0, "end")
