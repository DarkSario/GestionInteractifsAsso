"""Vue Tableaux personnalisés (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from db.models.tableaux import (
    add_colonne,
    add_ligne,
    add_tableau,
    apply_template,
    calculer_totaux,
    dupliquer_tableau,
    get_all_templates,
    get_colonnes_tableau,
    get_lignes_tableau,
    get_tableaux_evenement,
    save_template,
    set_cellule,
)
from ui.components.dialogs import afficher_info


class TableauxView(ctk.CTkFrame):
    """Composant UI pour les tableaux personnalisés d'un événement."""

    def __init__(self, parent: Any, evenement_id: int | None = None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._tableau_id: int | None = None
        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        self._tableau_id = None
        self.refresh()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            top, text="+ Nouveau tableau", command=self._nouveau_tableau
        ).pack(side="left")
        ctk.CTkButton(
            top, text="📂 Depuis template", command=self._depuis_template
        ).pack(side="left", padx=8)

        self._tree_tableaux = ttk.Treeview(
            self,
            columns=("nom", "lignes"),
            show="headings",
            height=5,
        )
        self._tree_tableaux.heading("nom", text="Nom du tableau")
        self._tree_tableaux.heading("lignes", text="Lignes")
        self._tree_tableaux.column("nom", width=420)
        self._tree_tableaux.column("lignes", width=80, anchor="center")
        self._tree_tableaux.pack(fill="x", padx=8, pady=4)
        self._tree_tableaux.bind("<<TreeviewSelect>>", self._on_select_tableau)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkButton(actions, text="+ Ligne", command=self._ajouter_ligne).pack(
            side="left"
        )
        ctk.CTkButton(actions, text="⚙️ Colonnes", command=self._ajouter_colonne).pack(
            side="left", padx=8
        )
        ctk.CTkButton(actions, text="💾 Template", command=self._sauver_template).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            actions, text="📋 Dupliquer", command=self._dupliquer_tableau
        ).pack(side="left", padx=8)

        self._lbl_totaux = ctk.CTkLabel(self, text="Totaux : —")
        self._lbl_totaux.pack(anchor="w", padx=8, pady=(2, 4))

        self._tree_lignes = ttk.Treeview(self, show="headings", height=10)
        self._tree_lignes.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _check_evenement(self) -> bool:
        if self._evenement_id:
            return True
        afficher_info(self, "Information", "Veuillez d'abord sauvegarder l'événement.")
        return False

    def refresh(self) -> None:
        self._tree_tableaux.delete(*self._tree_tableaux.get_children())
        self._tree_lignes.delete(*self._tree_lignes.get_children())
        self._lbl_totaux.configure(text="Totaux : —")

        if not self._evenement_id:
            return

        tableaux = get_tableaux_evenement(self._evenement_id)
        for t in tableaux:
            self._tree_tableaux.insert(
                "", "end", iid=str(t["id"]), values=(t["nom"], t["nb_lignes"])
            )

        if self._tableau_id and any(
            str(self._tableau_id) == i for i in self._tree_tableaux.get_children()
        ):
            self._tree_tableaux.selection_set(str(self._tableau_id))
            self._charger_tableau(self._tableau_id)

    def _on_select_tableau(self, _event: Any) -> None:
        selected = self._tree_tableaux.selection()
        if not selected:
            return
        try:
            self._tableau_id = int(selected[0])
        except (TypeError, ValueError):
            self._tableau_id = None
            return
        self._charger_tableau(self._tableau_id)

    def _charger_tableau(self, tableau_id: int) -> None:
        colonnes = get_colonnes_tableau(tableau_id)
        lignes = get_lignes_tableau(tableau_id)

        columns = ["statut"] + [f"col_{c['id']}" for c in colonnes]
        self._tree_lignes.configure(columns=columns)

        self._tree_lignes.heading("statut", text="St.")
        self._tree_lignes.column("statut", width=60, anchor="center")

        for c in colonnes:
            key = f"col_{c['id']}"
            self._tree_lignes.heading(key, text=c["nom"])
            self._tree_lignes.column(
                key, width=int(c.get("largeur") or 150), anchor="center"
            )

        self._tree_lignes.delete(*self._tree_lignes.get_children())
        for ligne in lignes:
            cellules = ligne.get("cellules") or {}
            valeurs = [
                ligne.get("statut_ligne", "normal"),
                *[(cellules.get(str(c["id"])) or "") for c in colonnes],
            ]
            self._tree_lignes.insert("", "end", iid=str(ligne["id"]), values=valeurs)

        totaux = calculer_totaux(tableau_id)
        if not totaux:
            self._lbl_totaux.configure(text="Totaux : aucun total automatique")
            return

        by_id = {int(c["id"]): c for c in colonnes}
        parts = []
        for col_id, total in totaux.items():
            nom = by_id.get(col_id, {}).get("nom", f"Colonne {col_id}")
            parts.append(f"{nom}: {total:,.2f}".replace(",", " ").replace(".", ","))
        self._lbl_totaux.configure(text="Totaux : " + " | ".join(parts))

    def _nouveau_tableau(self) -> None:
        if not self._check_evenement():
            return
        nom = simpledialog.askstring("Nouveau tableau", "Nom du tableau :", parent=self)
        if not nom:
            return
        tableau_id = add_tableau(self._evenement_id, nom, None, 0)
        self._tableau_id = tableau_id
        self.refresh()

    def _depuis_template(self) -> None:
        if not self._check_evenement():
            return
        templates = get_all_templates()
        if not templates:
            afficher_info(self, "Templates", "Aucun template disponible.")
            return
        template_id = templates[0]["id"]
        self._tableau_id = apply_template(template_id, self._evenement_id)
        self.refresh()

    def _dupliquer_tableau(self) -> None:
        if not self._check_evenement() or not self._tableau_id:
            return
        self._tableau_id = dupliquer_tableau(self._tableau_id, self._evenement_id)
        self.refresh()

    def _ajouter_colonne(self) -> None:
        if not self._tableau_id:
            afficher_info(self, "Colonnes", "Sélectionnez d'abord un tableau.")
            return
        nom = simpledialog.askstring("Nouvelle colonne", "Nom :", parent=self)
        if not nom:
            return
        type_colonne = simpledialog.askstring(
            "Nouvelle colonne",
            "Type de colonne (ex: texte, nombre, montant, liste_paiement) :",
            parent=self,
            initialvalue="texte",
        )
        add_colonne(
            self._tableau_id, nom, (type_colonne or "texte").strip(), None, 0, 0, 150
        )
        self._charger_tableau(self._tableau_id)

    def _ajouter_ligne(self) -> None:
        if not self._tableau_id:
            afficher_info(self, "Lignes", "Sélectionnez d'abord un tableau.")
            return
        ligne_id = add_ligne(self._tableau_id, None, "normal", 0)
        colonnes = get_colonnes_tableau(self._tableau_id)
        for col in colonnes:
            valeur = simpledialog.askstring(
                "Nouvelle ligne", f"{col['nom']} :", parent=self
            )
            if valeur:
                set_cellule(ligne_id, int(col["id"]), valeur)
        self._charger_tableau(self._tableau_id)

    def _sauver_template(self) -> None:
        if not self._tableau_id:
            afficher_info(self, "Template", "Sélectionnez d'abord un tableau.")
            return
        nom = simpledialog.askstring(
            "Sauvegarder template", "Nom du template :", parent=self
        )
        if not nom:
            return
        save_template(nom, None, self._tableau_id)
        afficher_info(self, "Template", "Template sauvegardé.")
