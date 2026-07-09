"""Dialogue de restauration d'une sauvegarde."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info
from utils.backup import (
    redemarrer_application,
    restaurer_sauvegarde,
    verifier_integrite_base,
)


class RestaurationDialog(ctk.CTkToplevel):
    """Confirme et lance la restauration d'une sauvegarde."""

    def __init__(self, parent: Any, sauvegarde: dict) -> None:
        super().__init__(parent)
        self._sauvegarde = sauvegarde
        self.title("🔄 Restaurer une sauvegarde")
        self.geometry("560x340")
        self.resizable(False, False)
        self.transient(parent)

        self._integrite = verifier_integrite_base(sauvegarde.get("chemin", ""))
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        sauvegarde = self._sauvegarde

        ctk.CTkLabel(
            self,
            text="🔄 Restaurer une sauvegarde",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 10))

        ctk.CTkLabel(
            self,
            text="Sauvegarde sélectionnée :",
            font=fonts.get("subtitle"),
        ).pack(anchor="w", padx=20)
        ctk.CTkLabel(
            self,
            text=f"📁 {sauvegarde.get('nom_fichier', '')}",
            font=fonts.get("normal"),
        ).pack(anchor="w", padx=30, pady=(4, 2))
        ctk.CTkLabel(
            self,
            text=f"📅 {sauvegarde.get('date_formatee', '—')} — {sauvegarde.get('taille_formatee', '—')}",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=30, pady=(0, 10))

        frame_warn = ctk.CTkFrame(self, fg_color="#fff3cd")
        frame_warn.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            frame_warn,
            text=(
                "⚠️ Attention\n\n"
                "Toutes les données saisies depuis cette sauvegarde seront perdues.\n\n"
                "Une sauvegarde de sécurité sera créée automatiquement avant la restauration."
            ),
            justify="left",
            font=fonts.get("normal"),
            text_color="#8a5a00",
        ).pack(anchor="w", padx=12, pady=12)

        icone = "✅" if self._integrite["valide"] else "❌"
        couleur = "#15803d" if self._integrite["valide"] else "#b91c1c"
        ctk.CTkLabel(
            self,
            text=f"Vérification intégrité : {icone} {self._integrite['message']}",
            font=fonts.get("normal"),
            text_color=couleur,
        ).pack(anchor="w", padx=20, pady=(0, 18))

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=110,
            fg_color="grey",
            command=self.destroy,
        ).pack(side="left")
        self._btn_restaurer = ctk.CTkButton(
            frame_btn,
            text="🔄 Confirmer la restauration",
            width=210,
            command=self._restaurer,
        )
        self._btn_restaurer.pack(side="right")

        if not self._integrite["valide"]:
            self._btn_restaurer.configure(state="disabled")

    def _restaurer(self) -> None:
        resultat = restaurer_sauvegarde(self._sauvegarde.get("chemin", ""))
        if not resultat["succes"]:
            afficher_erreur(self, "Échec de la restauration", resultat["message"])
            return

        afficher_info(
            self,
            "Restauration réussie",
            "La restauration a réussi.\n\nL'application va maintenant redémarrer.",
        )
        redemarrer_application()
