"""Fenêtre principale du module Buvette."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from ui import theme as app_theme
from ui.modules.buvette.achats_buvette import OngletAchatsBuvette
from ui.modules.buvette.bilan_annuel import OngletBilanAnnuel
from ui.modules.buvette.couts_evenement import OngletCoutsEvenement
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

        self._tabs.add("📋 Achats buvette")
        self._tabs.add("🔍 Inventaires")
        self._tabs.add("📊 Coûts par événement")
        self._tabs.add("📈 Bilan annuel")

        self._onglet_achats = OngletAchatsBuvette(self._tabs.tab("📋 Achats buvette"))
        self._onglet_achats.pack(fill="both", expand=True)

        self._onglet_inventaires = OngletInventaires(self._tabs.tab("🔍 Inventaires"))
        self._onglet_inventaires.pack(fill="both", expand=True)

        self._onglet_couts = OngletCoutsEvenement(self._tabs.tab("📊 Coûts par événement"))
        self._onglet_couts.pack(fill="both", expand=True)

        self._onglet_bilan = OngletBilanAnnuel(self._tabs.tab("📈 Bilan annuel"))
        self._onglet_bilan.pack(fill="both", expand=True)
