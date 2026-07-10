"""Onglet bilan annuel buvette."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from core.budget_evenement import get_bilan_annuel_buvette


class OngletBilanAnnuel(ctk.CTkFrame):
    """Affiche le bilan annuel buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._annee_var = ctk.StringVar(value="")
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Année scolaire (ex: 2025/2026)").pack(side="left")
        ctk.CTkEntry(top, textvariable=self._annee_var, width=160).pack(side="left", padx=8)
        ctk.CTkButton(top, text="Actualiser", command=self._refresh).pack(side="left")

        self._resume = ctk.CTkTextbox(self, height=420)
        self._resume.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _refresh(self) -> None:
        annee = self._annee_var.get().strip() or None
        bilan = get_bilan_annuel_buvette(annee)

        lignes = [
            f"Total achats buvette : {float(bilan.get('total_achats') or 0):.2f} €",
            f"Total coûts consommés : {float(bilan.get('total_couts_consommes') or 0):.2f} €",
            f"Stock buvette restant : {float(bilan.get('stock_restant') or 0):.2f} €",
            "",
            "Événement | Recettes | Coût buvette | Marge",
        ]
        for ev in bilan.get("par_evenement", []):
            lignes.append(
                f"{ev['nom']} | {ev['recettes']:.2f} € | {ev['cout_buvette']:.2f} € | {ev['marge']:.2f} €"
            )

        self._resume.delete("1.0", "end")
        self._resume.insert("1.0", "\n".join(lignes))
