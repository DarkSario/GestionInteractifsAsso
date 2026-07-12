"""Vue Tableaux personnalisés (Phase 5b) intégrée à la fiche événement."""

from __future__ import annotations

import json
from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from core.tableaux import get_valeurs_liste
from db.models.tableaux import (
    add_colonne,
    add_ligne,
    add_tableau,
    apply_template,
    calculer_totaux,
    delete_colonne,
    dupliquer_tableau,
    get_cellules_ligne,
    get_all_templates,
    get_colonnes_tableau,
    get_lignes_tableau,
    get_tableaux_evenement,
    save_template,
    set_cellule,
    update_ligne,
)
from ui.components.dialogs import afficher_info, demander_confirmation

_OPTIONS_TYPES_COLONNE = [
    ("Texte libre", "texte"),
    ("Nombre", "nombre"),
    ("Montant (€)", "montant"),
    ("Date", "date"),
    ("Case à cocher", "checkbox"),
    ("Liste — Mode de paiement", "liste_paiement"),
    ("Liste — Classes scolaires", "liste_classes"),
    ("Liste — Membres", "liste_membres"),
    ("Liste — Fournisseurs", "liste_fournisseurs"),
    ("Liste — Statut personnalisé", "liste_statut"),
    ("Liste personnalisée (valeurs libres)", "liste_perso"),
]


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
        ctk.CTkButton(
            actions, text="✏️ Modifier ligne", command=self._modifier_ligne
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(actions, text="⚙️ Colonnes", command=self._ajouter_colonne).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            actions, text="🗑️ Supprimer colonne", command=self._supprimer_colonne,
            fg_color="#b71c1c", hover_color="#7f0000",
        ).pack(side="left", padx=(0, 8))
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
        self._tree_lignes.bind("<Double-1>", self._modifier_ligne)

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
        dialog = _DialogColonne(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        add_colonne(
            self._tableau_id,
            dialog.result["nom"],
            dialog.result["type_colonne"],
            dialog.result.get("liste_perso_valeurs"),
            0,
            0,
            150,
        )
        self._charger_tableau(self._tableau_id)

    def _supprimer_colonne(self) -> None:
        if not self._tableau_id:
            afficher_info(self, "Colonnes", "Sélectionnez d'abord un tableau.")
            return
        colonnes = get_colonnes_tableau(self._tableau_id)
        if not colonnes:
            afficher_info(self, "Colonnes", "Ce tableau ne possède aucune colonne.")
            return
        dialog = _DialogChoisirColonne(self, colonnes)
        self.wait_window(dialog)
        if dialog.colonne_id is None:
            return
        nom_col = next((c["nom"] for c in colonnes if int(c["id"]) == dialog.colonne_id), "")
        if not demander_confirmation(
            self,
            "Supprimer la colonne",
            f"Supprimer la colonne « {nom_col} » et toutes ses données ?\n"
            "Cette action est irréversible.",
        ):
            return
        delete_colonne(dialog.colonne_id)
        self._charger_tableau(self._tableau_id)

    def _ajouter_ligne(self) -> None:
        if not self._tableau_id:
            afficher_info(self, "Lignes", "Sélectionnez d'abord un tableau.")
            return
        colonnes = get_colonnes_tableau(self._tableau_id)
        dialog = _DialogLigne(self, colonnes)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        ligne_id = add_ligne(self._tableau_id, None, "normal", 0)
        for col in colonnes:
            valeur = dialog.result.get(int(col["id"]), "")
            if valeur:
                set_cellule(ligne_id, int(col["id"]), valeur)
        self._charger_tableau(self._tableau_id)

    def _modifier_ligne(self, _event: Any | None = None) -> None:
        if not self._tableau_id:
            afficher_info(self, "Lignes", "Sélectionnez d'abord un tableau.")
            return
        selected = self._tree_lignes.selection()
        if not selected:
            afficher_info(self, "Lignes", "Sélectionnez d'abord une ligne.")
            return
        ligne_id = int(selected[0])
        colonnes = get_colonnes_tableau(self._tableau_id)
        cellules = get_cellules_ligne(ligne_id)
        dialog = _DialogLigne(self, colonnes, valeurs_initiales=cellules, titre="Modifier une ligne")
        self.wait_window(dialog)
        if dialog.result is None:
            return
        update_ligne(ligne_id, valeurs=dialog.result)
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


class _DialogChoisirColonne(ctk.CTkToplevel):
    """Dialogue de sélection d'une colonne à supprimer."""

    def __init__(self, parent: Any, colonnes: list[dict]) -> None:
        super().__init__(parent)
        self.title("Supprimer une colonne")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        self.colonne_id: int | None = None
        self._colonnes = colonnes
        self._var = ctk.StringVar(value=colonnes[0]["nom"] if colonnes else "")
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text="Sélectionnez la colonne à supprimer :").pack(anchor="w", padx=16, pady=(16, 4))
        for col in self._colonnes:
            ctk.CTkRadioButton(self, text=col["nom"], variable=self._var, value=col["nom"]).pack(
                anchor="w", padx=20, pady=3
            )
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(footer, text="Annuler", command=self.destroy).pack(side="right")
        ctk.CTkButton(
            footer, text="🗑️ Supprimer", fg_color="#b71c1c", hover_color="#7f0000",
            command=self._valider,
        ).pack(side="right", padx=(0, 8))

    def _valider(self) -> None:
        nom = self._var.get()
        col = next((c for c in self._colonnes if c["nom"] == nom), None)
        if col:
            self.colonne_id = int(col["id"])
        self.destroy()


