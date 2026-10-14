"""Dialogue de sélection des modules d'un événement."""

from __future__ import annotations

from typing import Any
import tkinter as tk

import customtkinter as ctk

from db.models.evenements import MODULES_EVENEMENT_DISPONIBLES
from ui import theme as app_theme
from ui.modules.evenements.constantes import LIBELLES_MODULES


class _DialogModules(ctk.CTkToplevel):
    """Dialogue d'activation/désactivation des modules d'un événement."""

    def __init__(self, parent: Any, modules_actuels: list[str]) -> None:
        super().__init__(parent)
        self.title("⚙️ Modules de l'événement")
        self.geometry("440x380")
        self.resizable(False, False)
        self.transient(parent)
        self.result: list[str] | None = None

        self._vars: dict[str, tk.BooleanVar] = {}
        actifs_set = set(modules_actuels)

        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        label = ctk.CTkLabel(
            self,
            text="Modules activés",
            font=fonts.get("subtitle", ("Arial", 14, "bold")),
        )
        label.pack(anchor="w", padx=20, pady=(16, 4))

        sous_titre = ctk.CTkLabel(
            self,
            text="Sélectionnez les modules à activer pour cet événement :",
            font=fonts.get("small"),
            text_color="gray",
        )
        sous_titre.pack(anchor="w", padx=20, pady=(0, 12))

        frame_cases = ctk.CTkFrame(self, fg_color="transparent")
        frame_cases.pack(fill="x", padx=20, pady=(0, 16))

        for module in MODULES_EVENEMENT_DISPONIBLES:
            libelle = LIBELLES_MODULES.get(module, module.capitalize())
            var = tk.BooleanVar(value=(module in actifs_set))
            self._vars[module] = var
            chk = ctk.CTkCheckBox(frame_cases, text=libelle, variable=var)
            chk.pack(anchor="w", pady=4)

        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(pady=(12, 16))

        ctk.CTkButton(
            frame_btns,
            text="Valider",
            width=110,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._valider,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            frame_btns,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        self.result = [mod for mod, var in self._vars.items() if var.get()]
        self.destroy()
