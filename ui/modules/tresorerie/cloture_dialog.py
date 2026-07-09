"""Dialogue de clôture d'exercice (Phase 6b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import customtkinter as ctk

from core.cloture import calculer_solde_cloture, valider_cloture
from db.models.cloture import cloturer_exercice
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class ClotureDialog(ctk.CTkToplevel):
    """Dialogue de confirmation de clôture d'un exercice."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        self._exercice = exercice
        nom = exercice.get("nom", "")
        self.title(f"🔒 Clôturer l'exercice {nom}")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        ex = self._exercice

        ctk.CTkLabel(
            self,
            text=f"🔒 Clôturer l'exercice {ex.get('nom', '')}",
            font=fonts.get("subtitle"),
        ).pack(padx=20, pady=(16, 6))

        # Période
        periode = (
            f"{self._fmt_date(ex['date_debut'])} → {self._fmt_date(ex['date_fin'])}"
        )
        ctk.CTkLabel(
            self, text=f"Période : {periode}", font=fonts.get("normal")
        ).pack(padx=20, pady=(0, 10))

        # Validation préalable
        erreurs = valider_cloture(int(ex["id"]))
        if erreurs:
            err_frame = ctk.CTkFrame(self, fg_color="#ffebee")
            err_frame.pack(fill="x", padx=20, pady=(0, 10))
            ctk.CTkLabel(
                err_frame,
                text="⚠️ Impossible de clôturer :",
                font=fonts.get("bold"),
                text_color="#b71c1c",
            ).pack(anchor="w", padx=10, pady=(6, 2))
            for err in erreurs:
                ctk.CTkLabel(
                    err_frame,
                    text=f"  • {err}",
                    font=fonts.get("normal"),
                    text_color="#b71c1c",
                ).pack(anchor="w", padx=10)
            ctk.CTkLabel(err_frame, text="").pack(pady=(2, 4))

            ctk.CTkButton(self, text="Fermer", width=100, command=self.destroy).pack(pady=16)
            return

        # Résumé financier
        self._solde_cloture = calculer_solde_cloture(int(ex["id"]))

        from db.models.cloture import get_stats_exercice
        stats = get_stats_exercice(int(ex["id"]))

        resume_frame = ctk.CTkFrame(self)
        resume_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(
            resume_frame, text="Résumé financier :", font=fonts.get("bold")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        for label, valeur, couleur in [
            ("Total recettes", stats["total_recettes"], "#2e7d32"),
            ("Total dépenses", stats["total_depenses"], "#b71c1c"),
            ("Solde de clôture", self._solde_cloture, "#1565c0"),
        ]:
            row = ctk.CTkFrame(resume_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(row, text=label, font=fonts.get("normal"), anchor="w").pack(
                side="left"
            )
            ctk.CTkLabel(
                row,
                text=self._fmt_montant(valeur),
                font=fonts.get("bold"),
                text_color=couleur,
            ).pack(side="right")

        ctk.CTkLabel(resume_frame, text="").pack(pady=(2, 4))

        # Avertissement
        avert_frame = ctk.CTkFrame(self, fg_color="#fff3e0")
        avert_frame.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(
            avert_frame,
            text=(
                "⚠️ Les opérations de cette période seront gelées\n"
                "   (lecture seule après clôture).\n\n"
                f"   Ce solde ({self._fmt_montant(self._solde_cloture)}) sera reporté\n"
                "   comme solde d'ouverture du prochain exercice."
            ),
            font=fonts.get("small"),
            text_color="#e65100",
            justify="left",
        ).pack(padx=10, pady=8)

        # Commentaire
        ctk.CTkLabel(self, text="Commentaire (optionnel) :", font=fonts.get("normal")).pack(
            anchor="w", padx=20
        )
        self._commentaire_entry = ctk.CTkEntry(self, placeholder_text="Optionnel")
        self._commentaire_entry.pack(fill="x", padx=20, pady=(4, 12))

        # Boutons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
            command=self.destroy
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="🔒 Confirmer la clôture",
            width=200,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._confirmer,
        ).pack(side="left", padx=8)

    def _confirmer(self) -> None:
        """Effectue la clôture après confirmation."""
        commentaire = self._commentaire_entry.get().strip() or None
        if commentaire:
            self._exercice["commentaire"] = commentaire

        ok = cloturer_exercice(int(self._exercice["id"]), self._solde_cloture)
        if ok:
            afficher_info(self, "Clôture effectuée", "L'exercice a été clôturé avec succès.")
            self.destroy()
        else:
            afficher_erreur(self, "Erreur", "La clôture a échoué. Veuillez réessayer.")

    @staticmethod
    def _fmt_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(value) if value else "—"

    @staticmethod
    def _fmt_montant(value: float) -> str:
        return f"{value:,.2f} €".replace(",", " ").replace(".", ",")