class _DialogColonne(ctk.CTkToplevel):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Ajouter une colonne")
        self.geometry("520x560")
        self.transient(parent)
        self.grab_set()
        self.result: dict | None = None
        self._var_nom = ctk.StringVar()
        self._var_type = ctk.StringVar(value="texte")
        self._var_liste = ctk.StringVar()
        self._build_ui()

    def _build_ui(self) -> None:
        ctk.CTkLabel(self, text="Nom de la colonne :").pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkEntry(self, textvariable=self._var_nom).pack(fill="x", padx=16)
        ctk.CTkLabel(self, text="Type :").pack(anchor="w", padx=16, pady=(12, 4))
        for label, value in _OPTIONS_TYPES_COLONNE:
            ctk.CTkRadioButton(self, text=label, variable=self._var_type, value=value).pack(
                anchor="w", padx=18, pady=2
            )
        ctk.CTkLabel(
            self,
            text="Valeurs (uniquement pour « Liste personnalisée », séparées par ;)",
        ).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkEntry(self, textvariable=self._var_liste).pack(fill="x", padx=16)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=16)
        ctk.CTkButton(footer, text="Annuler", command=self.destroy).pack(side="right")
        ctk.CTkButton(footer, text="✅ Ajouter", command=self._valider).pack(side="right", padx=(0, 8))

    def _valider(self) -> None:
        nom = self._var_nom.get().strip()
        if not nom:
            return
        type_colonne = self._var_type.get()
        liste_perso_valeurs = None
        if type_colonne == "liste_perso":
            valeurs = [v.strip() for v in self._var_liste.get().split(";") if v.strip()]
            liste_perso_valeurs = json.dumps(valeurs, ensure_ascii=False) if valeurs else "[]"
        self.result = {
            "nom": nom,
            "type_colonne": type_colonne,
            "liste_perso_valeurs": liste_perso_valeurs,
        }
        self.destroy()


class _DialogLigne(ctk.CTkToplevel):
    def __init__(
        self,
        parent: Any,
        colonnes: list[dict],
        valeurs_initiales: dict[int, str] | None = None,
        titre: str = "Ajouter une ligne",
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("560x520")
        self.transient(parent)
        self.grab_set()
        self.result: dict[int, str] | None = None
        self._vars: dict[int, ctk.StringVar] = {}
        self._colonnes = colonnes
        self._valeurs_initiales = valeurs_initiales or {}
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=12, pady=12)
        for col in self._colonnes:
            cid = int(col["id"])
            ctk.CTkLabel(scroll, text=f"{col['nom']} :").pack(anchor="w", pady=(6, 2))
            valeur_initiale = str(self._valeurs_initiales.get(cid, ""))
            var = ctk.StringVar(value=valeur_initiale)
            self._vars[cid] = var
            column_type = str(col.get("type_colonne") or "").strip().lower()
            if column_type.startswith("liste_"):
                valeurs = get_valeurs_liste(column_type, str(col.get("liste_perso_valeurs") or ""))
                widget = ctk.CTkComboBox(scroll, values=valeurs or [""], variable=var)
                if valeurs and not valeur_initiale:
                    var.set(valeurs[0])
            else:
                widget = ctk.CTkEntry(scroll, textvariable=var)
            widget.pack(fill="x")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(footer, text="Annuler", command=self.destroy).pack(side="right")
        ctk.CTkButton(footer, text="💾 Enregistrer", command=self._valider).pack(side="right", padx=(0, 8))

    def _valider(self) -> None:
        self.result = {cid: var.get().strip() for cid, var in self._vars.items()}
        self.destroy()
