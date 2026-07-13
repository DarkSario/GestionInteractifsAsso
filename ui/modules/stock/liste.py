"""Fenêtre principale de gestion du stock."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.models.categories import get_all_categories
from core.stock_v2 import get_article_tags
from db.models.stock import archiver_article, get_all_articles
from ui import theme as app_theme
from ui.components.dialogs import demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class ListeStock(ctk.CTkToplevel):
    """Fenêtre principale de gestion du stock général."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("📦 Stock général")
        self.geometry("1000x650")
        self.minsize(800, 500)
        self.transient(parent)

        self._tous_les_articles: list[dict] = []
        self._afficher_archives = tk.BooleanVar(value=False)
        self._recherche_var = tk.StringVar()
        self._recherche_var.trace_add("write", self._on_recherche_change)
        self._filtre_categorie_var = tk.StringVar(value="Toutes")
        self._categories: list[dict] = []

        self._build_ui()
        self._charger_categories()
        self._charger_articles()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # En-tête
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            frame_header,
            text="📦 Stock général",
            font=fonts.get("title"),
        ).pack(side="left")

        ctk.CTkButton(
            frame_header,
            text="⚙️ Référentiels",
            width=130,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self._ouvrir_referentiels,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            frame_header,
            text="📋 Inventaires",
            width=130,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self._ouvrir_inventaires,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            frame_header,
            text="+ Ajouter",
            width=110,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire_ajout,
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            frame_header,
            text="🔄 Actualiser",
            width=120,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self._charger_articles,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            frame_header,
            text="📦 Entrée",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire_entree,
        ).pack(side="right", padx=5)

        # Barre de recherche et filtres
        frame_search = ctk.CTkFrame(self, fg_color="transparent")
        frame_search.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            frame_search, text="🔍", font=fonts.get("normal")
        ).pack(side="left", padx=(0, 5))

        ctk.CTkEntry(
            frame_search,
            textvariable=self._recherche_var,
            placeholder_text="Rechercher un article…",
            width=280,
            font=fonts.get("normal"),
        ).pack(side="left")

        ctk.CTkLabel(
            frame_search, text="Catégorie :", font=fonts.get("normal")
        ).pack(side="left", padx=(15, 5))

        self._combo_filtre_cat = ctk.CTkOptionMenu(
            frame_search,
            values=["Toutes"],
            variable=self._filtre_categorie_var,
            width=200,
            font=fonts.get("normal"),
            command=lambda _: self._afficher_liste(),
        )
        self._combo_filtre_cat.pack(side="left")

        ctk.CTkCheckBox(
            frame_search,
            text="Afficher archivés",
            variable=self._afficher_archives,
            command=self._on_toggle_archives,
            font=fonts.get("normal"),
        ).pack(side="left", padx=(20, 0))

        # Tableau
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=15, pady=5)

        self._tree = self._build_treeview(frame_table)

        # Pied de page
        self._label_total = ctk.CTkLabel(
            self, text="", font=fonts.get("small"), anchor="w"
        )
        self._label_total.pack(fill="x", padx=15, pady=(0, 10))

    def _build_treeview(self, parent: ctk.CTkFrame) -> ttk.Treeview:
        columns = ("id", "nom", "categorie", "quantite", "seuil", "unite", "prix", "tags")

        style = ttk.Style()
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            bg = "#2b2b2b"
            fg = "#ffffff"
            heading_bg = "#1a1a2e"
        else:
            bg = "#f0f0f0"
            fg = "#000000"
            heading_bg = "#d0d0d0"

        style.theme_use("default")
        style.configure(
            "Stock.Treeview",
            background=bg,
            foreground=fg,
            rowheight=28,
            fieldbackground=bg,
            font=("Arial", 12),
        )
        style.configure(
            "Stock.Treeview.Heading",
            background=heading_bg,
            foreground=fg,
            font=("Arial", 12, "bold"),
        )
        style.map(
            "Stock.Treeview",
            background=[("selected", "#1f6aa5")],
            foreground=[("selected", "#ffffff")],
        )

        frame_tree = tk.Frame(parent, bg=bg)
        frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(
            frame_tree,
            columns=columns,
            show="headings",
            style="Stock.Treeview",
            selectmode="browse",
        )

        tree.heading("id", text="ID")
        tree.heading("nom", text="Nom")
        tree.heading("categorie", text="Catégorie")
        tree.heading("quantite", text="Qté")
        tree.heading("seuil", text="Seuil")
        tree.heading("unite", text="Unité")
        tree.heading("prix", text="Prix (€)")
        tree.heading("tags", text="Tags")

        tree.column("id", width=50, anchor="center", stretch=False)
        tree.column("nom", width=230)
        tree.column("categorie", width=180)
        tree.column("quantite", width=70, anchor="center")
        tree.column("seuil", width=70, anchor="center")
        tree.column("unite", width=120)
        tree.column("prix", width=90, anchor="e")
        tree.column("tags", width=220)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.bind("<Double-1>", self._on_double_clic)

        # Boutons d'action
        frame_actions = ctk.CTkFrame(parent, fg_color="transparent")
        frame_actions.pack(fill="x", padx=5, pady=(0, 5))

        colors = app_theme.COLORS
        fonts = app_theme.FONTS

        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier_selection,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="📋 Mouvements",
            width=130,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_mouvements,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="📦 Lots",
            width=100,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_lots,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_actions,
            text="🗄️ Archiver",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._archiver_selection,
        ).pack(side="left", padx=5)

        return tree

    # ── Chargement ────────────────────────────────────────────────────────────

    def _charger_categories(self) -> None:
        try:
            self._categories = get_all_categories()
        except Exception as exc:
            logger.exception("Erreur chargement catégories : %s", exc)
            self._categories = []

        cat_labels = self._build_cat_filter_labels()
        self._combo_filtre_cat.configure(values=["Toutes"] + cat_labels)

    def _build_cat_filter_labels(self) -> list[str]:
        labels = []
        for c in self._categories:
            if c.get("parent_nom"):
                labels.append(f"{c['parent_nom']} > {c['nom']}")
            else:
                labels.append(c["nom"])
        return labels

    def _charger_articles(self) -> None:
        try:
            self._tous_les_articles = get_all_articles(
                include_archives=self._afficher_archives.get()
            )
        except Exception as exc:
            logger.exception("Erreur chargement articles : %s", exc)
            self._tous_les_articles = []
        self._afficher_liste()

    def _afficher_liste(self) -> None:
        terme = self._recherche_var.get().strip().lower()
        filtre_cat = self._filtre_categorie_var.get()

        self._tree.delete(*self._tree.get_children())
        self._tree.tag_configure("alerte", foreground="#ff4444")
        self._tree.tag_configure("archive", foreground="#888888")

        articles_affiches = []
        nb_alertes = 0

        for a in self._tous_les_articles:
            # Filtre texte
            if terme:
                champs = (
                    (a.get("nom") or "").lower(),
                    (a.get("categorie_nom") or "").lower(),
                )
                if not any(terme in c for c in champs):
                    continue

            # Filtre catégorie
            if filtre_cat != "Toutes":
                cat_label = ""
                parent_nom = None
                for c in self._categories:
                    if c["id"] == a.get("categorie_id"):
                        parent_nom = c.get("parent_nom")
                        if parent_nom:
                            cat_label = f"{parent_nom} > {c['nom']}"
                        else:
                            cat_label = c["nom"]
                        break
                if cat_label != filtre_cat:
                    continue

            articles_affiches.append(a)

            quantite = a.get("quantite", 0) or 0
            seuil = a.get("seuil_alerte", 0) or 0
            is_alerte = quantite < seuil and not a.get("statut_archive")
            if is_alerte:
                nb_alertes += 1

            if a.get("statut_archive"):
                tag = "archive"
            elif is_alerte:
                tag = "alerte"
            else:
                tag = ""

            prix = a.get("prix_achat", 0.0) or 0.0
            prix_str = f"{prix:.2f}" if prix else ""

            self._tree.insert(
                "",
                "end",
                iid=str(a["id"]),
                values=(
                    a["id"],
                    a.get("nom", ""),
                    a.get("categorie_nom", "") or "",
                    quantite,
                    seuil,
                    a.get("unite_nom", "") or "",
                    prix_str,
                    ", ".join(t.get("nom", "") for t in get_article_tags(a["id"])) or "—",
                ),
                tags=(tag,),
            )

        # Mise à jour compteur
        total = len(articles_affiches)
        texte = f"Total : {total} article{'s' if total > 1 else ''}"
        if nb_alertes > 0:
            texte += f"  │  ⚠️ {nb_alertes} article{'s' if nb_alertes > 1 else ''} sous le seuil d'alerte"
        self._label_total.configure(text=texte)

    # ── Événements ────────────────────────────────────────────────────────────

    def _on_recherche_change(self, *_args: Any) -> None:
        self._afficher_liste()

    def _on_toggle_archives(self) -> None:
        self._charger_articles()

    def _on_double_clic(self, _event: Any) -> None:
        self._ouvrir_mouvements()

    def _get_article_selectionne(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            return None
        article_id = int(sel[0])
        return next((a for a in self._tous_les_articles if a["id"] == article_id), None)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _ouvrir_formulaire_ajout(self) -> None:
        from ui.modules.stock.formulaire_article import FormulaireArticle

        form = FormulaireArticle(self, article=None)
        form.grab_set()
        self.wait_window(form)
        self._charger_categories()
        self._charger_articles()

    def _ouvrir_formulaire_entree(self) -> None:
        from ui.modules.stock.formulaire_entree import FormulaireEntreeMarchandise

        form = FormulaireEntreeMarchandise(self)
        form.grab_set()
        self.wait_window(form)
        self._charger_categories()
        self._charger_articles()

    def _modifier_selection(self) -> None:
        article = self._get_article_selectionne()
        if not article:
            return
        from ui.modules.stock.formulaire_article import FormulaireArticle

        form = FormulaireArticle(self, article=article)
        form.grab_set()
        self.wait_window(form)
        self._charger_categories()
        self._charger_articles()

    def _ouvrir_mouvements(self) -> None:
        article = self._get_article_selectionne()
        if not article:
            return
        from ui.modules.stock.mouvements import MouvementsStock

        fenetre = MouvementsStock(self, article=article)
        fenetre.grab_set()
        self.wait_window(fenetre)
        self._charger_articles()

    def _ouvrir_lots(self) -> None:
        article = self._get_article_selectionne()
        if not article:
            return
        from ui.modules.stock.liste_lots import ListeLotsArticle

        fenetre = ListeLotsArticle(self, article=article)
        fenetre.grab_set()
        self.wait_window(fenetre)
        self._charger_articles()

    def _archiver_selection(self) -> None:
        article = self._get_article_selectionne()
        if not article:
            return
        confirme = demander_confirmation(
            self,
            "Archiver l'article",
            f"Archiver « {article.get('nom', '')} » ?\n"
            "L'article ne sera plus visible dans la liste principale mais ses données sont conservées.",
        )
        if confirme:
            try:
                archiver_article(article["id"])
                self._charger_articles()
            except Exception as exc:
                logger.exception("Erreur lors de l'archivage de l'article %s : %s", article["id"], exc)

    def _ouvrir_referentiels(self) -> None:
        from ui.modules.stock.referentiels import Referentiels

        fenetre = Referentiels(self)
        fenetre.grab_set()
        self.wait_window(fenetre)
        self._charger_categories()
        self._charger_articles()

    def _ouvrir_inventaires(self) -> None:
        from ui.modules.buvette.inventaires import OngletInventaires

        fenetre = ctk.CTkToplevel(self)
        fenetre.title("📋 Inventaires de stock")
        fenetre.geometry("900x560")
        fenetre.transient(self)
        fenetre.grab_set()
        onglet = OngletInventaires(fenetre)
        onglet.pack(fill="both", expand=True)
