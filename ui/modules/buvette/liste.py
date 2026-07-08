"""Fenêtre principale du module Buvette."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui import theme as app_theme
from ui.modules.buvette.approvisionnements import OngletApprovisionnements
from ui.modules.buvette.articles import OngletArticles
from ui.modules.buvette.caisses import OngletCaissesRecettes
from ui.modules.buvette.inventaires import OngletInventaires


class ListeBuvette(ctk.CTkToplevel):
    """Fenêtre principale avec onglets de gestion buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("🍺 Buvette")
        self.geometry("1180x760")
        self.minsize(980, 650)
        self.transient(parent)

        ctk.CTkLabel(
            self,
            text="🍺 Buvette",
            font=app_theme.FONTS.get("title"),
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self._tabs.add("Articles")
        self._tabs.add("Inventaires")
        self._tabs.add("Approvisionnements")
        self._tabs.add("Caisses & Recettes")

        self._onglet_articles = OngletArticles(self._tabs.tab("Articles"))
        self._onglet_articles.pack(fill="both", expand=True)

        self._onglet_inventaires = OngletInventaires(self._tabs.tab("Inventaires"))
        self._onglet_inventaires.pack(fill="both", expand=True)

        self._onglet_appro = OngletApprovisionnements(self._tabs.tab("Approvisionnements"))
        self._onglet_appro.pack(fill="both", expand=True)

        self._onglet_caisses = OngletCaissesRecettes(self._tabs.tab("Caisses & Recettes"))
        self._onglet_caisses.pack(fill="both", expand=True)
