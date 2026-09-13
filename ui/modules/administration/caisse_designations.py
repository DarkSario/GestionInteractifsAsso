"""Fenêtre de gestion des désignations de caisses."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.models.caisse_designations import (
    creer_designation_caisse,
    definir_activation_designation_caisse,
    get_designation_caisse,
    lister_designations_caisse,
    mettre_a_jour_designation_caisse,
    reinitialiser_designations_caisses,
    supprimer_designation_caisse,
)
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation


class GestionDesignationsCaisses(ctk.CTkToplevel):
    """Administration des désignations réutilisables de caisses."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Gestion des désignations de caisses")
        self.geometry("920x560")
        self.minsize(840, 500)
        self.transient(parent)
        self.grab_set()

        self._designations: list[dict] = []
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self,
            text="Gestion des désignations de caisses",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(16, 10))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkButton(
            actions, text="+ Nouvelle désignation", command=self._ajouter
        ).pack(side="left")
        ctk.CTkButton(
            actions, text="↻ Réinitialiser aux défauts", command=self._reinitialiser
        ).pack(side="left", padx=(8, 0))

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        self._tree = ttk.Treeview(
            table_frame,
            columns=("nom", "montant", "description", "actif", "ordre"),
            show="headings",
            height=12,
        )
        colonnes = (
            ("nom", "Désignation", 240, "w"),
            ("montant", "Montant", 120, "e"),
            ("description", "Description", 280, "w"),
            ("actif", "Actif", 90, "center"),
            ("ordre", "Ordre", 80, "center"),
        )
        for key, titre, width, anchor in colonnes:
            self._tree.heading(key, text=titre)
            self._tree.column(key, width=width, anchor=anchor)
        self._tree.pack(side="left", fill="both", expand=True)
        self._tree.bind("<Double-1>", lambda _event: self._modifier())

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(footer, text="✏️ Modifier", command=self._modifier).pack(
            side="left"
        )
        ctk.CTkButton(
            footer, text="✓ Activer / désactiver", command=self._toggle_actif
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            footer,
            text="🗑️ Supprimer",
            command=self._supprimer,
            fg_color="#b71c1c",
            hover_color="#7f0000",
        ).pack(side="left", padx=(8, 0))

    def _fmt_montant(self, value: float) -> str:
        return f"{float(value or 0):,.2f} €".replace(",", " ").replace(".", ",")

    def _refresh(self) -> None:
        self._designations = lister_designations_caisse(actif_only=False)
        self._tree.delete(*self._tree.get_children())
        for designation in self._designations:
            self._tree.insert(
                "",
                "end",
                iid=str(designation["id"]),
                values=(
                    designation.get("nom") or "",
                    self._fmt_montant(designation.get("montant_unitaire") or 0),
                    designation.get("description") or "",
                    "✓" if designation.get("actif") else "✗",
                    int(designation.get("ordre") or 0),
                ),
            )

    def _selection_id(self) -> int | None:
        selection = self._tree.selection()
        return int(selection[0]) if selection else None

    def _ajouter(self) -> None:
        dialog = _DialogDesignationCaisse(self, "Nouvelle désignation", None)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            creer_designation_caisse(**dialog.result)
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(
                self,
                "Désignations de caisses",
                f"Impossible de créer la désignation : {exc}",
            )
            return
        self._refresh()

    def _modifier(self) -> None:
        designation_id = self._selection_id()
        if not designation_id:
            afficher_info(
                self, "Désignations de caisses", "Sélectionnez une désignation."
            )
            return
        designation = get_designation_caisse(designation_id)
        if not designation:
            return
        dialog = _DialogDesignationCaisse(self, "Modifier la désignation", designation)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            mettre_a_jour_designation_caisse(designation_id, **dialog.result)
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(
                self,
                "Désignations de caisses",
                f"Impossible de modifier la désignation : {exc}",
            )
            return
        self._refresh()

    def _toggle_actif(self) -> None:
        designation_id = self._selection_id()
        if not designation_id:
            afficher_info(
                self, "Désignations de caisses", "Sélectionnez une désignation."
            )
            return
        designation = get_designation_caisse(designation_id)
        if not designation:
            return
        definir_activation_designation_caisse(
            designation_id, not bool(designation.get("actif"))
        )
        self._refresh()

    def _supprimer(self) -> None:
        designation_id = self._selection_id()
        if not designation_id:
            afficher_info(
                self, "Désignations de caisses", "Sélectionnez une désignation."
            )
            return
        designation = get_designation_caisse(designation_id)
        if not designation:
            return
        if not demander_confirmation(
            self,
            "Supprimer",
            f"Supprimer la désignation « {designation.get('nom') or ''} » ?",
        ):
            return
        supprimer_designation_caisse(designation_id)
        self._refresh()

    def _reinitialiser(self) -> None:
        if not demander_confirmation(
            self,
            "Réinitialiser",
            "Réinitialiser les désignations standards de caisses ?",
        ):
            return
        total = reinitialiser_designations_caisses()
        self._refresh()
        afficher_info(
            self, "Désignations de caisses", f"{total} désignation(s) disponible(s)."
        )


