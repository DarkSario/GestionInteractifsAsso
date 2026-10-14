"""Dialogue de saisie des dépenses d'un événement."""

from __future__ import annotations

from datetime import date
from typing import Any
import tkinter as tk

import customtkinter as ctk

from db.models.fournisseurs import get_all_fournisseurs
from db.models.membres import get_all_membres
from ui.components.dialogs import afficher_erreur
from utils.logger import get_logger

logger = get_logger(__name__)

MODES_DEPENSE = {
    "especes": "Espèces",
    "cheque": "Chèque",
    "carte": "Carte",
    "sumup": "SumUp",
    "virement": "Virement",
    "": "—",
}


class _DialogDepense(ctk.CTkToplevel):
    """Dialogue de création/édition d'une dépense."""

    def __init__(self, parent: Any, depense: dict | None = None) -> None:
        super().__init__(parent)
        self.title("Dépense")
        self.geometry("520x560")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._depense = depense

        self._var_libelle = tk.StringVar(value=depense["libelle"] if depense else "")
        self._var_montant = tk.StringVar(
            value=f"{depense['montant']:.2f}".replace(".", ",") if depense else ""
        )
        self._var_date = tk.StringVar(
            value=depense["date"] if depense else date.today().strftime("%Y-%m-%d")
        )
        self._var_categorie = tk.StringVar(
            value=depense.get("categorie") or "" if depense else ""
        )
        self._var_mode = tk.StringVar(
            value=(
                MODES_DEPENSE.get(depense.get("mode_paiement") or "", "—")
                if depense
                else "—"
            )
        )
        self._var_commentaire = tk.StringVar(
            value=depense.get("commentaire") or "" if depense else ""
        )
        self._var_avance_par = tk.StringVar(value="— Aucun —")
        self._var_remboursement = tk.StringVar(value="Non applicable")
        self._membres = get_all_membres()
        self._fournisseur_id: int | None = (
            depense.get("fournisseur_id") if depense else None
        )

        if depense and depense.get("avance_par_membre_id"):
            nom = f"{depense.get('avance_par_nom') or ''} {depense.get('avance_par_prenom') or ''}".strip()
            self._var_avance_par.set(nom or "— Aucun —")
        if depense and depense.get("remboursement_statut") == "en_attente":
            self._var_remboursement.set("En attente")
        self._fournisseurs = self._charger_fournisseurs()

        self._build()

    @staticmethod
    def _charger_fournisseurs() -> list[dict]:
        try:
            return get_all_fournisseurs()
        except Exception:
            logger.exception(
                "Impossible de charger les fournisseurs pour le dialogue de dépense."
            )
            return []

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=140, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field(
            "Libellé *",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_libelle, width=240),
        )
        field(
            "Montant *",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_montant, width=240),
        )
        field(
            "Date *",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_date, width=240, placeholder_text="AAAA-MM-JJ"
            ),
        )
        field(
            "Catégorie",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_categorie, width=240),
        )

        f_four = ctk.CTkFrame(scroll, fg_color="transparent")
        f_four.pack(fill="x", pady=3)
        ctk.CTkLabel(f_four, text="Fournisseur", width=140, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        noms = ["— Aucun —"] + [f["nom"] for f in self._fournisseurs]
        self._combo_fournisseur = ctk.CTkOptionMenu(f_four, values=noms, width=240)
        if self._fournisseur_id:
            four = next(
                (f for f in self._fournisseurs if f["id"] == self._fournisseur_id), None
            )
            self._combo_fournisseur.set(four["nom"] if four else "— Aucun —")
        else:
            self._combo_fournisseur.set("— Aucun —")
        self._combo_fournisseur.pack(side="left")

        field(
            "Mode paiement",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(MODES_DEPENSE.values()),
                variable=self._var_mode,
                width=240,
            ),
        )
        membres_values = ["— Aucun —"] + [
            f"{m['nom']} {m['prenom']}".strip() for m in self._membres
        ]
        field(
            "Avancé par",
            lambda p: ctk.CTkOptionMenu(
                p, values=membres_values, variable=self._var_avance_par, width=240
            ),
        )
        field(
            "Statut remboursement",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=["Non applicable", "En attente"],
                variable=self._var_remboursement,
                width=240,
            ),
        )
        field(
            "Commentaire",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_commentaire, width=240),
        )

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=(12, 4))
        ctk.CTkButton(
            frame_btn, text="Enregistrer", width=110, command=self._valider
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        libelle = self._var_libelle.get().strip()
        if not libelle:
            afficher_erreur(self, "Erreur", "Le libellé est obligatoire.")
            return
        montant_str = self._var_montant.get().strip().replace(",", ".")
        try:
            montant = float(montant_str)
        except ValueError:
            afficher_erreur(self, "Erreur", "Le montant doit être un nombre valide.")
            return
        date_val = self._var_date.get().strip()
        if not date_val:
            afficher_erreur(self, "Erreur", "La date est obligatoire.")
            return

        sel_four = self._combo_fournisseur.get()
        fournisseur_id: int | None = None
        if sel_four != "— Aucun —":
            four = next((f for f in self._fournisseurs if f["nom"] == sel_four), None)
            if four:
                fournisseur_id = four["id"]

        mode_label = self._var_mode.get()
        mode_inv = {v: k for k, v in MODES_DEPENSE.items()}
        mode = mode_inv.get(mode_label, None) or None

        membre = next(
            (
                m
                for m in self._membres
                if f"{m['nom']} {m['prenom']}".strip() == self._var_avance_par.get()
            ),
            None,
        )
        self.result = {
            "libelle": libelle,
            "montant": montant,
            "date": date_val,
            "categorie": self._var_categorie.get().strip() or None,
            "fournisseur_id": fournisseur_id,
            "mode_paiement": mode,
            "commentaire": self._var_commentaire.get().strip() or None,
            "avance_par_membre_id": int(membre["id"]) if membre else None,
            "remboursement_statut": (
                "en_attente"
                if self._var_remboursement.get() == "En attente" and membre
                else "non_applicable"
            ),
        }
        self.destroy()
