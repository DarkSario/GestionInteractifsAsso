"""Fenêtre de gestion des référentiels : Catégories, Unités, Fournisseurs."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.stock import valider_categorie, valider_fournisseur, valider_unite
from db.models.categories import (
    add_categorie,
    categorie_has_children,
    categorie_is_used,
    delete_categorie,
    get_all_categories,
    get_categories_parent,
    update_categorie,
)
from db.models.fournisseurs import (
    add_fournisseur,
    delete_fournisseur,
    fournisseur_is_used,
    get_all_fournisseurs,
    update_fournisseur,
)
from db.models.unites import (
    add_unite,
    delete_unite,
    get_all_unites,
    unite_is_used,
    update_unite,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class Referentiels(ctk.CTkToplevel):
    """Fenêtre de gestion des référentiels (catégories, unités, fournisseurs)."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("⚙️ Référentiels")
        self.geometry("800x600")
        self.minsize(700, 500)
        self.transient(parent)

        self._build_ui()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="⚙️ Référentiels",
            font=fonts.get("title"),
        ).pack(padx=15, pady=(15, 5), anchor="w")

        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self._tabview.add("Catégories")
        self._tabview.add("Unités")
        self._tabview.add("Fournisseurs")

        self._build_tab_categories(self._tabview.tab("Catégories"))
        self._build_tab_unites(self._tabview.tab("Unités"))
        self._build_tab_fournisseurs(self._tabview.tab("Fournisseurs"))

    # ── Onglet Catégories ─────────────────────────────────────────────────────

    def _build_tab_categories(self, parent: ctk.CTkFrame) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame_btn = ctk.CTkFrame(parent, fg_color="transparent")
        frame_btn.pack(fill="x", pady=(10, 5))

        ctk.CTkButton(
            frame_btn,
            text="➕ Catégorie",
            width=150,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_categorie,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_btn,
            text="➕ Sous-catégorie",
            width=160,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_sous_categorie,
        ).pack(side="left", padx=5)

        frame_tree = tk.Frame(parent)
        frame_tree.pack(fill="both", expand=True, pady=5)

        self._tree_cats = ttk.Treeview(
            frame_tree,
            columns=("id", "nom", "parent"),
            show="headings",
            selectmode="browse",
        )
        self._tree_cats.heading("id", text="ID")
        self._tree_cats.heading("nom", text="Nom")
        self._tree_cats.heading("parent", text="Catégorie parente")
        self._tree_cats.column("id", width=50, anchor="center", stretch=False)
        self._tree_cats.column("nom", width=250)
        self._tree_cats.column("parent", width=200)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self._tree_cats.yview)
        self._tree_cats.configure(yscrollcommand=scrollbar.set)
        self._tree_cats.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_actions = ctk.CTkFrame(parent, fg_color="transparent")
        frame_actions.pack(fill="x", pady=5)

        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier_categorie,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer_categorie,
        ).pack(side="left", padx=5)

        self._charger_categories()

    def _charger_categories(self) -> None:
        self._tree_cats.delete(*self._tree_cats.get_children())
        try:
            cats = get_all_categories()
        except Exception as exc:
            logger.exception("Erreur chargement catégories : %s", exc)
            return
        for c in cats:
            self._tree_cats.insert(
                "",
                "end",
                iid=str(c["id"]),
                values=(c["id"], c["nom"], c.get("parent_nom") or "—"),
            )

    def _get_categorie_selectionnee_id(self) -> int | None:
        sel = self._tree_cats.selection()
        if not sel:
            return None
        return int(sel[0])

    def _ajouter_categorie(self) -> None:
        _DialogSaisieNom(
            self,
            titre="Nouvelle catégorie",
            label="Nom de la catégorie :",
            on_valider=lambda nom: self._sauver_categorie(nom, None),
        )

    def _ajouter_sous_categorie(self) -> None:
        try:
            parents = get_categories_parent()
        except Exception as exc:
            afficher_erreur(self, "Erreur", str(exc))
            return
        if not parents:
            afficher_info(self, "Aucun parent", "Créez d'abord une catégorie parente.")
            return
        _DialogSousCategorie(
            self,
            parents=parents,
            on_valider=lambda nom, pid: self._sauver_categorie(nom, pid),
        )

    def _sauver_categorie(self, nom: str, parent_id: int | None) -> None:
        erreurs = valider_categorie(nom)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            add_categorie(nom.strip(), parent_id)
            self._charger_categories()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'ajouter la catégorie.\n{exc}")

    def _modifier_categorie(self) -> None:
        cat_id = self._get_categorie_selectionnee_id()
        if cat_id is None:
            return
        sel = self._tree_cats.item(str(cat_id))
        nom_actuel = sel["values"][1] if sel["values"] else ""
        _DialogSaisieNom(
            self,
            titre="Modifier la catégorie",
            label="Nouveau nom :",
            valeur_initiale=nom_actuel,
            on_valider=lambda nom: self._sauver_modif_categorie(cat_id, nom),
        )

    def _sauver_modif_categorie(self, cat_id: int, nom: str) -> None:
        erreurs = valider_categorie(nom)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            update_categorie(cat_id, nom.strip())
            self._charger_categories()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de modifier la catégorie.\n{exc}")

    def _supprimer_categorie(self) -> None:
        cat_id = self._get_categorie_selectionnee_id()
        if cat_id is None:
            return
        if categorie_is_used(cat_id):
            afficher_erreur(
                self,
                "Suppression impossible",
                "Cette catégorie est utilisée par des articles du stock.",
            )
            return
        if categorie_has_children(cat_id):
            afficher_erreur(
                self,
                "Suppression impossible",
                "Cette catégorie possède des sous-catégories. Supprimez-les d'abord.",
            )
            return
        if demander_confirmation(self, "Supprimer", "Supprimer cette catégorie ?"):
            try:
                delete_categorie(cat_id)
                self._charger_categories()
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))

    # ── Onglet Unités ─────────────────────────────────────────────────────────

    def _build_tab_unites(self, parent: ctk.CTkFrame) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame_btn = ctk.CTkFrame(parent, fg_color="transparent")
        frame_btn.pack(fill="x", pady=(10, 5))

        ctk.CTkButton(
            frame_btn,
            text="➕ Ajouter une unité",
            width=170,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_unite,
        ).pack(side="left", padx=5)

        frame_tree = tk.Frame(parent)
        frame_tree.pack(fill="both", expand=True, pady=5)

        self._tree_unites = ttk.Treeview(
            frame_tree,
            columns=("id", "nom"),
            show="headings",
            selectmode="browse",
        )
        self._tree_unites.heading("id", text="ID")
        self._tree_unites.heading("nom", text="Nom")
        self._tree_unites.column("id", width=60, anchor="center", stretch=False)
        self._tree_unites.column("nom", width=300)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self._tree_unites.yview)
        self._tree_unites.configure(yscrollcommand=scrollbar.set)
        self._tree_unites.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_actions = ctk.CTkFrame(parent, fg_color="transparent")
        frame_actions.pack(fill="x", pady=5)

        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier_unite,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer_unite,
        ).pack(side="left", padx=5)

        self._charger_unites()

    def _charger_unites(self) -> None:
        self._tree_unites.delete(*self._tree_unites.get_children())
        try:
            unites = get_all_unites()
        except Exception as exc:
            logger.exception("Erreur chargement unités : %s", exc)
            return
        for u in unites:
            self._tree_unites.insert("", "end", iid=str(u["id"]), values=(u["id"], u["nom"]))

    def _get_unite_selectionnee_id(self) -> int | None:
        sel = self._tree_unites.selection()
        if not sel:
            return None
        return int(sel[0])

    def _ajouter_unite(self) -> None:
        _DialogSaisieNom(
            self,
            titre="Nouvelle unité",
            label="Nom de l'unité :",
            on_valider=lambda nom: self._sauver_unite(nom),
        )

    def _sauver_unite(self, nom: str) -> None:
        erreurs = valider_unite(nom)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            add_unite(nom.strip())
            self._charger_unites()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'ajouter l'unité.\n{exc}")

    def _modifier_unite(self) -> None:
        unite_id = self._get_unite_selectionnee_id()
        if unite_id is None:
            return
        sel = self._tree_unites.item(str(unite_id))
        nom_actuel = sel["values"][1] if sel["values"] else ""
        _DialogSaisieNom(
            self,
            titre="Modifier l'unité",
            label="Nouveau nom :",
            valeur_initiale=nom_actuel,
            on_valider=lambda nom: self._sauver_modif_unite(unite_id, nom),
        )

    def _sauver_modif_unite(self, unite_id: int, nom: str) -> None:
        erreurs = valider_unite(nom)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            update_unite(unite_id, nom.strip())
            self._charger_unites()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de modifier l'unité.\n{exc}")

    def _supprimer_unite(self) -> None:
        unite_id = self._get_unite_selectionnee_id()
        if unite_id is None:
            return
        if unite_is_used(unite_id):
            afficher_erreur(
                self,
                "Suppression impossible",
                "Cette unité est utilisée dans le stock ou des mouvements.",
            )
            return
        if demander_confirmation(self, "Supprimer", "Supprimer cette unité ?"):
            try:
                delete_unite(unite_id)
                self._charger_unites()
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))

    # ── Onglet Fournisseurs ───────────────────────────────────────────────────

    def _build_tab_fournisseurs(self, parent: ctk.CTkFrame) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame_btn = ctk.CTkFrame(parent, fg_color="transparent")
        frame_btn.pack(fill="x", pady=(10, 5))

        ctk.CTkButton(
            frame_btn,
            text="➕ Ajouter un fournisseur",
            width=190,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_fournisseur,
        ).pack(side="left", padx=5)

        frame_tree = tk.Frame(parent)
        frame_tree.pack(fill="both", expand=True, pady=5)

        self._tree_fourns = ttk.Treeview(
            frame_tree,
            columns=("id", "nom", "telephone", "email"),
            show="headings",
            selectmode="browse",
        )
        self._tree_fourns.heading("id", text="ID")
        self._tree_fourns.heading("nom", text="Nom")
        self._tree_fourns.heading("telephone", text="Téléphone")
        self._tree_fourns.heading("email", text="E-mail")
        self._tree_fourns.column("id", width=50, anchor="center", stretch=False)
        self._tree_fourns.column("nom", width=200)
        self._tree_fourns.column("telephone", width=130)
        self._tree_fourns.column("email", width=200)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=self._tree_fourns.yview)
        self._tree_fourns.configure(yscrollcommand=scrollbar.set)
        self._tree_fourns.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_actions = ctk.CTkFrame(parent, fg_color="transparent")
        frame_actions.pack(fill="x", pady=5)

        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier_fournisseur,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer_fournisseur,
        ).pack(side="left", padx=5)

        self._charger_fournisseurs()

    def _charger_fournisseurs(self) -> None:
        self._tree_fourns.delete(*self._tree_fourns.get_children())
        try:
            fourns = get_all_fournisseurs()
        except Exception as exc:
            logger.exception("Erreur chargement fournisseurs : %s", exc)
            return
        for f in fourns:
            self._tree_fourns.insert(
                "",
                "end",
                iid=str(f["id"]),
                values=(f["id"], f["nom"], f.get("telephone") or "", f.get("email") or ""),
            )

    def _get_fournisseur_selectionne_id(self) -> int | None:
        sel = self._tree_fourns.selection()
        if not sel:
            return None
        return int(sel[0])

    def _ajouter_fournisseur(self) -> None:
        _DialogFournisseur(self, fournisseur=None, on_valider=self._sauver_fournisseur)

    def _sauver_fournisseur(
        self, nom: str, telephone: str, email: str, commentaire: str
    ) -> None:
        erreurs = valider_fournisseur(nom, email)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            add_fournisseur(nom.strip(), telephone, email, commentaire)
            self._charger_fournisseurs()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'ajouter le fournisseur.\n{exc}")

    def _modifier_fournisseur(self) -> None:
        fourn_id = self._get_fournisseur_selectionne_id()
        if fourn_id is None:
            return
        from db.models.fournisseurs import get_fournisseur_by_id
        fourn = get_fournisseur_by_id(fourn_id)
        if not fourn:
            return
        _DialogFournisseur(
            self,
            fournisseur=fourn,
            on_valider=lambda n, t, e, c: self._sauver_modif_fournisseur(fourn_id, n, t, e, c),
        )

    def _sauver_modif_fournisseur(
        self, fourn_id: int, nom: str, telephone: str, email: str, commentaire: str
    ) -> None:
        erreurs = valider_fournisseur(nom, email)
        if erreurs:
            afficher_erreur(self, "Erreur de saisie", erreurs[0][1])
            return
        try:
            update_fournisseur(fourn_id, nom.strip(), telephone, email, commentaire)
            self._charger_fournisseurs()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de modifier le fournisseur.\n{exc}")

    def _supprimer_fournisseur(self) -> None:
        fourn_id = self._get_fournisseur_selectionne_id()
        if fourn_id is None:
            return
        if fournisseur_is_used(fourn_id):
            afficher_erreur(
                self,
                "Suppression impossible",
                "Ce fournisseur est utilisé dans des mouvements de stock.",
            )
            return
        if demander_confirmation(self, "Supprimer", "Supprimer ce fournisseur ?"):
            try:
                delete_fournisseur(fourn_id)
                self._charger_fournisseurs()
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))


