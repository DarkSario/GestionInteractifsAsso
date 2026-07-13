"""Éditeur du template Bilan AG (Phase 16).

Fenêtre CTkToplevel permettant de modifier le fichier
config/bilan_ag_template.md directement depuis l'interface.
"""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from core.bilan_ag import (
    VARIABLES_DISPONIBLES,
    get_template_bilan,
    reset_template_bilan,
    save_template_bilan,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class EditeurTemplateBilan(ctk.CTkToplevel):
    """Éditeur du template Markdown du Bilan AG.

    Permet de modifier le template, affiche les variables disponibles
    et offre un bouton de restauration vers le modèle par défaut.
    """

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("✏️ Modifier le modèle Bilan AG")
        self.geometry("1000x680")
        self.minsize(800, 500)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._charger_template()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # ── En-tête ───────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            frame_header,
            text="✏️ Modifier le modèle Bilan AG",
            font=fonts.get("title"),
        ).pack(side="left")

        # ── Zone principale (éditeur + panneau variables) ─────────────────────
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=16, pady=4)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=1)
        frame_main.rowconfigure(0, weight=1)

        # Éditeur Markdown
        frame_editor = ctk.CTkFrame(frame_main)
        frame_editor.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            frame_editor,
            text="Contenu du template (Markdown)",
            font=fonts.get("bold"),
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(
            frame_editor,
            text="Utilisez {{variable}} pour insérer des données dynamiques.",
            font=fonts.get("small"),
            text_color="grey",
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(0, 4))
        self._textbox = ctk.CTkTextbox(
            frame_editor,
            font=("Courier New", 12),
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Panneau variables disponibles
        frame_vars = ctk.CTkFrame(frame_main)
        frame_vars.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            frame_vars,
            text="Variables disponibles",
            font=fonts.get("bold"),
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        scroll_vars = ctk.CTkScrollableFrame(frame_vars, fg_color="transparent")
        scroll_vars.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        for nom, description in VARIABLES_DISPONIBLES:
            f = ctk.CTkFrame(scroll_vars, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(
                f,
                text=f"{{{{{nom}}}}}",
                font=("Courier New", 11),
                text_color=colors.get("primary", "#1f6aa5"),
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                f,
                text=f"  {description}",
                font=fonts.get("small"),
                text_color="grey",
                anchor="w",
            ).pack(anchor="w")

        # ── Boutons ───────────────────────────────────────────────────────────
        frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        frame_buttons.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkButton(
            frame_buttons,
            text="❌ Annuler",
            width=100,
            fg_color="grey",
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            frame_buttons,
            text="🔄 Restaurer le modèle par défaut",
            width=240,
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._restaurer_defaut,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            frame_buttons,
            text="💾 Enregistrer",
            width=150,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._enregistrer,
        ).pack(side="right")

    def _charger_template(self) -> None:
        try:
            contenu = get_template_bilan()
            self._textbox.delete("1.0", "end")
            self._textbox.insert("1.0", contenu)
        except Exception as exc:
            logger.exception("EditeurTemplateBilan._charger_template: %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible de charger le template : {exc}")

    def _enregistrer(self) -> None:
        contenu = self._textbox.get("1.0", "end")
        try:
            save_template_bilan(contenu)
            afficher_info(self, "Succès", "Le modèle Bilan AG a été enregistré.")
        except Exception as exc:
            logger.exception("EditeurTemplateBilan._enregistrer: %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer le template : {exc}")

    def _restaurer_defaut(self) -> None:
        if not demander_confirmation(
            self,
            "Restaurer le modèle par défaut",
            "Toutes vos modifications seront perdues.\n"
            "Voulez-vous vraiment restaurer le modèle par défaut ?",
        ):
            return
        try:
            reset_template_bilan()
            self._charger_template()
            afficher_info(self, "Succès", "Le modèle par défaut a été restauré.")
        except Exception as exc:
            logger.exception("EditeurTemplateBilan._restaurer_defaut: %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible de restaurer le template : {exc}")
