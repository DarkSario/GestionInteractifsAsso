"""Onglet budget et bilan d'un événement."""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from core.budget_evenement import (
    get_bilan_reel,
    get_or_create_budget,
    get_seuil_rentabilite,
    sauvegarder_budget,
)
from ui.components.dialogs import afficher_erreur, afficher_info
from utils.logger import get_logger

logger = get_logger(__name__)


class BudgetEvenementView(ctk.CTkFrame):
    """Vue budget prévisionnel vs réel."""

    def __init__(self, parent: Any, evenement_id: int | None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self._content = ctk.CTkTextbox(self, height=380)
        self._content.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=10, pady=(0, 10))

        self._recettes_var = tk.StringVar(value="0")
        self._depenses_var = tk.StringVar(value="0")
        self._cout_var = tk.StringVar(value="0")
        self._nb_var = tk.StringVar(value="0")
        self._prix_var = tk.StringVar(value="0")

        champs = [
            ("Recettes prévues", self._recettes_var),
            ("Dépenses prévues", self._depenses_var),
            ("Coût buvette prévu", self._cout_var),
            ("Nb personnes attendues", self._nb_var),
            ("Prix moyen entrée", self._prix_var),
        ]
        for idx, (label, var) in enumerate(champs):
            ctk.CTkLabel(form, text=label).grid(row=idx, column=0, sticky="w", padx=6, pady=4)
            ctk.CTkEntry(form, textvariable=var, width=180).grid(row=idx, column=1, sticky="w", padx=6, pady=4)

        ctk.CTkButton(form, text="✏️ Modifier budget prévisionnel", command=self._save).grid(
            row=len(champs), column=1, sticky="e", padx=6, pady=8
        )

    def set_evenement_id(self, evenement_id: int | None) -> None:
        """Met à jour l'événement chargé puis rafraîchit la vue."""
        self._evenement_id = evenement_id
        try:
            if self.winfo_exists():
                self._refresh()
        except Exception:
            pass

    def _refresh(self) -> None:
        try:
            if not self._content.winfo_exists():
                return
        except Exception:
            return
        self._content.delete("1.0", "end")
        if not self._evenement_id:
            self._content.insert("1.0", "Sauvegardez d'abord l'événement pour activer le budget.")
            return

        budget = get_or_create_budget(self._evenement_id)
        bilan = get_bilan_reel(self._evenement_id)
        seuil = get_seuil_rentabilite(self._evenement_id)

        self._recettes_var.set(str(float(budget.get("recettes_prevues") or 0)))
        self._depenses_var.set(str(float(budget.get("depenses_prevues") or 0)))
        self._cout_var.set(str(float(budget.get("cout_buvette_prevu") or 0)))
        self._nb_var.set(str(int(budget.get("nb_personnes_attendues") or 0)))
        self._prix_var.set(str(float(budget.get("prix_moyen_entree") or 0)))

        statut_seuil = (
            "✅ Atteint"
            if seuil["atteint"]
            else f"❌ Non atteint (manque {seuil['manque']})"
        )
        texte = (
            "PRÉVISIONNEL vs RÉEL\n\n"
            f"Recettes réelles : {bilan['recettes_reelles']:.2f} €\n"
            f"Dépenses réelles : {bilan['depenses_reelles']:.2f} €\n"
            f"Coût buvette réel : {bilan['cout_buvette_reel']:.2f} €\n"
            f"Bénéfice net réel : {bilan['benefice_reel']:.2f} €\n\n"
            "Seuil de rentabilité\n"
            f"Prix moyen entrée : {seuil['prix_moyen']:.2f} €\n"
            f"Seuil prévu : {seuil['seuil_prevu']} personnes\n"
            f"Personnes réelles : {seuil['personnes_reelles']} personnes\n"
            f"Statut : {statut_seuil}"
        )
        self._content.insert("1.0", texte)

    def _save(self) -> None:
        if not self._evenement_id:
            afficher_info(self, "Budget", "Sauvegardez d'abord l'événement.")
            return
        try:
            ok = sauvegarder_budget(
                self._evenement_id,
                float(self._recettes_var.get().replace(",", ".")),
                float(self._depenses_var.get().replace(",", ".")),
                float(self._cout_var.get().replace(",", ".")),
                int(self._nb_var.get() or 0),
                float(self._prix_var.get().replace(",", ".")),
            )
        except ValueError:
            afficher_erreur(
                self,
                "Erreur",
                "Veuillez saisir des valeurs numériques valides pour le budget.",
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur sauvegarde budget événement : %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible de sauvegarder le budget : {exc}")
            return
        if ok:
            self._refresh()
        else:
            afficher_erreur(self, "Erreur", "Impossible de sauvegarder le budget.")