# ── Dialogs internes ─────────────────────────────────────────────────────────


class _DialogSaisieNom(ctk.CTkToplevel):
    """Dialog simple pour saisir un nom."""

    def __init__(
        self,
        parent: Any,
        titre: str,
        label: str,
        on_valider: Any,
        valeur_initiale: str = "",
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.resizable(False, False)
        self.transient(parent)
        self._on_valider = on_valider

        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(frame, text=label, font=fonts.get("normal")).pack(anchor="w")

        self._entry = ctk.CTkEntry(frame, width=300, font=fonts.get("normal"))
        self._entry.pack(pady=(5, 10))
        if valeur_initiale:
            self._entry.insert(0, valeur_initiale)

        self._err_label = ctk.CTkLabel(
            frame, text="", font=fonts.get("small"), text_color="#e05050"
        )
        self._err_label.pack()

        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn.pack(pady=(5, 0))

        ctk.CTkButton(
            frame_btn,
            text="Enregistrer",
            width=120,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._soumettre,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=90,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=5)

        self.grab_set()
        self._entry.focus()

    def _soumettre(self) -> None:
        nom = self._entry.get().strip()
        if not nom:
            self._err_label.configure(text="Le nom est obligatoire.")
            return
        self._on_valider(nom)
        self.destroy()


class _DialogSousCategorie(ctk.CTkToplevel):
    """Dialog pour créer une sous-catégorie avec sélection du parent."""

    def __init__(
        self,
        parent: Any,
        parents: list[dict],
        on_valider: Any,
    ) -> None:
        super().__init__(parent)
        self.title("Nouvelle sous-catégorie")
        self.resizable(False, False)
        self.transient(parent)
        self._parents = parents
        self._on_valider = on_valider

        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(frame, text="Catégorie parente :", font=fonts.get("normal")).pack(anchor="w")
        parent_noms = [p["nom"] for p in parents]
        self._parent_var = ctk.StringVar(value=parent_noms[0] if parent_noms else "")
        self._combo_parent = ctk.CTkOptionMenu(
            frame, values=parent_noms, variable=self._parent_var, width=300, font=fonts.get("normal")
        )
        self._combo_parent.pack(pady=(5, 10))

        ctk.CTkLabel(frame, text="Nom de la sous-catégorie :", font=fonts.get("normal")).pack(anchor="w")
        self._entry = ctk.CTkEntry(frame, width=300, font=fonts.get("normal"))
        self._entry.pack(pady=(5, 5))

        self._err_label = ctk.CTkLabel(
            frame, text="", font=fonts.get("small"), text_color="#e05050"
        )
        self._err_label.pack()

        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn.pack(pady=(5, 0))

        ctk.CTkButton(
            frame_btn,
            text="Enregistrer",
            width=120,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._soumettre,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=90,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=5)

        self.grab_set()
        self._entry.focus()

    def _soumettre(self) -> None:
        nom = self._entry.get().strip()
        if not nom:
            self._err_label.configure(text="Le nom est obligatoire.")
            return
        nom_parent = self._parent_var.get()
        parent = next((p for p in self._parents if p["nom"] == nom_parent), None)
        if not parent:
            self._err_label.configure(text="Sélectionnez une catégorie parente.")
            return
        self._on_valider(nom, parent["id"])
        self.destroy()


class _DialogFournisseur(ctk.CTkToplevel):
    """Dialog pour créer ou modifier un fournisseur."""

    def __init__(
        self,
        parent: Any,
        fournisseur: dict | None,
        on_valider: Any,
    ) -> None:
        super().__init__(parent)
        self._fourn = fournisseur
        self._on_valider = on_valider
        titre = "Modifier le fournisseur" if fournisseur else "Nouveau fournisseur"
        self.title(titre)
        self.resizable(False, False)
        self.transient(parent)

        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=15)

        champs = [("nom", "Nom *"), ("telephone", "Téléphone"), ("email", "E-mail")]
        self._entries: dict[str, ctk.CTkEntry] = {}

        for row_idx, (key, label) in enumerate(champs):
            ctk.CTkLabel(frame, text=label, font=fonts.get("normal"), anchor="w", width=100).grid(
                row=row_idx, column=0, sticky="w", pady=4
            )
            entry = ctk.CTkEntry(frame, width=280, font=fonts.get("normal"))
            entry.grid(row=row_idx, column=1, sticky="ew", pady=4)
            self._entries[key] = entry

        ctk.CTkLabel(frame, text="Commentaire", font=fonts.get("normal"), anchor="w", width=100).grid(
            row=len(champs), column=0, sticky="nw", pady=4
        )
        self._commentaire = ctk.CTkTextbox(frame, width=280, height=70, font=fonts.get("normal"))
        self._commentaire.grid(row=len(champs), column=1, sticky="ew", pady=4)

        self._err_label = ctk.CTkLabel(
            frame, text="", font=fonts.get("small"), text_color="#e05050"
        )
        self._err_label.grid(row=len(champs) + 1, column=0, columnspan=2, sticky="w")

        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn.grid(row=len(champs) + 2, column=0, columnspan=2, pady=(10, 0))

        ctk.CTkButton(
            frame_btn,
            text="Enregistrer",
            width=120,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._soumettre,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=90,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=5)

        if fournisseur:
            self._preremplir()

        self.grab_set()
        self._entries["nom"].focus()

    def _preremplir(self) -> None:
        f = self._fourn
        for key in ("nom", "telephone", "email"):
            val = f.get(key) or ""
            self._entries[key].delete(0, "end")
            self._entries[key].insert(0, val)
        self._commentaire.delete("1.0", "end")
        self._commentaire.insert("1.0", f.get("commentaire") or "")

    def _soumettre(self) -> None:
        nom = self._entries["nom"].get().strip()
        telephone = self._entries["telephone"].get().strip()
        email = self._entries["email"].get().strip()
        commentaire = self._commentaire.get("1.0", "end").strip()

        if not nom:
            self._err_label.configure(text="Le nom est obligatoire.")
            return

        self._on_valider(nom, telephone or None, email or None, commentaire or None)
        self.destroy()
