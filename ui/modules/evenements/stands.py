"""Vue Stands (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from db.models.stands import (
    add_attente,
    add_stand,
    finaliser_location_stand,
    get_attente_evenement,
    get_stands_evenement,
    get_stats_stands,
    promouvoir_attente,
)
from ui.components.dialogs import afficher_info


class StandsView(ctk.CTkFrame):
    """Composant UI pour la gestion des stands."""

    def __init__(self, parent: Any, evenement_id: int | None = None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        self.refresh()

    def _build_ui(self) -> None:
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(actions, text="+ Ajouter un stand", command=self._ajouter_stand).pack(side="left")
        self._btn_attente = ctk.CTkButton(actions, text="📋 Liste d'attente (0)", command=self._ouvrir_attente)
        self._btn_attente.pack(side="left", padx=8)

        self._tree = ttk.Treeview(
            self,
            columns=("empl", "nom", "responsable", "type", "location"),
            show="headings",
            height=10,
        )
        for col, label, width in [
            ("empl", "Empl.", 80),
            ("nom", "Nom stand", 260),
            ("responsable", "Responsable", 220),
            ("type", "Type", 120),
            ("location", "Loc.", 100),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._btn_finaliser = ctk.CTkButton(self, text="💸 Finaliser location sélectionnée", command=self._finaliser_location)
        self._btn_finaliser.pack(
            anchor="w", padx=8, pady=(4, 0)
        )
        self._tree.bind("<<TreeviewSelect>>", self._on_select_stand)

        self._lbl_stats = ctk.CTkLabel(self, text="Stats : —")
        self._lbl_stats.pack(anchor="w", padx=8, pady=(4, 8))

    def _check_evenement(self) -> bool:
        if self._evenement_id:
            return True
        afficher_info(self, "Information", "Veuillez d'abord sauvegarder l'événement.")
        return False

    def _fmt(self, value: float) -> str:
        return f"{value:,.2f}€".replace(",", " ").replace(".", ",")

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        if not self._evenement_id:
            self._lbl_stats.configure(text="Stats : sauvegardez d'abord l'événement")
            self._btn_attente.configure(text="📋 Liste d'attente (0)")
            return

        stands = get_stands_evenement(self._evenement_id)
        for s in stands:
            responsable = s.get("responsable_nom_externe") or " ".join(
                p for p in [s.get("responsable_prenom"), s.get("responsable_nom")] if p
            ).strip()
            self._tree.insert(
                "",
                "end",
                iid=str(s["id"]),
                values=(
                    s.get("numero_emplacement") or "—",
                    s.get("nom_stand"),
                    responsable or "—",
                    "Bénévole" if s.get("type_stand") == "benevole" else (
                        "🟢 Recette" if (s.get("type_location") or "recette") == "recette" else "🔴 Dépense"
                    ),
                    self._fmt(float(s.get("montant_location") or 0)) if s.get("type_stand") == "location" else "—",
                ),
            )

        attente = get_attente_evenement(self._evenement_id)
        self._btn_attente.configure(text=f"📋 Liste d'attente ({len(attente)})")

        stats = get_stats_stands(self._evenement_id)
        self._lbl_stats.configure(
            text=(
                "Stats : "
                f"{stats['total']} stands | {stats['benevoles']} bénévoles | "
                f"{stats['locations']} locations | "
                f"{self._fmt(stats['montant_locations'])} recettes | "
                f"{self._fmt(stats['montant_locations_depenses'])} dépenses"
            )
        )
        self._on_select_stand()

    def _ajouter_stand(self) -> None:
        if not self._check_evenement():
            return
        nom = simpledialog.askstring("Nouveau stand", "Nom du stand :", parent=self)
        if not nom:
            return
        emplacement = simpledialog.askstring("Nouveau stand", "Emplacement (ex: A1) :", parent=self)
        type_stand = simpledialog.askstring(
            "Nouveau stand",
            "Type (benevole/location) :",
            parent=self,
            initialvalue="benevole",
        )
        type_stand = (type_stand or "benevole").strip().lower()
        if type_stand not in {"benevole", "location"}:
            type_stand = "benevole"
        montant = 0.0
        type_location = "recette"
        if type_stand == "location":
            type_location_txt = simpledialog.askstring(
                "Type location",
                "Type (recette/depense) :",
                parent=self,
                initialvalue="recette",
            )
            type_location = (type_location_txt or "recette").strip().lower()
            if type_location not in {"recette", "depense"}:
                type_location = "recette"
            valeur = simpledialog.askstring("Location", "Montant de location :", parent=self, initialvalue="0")
            try:
                montant = float((valeur or "0").replace(",", "."))
            except ValueError:
                montant = 0.0

        add_stand(
            self._evenement_id,
            emplacement,
            nom,
            type_stand,
            None,
            None,
            montant,
            type_location,
            0,
            None,
        )
        self.refresh()

    def _finaliser_location(self) -> None:
        if not self._check_evenement():
            return
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Location", "Sélectionnez un stand de location.")
            return
        try:
            stand_id = int(selected[0])
        except (TypeError, ValueError):
            afficher_info(self, "Location", "Sélection invalide.")
            return
        ok = finaliser_location_stand(stand_id)
        if ok:
            afficher_info(self, "Location", "Location comptabilisée.")
        else:
            afficher_info(self, "Location", "Impossible de finaliser cette location.")
        self.refresh()

    def _on_select_stand(self, _event: Any | None = None) -> None:
        selected = self._tree.selection()
        if not selected:
            self._btn_finaliser.configure(text="💸 Finaliser location sélectionnée")
            return
        valeurs = self._tree.item(selected[0], "values")
        type_txt = str(valeurs[3]) if valeurs else ""
        if "🔴" in type_txt:
            self._btn_finaliser.configure(text="💸 Finaliser la dépense sélectionnée")
        else:
            self._btn_finaliser.configure(text="💸 Finaliser la recette sélectionnée")

    def _ouvrir_attente(self) -> None:
        if not self._check_evenement():
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("📋 Liste d'attente")
        dialog.geometry("520x360")
        dialog.transient(self)

        ctk.CTkButton(dialog, text="+ Inscrire", command=lambda: self._inscrire_attente(dialog)).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        tree = ttk.Treeview(dialog, columns=("nom", "contact"), show="headings", height=10)
        tree.heading("nom", text="Nom")
        tree.heading("contact", text="Contact")
        tree.column("nom", width=240)
        tree.column("contact", width=220)
        tree.pack(fill="both", expand=True, padx=12, pady=6)

        for a in get_attente_evenement(self._evenement_id):
            nom = " ".join(p for p in [a.get("nom"), a.get("prenom")] if p)
            tree.insert("", "end", iid=str(a["id"]), values=(nom, a.get("contact") or "—"))

        def promouvoir() -> None:
            selected = tree.selection()
            if not selected:
                return
            promouvoir_attente(int(selected[0]))
            dialog.destroy()
            self.refresh()

        ctk.CTkButton(dialog, text="➡️ Promouvoir vers stand", command=promouvoir).pack(
            anchor="w", padx=12, pady=(0, 10)
        )

    def _inscrire_attente(self, parent: Any) -> None:
        nom = simpledialog.askstring("Liste d'attente", "Nom :", parent=parent)
        if not nom:
            return
        prenom = simpledialog.askstring("Liste d'attente", "Prénom :", parent=parent)
        contact = simpledialog.askstring("Liste d'attente", "Contact :", parent=parent)
        add_attente(self._evenement_id, nom, prenom, contact, None)
        parent.destroy()
        self._ouvrir_attente()