class _DialogDesignationCaisse(ctk.CTkToplevel):
    def __init__(self, parent: Any, titre: str, designation: dict | None) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("460x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: dict | None = None

        self._nom_var = tk.StringVar(value=(designation or {}).get("nom") or "")
        montant_initial = (designation or {}).get("montant_unitaire")
        self._montant_var = tk.StringVar(
            value="" if montant_initial is None else str(montant_initial)
        )
        self._description_var = tk.StringVar(
            value=(designation or {}).get("description") or ""
        )
        self._ordre_var = tk.StringVar(value=str((designation or {}).get("ordre") or 0))
        self._actif_var = tk.BooleanVar(value=bool((designation or {}).get("actif", 1)))

        self._build_ui()
        self.focus()

    def _build_ui(self) -> None:
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=(18, 0))

        ctk.CTkLabel(form, text="Désignation *").pack(anchor="w", pady=(0, 2))
        self._nom_entry = ctk.CTkEntry(form, textvariable=self._nom_var, width=380)
        self._nom_entry.pack(fill="x")

        ctk.CTkLabel(form, text="Montant unitaire (€) *").pack(
            anchor="w", pady=(10, 2)
        )
        ctk.CTkEntry(form, textvariable=self._montant_var, width=380).pack(fill="x")

        ctk.CTkLabel(form, text="Description").pack(anchor="w", pady=(10, 2))
        ctk.CTkEntry(form, textvariable=self._description_var, width=380).pack(fill="x")

        ctk.CTkLabel(form, text="Ordre").pack(anchor="w", pady=(10, 2))
        ctk.CTkEntry(form, textvariable=self._ordre_var, width=380).pack(fill="x")

        ctk.CTkCheckBox(
            form, text="Actif", variable=self._actif_var, onvalue=True, offvalue=False
        ).pack(anchor="w", pady=(12, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(16, 20))
        ctk.CTkButton(
            actions,
            text="Annuler",
            width=120,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy,
        ).pack(side="right")
        ctk.CTkButton(
            actions,
            text="Enregistrer",
            width=140,
            command=self._valider,
        ).pack(
            side="right", padx=(0, 10)
        )

    def _valider(self) -> None:
        nom = self._nom_var.get().strip()
        if not nom:
            afficher_erreur(self, "Désignations de caisses", "Le nom est obligatoire.")
            return
        montant_brut = self._montant_var.get().strip()
        if not montant_brut:
            afficher_erreur(
                self,
                "Désignations de caisses",
                "Le montant unitaire est obligatoire.",
            )
            return
        try:
            montant = float(montant_brut.replace(",", "."))
            ordre = int(self._ordre_var.get().strip() or "0")
        except ValueError:
            afficher_erreur(
                self,
                "Désignations de caisses",
                "Montant et ordre doivent être numériques.",
            )
            return
        if montant < 0:
            afficher_erreur(
                self,
                "Désignations de caisses",
                "Le montant unitaire doit être positif ou nul.",
            )
            return
        self.result = {
            "nom": nom,
            "montant_unitaire": montant,
            "description": self._description_var.get().strip(),
            "ordre": ordre,
            "actif": bool(self._actif_var.get()),
        }
        self.destroy()
