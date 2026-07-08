"""Fenêtre principale du module Trésorerie."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import (
    CATEGORIES_DEPENSE,
    MOYENS_PAIEMENT,
    STATUTS_REGLEMENT,
    TYPES_DON,
    TYPES_MOUVEMENT_BANQUE,
    calculer_bilan,
    valider_depense,
    valider_don,
    valider_mouvement_banque,
    valider_retrocession,
)
from db.models.tresorerie import (
    add_depot_retrait,
    add_depense_diverse,
    add_depense_reguliere,
    add_don,
    add_retrocession,
    delete_depot_retrait,
    delete_depense_diverse,
    delete_depense_reguliere,
    delete_don,
    delete_retrocession,
    get_all_depenses_diverses,
    get_all_depenses_regulieres,
    get_all_depots_retraits,
    get_all_dons,
    get_all_retrocessions,
    get_journal_general,
    update_depot_retrait,
    update_depense_diverse,
    update_depense_reguliere,
    update_don,
)
from ui import theme as app_theme
from ui.components.dialogs import (
    afficher_erreur,
    afficher_info,
    demander_confirmation,
)

_AUJOURD_HUI = date.today().strftime("%Y-%m-%d")
_ANNEE_COURANTE = str(date.today().year)


def _fmt(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "\u202f").replace(".", ",")


def _safe_float(text: str) -> float:
    try:
        return float(str(text).replace(",", ".").replace("\u202f", "").replace(" ", ""))
    except (TypeError, ValueError):
        return 0.0


# ── Fenêtre principale ────────────────────────────────────────────────────────


class ListeTresorerie(ctk.CTkToplevel):
    """Fenêtre principale du module Trésorerie avec onglets."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("💰 Trésorerie")
        self.geometry("1200x760")
        self.minsize(980, 620)
        self.transient(parent)

        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            header, text="💰 Trésorerie", font=fonts.get("title")
        ).pack(side="left")

        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        for tab_name in [
            "📊 Résumé",
            "🎁 Dons & Subventions",
            "📤 Dépenses régulières",
            "📤 Dépenses diverses",
            "🏦 Banque",
            "🔄 Rétrocessions",
            "📋 Journal",
        ]:
            self._tabs.add(tab_name)

        self._onglet_resume = OngletResume(self._tabs.tab("📊 Résumé"))
        self._onglet_resume.pack(fill="both", expand=True)

        self._onglet_dons = OngletDons(self._tabs.tab("🎁 Dons & Subventions"))
        self._onglet_dons.pack(fill="both", expand=True)

        self._onglet_dep_reg = OngletDepenses(
            self._tabs.tab("📤 Dépenses régulières"),
            table="reguliere",
        )
        self._onglet_dep_reg.pack(fill="both", expand=True)

        self._onglet_dep_div = OngletDepenses(
            self._tabs.tab("📤 Dépenses diverses"),
            table="diverse",
        )
        self._onglet_dep_div.pack(fill="both", expand=True)

        self._onglet_banque = OngletBanque(self._tabs.tab("🏦 Banque"))
        self._onglet_banque.pack(fill="both", expand=True)

        self._onglet_retro = OngletRetrocessions(self._tabs.tab("🔄 Rétrocessions"))
        self._onglet_retro.pack(fill="both", expand=True)

        self._onglet_journal = OngletJournal(self._tabs.tab("📋 Journal"))
        self._onglet_journal.pack(fill="both", expand=True)

        self._tabs.configure(command=self._on_tab_change)

    def _on_tab_change(self) -> None:
        tab = self._tabs.get()
        if tab == "📊 Résumé":
            self._onglet_resume.refresh()
        elif tab == "📋 Journal":
            self._onglet_journal.refresh()


# ── Onglet Résumé ─────────────────────────────────────────────────────────────


