"""Onglet Articles du module Buvette."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.buvette import valider_article_buvette
from db.models.buvette import (
    add_article_buvette,
    archiver_article_buvette,
    get_all_articles_buvette,
    update_article_buvette,
)
from db.models.categories import get_all_categories
from db.models.stock import get_all_articles
from db.models.unites import get_all_unites
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation


class OngletArticles(ctk.CTkFrame):
    """Liste et gestion des articles buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)

        self._articles: list[dict] = []
        self._categories: list[dict] = []
        self._recherche_var = tk.StringVar()
        self._recherche_var.trace_add("write", self._on_recherche_change)
        self._filtre_cat_var = tk.StringVar(value="Toutes")

        self._build_ui()
        self._charger_donnees()

    def _build_ui(self) -> None:
        frame_top = ctk.CTkFrame(self, fg_color="transparent")
        frame_top.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            frame_top,
            text="+ Ajouter",
            width=120,
            command=self._ajouter,
        ).pack(side="left")

        ctk.CTkEntry(
            frame_top,
            textvariable=self._recherche_var,
            placeholder_text="Rechercher...",
            width=260,
        ).pack(side="right", padx=(8, 0))

        self._combo_filtre = ctk.CTkOptionMenu(
            frame_top,
            values=["Toutes"],
            variable=self._filtre_cat_var,
            command=lambda _: self._rafraichir_table(),
            width=260,
        )
        self._combo_filtre.pack(side="right", padx=(8, 0))

        ctk.CTkLabel(frame_top, text="Catégorie :").pack(side="right")

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame_table,
            columns=("id", "nom", "categorie", "stock", "prix"),
            show="headings",
            height=14,
        )
        self._tree.heading("id", text="ID")
        self._tree.heading("nom", text="Nom")
        self._tree.heading("categorie", text="Catégorie")
        self._tree.heading("stock", text="Stock")
        self._tree.heading("prix", text="Prix")

        self._tree.column("id", width=55, anchor="center", stretch=False)
        self._tree.column("nom", width=300)
        self._tree.column("categorie", width=280)
        self._tree.column("stock", width=90, anchor="center")
        self._tree.column("prix", width=120, anchor="e")

        self._tree.tag_configure("alerte", foreground="#ff4444")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(frame_actions, text="✏️ Modifier", command=self._modifier).pack(side="left")
        ctk.CTkButton(
            frame_actions,
            text="🗄️ Archiver",
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._archiver,
        ).pack(side="left", padx=8)

    def _charger_donnees(self) -> None:
        self._articles = get_all_articles_buvette(include_archives=False)
        self._categories = get_all_categories()

        labels = ["Toutes"] + [self._label_categorie(c) for c in self._categories]
        self._combo_filtre.configure(values=labels)
        if self._filtre_cat_var.get() not in labels:
            self._filtre_cat_var.set("Toutes")

        self._rafraichir_table()

    def _label_categorie(self, categorie: dict) -> str:
        if categorie.get("parent_nom"):
            return f"{categorie['parent_nom']} > {categorie['nom']}"
        return categorie.get("nom") or ""

    def _rafraichir_table(self) -> None:
        terme = self._recherche_var.get().strip().lower()
        filtre_cat = self._filtre_cat_var.get()

        self._tree.delete(*self._tree.get_children())
        for article in self._articles:
            if terme and terme not in (article.get("nom") or "").lower() and terme not in (
                article.get("categorie_nom") or ""
            ).lower():
                continue

            if filtre_cat != "Toutes":
                cat_label = ""
                for c in self._categories:
                    if c["id"] == article.get("categorie_id"):
                        cat_label = self._label_categorie(c)
                        break
                if cat_label != filtre_cat:
                    continue

            stock = int(article.get("stock_actuel") or 0)
            tag = "alerte" if stock <= 3 else ""
            self._tree.insert(
                "",
                "end",
                iid=str(article["id"]),
                values=(
                    article["id"],
                    article.get("nom") or "",
                    article.get("categorie_nom") or "",
                    stock,
                    self._fmt_euro(article.get("prix_vente")),
                ),
                tags=(tag,),
            )

    def _get_selected(self) -> dict | None:
        selection = self._tree.selection()
        if not selection:
            return None
        article_id = int(selection[0])
        return next((a for a in self._articles if a["id"] == article_id), None)

    def _on_recherche_change(self, *_args: Any) -> None:
        self._rafraichir_table()

    def _ajouter(self) -> None:
        form = _FormulaireArticleBuvette(self, article=None)
        self.wait_window(form)
        self._charger_donnees()

    def _modifier(self) -> None:
        article = self._get_selected()
        if not article:
            afficher_info(self, "Article", "Sélectionnez un article à modifier.")
            return

        form = _FormulaireArticleBuvette(self, article=article)
        self.wait_window(form)
        self._charger_donnees()

    def _archiver(self) -> None:
        article = self._get_selected()
        if not article:
            afficher_info(self, "Article", "Sélectionnez un article à archiver.")
            return

        ok = demander_confirmation(
            self,
            "Archiver l'article",
            f"Archiver « {article.get('nom', '')} » ?\nL'article ne sera plus proposé dans la buvette.",
        )
        if ok:
            archiver_article_buvette(article["id"])
            self._charger_donnees()

    @staticmethod
    def _fmt_euro(value: Any) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")


