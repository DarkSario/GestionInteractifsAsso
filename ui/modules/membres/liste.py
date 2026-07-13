"""Fenêtre de liste des membres (adhérents)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.models.membres import archiver_membre, get_all_membres
from ui import theme as app_theme
from ui.components.dialogs import demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class ListeMembres(ctk.CTkToplevel):
    """Fenêtre de gestion des membres de l'association."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("👥 Gestion des Membres")
        self.geometry("900x600")
        self.minsize(700, 450)
        self.transient(parent)

        # Données en mémoire
        self._tous_les_membres: list[dict] = []
        self._afficher_archives = tk.BooleanVar(value=False)
        self._recherche_var = tk.StringVar()
        self._recherche_var.trace_add("write", self._on_recherche_change)

        self._build_ui()
        self._charger_membres()

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # ── En-tête ───────────────────────────────────────────────────────────
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            frame_header,
            text="👥 Gestion des Membres",
            font=fonts.get("title"),
        ).pack(side="left")

        ctk.CTkButton(
            frame_header,
            text="+ Ajouter",
            width=110,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire_ajout,
        ).pack(side="right")

        # ── Barre de recherche ────────────────────────────────────────────────
        frame_search = ctk.CTkFrame(self, fg_color="transparent")
        frame_search.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(
            frame_search,
            text="🔍",
            font=fonts.get("normal"),
        ).pack(side="left", padx=(0, 5))

        ctk.CTkEntry(
            frame_search,
            textvariable=self._recherche_var,
            placeholder_text="Rechercher par nom, prénom ou statut…",
            width=350,
            font=fonts.get("normal"),
        ).pack(side="left")

        ctk.CTkCheckBox(
            frame_search,
            text="Archivés",
            variable=self._afficher_archives,
            command=self._on_toggle_archives,
            font=fonts.get("normal"),
        ).pack(side="left", padx=(20, 0))

        # ── Tableau ───────────────────────────────────────────────────────────
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=15, pady=5)

        self._tree = self._build_treeview(frame_table)

        # ── Pied de page ──────────────────────────────────────────────────────
        self._label_total = ctk.CTkLabel(
            self,
            text="",
            font=fonts.get("small"),
            anchor="w",
        )
        self._label_total.pack(fill="x", padx=15, pady=(0, 10))

    def _build_treeview(self, parent: ctk.CTkFrame) -> ttk.Treeview:
        """Crée et configure le ttk.Treeview avec scrollbar."""
        columns = ("id", "nom", "prenom", "statut", "date_adhesion")

        style = ttk.Style()
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            bg = "#2b2b2b"
            fg = "#ffffff"
            selected_bg = "#1f6aa5"
            heading_bg = "#1a1a2e"
        else:
            bg = "#f0f0f0"
            fg = "#000000"
            selected_bg = "#1f6aa5"
            heading_bg = "#d0d0d0"

        style.theme_use("default")
        style.configure(
            "Membres.Treeview",
            background=bg,
            foreground=fg,
            rowheight=28,
            fieldbackground=bg,
            font=("Arial", 12),
        )
        style.configure(
            "Membres.Treeview.Heading",
            background=heading_bg,
            foreground=fg,
            font=("Arial", 12, "bold"),
        )
        style.map(
            "Membres.Treeview",
            background=[("selected", selected_bg)],
            foreground=[("selected", "#ffffff")],
        )

        frame_tree = tk.Frame(parent, bg=bg)
        frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(
            frame_tree,
            columns=columns,
            show="headings",
            style="Membres.Treeview",
            selectmode="browse",
        )

        tree.heading("id", text="ID")
        tree.heading("nom", text="Nom")
        tree.heading("prenom", text="Prénom")
        tree.heading("statut", text="Statut")
        tree.heading("date_adhesion", text="Date adhésion")

        tree.column("id", width=50, anchor="center", stretch=False)
        tree.column("nom", width=180)
        tree.column("prenom", width=150)
        tree.column("statut", width=200)
        tree.column("date_adhesion", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Colonne fictive pour les boutons — on utilise les événements de clic
        tree.bind("<Double-1>", self._on_double_clic)

        # Ajout des boutons d'action via frame de boutons (hors Treeview)
        self._frame_actions = ctk.CTkFrame(parent, fg_color="transparent")
        self._frame_actions.pack(fill="x", padx=5, pady=(0, 5))

        colors = app_theme.COLORS
        fonts = app_theme.FONTS

        ctk.CTkButton(
            self._frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier_selection,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self._frame_actions,
            text="🗑️ Archiver",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._archiver_selection,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            self._frame_actions,
            text="💳 Cotisations",
            width=130,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_cotisations,
        ).pack(side="left", padx=5)

        return tree

    # ── Chargement et affichage des données ───────────────────────────────────

    def _charger_membres(self) -> None:
        """Recharge les membres depuis la base de données."""
        try:
            self._tous_les_membres = get_all_membres(
                include_archives=self._afficher_archives.get()
            )
        except Exception as exc:
            logger.exception("Erreur lors du chargement des membres : %s", exc)
            self._tous_les_membres = []
        self._afficher_liste()

    def _afficher_liste(self) -> None:
        """Filtre et affiche la liste des membres dans le Treeview."""
        terme = self._recherche_var.get().strip().lower()

        self._tree.delete(*self._tree.get_children())

        membres_affiches = []
        for m in self._tous_les_membres:
            if terme:
                champs = (
                    (m.get("nom") or "").lower(),
                    (m.get("prenom") or "").lower(),
                    (m.get("statut") or "").lower(),
                )
                if not any(terme in c for c in champs):
                    continue

            membres_affiches.append(m)
            tag = "archive" if m.get("statut_archive") else ""
            self._tree.insert(
                "",
                "end",
                iid=str(m["id"]),
                values=(
                    m["id"],
                    m.get("nom", ""),
                    m.get("prenom", ""),
                    m.get("statut", ""),
                    self._formater_date(m.get("date_adhesion", "")),
                ),
                tags=(tag,),
            )

        # Style pour les membres archivés
        self._tree.tag_configure("archive", foreground="#888888")

        self._mettre_a_jour_compteur(membres_affiches)

    def _mettre_a_jour_compteur(self, membres_affiches: list[dict]) -> None:
        actifs = sum(1 for m in membres_affiches if not m.get("statut_archive"))
        archives = sum(1 for m in membres_affiches if m.get("statut_archive"))

        def pluriel(n: int, mot: str) -> str:
            return f"{n} {mot}{'s' if n > 1 else ''}"

        if self._afficher_archives.get() and archives > 0:
            texte = (
                f"Total : {pluriel(actifs, 'membre')} actif{'s' if actifs > 1 else ''}, "
                f"{pluriel(archives, 'archivé')}"
            )
        else:
            texte = f"Total : {pluriel(actifs, 'membre')} actif{'s' if actifs > 1 else ''}"
        self._label_total.configure(text=texte)

    # ── Événements ────────────────────────────────────────────────────────────

    def _on_recherche_change(self, *_args: Any) -> None:
        self._afficher_liste()

    def _on_toggle_archives(self) -> None:
        self._charger_membres()

    def _on_double_clic(self, _event: Any) -> None:
        self._modifier_selection()

    def _get_membre_selectionne(self) -> dict | None:
        selection = self._tree.selection()
        if not selection:
            return None
        membre_id = int(selection[0])
        return next((m for m in self._tous_les_membres if m["id"] == membre_id), None)

    def _modifier_selection(self) -> None:
        membre = self._get_membre_selectionne()
        if not membre:
            return
        self._ouvrir_formulaire_edition(membre)

    def _archiver_selection(self) -> None:
        membre = self._get_membre_selectionne()
        if not membre:
            return

        nom_complet = f"{membre.get('prenom', '')} {membre.get('nom', '')}".strip()
        confirme = demander_confirmation(
            self,
            "Archiver le membre",
            f"Voulez-vous archiver {nom_complet} ?\n"
            "Il ne sera plus visible dans la liste principale mais ses données sont conservées.",
        )
        if confirme:
            try:
                archiver_membre(membre["id"])
                self._charger_membres()
            except Exception as exc:
                logger.exception("Erreur lors de l'archivage du membre %s : %s", membre["id"], exc)

    # ── Formulaire ────────────────────────────────────────────────────────────

    def _ouvrir_formulaire_ajout(self) -> None:
        from ui.modules.membres.formulaire import FormulaireMembreModal

        form = FormulaireMembreModal(self, membre=None)
        form.grab_set()
        self.wait_window(form)
        self._charger_membres()

    def _ouvrir_formulaire_edition(self, membre: dict) -> None:
        from ui.modules.membres.formulaire import FormulaireMembreModal

        form = FormulaireMembreModal(self, membre=membre)
        form.grab_set()
        self.wait_window(form)
        self._charger_membres()

    def _ouvrir_cotisations(self) -> None:
        from ui.modules.membres.cotisations import GestionCotisations

        fenetre = GestionCotisations(self)
        self.wait_window(fenetre)

    # ── Utilitaires ───────────────────────────────────────────────────────────

    @staticmethod
    def _formater_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            from datetime import datetime

            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value or ""
