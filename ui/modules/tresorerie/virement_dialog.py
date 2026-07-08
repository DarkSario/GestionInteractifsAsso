"""Dialogue de virement interne."""

from __future__ import annotations

from datetime import date
from typing import Any

import customtkinter as ctk

from core.tresorerie import to_float
from db.models.tresorerie import add_virement_interne, get_all_comptes
from ui.components.dialogs import afficher_erreur, afficher_info


class VirementDialog(ctk.CTkToplevel):
    """Fenêtre modale de création d'un virement interne."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("↔️ Virement interne")
        self.geometry("460x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._comptes = get_all_comptes(actif_only=True)
        if len(self._comptes) < 2:
            afficher_erreur(
                self,
                "Virement",
                (
                    "Impossible de créer un virement : au moins deux comptes actifs "
                    "sont nécessaires. Veuillez créer un compte supplémentaire avant "
                    "de continuer."
                ),
            )
            self.destroy()
            return

        self._nom_to_id = {c["nom"]: int(c["id"]) for c in self._comptes}

        noms = list(self._nom_to_id.keys())
        self._source_var = ctk.StringVar(value=noms[0])
        self._dest_var = ctk.StringVar(value=noms[1] if len(noms) > 1 else noms[0])
        self._montant_var = ctk.StringVar(value="0,00")
        self._date_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._libelle_var = ctk.StringVar(value="Virement interne")
        self._commentaire_var = ctk.StringVar(value="")

        self._build_ui(noms)

    def _build_ui(self, noms: list[str]) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="De *").grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(frame, values=noms, variable=self._source_var).grid(row=0, column=1, sticky="ew", pady=5)

        ctk.CTkLabel(frame, text="Vers *").grid(row=1, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(frame, values=noms, variable=self._dest_var).grid(row=1, column=1, sticky="ew", pady=5)

        ctk.CTkLabel(frame, text="Montant *").grid(row=2, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._montant_var).grid(row=2, column=1, sticky="ew", pady=5)

        ctk.CTkLabel(frame, text="Date *").grid(row=3, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._date_var).grid(row=3, column=1, sticky="ew", pady=5)

        ctk.CTkLabel(frame, text="Libellé").grid(row=4, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._libelle_var).grid(row=4, column=1, sticky="ew", pady=5)

        ctk.CTkLabel(frame, text="Commentaire").grid(row=5, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._commentaire_var).grid(row=5, column=1, sticky="ew", pady=5)

        frame.columnconfigure(1, weight=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(footer, text="Annuler", command=self.destroy).pack(side="right")
        ctk.CTkButton(footer, text="✅ Valider", command=self._valider).pack(side="right", padx=(0, 8))

    def _valider(self) -> None:
        source_nom = self._source_var.get()
        dest_nom = self._dest_var.get()
        if source_nom == dest_nom:
            afficher_erreur(self, "Virement", "Le compte source et destination doivent être différents.")
            return

        montant = to_float(self._montant_var.get())
        if montant is None:
            afficher_erreur(self, "Virement", "Le montant est invalide.")
            return
        if montant <= 0:
            afficher_erreur(self, "Virement", "Le montant doit être supérieur à 0.")
            return

        add_virement_interne(
            self._nom_to_id[source_nom],
            self._nom_to_id[dest_nom],
            montant,
            self._date_var.get(),
            self._libelle_var.get(),
            self._commentaire_var.get(),
        )
        afficher_info(self, "Virement", "Virement interne enregistré.")
        self.destroy()
