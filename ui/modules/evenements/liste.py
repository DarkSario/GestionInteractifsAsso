"""Fenêtre liste des événements."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.models.evenements import get_all_evenements
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur

COULEURS_STATUT = {
    "planifie": "#1a7abf",
    "en_cours": "#28a745",
    "termine": "#6c757d",
    "annule": "#dc3545",
}

LABELS_STATUT = {
    "planifie": "Planifié",
    "en_cours": "En cours",
    "termine": "Terminé",
    "annule": "Annulé",
    "": "Tous",
}


class ListeEvenements(ctk.CTkToplevel):
    """Fenêtre principale de gestion des événements."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("🎪 Événements")
        self.geometry("1000x640")
        self.minsize(800, 500)
        self.transient(parent)

        self._evenements: list[dict] = []
        self._filtre_statut = tk.StringVar(value="")
        self._recherche_var = tk.StringVar()
        self._recherche_var.trace_add("write", self._on_recherche)

        self._build_ui()
        self._charger_donnees()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # Titre
        ctk.CTkLabel(
            self,
            text="🎪 Événements",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=16, pady=(14, 6))

        # Barre d'outils
        frame_top = ctk.CTkFrame(self, fg_color="transparent")
        frame_top.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            frame_top,
            text="+ Nouvel événement",
            width=160,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._nouveau,
        ).pack(side="left")

        # Filtre statut
        ctk.CTkLabel(frame_top, text="Statut :").pack(side="left", padx=(20, 4))
        self._combo_statut = ctk.CTkOptionMenu(
            frame_top,
            values=list(LABELS_STATUT.values()),
            command=self._on_filtre_statut,
            width=140,
        )
        self._combo_statut.set("Tous")
        self._combo_statut.pack(side="left")

        # Recherche
        ctk.CTkEntry(
            frame_top,
            textvariable=self._recherche_var,
            placeholder_text="🔍 Rechercher...",
            width=220,
        ).pack(side="right")

        # Tableau
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._tree = ttk.Treeview(
            frame_table,
            columns=("id", "nom", "type", "date", "recettes", "depenses", "statut"),
            show="headings",
            height=18,
        )
        self._tree.heading("id", text="ID")
        self._tree.heading("nom", text="Nom")
        self._tree.heading("type", text="Type")
        self._tree.heading("date", text="Date début")
        self._tree.heading("recettes", text="Recettes")
        self._tree.heading("depenses", text="Dépenses")
        self._tree.heading("statut", text="Statut")

        self._tree.column("id", width=55, anchor="center", stretch=False)
        self._tree.column("nom", width=330)
        self._tree.column("type", width=160)
        self._tree.column("date", width=110, anchor="center")
        self._tree.column("recettes", width=120, anchor="e")
        self._tree.column("depenses", width=120, anchor="e")
        self._tree.column("statut", width=110, anchor="center")

        for code, couleur in COULEURS_STATUT.items():
            self._tree.tag_configure(code, foreground=couleur)

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", self._on_double_click)

        # Bouton voir
        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkButton(
            frame_actions,
            text="👁️  Ouvrir la fiche",
            width=160,
            command=self._ouvrir_fiche,
        ).pack(side="left")

        ctk.CTkButton(
            frame_actions,
            text="Rafraîchir",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self._charger_donnees,
        ).pack(side="left", padx=(8, 0))

    # ── Données ───────────────────────────────────────────────────────────────

    def _charger_donnees(self) -> None:
        try:
            self._evenements = get_all_evenements()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de charger les événements :\n{exc}")
            self._evenements = []
        self._rafraichir_table()

    def _rafraichir_table(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)

        statut_label = self._combo_statut.get()
        statut_filtre = next(
            (k for k, v in LABELS_STATUT.items() if v == statut_label), ""
        )
        recherche = self._recherche_var.get().strip().lower()

        for evt in self._evenements:
            if statut_filtre and evt["statut"] != statut_filtre:
                continue
            if recherche and recherche not in (evt["nom"] or "").lower():
                if recherche not in (evt["type"] or "").lower():
                    continue

            date_affich = self._format_date(evt.get("date_debut", ""))
            statut_label_evt = LABELS_STATUT.get(evt["statut"], evt["statut"])
            tag = evt["statut"]

            self._tree.insert(
                "",
                "end",
                values=(
                    evt["id"],
                    evt["nom"] or "",
                    evt["type"] or "",
                    date_affich,
                    self._format_montant(evt.get("total_recettes", 0)),
                    self._format_montant(evt.get("total_depenses", 0)),
                    statut_label_evt,
                ),
                tags=(tag,),
            )

    # ── Événements UI ─────────────────────────────────────────────────────────

    def _on_recherche(self, *_) -> None:
        self._rafraichir_table()

    def _on_filtre_statut(self, _value: str) -> None:
        self._rafraichir_table()

    def _on_double_click(self, _event: Any) -> None:
        self._ouvrir_fiche()

    def _nouveau(self) -> None:
        from ui.modules.evenements.fiche import FicheEvenement

        fiche = FicheEvenement(self, evenement_id=None)
        fiche.grab_set()
        self.wait_window(fiche)
        self._charger_donnees()

    def _ouvrir_fiche(self) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        valeurs = self._tree.item(selection[0], "values")
        if not valeurs:
            return
        evt_id = int(valeurs[0])

        from ui.modules.evenements.fiche import FicheEvenement

        fiche = FicheEvenement(self, evenement_id=evt_id)
        fiche.grab_set()
        self.wait_window(fiche)
        self._charger_donnees()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return value or ""

    @staticmethod
    def _format_montant(value: float | int | str) -> str:
        try:
            montant = float(value or 0)
        except (TypeError, ValueError):
            montant = 0.0
        return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")