class _FormulaireArticleBuvette(ctk.CTkToplevel):
    """Fenêtre d'ajout/modification d'un article buvette."""

    def __init__(self, parent: Any, article: dict | None) -> None:
        super().__init__(parent)
        self._article = article

        self.title("Article buvette")
        self.geometry("640x560")
        self.transient(parent)
        self.grab_set()

        self._categories = get_all_categories()
        self._unites = get_all_unites()
        self._stocks = get_all_articles(include_archives=False)

        self._nom_var = tk.StringVar(value=(article.get("nom") if article else ""))
        self._cat_var = tk.StringVar(value="")
        self._unite_var = tk.StringVar(value="")
        self._contenance_var = tk.StringVar(value=(article.get("contenance") if article else ""))
        self._prix_vente_var = tk.StringVar(
            value=self._to_str_decimal(article.get("prix_vente") if article else 0)
        )
        self._prix_achat_var = tk.StringVar(
            value=self._to_str_decimal(article.get("prix_achat") if article else 0)
        )
        self._stock_var = tk.StringVar(value="— Aucun —")
        self._commentaire = ctk.CTkTextbox(self, height=90)

        self._build_ui()
        self._prefill_choices()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=14, pady=14)

        fields = [
            ("Nom *", ctk.CTkEntry(container, textvariable=self._nom_var)),
            (
                "Catégorie *",
                ctk.CTkOptionMenu(
                    container,
                    values=self._category_labels() or [""],
                    variable=self._cat_var,
                    dynamic_resizing=False,
                ),
            ),
            (
                "Unité *",
                ctk.CTkOptionMenu(
                    container,
                    values=[u["nom"] for u in self._unites] or [""],
                    variable=self._unite_var,
                    dynamic_resizing=False,
                ),
            ),
            ("Contenance", ctk.CTkEntry(container, textvariable=self._contenance_var)),
            ("Prix de vente (€) *", ctk.CTkEntry(container, textvariable=self._prix_vente_var)),
            ("Prix d'achat (€)", ctk.CTkEntry(container, textvariable=self._prix_achat_var)),
            (
                "Lié au stock général",
                ctk.CTkOptionMenu(
                    container,
                    values=["— Aucun —"] + [a["nom"] for a in self._stocks],
                    variable=self._stock_var,
                    dynamic_resizing=False,
                ),
            ),
        ]

        for i, (label, widget) in enumerate(fields):
            ctk.CTkLabel(container, text=label, font=fonts.get("normal")).grid(
                row=i, column=0, sticky="w", padx=8, pady=(8, 2)
            )
            widget.grid(row=i, column=1, sticky="ew", padx=8, pady=(8, 2))

        ctk.CTkLabel(container, text="Commentaire", font=fonts.get("normal")).grid(
            row=len(fields), column=0, sticky="nw", padx=8, pady=(8, 2)
        )
        self._commentaire.grid(row=len(fields), column=1, sticky="nsew", padx=8, pady=(8, 2))

        if self._article and self._article.get("commentaire"):
            self._commentaire.insert("1.0", self._article["commentaire"])

        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(len(fields), weight=1)

        ctk.CTkButton(container, text="Enregistrer", command=self._save).grid(
            row=len(fields) + 1, column=1, sticky="e", padx=8, pady=(12, 8)
        )

    def _category_labels(self) -> list[str]:
        labels: list[str] = []
        for c in self._categories:
            if c.get("parent_nom"):
                labels.append(f"{c['parent_nom']} > {c['nom']}")
            else:
                labels.append(c["nom"])
        return labels

    def _prefill_choices(self) -> None:
        if self._categories and not self._cat_var.get():
            self._cat_var.set(self._category_labels()[0])
        if self._unites and not self._unite_var.get():
            self._unite_var.set(self._unites[0]["nom"])

        if not self._article:
            return

        cat_id = self._article.get("categorie_id")
        for c in self._categories:
            if c["id"] == cat_id:
                self._cat_var.set(
                    f"{c['parent_nom']} > {c['nom']}" if c.get("parent_nom") else c["nom"]
                )
                break

        unite_id = self._article.get("unite_id")
        for u in self._unites:
            if u["id"] == unite_id:
                self._unite_var.set(u["nom"])
                break

        stock_id = self._article.get("stock_id")
        if stock_id:
            stock = next((s for s in self._stocks if s["id"] == stock_id), None)
            if stock:
                self._stock_var.set(stock["nom"])

    def _save(self) -> None:
        categorie = self._find_categorie(self._cat_var.get())
        unite = self._find_unite(self._unite_var.get())

        erreurs = valider_article_buvette(
            self._nom_var.get(),
            self._prix_vente_var.get(),
            categorie["id"] if categorie else None,
            unite["id"] if unite else None,
        )
        if erreurs:
            afficher_erreur(self, "Validation", "\n".join(erreurs))
            return

        stock = next((s for s in self._stocks if s["nom"] == self._stock_var.get()), None)
        stock_id = stock["id"] if stock else None

        nom = self._nom_var.get().strip()
        contenance = self._contenance_var.get().strip()
        commentaire = self._commentaire.get("1.0", "end").strip()
        prix_vente = self._to_float(self._prix_vente_var.get())
        prix_achat = self._to_float(self._prix_achat_var.get())

        try:
            if self._article:
                update_article_buvette(
                    article_id=self._article["id"],
                    nom=nom,
                    categorie_id=categorie["id"] if categorie else None,
                    unite_id=unite["id"] if unite else None,
                    contenance=contenance,
                    prix_vente=prix_vente,
                    prix_achat=prix_achat,
                    stock_id=stock_id,
                    commentaire=commentaire,
                )
            else:
                add_article_buvette(
                    nom=nom,
                    categorie_id=categorie["id"] if categorie else None,
                    unite_id=unite["id"] if unite else None,
                    contenance=contenance,
                    prix_vente=prix_vente,
                    prix_achat=prix_achat,
                    stock_id=stock_id,
                    commentaire=commentaire,
                )
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer l'article :\n{exc}")
            return

        self.destroy()

    def _find_categorie(self, label: str) -> dict | None:
        for c in self._categories:
            lbl = f"{c['parent_nom']} > {c['nom']}" if c.get("parent_nom") else c["nom"]
            if lbl == label:
                return c
        return None

    def _find_unite(self, nom: str) -> dict | None:
        return next((u for u in self._unites if u["nom"] == nom), None)

    @staticmethod
    def _to_float(value: str) -> float:
        try:
            return float((value or "0").replace(",", "."))
        except ValueError:
            return 0.0

    @staticmethod
    def _to_str_decimal(value: Any) -> str:
        try:
            val = float(value or 0)
        except (TypeError, ValueError):
            val = 0.0
        return f"{val:.2f}".replace(".", ",")