class OngletResume(ctk.CTkFrame):
    """Onglet de synthèse financière."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(top, text="Exercice :", font=fonts.get("normal")).pack(
            side="left"
        )
        self._annee_var = tk.StringVar(value=_ANNEE_COURANTE)
        ctk.CTkEntry(top, textvariable=self._annee_var, width=80, font=fonts.get("normal")).pack(
            side="left", padx=(6, 10)
        )
        ctk.CTkButton(
            top,
            text="🔄 Actualiser",
            width=110,
            command=self.refresh,
            font=fonts.get("bold"),
            fg_color=primary,
        ).pack(side="left")

        self._frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        self._frame_cards.pack(fill="both", expand=True, padx=10, pady=6)

    def refresh(self) -> None:
        for widget in self._frame_cards.winfo_children():
            widget.destroy()

        exercice = self._annee_var.get().strip() or None
        bilan = calculer_bilan(exercice)

        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")

        cards = [
            ("Solde d'ouverture", bilan["solde_ouverture"], "neutral"),
            ("Total dons/subventions", bilan["total_dons"], "positive"),
            ("Dépenses régulières", bilan["total_depenses_regulieres"], "negative"),
            ("Dépenses diverses", bilan["total_depenses_diverses"], "negative"),
            ("Rétrocessions écoles", bilan["total_retrocessions"], "negative"),
            ("Total recettes", bilan["total_recettes"], "positive"),
            ("Total dépenses", bilan["total_depenses"], "negative"),
            ("Solde théorique", bilan["solde_theorique"], "highlight"),
            ("Dépôts bancaires", bilan["total_depots"], "positive"),
            ("Retraits bancaires", bilan["total_retraits"], "negative"),
            ("Solde bancaire", bilan["solde_banque"], "highlight"),
        ]

        color_map = {
            "positive": "#28a745",
            "negative": "#dc3545",
            "neutral": colors.get("text", "#ffffff"),
            "highlight": primary,
        }

        for i, (label, value, style) in enumerate(cards):
            row, col = divmod(i, 4)
            card = ctk.CTkFrame(self._frame_cards)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._frame_cards.grid_columnconfigure(col, weight=1)

            ctk.CTkLabel(card, text=label, font=fonts.get("small"), anchor="center").pack(
                pady=(10, 2)
            )
            ctk.CTkLabel(
                card,
                text=_fmt(value),
                font=fonts.get("bold"),
                text_color=color_map[style],
                anchor="center",
            ).pack(pady=(0, 10))


# ── Onglet Dons & Subventions ─────────────────────────────────────────────────


class OngletDons(ctk.CTkFrame):
    """Onglet de gestion des dons et subventions."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self._dons: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")
        hover = colors.get("secondary", "#144870")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            actions,
            text="+ Ajouter",
            width=110,
            command=self._ajouter,
            font=fonts.get("bold"),
            fg_color=primary,
            hover_color=hover,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="✏️ Modifier",
            width=110,
            command=self._modifier,
            font=fonts.get("normal"),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            width=110,
            command=self._supprimer,
            font=fonts.get("normal"),
            fg_color="#c0392b",
            hover_color="#922b21",
        ).pack(side="left")

        self._tree = ttk.Treeview(
            self,
            columns=("date", "source", "type", "montant", "justificatif", "commentaire"),
            show="headings",
            height=14,
        )
        for col, label, width in [
            ("date", "Date", 100),
            ("source", "Source", 200),
            ("type", "Type", 100),
            ("montant", "Montant", 110),
            ("justificatif", "Justificatif", 140),
            ("commentaire", "Commentaire", 220),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._lbl_total = ctk.CTkLabel(self, text="Total : 0,00 €", font=fonts.get("bold"))
        self._lbl_total.pack(anchor="e", padx=16, pady=(2, 8))

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._dons = get_all_dons()
        total = 0.0
        for d in self._dons:
            montant = float(d.get("montant") or 0)
            total += montant
            self._tree.insert(
                "",
                "end",
                iid=str(d["id"]),
                values=(
                    d.get("date") or "",
                    d.get("source") or "",
                    d.get("type") or "",
                    _fmt(montant),
                    d.get("justificatif") or "",
                    d.get("commentaire") or "",
                ),
            )
        self._lbl_total.configure(text=f"Total : {_fmt(total)}")

    def _get_selected_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            afficher_info(self, "Sélection", "Veuillez sélectionner un don.")
            return None
        return int(sel[0])

    def _ajouter(self) -> None:
        dlg = DialogDon(self)
        self.wait_window(dlg)
        if dlg.result:
            erreurs = valider_don(dlg.result["date"], dlg.result["source"], dlg.result["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            add_don(
                dlg.result["date"],
                dlg.result["source"],
                _safe_float(dlg.result["montant"]),
                dlg.result["type_don"],
                dlg.result["justificatif"] or None,
                dlg.result["commentaire"] or None,
            )
            self.refresh()

    def _modifier(self) -> None:
        don_id = self._get_selected_id()
        if don_id is None:
            return
        don = next((d for d in self._dons if d["id"] == don_id), None)
        if don is None:
            return
        dlg = DialogDon(self, initial=don)
        self.wait_window(dlg)
        if dlg.result:
            erreurs = valider_don(dlg.result["date"], dlg.result["source"], dlg.result["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            update_don(
                don_id,
                dlg.result["date"],
                dlg.result["source"],
                _safe_float(dlg.result["montant"]),
                dlg.result["type_don"],
                dlg.result["justificatif"] or None,
                dlg.result["commentaire"] or None,
            )
            self.refresh()

    def _supprimer(self) -> None:
        don_id = self._get_selected_id()
        if don_id is None:
            return
        if demander_confirmation(self, "Suppression", "Supprimer ce don ?"):
            delete_don(don_id)
            self.refresh()


# ── Onglet Dépenses (régulières et diverses) ──────────────────────────────────


class OngletDepenses(ctk.CTkFrame):
    """Onglet générique pour les dépenses régulières ou diverses."""

    def __init__(self, parent: Any, table: str) -> None:
        super().__init__(parent, fg_color="transparent")
        self._table = table  # "reguliere" ou "diverse"
        self._depenses: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")
        hover = colors.get("secondary", "#144870")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            actions,
            text="+ Ajouter",
            width=110,
            command=self._ajouter,
            font=fonts.get("bold"),
            fg_color=primary,
            hover_color=hover,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="✏️ Modifier",
            width=110,
            command=self._modifier,
            font=fonts.get("normal"),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            width=110,
            command=self._supprimer,
            font=fonts.get("normal"),
            fg_color="#c0392b",
            hover_color="#922b21",
        ).pack(side="left")

        self._tree = ttk.Treeview(
            self,
            columns=("date", "categorie", "montant", "fournisseur", "paiement", "statut", "commentaire"),
            show="headings",
            height=14,
        )
        for col, label, width in [
            ("date", "Date", 100),
            ("categorie", "Catégorie", 160),
            ("montant", "Montant", 110),
            ("fournisseur", "Fournisseur", 160),
            ("paiement", "Paiement", 100),
            ("statut", "Statut", 100),
            ("commentaire", "Commentaire", 180),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._lbl_total = ctk.CTkLabel(self, text="Total : 0,00 €", font=fonts.get("bold"))
        self._lbl_total.pack(anchor="e", padx=16, pady=(2, 8))

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        if self._table == "reguliere":
            self._depenses = get_all_depenses_regulieres()
        else:
            self._depenses = get_all_depenses_diverses()

        total = 0.0
        for d in self._depenses:
            montant = float(d.get("montant") or 0)
            total += montant
            self._tree.insert(
                "",
                "end",
                iid=str(d["id"]),
                values=(
                    d.get("date_depense") or "",
                    d.get("categorie") or "",
                    _fmt(montant),
                    d.get("fournisseur") or "",
                    d.get("moyen_paiement") or "",
                    d.get("statut_reglement") or "",
                    d.get("commentaire") or "",
                ),
            )
        self._lbl_total.configure(text=f"Total : {_fmt(total)}")

    def _get_selected_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            afficher_info(self, "Sélection", "Veuillez sélectionner une dépense.")
            return None
        return int(sel[0])

    def _ajouter(self) -> None:
        dlg = DialogDepense(self)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            erreurs = valider_depense(r["date_depense"], r["categorie"], r["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            kwargs = dict(
                date_depense=r["date_depense"],
                categorie=r["categorie"],
                montant=_safe_float(r["montant"]),
                fournisseur=r["fournisseur"] or None,
                moyen_paiement=r["moyen_paiement"] or None,
                numero_cheque=r["numero_cheque"] or None,
                numero_facture=r["numero_facture"] or None,
                statut_reglement=r["statut_reglement"],
                commentaire=r["commentaire"] or None,
            )
            if self._table == "reguliere":
                add_depense_reguliere(**kwargs)
            else:
                add_depense_diverse(**kwargs)
            self.refresh()

    def _modifier(self) -> None:
        dep_id = self._get_selected_id()
        if dep_id is None:
            return
        dep = next((d for d in self._depenses if d["id"] == dep_id), None)
        if dep is None:
            return
        dlg = DialogDepense(self, initial=dep)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            erreurs = valider_depense(r["date_depense"], r["categorie"], r["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            kwargs = dict(
                depense_id=dep_id,
                date_depense=r["date_depense"],
                categorie=r["categorie"],
                montant=_safe_float(r["montant"]),
                fournisseur=r["fournisseur"] or None,
                moyen_paiement=r["moyen_paiement"] or None,
                numero_cheque=r["numero_cheque"] or None,
                numero_facture=r["numero_facture"] or None,
                statut_reglement=r["statut_reglement"],
                commentaire=r["commentaire"] or None,
            )
            if self._table == "reguliere":
                update_depense_reguliere(**kwargs)
            else:
                update_depense_diverse(**kwargs)
            self.refresh()

    def _supprimer(self) -> None:
        dep_id = self._get_selected_id()
        if dep_id is None:
            return
        if demander_confirmation(self, "Suppression", "Supprimer cette dépense ?"):
            if self._table == "reguliere":
                delete_depense_reguliere(dep_id)
            else:
                delete_depense_diverse(dep_id)
            self.refresh()


# ── Onglet Banque ─────────────────────────────────────────────────────────────


class OngletBanque(ctk.CTkFrame):
    """Onglet de gestion des dépôts et retraits bancaires."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self._mouvements: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")
        hover = colors.get("secondary", "#144870")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            actions,
            text="+ Ajouter",
            width=110,
            command=self._ajouter,
            font=fonts.get("bold"),
            fg_color=primary,
            hover_color=hover,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="✏️ Modifier",
            width=110,
            command=self._modifier,
            font=fonts.get("normal"),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            width=110,
            command=self._supprimer,
            font=fonts.get("normal"),
            fg_color="#c0392b",
            hover_color="#922b21",
        ).pack(side="left")

        self._tree = ttk.Treeview(
            self,
            columns=("date", "type", "montant", "reference", "banque", "pointe", "commentaire"),
            show="headings",
            height=14,
        )
        for col, label, width in [
            ("date", "Date", 100),
            ("type", "Type", 100),
            ("montant", "Montant", 110),
            ("reference", "Référence", 140),
            ("banque", "Banque", 140),
            ("pointe", "Pointé", 80),
            ("commentaire", "Commentaire", 200),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=8, pady=(2, 8))
        self._lbl_depots = ctk.CTkLabel(bottom, text="Dépôts : 0,00 €", font=fonts.get("normal"))
        self._lbl_depots.pack(side="left", padx=8)
        self._lbl_retraits = ctk.CTkLabel(bottom, text="Retraits : 0,00 €", font=fonts.get("normal"))
        self._lbl_retraits.pack(side="left", padx=8)
        self._lbl_solde = ctk.CTkLabel(bottom, text="Solde : 0,00 €", font=fonts.get("bold"))
        self._lbl_solde.pack(side="right", padx=16)

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._mouvements = get_all_depots_retraits()
        total_depots = 0.0
        total_retraits = 0.0
        for m in self._mouvements:
            montant = float(m.get("montant") or 0)
            if m.get("type") == "dépôt":
                total_depots += montant
            else:
                total_retraits += montant
            self._tree.insert(
                "",
                "end",
                iid=str(m["id"]),
                values=(
                    m.get("date") or "",
                    m.get("type") or "",
                    _fmt(montant),
                    m.get("reference") or "",
                    m.get("banque") or "",
                    "✓" if m.get("pointe") else "",
                    m.get("commentaire") or "",
                ),
            )
        self._lbl_depots.configure(text=f"Dépôts : {_fmt(total_depots)}")
        self._lbl_retraits.configure(text=f"Retraits : {_fmt(total_retraits)}")
        self._lbl_solde.configure(text=f"Solde : {_fmt(total_depots - total_retraits)}")

    def _get_selected_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            afficher_info(self, "Sélection", "Veuillez sélectionner un mouvement.")
            return None
        return int(sel[0])

    def _ajouter(self) -> None:
        dlg = DialogBanque(self)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            erreurs = valider_mouvement_banque(r["date"], r["type_mouvement"], r["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            add_depot_retrait(
                r["date"],
                r["type_mouvement"],
                _safe_float(r["montant"]),
                r["reference"] or None,
                r["banque"] or None,
                1 if r["pointe"] else 0,
                r["commentaire"] or None,
            )
            self.refresh()

    def _modifier(self) -> None:
        mvt_id = self._get_selected_id()
        if mvt_id is None:
            return
        mvt = next((m for m in self._mouvements if m["id"] == mvt_id), None)
        if mvt is None:
            return
        dlg = DialogBanque(self, initial=mvt)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            erreurs = valider_mouvement_banque(r["date"], r["type_mouvement"], r["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            update_depot_retrait(
                mvt_id,
                r["date"],
                r["type_mouvement"],
                _safe_float(r["montant"]),
                r["reference"] or None,
                r["banque"] or None,
                1 if r["pointe"] else 0,
                r["commentaire"] or None,
            )
            self.refresh()

    def _supprimer(self) -> None:
        mvt_id = self._get_selected_id()
        if mvt_id is None:
            return
        if demander_confirmation(self, "Suppression", "Supprimer ce mouvement bancaire ?"):
            delete_depot_retrait(mvt_id)
            self.refresh()


# ── Onglet Rétrocessions ──────────────────────────────────────────────────────


class OngletRetrocessions(ctk.CTkFrame):
    """Onglet de gestion des rétrocessions aux écoles."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self._retrocessions: list[dict] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")
        hover = colors.get("secondary", "#144870")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkButton(
            actions,
            text="+ Ajouter",
            width=110,
            command=self._ajouter,
            font=fonts.get("bold"),
            fg_color=primary,
            hover_color=hover,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            width=110,
            command=self._supprimer,
            font=fonts.get("normal"),
            fg_color="#c0392b",
            hover_color="#922b21",
        ).pack(side="left", padx=6)

        self._tree = ttk.Treeview(
            self,
            columns=("date", "ecole", "montant", "commentaire"),
            show="headings",
            height=14,
        )
        for col, label, width in [
            ("date", "Date", 100),
            ("ecole", "École", 260),
            ("montant", "Montant", 120),
            ("commentaire", "Commentaire", 320),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._lbl_total = ctk.CTkLabel(self, text="Total : 0,00 €", font=fonts.get("bold"))
        self._lbl_total.pack(anchor="e", padx=16, pady=(2, 8))

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        self._retrocessions = get_all_retrocessions()
        total = 0.0
        for r in self._retrocessions:
            montant = float(r.get("montant") or 0)
            total += montant
            self._tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r.get("date") or "",
                    r.get("ecole") or "",
                    _fmt(montant),
                    r.get("commentaire") or "",
                ),
            )
        self._lbl_total.configure(text=f"Total : {_fmt(total)}")

    def _get_selected_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            afficher_info(self, "Sélection", "Veuillez sélectionner une rétrocession.")
            return None
        return int(sel[0])

    def _ajouter(self) -> None:
        dlg = DialogRetrocession(self)
        self.wait_window(dlg)
        if dlg.result:
            r = dlg.result
            erreurs = valider_retrocession(r["date"], r["ecole"], r["montant"])
            if erreurs:
                afficher_erreur(self, "Erreur de saisie", "\n".join(erreurs))
                return
            add_retrocession(r["date"], r["ecole"], _safe_float(r["montant"]), r["commentaire"] or None)
            self.refresh()

    def _supprimer(self) -> None:
        retro_id = self._get_selected_id()
        if retro_id is None:
            return
        if demander_confirmation(self, "Suppression", "Supprimer cette rétrocession ?"):
            delete_retrocession(retro_id)
            self.refresh()


# ── Onglet Journal ────────────────────────────────────────────────────────────


class OngletJournal(ctk.CTkFrame):
    """Onglet Journal général (toutes opérations chronologiques)."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent, fg_color="transparent")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(top, text="Exercice :", font=fonts.get("normal")).pack(side="left")
        self._annee_var = tk.StringVar(value=_ANNEE_COURANTE)
        ctk.CTkEntry(top, textvariable=self._annee_var, width=80, font=fonts.get("normal")).pack(
            side="left", padx=(6, 10)
        )
        ctk.CTkButton(
            top,
            text="🔄 Actualiser",
            width=110,
            command=self.refresh,
            font=fonts.get("bold"),
            fg_color=primary,
        ).pack(side="left")

        self._tree = ttk.Treeview(
            self,
            columns=("date", "libelle", "categorie", "sens", "montant", "origine"),
            show="headings",
            height=16,
        )
        for col, label, width in [
            ("date", "Date", 100),
            ("libelle", "Libellé", 200),
            ("categorie", "Catégorie", 160),
            ("sens", "Sens", 100),
            ("montant", "Montant", 110),
            ("origine", "Origine", 160),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor="center")
        self._tree.pack(fill="both", expand=True, padx=8, pady=4)

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        exercice = self._annee_var.get().strip() or None
        lignes = get_journal_general(exercice)
        for i, ligne in enumerate(lignes):
            montant = float(ligne.get("montant") or 0)
            sens = ligne.get("sens") or ""
            self._tree.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    ligne.get("date") or "",
                    ligne.get("libelle") or "",
                    ligne.get("categorie") or "",
                    sens,
                    _fmt(montant),
                    ligne.get("origine") or "",
                ),
            )


# ── Dialogues de saisie ───────────────────────────────────────────────────────


class _BaseDialog(ctk.CTkToplevel):
    """Base pour les dialogues de saisie."""

    def __init__(self, parent: Any, title: str, width: int = 500, height: int = 400) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: dict | None = None

    def _add_field(
        self,
        frame: ctk.CTkFrame,
        label: str,
        row: int,
        widget: Any,
    ) -> None:
        ctk.CTkLabel(frame, text=label, anchor="w").grid(
            row=row, column=0, padx=10, pady=6, sticky="w"
        )
        widget.grid(row=row, column=1, padx=10, pady=6, sticky="ew")

    def _buttons(self, frame: ctk.CTkFrame) -> None:
        colors = app_theme.COLORS
        primary = colors.get("primary", "#1f6aa5")
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=20, column=0, columnspan=2, pady=14)
        ctk.CTkButton(
            btn_frame, text="✔ Valider", command=self._valider, fg_color=primary, width=110
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame, text="✘ Annuler", command=self.destroy, width=110
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        raise NotImplementedError


def _combo(parent: Any, values: list[str], initial: str = "", width: int = 220) -> ttk.Combobox:
    var = tk.StringVar(value=initial)
    cb = ttk.Combobox(parent, textvariable=var, values=values, width=width // 8, state="readonly")
    cb._var = var  # type: ignore[attr-defined]
    return cb


class DialogDon(_BaseDialog):
    """Dialogue de saisie d'un don/subvention."""

    def __init__(self, parent: Any, initial: dict | None = None) -> None:
        super().__init__(parent, "Don / Subvention", width=520, height=380)
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=10)
        frame.grid_columnconfigure(1, weight=1)

        init = initial or {}

        self._date_var = tk.StringVar(value=init.get("date") or _AUJOURD_HUI)
        self._source_var = tk.StringVar(value=init.get("source") or "")
        self._montant_var = tk.StringVar(value=str(init.get("montant") or ""))
        self._justif_var = tk.StringVar(value=init.get("justificatif") or "")
        self._commentaire_var = tk.StringVar(value=init.get("commentaire") or "")

        self._add_field(frame, "Date (AAAA-MM-JJ) *", 0, ctk.CTkEntry(frame, textvariable=self._date_var, width=220))
        self._add_field(frame, "Source *", 1, ctk.CTkEntry(frame, textvariable=self._source_var, width=220))
        self._add_field(frame, "Montant (€) *", 2, ctk.CTkEntry(frame, textvariable=self._montant_var, width=220))

        self._type_cb = _combo(frame, TYPES_DON, init.get("type") or TYPES_DON[0])
        self._add_field(frame, "Type", 3, self._type_cb)

        self._add_field(frame, "Justificatif", 4, ctk.CTkEntry(frame, textvariable=self._justif_var, width=220))
        self._add_field(frame, "Commentaire", 5, ctk.CTkEntry(frame, textvariable=self._commentaire_var, width=220))

        self._buttons(frame)

    def _valider(self) -> None:
        self.result = {
            "date": self._date_var.get().strip(),
            "source": self._source_var.get().strip(),
            "montant": self._montant_var.get().strip(),
            "type_don": self._type_cb._var.get(),  # type: ignore[attr-defined]
            "justificatif": self._justif_var.get().strip(),
            "commentaire": self._commentaire_var.get().strip(),
        }
        self.destroy()


class DialogDepense(_BaseDialog):
    """Dialogue de saisie d'une dépense."""

    def __init__(self, parent: Any, initial: dict | None = None) -> None:
        super().__init__(parent, "Dépense", width=540, height=450)
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=10)
        frame.grid_columnconfigure(1, weight=1)

        init = initial or {}

        self._date_var = tk.StringVar(value=init.get("date_depense") or _AUJOURD_HUI)
        self._montant_var = tk.StringVar(value=str(init.get("montant") or ""))
        self._fournisseur_var = tk.StringVar(value=init.get("fournisseur") or "")
        self._no_cheque_var = tk.StringVar(value=init.get("numero_cheque") or "")
        self._no_facture_var = tk.StringVar(value=init.get("numero_facture") or "")
        self._commentaire_var = tk.StringVar(value=init.get("commentaire") or "")

        self._add_field(frame, "Date (AAAA-MM-JJ) *", 0, ctk.CTkEntry(frame, textvariable=self._date_var, width=220))
        self._add_field(frame, "Montant (€) *", 1, ctk.CTkEntry(frame, textvariable=self._montant_var, width=220))

        self._categorie_cb = _combo(frame, CATEGORIES_DEPENSE, init.get("categorie") or CATEGORIES_DEPENSE[0])
        self._add_field(frame, "Catégorie *", 2, self._categorie_cb)

        self._add_field(frame, "Fournisseur", 3, ctk.CTkEntry(frame, textvariable=self._fournisseur_var, width=220))

        self._paiement_cb = _combo(frame, MOYENS_PAIEMENT, init.get("moyen_paiement") or MOYENS_PAIEMENT[0])
        self._add_field(frame, "Paiement", 4, self._paiement_cb)

        self._add_field(frame, "N° chèque", 5, ctk.CTkEntry(frame, textvariable=self._no_cheque_var, width=220))
        self._add_field(frame, "N° facture", 6, ctk.CTkEntry(frame, textvariable=self._no_facture_var, width=220))

        self._statut_cb = _combo(frame, STATUTS_REGLEMENT, init.get("statut_reglement") or STATUTS_REGLEMENT[0])
        self._add_field(frame, "Statut règlement", 7, self._statut_cb)

        self._add_field(frame, "Commentaire", 8, ctk.CTkEntry(frame, textvariable=self._commentaire_var, width=220))

        self._buttons(frame)

    def _valider(self) -> None:
        self.result = {
            "date_depense": self._date_var.get().strip(),
            "montant": self._montant_var.get().strip(),
            "categorie": self._categorie_cb._var.get(),  # type: ignore[attr-defined]
            "fournisseur": self._fournisseur_var.get().strip(),
            "moyen_paiement": self._paiement_cb._var.get(),  # type: ignore[attr-defined]
            "numero_cheque": self._no_cheque_var.get().strip(),
            "numero_facture": self._no_facture_var.get().strip(),
            "statut_reglement": self._statut_cb._var.get(),  # type: ignore[attr-defined]
            "commentaire": self._commentaire_var.get().strip(),
        }
        self.destroy()


class DialogBanque(_BaseDialog):
    """Dialogue de saisie d'un dépôt/retrait bancaire."""

    def __init__(self, parent: Any, initial: dict | None = None) -> None:
        super().__init__(parent, "Mouvement bancaire", width=500, height=360)
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=10)
        frame.grid_columnconfigure(1, weight=1)

        init = initial or {}

        self._date_var = tk.StringVar(value=init.get("date") or _AUJOURD_HUI)
        self._montant_var = tk.StringVar(value=str(init.get("montant") or ""))
        self._reference_var = tk.StringVar(value=init.get("reference") or "")
        self._banque_var = tk.StringVar(value=init.get("banque") or "")
        self._pointe_var = tk.BooleanVar(value=bool(init.get("pointe")))
        self._commentaire_var = tk.StringVar(value=init.get("commentaire") or "")

        self._add_field(frame, "Date (AAAA-MM-JJ) *", 0, ctk.CTkEntry(frame, textvariable=self._date_var, width=220))

        self._type_cb = _combo(frame, TYPES_MOUVEMENT_BANQUE, init.get("type") or TYPES_MOUVEMENT_BANQUE[0])
        self._add_field(frame, "Type *", 1, self._type_cb)

        self._add_field(frame, "Montant (€) *", 2, ctk.CTkEntry(frame, textvariable=self._montant_var, width=220))
        self._add_field(frame, "Référence", 3, ctk.CTkEntry(frame, textvariable=self._reference_var, width=220))
        self._add_field(frame, "Banque", 4, ctk.CTkEntry(frame, textvariable=self._banque_var, width=220))
        self._add_field(frame, "Pointé", 5, ctk.CTkCheckBox(frame, text="", variable=self._pointe_var))
        self._add_field(frame, "Commentaire", 6, ctk.CTkEntry(frame, textvariable=self._commentaire_var, width=220))

        self._buttons(frame)

    def _valider(self) -> None:
        self.result = {
            "date": self._date_var.get().strip(),
            "type_mouvement": self._type_cb._var.get(),  # type: ignore[attr-defined]
            "montant": self._montant_var.get().strip(),
            "reference": self._reference_var.get().strip(),
            "banque": self._banque_var.get().strip(),
            "pointe": self._pointe_var.get(),
            "commentaire": self._commentaire_var.get().strip(),
        }
        self.destroy()


