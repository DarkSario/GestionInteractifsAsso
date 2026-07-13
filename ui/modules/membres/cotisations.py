"""Sous-onglet Cotisations dans la fiche/liste des adhérents (Phase 16)."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.models.cotisations import (
    add_cotisation,
    delete_cotisation,
    get_cotisations_adherent,
    get_cotisations_exercice,
    get_stats_cotisations,
    update_cotisation,
)
from core.cotisations import (
    get_annee_courante,
    get_montant_cotisation_defaut,
    renouveler_annee_courante,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)

_STATUTS_COULEURS = {
    "offerte": "grey",
    "payee": "#27ae60",
    "en_attente": "#e67e22",
}
_STATUTS_LIBELLES = {
    "offerte": "Offerte",
    "payee": "Payée",
    "en_attente": "En attente",
}


class OngletCotisationsAdherent(ctk.CTkFrame):
    """Onglet Cotisations pour la fiche d'un adhérent."""

    def __init__(self, parent: Any, adherent_id: int, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._adherent_id = adherent_id
        self._cotisations: list[dict] = []
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # En-tête avec bouton ajouter
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(
            frame_header,
            text="💳 Cotisations",
            font=fonts.get("subtitle"),
        ).pack(side="left")
        ctk.CTkButton(
            frame_header,
            text="+ Ajouter cotisation",
            width=160,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter,
        ).pack(side="right")

        # Tableau
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=8, pady=4)
        self._tree = self._build_treeview(frame_table)

        # Boutons actions
        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer,
        ).pack(side="left", padx=5)

    def _build_treeview(self, parent: ctk.CTkFrame) -> ttk.Treeview:
        columns = ("annee", "montant", "statut", "date_paiement", "mode", "commentaire")

        style = ttk.Style()
        appearance = ctk.get_appearance_mode()
        bg = "#2b2b2b" if appearance == "Dark" else "#f0f0f0"
        fg = "#ffffff" if appearance == "Dark" else "#000000"

        style.configure(
            "Cotisations.Treeview",
            background=bg,
            foreground=fg,
            rowheight=26,
            fieldbackground=bg,
            font=("Arial", 11),
        )
        style.configure(
            "Cotisations.Treeview.Heading",
            background="#1a1a2e" if appearance == "Dark" else "#d0d0d0",
            foreground=fg,
            font=("Arial", 11, "bold"),
        )

        frame_tree = tk.Frame(parent, bg=bg)
        frame_tree.pack(fill="both", expand=True, padx=4, pady=4)

        tree = ttk.Treeview(
            frame_tree,
            columns=columns,
            show="headings",
            style="Cotisations.Treeview",
            selectmode="browse",
            height=8,
        )
        tree.heading("annee", text="Année")
        tree.heading("montant", text="Montant")
        tree.heading("statut", text="Statut")
        tree.heading("date_paiement", text="Date paiement")
        tree.heading("mode", text="Mode")
        tree.heading("commentaire", text="Commentaire")

        tree.column("annee", width=70, anchor="center")
        tree.column("montant", width=90, anchor="e")
        tree.column("statut", width=100, anchor="center")
        tree.column("date_paiement", width=110, anchor="center")
        tree.column("mode", width=100)
        tree.column("commentaire", width=200)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.bind("<Double-1>", lambda _e: self._modifier())
        return tree

    def _charger(self) -> None:
        self._cotisations = get_cotisations_adherent(self._adherent_id)
        self._tree.delete(*self._tree.get_children())
        for c in self._cotisations:
            statut = c.get("statut", "offerte")
            libelle = _STATUTS_LIBELLES.get(statut, statut)
            montant = float(c.get("montant") or 0)
            self._tree.insert(
                "", "end",
                iid=str(c["id"]),
                values=(
                    c.get("annee", ""),
                    f"{montant:.2f} €",
                    libelle,
                    c.get("date_paiement") or "",
                    c.get("mode_paiement") or "",
                    c.get("commentaire") or "",
                ),
                tags=(statut,),
            )
        # Couleurs par statut
        for statut, couleur in _STATUTS_COULEURS.items():
            self._tree.tag_configure(statut, foreground=couleur)

    def _get_selection(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            return None
        cot_id = int(sel[0])
        return next((c for c in self._cotisations if c["id"] == cot_id), None)

    def _ajouter(self) -> None:
        _FormulaireCotisation(self, adherent_id=self._adherent_id, on_save=self._charger)

    def _modifier(self) -> None:
        c = self._get_selection()
        if not c:
            return
        _FormulaireCotisation(self, cotisation=c, on_save=self._charger)

    def _supprimer(self) -> None:
        c = self._get_selection()
        if not c:
            return
        if demander_confirmation(
            self,
            "Supprimer la cotisation",
            f"Supprimer la cotisation {c.get('annee')} ?"
        ):
            delete_cotisation(c["id"])
            self._charger()


class GestionCotisations(ctk.CTkToplevel):
    """Fenêtre de gestion des cotisations (vue globale par année)."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("💳 Cotisations Adhérents")
        self.geometry("1000x640")
        self.minsize(800, 500)
        self.transient(parent)

        self._annee_var = ctk.IntVar(value=get_annee_courante())
        self._cotisations: list[dict] = []
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # En-tête
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(
            frame_header,
            text="💳 Cotisations Adhérents",
            font=fonts.get("title"),
        ).pack(side="left")

        # Sélecteur d'année
        f_annee = ctk.CTkFrame(frame_header, fg_color="transparent")
        f_annee.pack(side="right")
        ctk.CTkLabel(f_annee, text="Année :", font=fonts.get("normal")).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(f_annee, textvariable=self._annee_var, width=70).pack(side="left")
        ctk.CTkButton(
            f_annee,
            text="🔄",
            width=40,
            font=fonts.get("normal"),
            command=self._charger,
        ).pack(side="left", padx=(4, 0))

        # Statistiques
        self._frame_stats = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_stats.pack(fill="x", padx=15, pady=(0, 4))

        # Bouton renouveler en masse
        frame_actions_top = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions_top.pack(fill="x", padx=15, pady=(0, 4))
        ctk.CTkButton(
            frame_actions_top,
            text="🔄 Renouveler en masse",
            width=200,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._renouveler_masse,
        ).pack(side="left")

        # Tableau
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=15, pady=4)
        self._tree = self._build_treeview(frame_table)

        # Actions bas
        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkButton(
            frame_actions,
            text="✏️ Modifier",
            width=110,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._modifier,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=110,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer,
        ).pack(side="left", padx=5)

    def _build_treeview(self, parent: ctk.CTkFrame) -> ttk.Treeview:
        columns = ("id", "nom", "prenom", "montant", "statut", "date_paiement", "mode")

        style = ttk.Style()
        appearance = ctk.get_appearance_mode()
        bg = "#2b2b2b" if appearance == "Dark" else "#f0f0f0"
        fg = "#ffffff" if appearance == "Dark" else "#000000"

        style.configure(
            "CotisationsGlobal.Treeview",
            background=bg,
            foreground=fg,
            rowheight=26,
            fieldbackground=bg,
            font=("Arial", 11),
        )
        style.configure(
            "CotisationsGlobal.Treeview.Heading",
            background="#1a1a2e" if appearance == "Dark" else "#d0d0d0",
            foreground=fg,
            font=("Arial", 11, "bold"),
        )

        frame_tree = tk.Frame(parent, bg=bg)
        frame_tree.pack(fill="both", expand=True, padx=4, pady=4)

        tree = ttk.Treeview(
            frame_tree,
            columns=columns,
            show="headings",
            style="CotisationsGlobal.Treeview",
            selectmode="browse",
        )
        tree.heading("id", text="ID")
        tree.heading("nom", text="Nom")
        tree.heading("prenom", text="Prénom")
        tree.heading("montant", text="Montant")
        tree.heading("statut", text="Statut")
        tree.heading("date_paiement", text="Date paiement")
        tree.heading("mode", text="Mode")

        tree.column("id", width=50, anchor="center", stretch=False)
        tree.column("nom", width=160)
        tree.column("prenom", width=130)
        tree.column("montant", width=90, anchor="e")
        tree.column("statut", width=100, anchor="center")
        tree.column("date_paiement", width=110, anchor="center")
        tree.column("mode", width=120)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for statut, couleur in _STATUTS_COULEURS.items():
            tree.tag_configure(statut, foreground=couleur)

        tree.bind("<Double-1>", lambda _e: self._modifier())
        return tree

    def _charger(self) -> None:
        annee = self._annee_var.get()
        self._cotisations = get_cotisations_exercice(annee)

        # Stats
        for w in self._frame_stats.winfo_children():
            w.destroy()
        stats = get_stats_cotisations(annee)
        texte = (
            f"Total : {stats['total']} | "
            f"Payées : {stats['nb_payees']} | "
            f"Offertes : {stats['nb_offertes']} | "
            f"En attente : {stats['nb_en_attente']} | "
            f"Montant collecté : {stats['montant_paye']:.2f} €"
        )
        ctk.CTkLabel(
            self._frame_stats,
            text=texte,
            font=app_theme.FONTS.get("small"),
            text_color="grey",
        ).pack(anchor="w")

        self._tree.delete(*self._tree.get_children())
        for c in self._cotisations:
            statut = c.get("statut", "offerte")
            libelle = _STATUTS_LIBELLES.get(statut, statut)
            montant = float(c.get("montant") or 0)
            self._tree.insert(
                "", "end",
                iid=str(c["id"]),
                values=(
                    c.get("adherent_id", ""),
                    c.get("nom", ""),
                    c.get("prenom", ""),
                    f"{montant:.2f} €",
                    libelle,
                    c.get("date_paiement") or "",
                    c.get("mode_paiement") or "",
                ),
                tags=(statut,),
            )

    def _get_selection(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            return None
        cot_id = int(sel[0])
        return next((c for c in self._cotisations if c["id"] == cot_id), None)

    def _modifier(self) -> None:
        c = self._get_selection()
        if not c:
            return
        _FormulaireCotisation(self, cotisation=c, on_save=self._charger)

    def _supprimer(self) -> None:
        c = self._get_selection()
        if not c:
            return
        nom = f"{c.get('prenom', '')} {c.get('nom', '')}".strip()
        if demander_confirmation(
            self,
            "Supprimer la cotisation",
            f"Supprimer la cotisation {c.get('annee')} de {nom} ?",
        ):
            delete_cotisation(c["id"])
            self._charger()

    def _renouveler_masse(self) -> None:
        annee = self._annee_var.get()
        montant_defaut = get_montant_cotisation_defaut()
        msg = (
            f"Créer les cotisations {annee} pour tous les adhérents actifs\n"
            f"qui n'en ont pas encore ?\n\n"
            f"Montant par défaut : {montant_defaut:.2f} €\n"
            f"(0 € = cotisation offerte)"
        )
        if not demander_confirmation(self, "Renouveler en masse", msg):
            return
        nb = renouveler_annee_courante(annee=annee)
        afficher_info(self, "Succès", f"{nb} cotisation(s) créée(s) pour {annee}.")
        self._charger()


# ── Formulaire ajout/modification ─────────────────────────────────────────────


class _FormulaireCotisation(ctk.CTkToplevel):
    """Fenêtre modale pour ajouter ou modifier une cotisation."""

    def __init__(
        self,
        parent: Any,
        cotisation: dict | None = None,
        adherent_id: int | None = None,
        on_save=None,
    ) -> None:
        super().__init__(parent)
        self.title("✏️ Cotisation" if cotisation else "+ Ajouter une cotisation")
        self.geometry("440x360")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._cotisation = cotisation
        self._adherent_id = adherent_id or (cotisation["adherent_id"] if cotisation else None)
        self._on_save = on_save

        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=8)

        def champ(label: str, var: ctk.Variable, placeholder: str = "") -> ctk.CTkEntry:
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=130, anchor="ne").pack(side="left", padx=(0, 8))
            entry = ctk.CTkEntry(f, textvariable=var, width=240, placeholder_text=placeholder)
            entry.pack(side="left", fill="x", expand=True)
            return entry

        self._annee_var = ctk.StringVar(value=str(cotisation["annee"] if cotisation else get_annee_courante()))
        self._montant_var = ctk.StringVar(value=str(cotisation["montant"] if cotisation else f"{get_montant_cotisation_defaut():.2f}"))
        self._date_var = ctk.StringVar(value=cotisation.get("date_paiement") or "" if cotisation else "")
        self._mode_var = ctk.StringVar(value=cotisation.get("mode_paiement") or "" if cotisation else "")
        self._commentaire_var = ctk.StringVar(value=cotisation.get("commentaire") or "" if cotisation else "")

        champ("Année *", self._annee_var, "2026")
        champ("Montant (€) *", self._montant_var, "0.00")

        # Statut
        f_statut = ctk.CTkFrame(frame, fg_color="transparent")
        f_statut.pack(fill="x", pady=3)
        ctk.CTkLabel(f_statut, text="Statut *", width=130, anchor="ne").pack(side="left", padx=(0, 8))
        self._statut_var = ctk.StringVar(
            value=cotisation.get("statut", "offerte") if cotisation else "offerte"
        )
        ctk.CTkOptionMenu(
            f_statut,
            variable=self._statut_var,
            values=["offerte", "payee", "en_attente"],
            width=200,
        ).pack(side="left")

        champ("Date paiement", self._date_var, "AAAA-MM-JJ")
        champ("Mode paiement", self._mode_var, "ex. espèces, chèque…")
        champ("Commentaire", self._commentaire_var, "")

        f_btn = ctk.CTkFrame(frame, fg_color="transparent")
        f_btn.pack(fill="x", pady=(12, 4))
        ctk.CTkButton(
            f_btn, text="Annuler", width=80, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            f_btn, text="💾 Enregistrer", width=140, command=self._enregistrer
        ).pack(side="right")

    def _enregistrer(self) -> None:
        try:
            annee = int(self._annee_var.get().strip())
        except ValueError:
            afficher_erreur(self, "Erreur", "L'année doit être un entier.")
            return
        try:
            montant = float(self._montant_var.get().strip().replace(",", "."))
        except ValueError:
            afficher_erreur(self, "Erreur", "Le montant doit être un nombre.")
            return
        statut = self._statut_var.get()
        if montant == 0.0:
            statut = "offerte"

        kwargs = dict(
            annee=annee,
            montant=montant,
            statut=statut,
            date_paiement=self._date_var.get().strip() or None,
            mode_paiement=self._mode_var.get().strip() or None,
            commentaire=self._commentaire_var.get().strip() or None,
        )

        if self._cotisation:
            update_cotisation(self._cotisation["id"], **kwargs)
        else:
            add_cotisation(adherent_id=self._adherent_id, **kwargs)

        if self._on_save:
            self._on_save()
        self.destroy()
