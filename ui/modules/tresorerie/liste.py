"""Fenêtre principale du module Trésorerie (Phase 6a)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui import theme as app_theme
from ui.modules.tresorerie.comptes import build_tab_comptes
from ui.modules.tresorerie.depot_especes import build_tab_depot_especes
from ui.modules.tresorerie.operations import build_tab_operations
from ui.modules.tresorerie.remises import build_tab_remises
from ui.modules.tresorerie.subventions import build_tab_subventions


class ListeTresorerie(ctk.CTkToplevel):
    """Fenêtre principale Trésorerie avec onglets."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("💰 Trésorerie")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.transient(parent)

        fonts = app_theme.FONTS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            header,
            text="💰 Trésorerie",
            font=fonts.get("title"),
        ).pack(side="left")

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        tab_comptes = tabs.add("💰 Comptes")
        tab_operations = tabs.add("📋 Opérations")
        tab_remises = tabs.add("🏦 Remises chèques")
        tab_subventions = tabs.add("🎁 Subventions")
        tab_depot = tabs.add("💵 Dépôt Espèces")

        build_tab_comptes(tab_comptes, self)
        build_tab_operations(tab_operations, self)
        build_tab_remises(tab_remises, self)
        build_tab_subventions(tab_subventions, self)
        build_tab_depot_especes(tab_depot, self)