class DialogRetrocession(_BaseDialog):
    """Dialogue de saisie d'une rétrocession."""

    def __init__(self, parent: Any, initial: dict | None = None) -> None:
        super().__init__(parent, "Rétrocession", width=500, height=320)
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=16, pady=10)
        frame.grid_columnconfigure(1, weight=1)

        init = initial or {}

        self._date_var = tk.StringVar(value=init.get("date") or _AUJOURD_HUI)
        self._ecole_var = tk.StringVar(value=init.get("ecole") or "")
        self._montant_var = tk.StringVar(value=str(init.get("montant") or ""))
        self._commentaire_var = tk.StringVar(value=init.get("commentaire") or "")

        self._add_field(frame, "Date (AAAA-MM-JJ) *", 0, ctk.CTkEntry(frame, textvariable=self._date_var, width=220))
        self._add_field(frame, "École *", 1, ctk.CTkEntry(frame, textvariable=self._ecole_var, width=220))
        self._add_field(frame, "Montant (€) *", 2, ctk.CTkEntry(frame, textvariable=self._montant_var, width=220))
        self._add_field(frame, "Commentaire", 3, ctk.CTkEntry(frame, textvariable=self._commentaire_var, width=220))

        self._buttons(frame)

    def _valider(self) -> None:
        self.result = {
            "date": self._date_var.get().strip(),
            "ecole": self._ecole_var.get().strip(),
            "montant": self._montant_var.get().strip(),
            "commentaire": self._commentaire_var.get().strip(),
        }
        self.destroy()
