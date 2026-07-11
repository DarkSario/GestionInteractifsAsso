"""Fiche détail d'un événement avec onglets Général, Billetterie, Dépenses, Bénévoles, Budget."""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.evenements import (
    calculer_bilan_evenement,
    calculer_frais_sumup,
    generer_numero_billet,
    valider_evenement,
    valider_tarif,
    valider_vente,
)
from db.models.evenements import (
    MODULES_EVENEMENT_DISPONIBLES,
    add_benevole,
    add_billet,
    add_depense,
    add_evenement,
    add_tarif,
    add_vente,
    add_vente_ligne,
    annuler_vente,
    delete_benevole,
    delete_depense,
    delete_tarif,
    get_benevoles_evenement,
    get_depenses_evenement,
    get_evenement_by_id,
    get_lignes_vente,
    get_parametre,
    get_stats_benevoles,
    get_stats_billetterie,
    get_tarifs_evenement,
    get_ventes_evenement,
    modules_actifs_depuis_json,
    serialiser_modules_actifs,
    update_benevole,
    update_depense,
    update_evenement,
    update_tarif,
)
from db.models.fournisseurs import get_all_fournisseurs
from db.models.membres import get_all_membres
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from ui.modules.evenements.budget_evenement import BudgetEvenementView
from ui.modules.evenements.stands import StandsView
from ui.modules.evenements.tableaux import TableauxView
from ui.modules.evenements.tombola import TombolaView

STATUTS_EVENEMENT = ["planifie", "en_cours", "termine", "annule"]
LABELS_STATUT = {
    "planifie": "Planifié",
    "en_cours": "En cours",
    "termine": "Terminé",
    "annule": "Annulé",
}
STATUTS_LABELS = {v: k for k, v in LABELS_STATUT.items()}

CANAUX = {"sur_place": "Sur place", "prevente": "Prévente"}
CANAUX_INV = {v: k for k, v in CANAUX.items()}

MODES_PAIEMENT = {
    "especes": "Espèces",
    "cheque": "Chèque",
    "carte": "Carte",
    "sumup": "SumUp",
}
MODES_INV = {v: k for k, v in MODES_PAIEMENT.items()}

MODES_DEPENSE = {
    "especes": "Espèces",
    "cheque": "Chèque",
    "carte": "Carte",
    "sumup": "SumUp",
    "virement": "Virement",
    "": "—",
}

ONGLETS_MODULES = {
    "🎫 Billetterie": {"billetterie"},
    "💸 Dépenses": {"depenses"},
    "💰 Budget": {"budget_previsionnel"},
    "👥 Bénévoles": {"benevoles"},
    "🎰 Tombola": {"tombola_classique", "tombola_solidaire"},
    "🏪 Stands": {"stands"},
    "📊 Tableaux": {"tableaux"},
}

LIBELLES_MODULES = {
    "billetterie": "Billetterie",
    "depenses": "Dépenses",
    "benevoles": "Bénévoles",
    "tombola_classique": "Tombola",
    "tombola_solidaire": "Tombola solidaire",
    "stands": "Stands",
    "tableaux": "Tableaux",
    "budget_previsionnel": "Budget",
}

STATUTS_BENEVOLE = {
    "confirme": "Confirmé",
    "desiste": "Désisté",
    "remplace": "Remplacé",
}
STATUTS_BEN_INV = {v: k for k, v in STATUTS_BENEVOLE.items()}


def serialiser_modules_depuis_cases(
    vars_modules: dict[str, tk.BooleanVar | bool],
) -> str:
    modules = [
        module
        for module, var in vars_modules.items()
        if bool(var.get() if hasattr(var, "get") else var)
    ]
    return serialiser_modules_actifs(modules)


class FicheEvenement(ctk.CTkToplevel):
    """Fenêtre de création/édition d'un événement avec onglets."""

    def __init__(self, parent: Any, evenement_id: int | None) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._evenement: dict | None = None

        titre = "Nouvel événement" if evenement_id is None else "Fiche événement"
        self.title(f"🎪 {titre}")
        self.geometry("1100x760")
        self.minsize(900, 600)
        self.transient(parent)

        self._build_ui()

        if evenement_id is not None:
            self._charger_evenement()

    # ── Construction globale ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        # Barre supérieure : titre + bouton exporter
        frame_top = ctk.CTkFrame(self, fg_color="transparent")
        frame_top.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            frame_top,
            text="🎪 Fiche événement",
            font=fonts.get("title"),
        ).pack(side="left")

        ctk.CTkButton(
            frame_top,
            text="⚙️ Modules",
            width=120,
            command=self._ouvrir_modules,
        ).pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            frame_top,
            text="📤 Exporter",
            width=130,
            command=self._ouvrir_export,
        ).pack(side="right")

        self._tabs = ctk.CTkTabview(self)
        self._tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self._tabs.add("📋 Général")
        self._tabs.add("🎫 Billetterie")
        self._tabs.add("💸 Dépenses")
        self._tabs.add("💰 Budget")
        self._tabs.add("👥 Bénévoles")
        self._tabs.add("🎰 Tombola")
        self._tabs.add("🏪 Stands")
        self._tabs.add("📊 Tableaux")

        self._build_onglet_general(self._tabs.tab("📋 Général"))
        self._build_onglet_billetterie(self._tabs.tab("🎫 Billetterie"))
        self._build_onglet_depenses(self._tabs.tab("💸 Dépenses"))
        self._build_onglet_budget(self._tabs.tab("💰 Budget"))
        self._build_onglet_benevoles(self._tabs.tab("👥 Bénévoles"))
        self._build_onglet_tombola(self._tabs.tab("🎰 Tombola"))
        self._build_onglet_stands(self._tabs.tab("🏪 Stands"))
        self._build_onglet_tableaux(self._tabs.tab("📊 Tableaux"))

    def _ouvrir_export(self) -> None:
        """Ouvre le dialogue d'export de l'événement."""
        if not self._evenement_id:
            from ui.components.dialogs import afficher_erreur

            afficher_erreur(self, "Erreur", "Veuillez d'abord sauvegarder l'événement.")
            return
        from ui.modules.evenements.export_dialog import ExportDialog

        dialog = ExportDialog(self, self._evenement_id)
        self.wait_window(dialog)

    # ══════════════════════════════════════════════════════════════════════════
    # Onglet Général
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_general(self, parent: Any) -> None:
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        def row(label: str, widget_fn, **kwargs):
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=180, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f, **kwargs)
            w.pack(side="left", fill="x", expand=True)
            return w

        # Nom
        self._var_nom = tk.StringVar()
        row("Nom *", lambda p, **kw: ctk.CTkEntry(p, textvariable=self._var_nom, **kw))

        # Type
        self._var_type = tk.StringVar()
        row("Type", lambda p, **kw: ctk.CTkEntry(p, textvariable=self._var_type, **kw))

        # Description
        f_desc = ctk.CTkFrame(frame, fg_color="transparent")
        f_desc.pack(fill="x", pady=3)
        ctk.CTkLabel(f_desc, text="Description", width=180, anchor="ne").pack(
            side="left", padx=(0, 8), anchor="n", pady=2
        )
        self._txt_description = ctk.CTkTextbox(f_desc, height=80)
        self._txt_description.pack(side="left", fill="x", expand=True)

        # Date début
        self._var_date_debut = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        row(
            "Date début *",
            lambda p, **kw: ctk.CTkEntry(
                p,
                textvariable=self._var_date_debut,
                placeholder_text="AAAA-MM-JJ",
                **kw,
            ),
        )

        # Date fin
        self._var_date_fin = tk.StringVar()
        row(
            "Date fin",
            lambda p, **kw: ctk.CTkEntry(
                p,
                textvariable=self._var_date_fin,
                placeholder_text="AAAA-MM-JJ (optionnel)",
                **kw,
            ),
        )

        # Statut
        self._var_statut = tk.StringVar(value="Planifié")
        row(
            "Statut",
            lambda p, **kw: ctk.CTkOptionMenu(
                p, values=list(LABELS_STATUT.values()), variable=self._var_statut, **kw
            ),
        )

        # Budget prévisionnel
        self._var_budget = tk.StringVar()
        row(
            "Budget prévisionnel",
            lambda p, **kw: ctk.CTkEntry(
                p,
                textvariable=self._var_budget,
                placeholder_text="Montant optionnel",
                **kw,
            ),
        )

        modules_frame = ctk.CTkFrame(frame)
        modules_frame.pack(fill="x", pady=(10, 6))
        ctk.CTkLabel(
            modules_frame,
            text="Modules activés",
            font=fonts.get("bold"),
        ).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkLabel(
            modules_frame,
            text=(
                "Choisissez les modules à activer pour cet événement.\n"
                "Ces choix pourront être modifiés ultérieurement."
            ),
        ).pack(anchor="w", padx=12, pady=(0, 6))

        self._vars_modules: dict[str, tk.BooleanVar] = {}
        grille_modules = ctk.CTkFrame(modules_frame, fg_color="transparent")
        grille_modules.pack(fill="x", padx=12, pady=(0, 10))
        for index, module in enumerate(MODULES_EVENEMENT_DISPONIBLES):
            var = tk.BooleanVar(value=module in {"billetterie", "depenses"})
            self._vars_modules[module] = var
            checkbox = ctk.CTkCheckBox(
                grille_modules,
                text=LIBELLES_MODULES.get(module, module.replace("_", " ").title()),
                variable=var,
                onvalue=True,
                offvalue=False,
            )
            checkbox.grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=4)

        # Bilan de fin
        f_bilan = ctk.CTkFrame(frame, fg_color="transparent")
        f_bilan.pack(fill="x", pady=3)
        ctk.CTkLabel(f_bilan, text="Bilan de fin", width=180, anchor="ne").pack(
            side="left", padx=(0, 8), anchor="n", pady=2
        )
        self._txt_bilan = ctk.CTkTextbox(f_bilan, height=80)
        self._txt_bilan.pack(side="left", fill="x", expand=True)

        # Résumé financier (lecture seule)
        sep = ctk.CTkFrame(frame, height=2, fg_color="#444")
        sep.pack(fill="x", pady=8)

        ctk.CTkLabel(frame, text="Résumé financier", font=fonts.get("bold")).pack(
            anchor="w", pady=(0, 4)
        )

        self._lbl_recettes = ctk.CTkLabel(frame, text="Recettes billetterie : —")
        self._lbl_recettes.pack(anchor="w", padx=16)
        self._lbl_depenses = ctk.CTkLabel(frame, text="Dépenses : —")
        self._lbl_depenses.pack(anchor="w", padx=16)
        self._lbl_benefice = ctk.CTkLabel(frame, text="Bénéfice estimé : —")
        self._lbl_benefice.pack(anchor="w", padx=16)

        # Bouton sauvegarder
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="#444")
        sep2.pack(fill="x", pady=8)

        ctk.CTkButton(
            frame,
            text="💾 Sauvegarder",
            command=self._sauvegarder_general,
        ).pack(anchor="w")

    def _charger_evenement(self) -> None:
        if not self._evenement_id:
            return
        evt = get_evenement_by_id(self._evenement_id)
        if not evt:
            return
        self._evenement = evt

        self._var_nom.set(evt.get("nom") or "")
        self._var_type.set(evt.get("type") or "")
        self._txt_description.delete("1.0", "end")
        self._txt_description.insert("1.0", evt.get("description") or "")
        self._var_date_debut.set(evt.get("date_debut") or "")
        self._var_date_fin.set(evt.get("date_fin") or "")
        self._var_statut.set(
            LABELS_STATUT.get(evt.get("statut", "planifie"), "Planifié")
        )
        budget = evt.get("budget_previsionnel")
        self._var_budget.set(
            f"{float(budget):.2f}".replace(".", ",") if budget is not None else ""
        )
        self._definir_modules_selection(
            modules_actifs_depuis_json(evt.get("modules_actifs_json"))
        )
        self._txt_bilan.delete("1.0", "end")
        self._txt_bilan.insert("1.0", evt.get("bilan_fin") or "")

        self._actualiser_resume_financier()
        self._charger_billetterie()
        self._charger_depenses()
        self._charger_benevoles()
        self._budget_view.set_evenement_id(self._evenement_id)
        self._tombola_view.set_evenement_id(self._evenement_id)
        self._stands_view.set_evenement_id(self._evenement_id)
        self._tableaux_view.set_evenement_id(self._evenement_id)
        self._appliquer_modules_actifs()

    def _sauvegarder_general(self) -> None:
        nom = self._var_nom.get().strip()
        type_ = self._var_type.get().strip() or None
        description = self._txt_description.get("1.0", "end").strip() or None
        date_debut = self._var_date_debut.get().strip()
        date_fin = self._var_date_fin.get().strip() or None
        statut_label = self._var_statut.get()
        statut = STATUTS_LABELS.get(statut_label, "planifie")
        bilan = self._txt_bilan.get("1.0", "end").strip() or None

        budget_str = self._var_budget.get().strip().replace(",", ".")
        budget: float | None = None
        if budget_str:
            try:
                budget = float(budget_str)
            except ValueError:
                afficher_erreur(
                    self, "Erreur", "Le budget prévisionnel doit être un nombre."
                )
                return

        erreurs = valider_evenement(nom, date_debut, date_fin)
        if erreurs:
            afficher_erreur(self, "Données invalides", "\n".join(erreurs))
            return

        try:
            modules_actifs_json = serialiser_modules_depuis_cases(self._vars_modules)
            if self._evenement_id is None:
                self._evenement_id = add_evenement(
                    nom,
                    type_,
                    description,
                    date_debut,
                    date_fin,
                    statut,
                    budget,
                    modules_actifs_json,
                )
                update_evenement(self._evenement_id, bilan_fin=bilan)
                afficher_info(self, "Succès", "Événement créé avec succès.")
            else:
                update_evenement(
                    self._evenement_id,
                    nom=nom,
                    type=type_,
                    description=description,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    statut=statut,
                    budget_previsionnel=budget,
                    bilan_fin=bilan,
                    modules_actifs_json=modules_actifs_json,
                )
                afficher_info(self, "Succès", "Événement mis à jour.")
        except Exception as exc:
            afficher_erreur(self, "Erreur", str(exc))
            return

        self._evenement = get_evenement_by_id(self._evenement_id) if self._evenement_id else None
        self._actualiser_resume_financier()
        self._budget_view.set_evenement_id(self._evenement_id)
        self._tombola_view.set_evenement_id(self._evenement_id)
        self._stands_view.set_evenement_id(self._evenement_id)
        self._tableaux_view.set_evenement_id(self._evenement_id)
        self._appliquer_modules_actifs()

    def _appliquer_modules_actifs(self) -> None:
        if not self._evenement:
            return
        modules_actifs = set(
            modules_actifs_depuis_json(self._evenement.get("modules_actifs_json"))
        )
        if modules_actifs == set(MODULES_EVENEMENT_DISPONIBLES):
            return
        for nom_onglet, modules_onglet in ONGLETS_MODULES.items():
            if modules_actifs.intersection(modules_onglet):
                continue
            try:
                self._tabs.delete(nom_onglet)
            except Exception:
                continue

    def _ouvrir_modules(self) -> None:
        self._tabs.set("📋 Général")

    def _definir_modules_selection(self, modules: list[str]) -> None:
        selection = set(modules)
        for module, var in self._vars_modules.items():
            var.set(module in selection)

    def _actualiser_resume_financier(self) -> None:
        if not self._evenement_id:
            return
        try:
            bilan = calculer_bilan_evenement(self._evenement_id)
            self._lbl_recettes.configure(
                text=f"Recettes billetterie : {self._fmt(bilan['recettes_total'])}"
            )
            self._lbl_depenses.configure(
                text=f"Dépenses : {self._fmt(bilan['depenses_total'])}"
            )
            benefice = bilan["benefice"]
            couleur = "#28a745" if benefice >= 0 else "#dc3545"
            self._lbl_benefice.configure(
                text=f"Bénéfice estimé : {self._fmt(benefice)}",
                text_color=couleur,
            )
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # Onglet Billetterie
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_billetterie(self, parent: Any) -> None:
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Tarifs ────────────────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="Tarifs configurés", font=fonts.get("bold")).pack(
            anchor="w", pady=(0, 4)
        )

        frame_tarifs = ctk.CTkFrame(frame)
        frame_tarifs.pack(fill="x", pady=(0, 6))

        self._tree_tarifs = ttk.Treeview(
            frame_tarifs,
            columns=("id", "nom", "prix", "gratuit"),
            show="headings",
            height=5,
        )
        self._tree_tarifs.heading("id", text="ID")
        self._tree_tarifs.heading("nom", text="Nom")
        self._tree_tarifs.heading("prix", text="Prix")
        self._tree_tarifs.heading("gratuit", text="Gratuit")
        self._tree_tarifs.column("id", width=50, anchor="center", stretch=False)
        self._tree_tarifs.column("nom", width=280)
        self._tree_tarifs.column("prix", width=100, anchor="e")
        self._tree_tarifs.column("gratuit", width=80, anchor="center")
        self._tree_tarifs.pack(fill="x", padx=4, pady=4)

        frame_btn_tarifs = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn_tarifs.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            frame_btn_tarifs,
            text="+ Ajouter un tarif",
            width=150,
            command=self._ajouter_tarif,
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn_tarifs,
            text="✏️ Modifier",
            width=100,
            command=self._modifier_tarif,
        ).pack(side="left", padx=(6, 0))
        ctk.CTkButton(
            frame_btn_tarifs,
            text="🗑️ Supprimer",
            width=110,
            fg_color="#dc3545",
            hover_color="#a71d2a",
            command=self._supprimer_tarif,
        ).pack(side="left", padx=(6, 0))

        # ── Ventes ────────────────────────────────────────────────────────────
        sep = ctk.CTkFrame(frame, height=2, fg_color="#444")
        sep.pack(fill="x", pady=8)

        ctk.CTkLabel(frame, text="Ventes", font=fonts.get("bold")).pack(
            anchor="w", pady=(0, 4)
        )

        ctk.CTkButton(
            frame,
            text="+ Enregistrer une vente",
            width=190,
            command=self._nouvelle_vente,
        ).pack(anchor="w", pady=(0, 6))

        frame_ventes = ctk.CTkFrame(frame)
        frame_ventes.pack(fill="x", pady=(0, 4))

        self._tree_ventes = ttk.Treeview(
            frame_ventes,
            columns=("id", "date", "canal", "mode", "montant", "statut"),
            show="headings",
            height=8,
        )
        self._tree_ventes.heading("id", text="ID")
        self._tree_ventes.heading("date", text="Date")
        self._tree_ventes.heading("canal", text="Canal")
        self._tree_ventes.heading("mode", text="Paiement")
        self._tree_ventes.heading("montant", text="Montant")
        self._tree_ventes.heading("statut", text="Statut")

        self._tree_ventes.column("id", width=50, anchor="center", stretch=False)
        self._tree_ventes.column("date", width=100, anchor="center")
        self._tree_ventes.column("canal", width=100, anchor="center")
        self._tree_ventes.column("mode", width=100, anchor="center")
        self._tree_ventes.column("montant", width=110, anchor="e")
        self._tree_ventes.column("statut", width=90, anchor="center")

        self._tree_ventes.tag_configure("annule", foreground="#dc3545")
        self._tree_ventes.tag_configure("rembourse", foreground="#fd7e14")

        sv = ttk.Scrollbar(
            frame_ventes, orient="vertical", command=self._tree_ventes.yview
        )
        self._tree_ventes.configure(yscrollcommand=sv.set)
        self._tree_ventes.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        sv.pack(side="right", fill="y", pady=4)

        frame_btn_ventes = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn_ventes.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            frame_btn_ventes,
            text="👁️ Voir détail",
            width=120,
            command=self._voir_vente,
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn_ventes,
            text="❌ Annuler vente",
            width=130,
            fg_color="#dc3545",
            hover_color="#a71d2a",
            command=self._annuler_vente,
        ).pack(side="left", padx=(6, 0))

        # ── Stats ─────────────────────────────────────────────────────────────
        sep2 = ctk.CTkFrame(frame, height=2, fg_color="#444")
        sep2.pack(fill="x", pady=8)

        self._lbl_stats_billet = ctk.CTkLabel(
            frame,
            text="Total billets : — | Recette brute : — | Net : —",
            font=fonts.get("small"),
        )
        self._lbl_stats_billet.pack(anchor="w")

    def _charger_billetterie(self) -> None:
        if not self._evenement_id:
            return
        # Tarifs
        for item in self._tree_tarifs.get_children():
            self._tree_tarifs.delete(item)
        for t in get_tarifs_evenement(self._evenement_id):
            self._tree_tarifs.insert(
                "",
                "end",
                values=(
                    t["id"],
                    t["nom"],
                    f"{t['prix']:.2f} €",
                    "✅" if t["est_gratuit"] else "❌",
                ),
            )
        # Ventes
        for item in self._tree_ventes.get_children():
            self._tree_ventes.delete(item)
        for v in get_ventes_evenement(self._evenement_id):
            tag = v["statut"] if v["statut"] != "valide" else ""
            self._tree_ventes.insert(
                "",
                "end",
                values=(
                    v["id"],
                    self._format_date(v.get("date", "")),
                    CANAUX.get(v["canal"], v["canal"]),
                    MODES_PAIEMENT.get(v["mode_paiement"], v["mode_paiement"]),
                    f"{v['montant_total']:.2f} €",
                    v["statut"].capitalize(),
                ),
                tags=(tag,),
            )
        # Stats
        stats = get_stats_billetterie(self._evenement_id)
        self._lbl_stats_billet.configure(
            text=(
                f"Total billets : {stats['total_billets']} | "
                f"Recette brute : {self._fmt(stats['total_recette'])} | "
                f"Net : {self._fmt(stats['total_net'])}"
            )
        )

    def _ajouter_tarif(self) -> None:
        if not self._evenement_id:
            afficher_erreur(self, "Erreur", "Veuillez d'abord sauvegarder l'événement.")
            return
        dialog = _DialogTarif(self)
        self.wait_window(dialog)
        if dialog.result:
            erreurs = valider_tarif(dialog.result["nom"], dialog.result["prix"])
            if erreurs:
                afficher_erreur(self, "Erreur", "\n".join(erreurs))
                return
            tarifs = get_tarifs_evenement(self._evenement_id)
            ordre = len(tarifs)
            add_tarif(
                self._evenement_id,
                dialog.result["nom"],
                float(str(dialog.result["prix"]).replace(",", ".")),
                1 if dialog.result["est_gratuit"] else 0,
                ordre,
            )
            self._charger_billetterie()

    def _modifier_tarif(self) -> None:
        sel = self._tree_tarifs.selection()
        if not sel:
            return
        vals = self._tree_tarifs.item(sel[0], "values")
        tarif_id = int(vals[0])
        tarifs = get_tarifs_evenement(self._evenement_id)
        tarif = next((t for t in tarifs if t["id"] == tarif_id), None)
        if not tarif:
            return
        dialog = _DialogTarif(self, tarif=tarif)
        self.wait_window(dialog)
        if dialog.result:
            erreurs = valider_tarif(dialog.result["nom"], dialog.result["prix"])
            if erreurs:
                afficher_erreur(self, "Erreur", "\n".join(erreurs))
                return
            update_tarif(
                tarif_id,
                nom=dialog.result["nom"],
                prix=float(str(dialog.result["prix"]).replace(",", ".")),
                est_gratuit=1 if dialog.result["est_gratuit"] else 0,
            )
            self._charger_billetterie()

    def _supprimer_tarif(self) -> None:
        sel = self._tree_tarifs.selection()
        if not sel:
            return
        vals = self._tree_tarifs.item(sel[0], "values")
        tarif_id = int(vals[0])
        if demander_confirmation(self, "Supprimer", "Supprimer ce tarif ?"):
            delete_tarif(tarif_id)
            self._charger_billetterie()

    def _nouvelle_vente(self) -> None:
        if not self._evenement_id:
            afficher_erreur(self, "Erreur", "Veuillez d'abord sauvegarder l'événement.")
            return
        tarifs = get_tarifs_evenement(self._evenement_id)
        if not tarifs:
            afficher_erreur(
                self,
                "Erreur",
                "Ajoutez au moins un tarif avant d'enregistrer une vente.",
            )
            return
        dialog = _DialogVente(self, self._evenement_id, tarifs)
        self.wait_window(dialog)
        if dialog.result:
            self._enregistrer_vente(dialog.result)
            self._charger_billetterie()
            self._actualiser_resume_financier()

    def _enregistrer_vente(self, data: dict) -> None:
        taux_str = get_parametre("taux_sumup") or "1.75"
        taux = float(taux_str)

        lignes = [ligne for ligne in data["lignes"] if int(ligne["quantite"]) > 0]
        montant_total = sum(
            int(ligne["quantite"])
            * float(str(ligne["prix_unitaire"]).replace(",", "."))
            for ligne in lignes
        )
        frais = (
            calculer_frais_sumup(montant_total, taux)
            if data["mode_paiement"] in {"sumup", "carte"}
            else 0.0
        )
        montant_net = montant_total - frais

        vente_id = add_vente(
            evenement_id=self._evenement_id,
            date=data["date"],
            canal=data["canal"],
            mode_paiement=data["mode_paiement"],
            nom_tireur=data.get("nom_tireur"),
            montant_total=montant_total,
            frais_sumup=frais,
            montant_net=montant_net,
            commentaire=data.get("commentaire"),
        )

        # Compteur par tarif pour la numérotation
        compteurs: dict[int, int] = {}
        for ligne in lignes:
            tarif_id = ligne["tarif_id"]
            qte = int(ligne["quantite"])
            prix_u = float(str(ligne["prix_unitaire"]).replace(",", "."))
            ligne_id = add_vente_ligne(vente_id, tarif_id, qte, prix_u)

            tarif_nom = ligne.get("tarif_nom", str(tarif_id))
            for _ in range(qte):
                compteurs[tarif_id] = compteurs.get(tarif_id, 0) + 1
                numero = generer_numero_billet(
                    self._evenement_id, tarif_nom, compteurs[tarif_id]
                )
                add_billet(ligne_id, numero, tarif_id)

    def _voir_vente(self) -> None:
        sel = self._tree_ventes.selection()
        if not sel:
            return
        vals = self._tree_ventes.item(sel[0], "values")
        vente_id = int(vals[0])
        lignes = get_lignes_vente(vente_id)
        texte = "\n".join(
            f"  {ligne['tarif_nom']}  ×{ligne['quantite']}  = {ligne['sous_total']:.2f} €"
            for ligne in lignes
        )
        afficher_info(self, "Détail de la vente", texte or "Aucune ligne.")

    def _annuler_vente(self) -> None:
        sel = self._tree_ventes.selection()
        if not sel:
            return
        vals = self._tree_ventes.item(sel[0], "values")
        vente_id = int(vals[0])
        # Vérifie le statut réel depuis la base (pas le texte affiché)
        ventes = get_ventes_evenement(self._evenement_id)
        vente = next((v for v in ventes if v["id"] == vente_id), None)
        if vente and vente["statut"] == "annule":
            afficher_info(self, "Info", "Cette vente est déjà annulée.")
            return
        if demander_confirmation(
            self, "Annuler la vente", "Confirmer l'annulation de cette vente ?"
        ):
            dialog = _DialogMotif(self)
            self.wait_window(dialog)
            motif = dialog.motif or ""
            annuler_vente(vente_id, motif)
            self._charger_billetterie()
            self._actualiser_resume_financier()

    # ══════════════════════════════════════════════════════════════════════════
    # Onglet Dépenses
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_depenses(self, parent: Any) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        frame_top = ctk.CTkFrame(frame, fg_color="transparent")
        frame_top.pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            frame_top,
            text="+ Ajouter une dépense",
            width=170,
            command=self._ajouter_depense,
        ).pack(side="left")

        frame_table = ctk.CTkFrame(frame)
        frame_table.pack(fill="both", expand=True)

        self._tree_depenses = ttk.Treeview(
            frame_table,
            columns=("id", "libelle", "montant", "date", "fournisseur", "mode"),
            show="headings",
            height=16,
        )
        self._tree_depenses.heading("id", text="ID")
        self._tree_depenses.heading("libelle", text="Libellé")
        self._tree_depenses.heading("montant", text="Montant")
        self._tree_depenses.heading("date", text="Date")
        self._tree_depenses.heading("fournisseur", text="Fournisseur")
        self._tree_depenses.heading("mode", text="Paiement")

        self._tree_depenses.column("id", width=50, anchor="center", stretch=False)
        self._tree_depenses.column("libelle", width=280)
        self._tree_depenses.column("montant", width=110, anchor="e")
        self._tree_depenses.column("date", width=100, anchor="center")
        self._tree_depenses.column("fournisseur", width=160)
        self._tree_depenses.column("mode", width=100, anchor="center")

        sd = ttk.Scrollbar(
            frame_table, orient="vertical", command=self._tree_depenses.yview
        )
        self._tree_depenses.configure(yscrollcommand=sd.set)
        self._tree_depenses.pack(side="left", fill="both", expand=True)
        sd.pack(side="right", fill="y")

        frame_bas = ctk.CTkFrame(frame, fg_color="transparent")
        frame_bas.pack(fill="x", pady=6)

        ctk.CTkButton(
            frame_bas,
            text="✏️ Modifier",
            width=100,
            command=self._modifier_depense,
        ).pack(side="left")
        ctk.CTkButton(
            frame_bas,
            text="🗑️ Supprimer",
            width=110,
            fg_color="#dc3545",
            hover_color="#a71d2a",
            command=self._supprimer_depense,
        ).pack(side="left", padx=(6, 0))

        self._lbl_total_depenses = ctk.CTkLabel(frame, text="Total dépenses : —")
        self._lbl_total_depenses.pack(anchor="w", padx=4, pady=(4, 0))

    def _charger_depenses(self) -> None:
        if not self._evenement_id:
            return
        for item in self._tree_depenses.get_children():
            self._tree_depenses.delete(item)
        total = 0.0
        for d in get_depenses_evenement(self._evenement_id):
            total += float(d["montant"] or 0)
            self._tree_depenses.insert(
                "",
                "end",
                values=(
                    d["id"],
                    d["libelle"],
                    f"{d['montant']:.2f} €",
                    self._format_date(d.get("date", "")),
                    d.get("fournisseur_nom") or "",
                    MODES_DEPENSE.get(d.get("mode_paiement") or "", "—"),
                ),
            )
        self._lbl_total_depenses.configure(text=f"Total dépenses : {self._fmt(total)}")

    def _ajouter_depense(self) -> None:
        if not self._evenement_id:
            afficher_erreur(self, "Erreur", "Veuillez d'abord sauvegarder l'événement.")
            return
        dialog = _DialogDepense(self)
        self.wait_window(dialog)
        if dialog.result:
            add_depense(
                evenement_id=self._evenement_id,
                libelle=dialog.result["libelle"],
                montant=float(str(dialog.result["montant"]).replace(",", ".")),
                date=dialog.result["date"],
                categorie=dialog.result.get("categorie"),
                fournisseur_id=dialog.result.get("fournisseur_id"),
                mode_paiement=dialog.result.get("mode_paiement"),
                commentaire=dialog.result.get("commentaire"),
            )
            self._charger_depenses()
            self._actualiser_resume_financier()

    def _modifier_depense(self) -> None:
        sel = self._tree_depenses.selection()
        if not sel:
            return
        vals = self._tree_depenses.item(sel[0], "values")
        depense_id = int(vals[0])
        depenses = get_depenses_evenement(self._evenement_id)
        dep = next((d for d in depenses if d["id"] == depense_id), None)
        if not dep:
            return
        dialog = _DialogDepense(self, depense=dep)
        self.wait_window(dialog)
        if dialog.result:
            update_depense(
                depense_id,
                libelle=dialog.result["libelle"],
                montant=float(str(dialog.result["montant"]).replace(",", ".")),
                date=dialog.result["date"],
                categorie=dialog.result.get("categorie"),
                fournisseur_id=dialog.result.get("fournisseur_id"),
                mode_paiement=dialog.result.get("mode_paiement"),
                commentaire=dialog.result.get("commentaire"),
            )
            self._charger_depenses()
            self._actualiser_resume_financier()

    def _supprimer_depense(self) -> None:
        sel = self._tree_depenses.selection()
        if not sel:
            return
        vals = self._tree_depenses.item(sel[0], "values")
        depense_id = int(vals[0])
        if demander_confirmation(self, "Supprimer", "Supprimer cette dépense ?"):
            delete_depense(depense_id)
            self._charger_depenses()
            self._actualiser_resume_financier()

    # ══════════════════════════════════════════════════════════════════════════
    # Onglet Budget
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_budget(self, parent: Any) -> None:
        self._budget_view = BudgetEvenementView(parent, self._evenement_id)
        self._budget_view.pack(fill="both", expand=True, padx=10, pady=10)

    # ══════════════════════════════════════════════════════════════════════════
    # Onglet Bénévoles
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_benevoles(self, parent: Any) -> None:
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        frame_top = ctk.CTkFrame(frame, fg_color="transparent")
        frame_top.pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            frame_top,
            text="+ Ajouter un bénévole",
            width=170,
            command=self._ajouter_benevole,
        ).pack(side="left")

        frame_table = ctk.CTkFrame(frame)
        frame_table.pack(fill="both", expand=True)

        self._tree_benevoles = ttk.Treeview(
            frame_table,
            columns=("id", "nom", "role", "heures", "statut"),
            show="headings",
            height=16,
        )
        self._tree_benevoles.heading("id", text="ID")
        self._tree_benevoles.heading("nom", text="Nom")
        self._tree_benevoles.heading("role", text="Rôle")
        self._tree_benevoles.heading("heures", text="Heures")
        self._tree_benevoles.heading("statut", text="Statut")

        self._tree_benevoles.column("id", width=50, anchor="center", stretch=False)
        self._tree_benevoles.column("nom", width=260)
        self._tree_benevoles.column("role", width=160)
        self._tree_benevoles.column("heures", width=130, anchor="center")
        self._tree_benevoles.column("statut", width=110, anchor="center")

        self._tree_benevoles.tag_configure("desiste", foreground="#dc3545")
        self._tree_benevoles.tag_configure("remplace", foreground="#fd7e14")

        sb = ttk.Scrollbar(
            frame_table, orient="vertical", command=self._tree_benevoles.yview
        )
        self._tree_benevoles.configure(yscrollcommand=sb.set)
        self._tree_benevoles.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        frame_bas = ctk.CTkFrame(frame, fg_color="transparent")
        frame_bas.pack(fill="x", pady=6)

        ctk.CTkButton(
            frame_bas,
            text="✏️ Modifier",
            width=100,
            command=self._modifier_benevole,
        ).pack(side="left")
        ctk.CTkButton(
            frame_bas,
            text="🗑️ Supprimer",
            width=110,
            fg_color="#dc3545",
            hover_color="#a71d2a",
            command=self._supprimer_benevole,
        ).pack(side="left", padx=(6, 0))

        self._lbl_stats_benevoles = ctk.CTkLabel(
            frame, text="Total : — bénévoles | — h confirmées"
        )
        self._lbl_stats_benevoles.pack(anchor="w", padx=4, pady=(4, 0))

    def _charger_benevoles(self) -> None:
        if not self._evenement_id:
            return
        for item in self._tree_benevoles.get_children():
            self._tree_benevoles.delete(item)

        for b in get_benevoles_evenement(self._evenement_id):
            if b.get("membre_id"):
                nom = f"{b.get('membre_nom', '')} {b.get('membre_prenom', '')}".strip()
            else:
                nom = (
                    f"{b.get('prenom_externe', '')} {b.get('nom_externe', '')}".strip()
                )
                if not nom:
                    nom = "(externe)"
                else:
                    nom += " (ext.)"

            heures = "—"
            if b.get("heure_debut") and b.get("heure_fin"):
                heures = f"{b['heure_debut']}–{b['heure_fin']}"

            tag = b["statut"] if b["statut"] != "confirme" else ""
            self._tree_benevoles.insert(
                "",
                "end",
                values=(
                    b["id"],
                    nom,
                    b.get("role") or "",
                    heures,
                    STATUTS_BENEVOLE.get(b["statut"], b["statut"]),
                ),
                tags=(tag,),
            )

        stats = get_stats_benevoles(self._evenement_id)
        h = stats["total_heures"]
        self._lbl_stats_benevoles.configure(
            text=f"Total : {stats['total']} bénévoles | {h:.1f} h confirmées"
        )

    def _ajouter_benevole(self) -> None:
        if not self._evenement_id:
            afficher_erreur(self, "Erreur", "Veuillez d'abord sauvegarder l'événement.")
            return
        membres = get_all_membres()
        dialog = _DialogBenevole(self, membres=membres)
        self.wait_window(dialog)
        if dialog.result:
            add_benevole(
                evenement_id=self._evenement_id,
                membre_id=dialog.result.get("membre_id"),
                nom_externe=dialog.result.get("nom_externe"),
                prenom_externe=dialog.result.get("prenom_externe"),
                role=dialog.result.get("role"),
                heure_debut=dialog.result.get("heure_debut"),
                heure_fin=dialog.result.get("heure_fin"),
                statut=dialog.result.get("statut", "confirme"),
                commentaire=dialog.result.get("commentaire"),
            )
            self._charger_benevoles()

    def _modifier_benevole(self) -> None:
        sel = self._tree_benevoles.selection()
        if not sel:
            return
        vals = self._tree_benevoles.item(sel[0], "values")
        benevole_id = int(vals[0])
        benevoles = get_benevoles_evenement(self._evenement_id)
        ben = next((b for b in benevoles if b["id"] == benevole_id), None)
        if not ben:
            return
        membres = get_all_membres()
        dialog = _DialogBenevole(self, membres=membres, benevole=ben)
        self.wait_window(dialog)
        if dialog.result:
            update_benevole(
                benevole_id,
                membre_id=dialog.result.get("membre_id"),
                nom_externe=dialog.result.get("nom_externe"),
                prenom_externe=dialog.result.get("prenom_externe"),
                role=dialog.result.get("role"),
                heure_debut=dialog.result.get("heure_debut"),
                heure_fin=dialog.result.get("heure_fin"),
                statut=dialog.result.get("statut", "confirme"),
                commentaire=dialog.result.get("commentaire"),
            )
            self._charger_benevoles()

    def _supprimer_benevole(self) -> None:
        sel = self._tree_benevoles.selection()
        if not sel:
            return
        vals = self._tree_benevoles.item(sel[0], "values")
        benevole_id = int(vals[0])
        if demander_confirmation(
            self, "Supprimer", "Supprimer ce bénévole de l'événement ?"
        ):
            delete_benevole(benevole_id)
            self._charger_benevoles()

    # ══════════════════════════════════════════════════════════════════════════
    # Onglets Phase 5b
    # ══════════════════════════════════════════════════════════════════════════

    def _build_onglet_tombola(self, parent: Any) -> None:
        self._tombola_view = TombolaView(parent, self._evenement_id)
        self._tombola_view.pack(fill="both", expand=True)

    def _build_onglet_stands(self, parent: Any) -> None:
        self._stands_view = StandsView(parent, self._evenement_id)
        self._stands_view.pack(fill="both", expand=True)

    def _build_onglet_tableaux(self, parent: Any) -> None:
        self._tableaux_view = TableauxView(parent, self._evenement_id)
        self._tableaux_view.pack(fill="both", expand=True)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(val: float) -> str:
        return f"{val:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return value or ""


# ══════════════════════════════════════════════════════════════════════════════
# Dialogues auxiliaires
# ══════════════════════════════════════════════════════════════════════════════


class _DialogTarif(ctk.CTkToplevel):
    """Dialogue de création/édition d'un tarif."""

    def __init__(self, parent: Any, tarif: dict | None = None) -> None:
        super().__init__(parent)
        self.title("Tarif")
        self.geometry("400x280")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None

        self._var_nom = tk.StringVar(value=tarif["nom"] if tarif else "")
        self._var_prix = tk.StringVar(
            value=f"{tarif['prix']:.2f}".replace(".", ",") if tarif else "0,00"
        )
        self._var_gratuit = tk.BooleanVar(
            value=bool(tarif["est_gratuit"]) if tarif else False
        )

        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Nom du tarif *").pack(
            anchor="w", padx=20, pady=(16, 2)
        )
        ctk.CTkEntry(self, textvariable=self._var_nom, width=320).pack(padx=20)

        ctk.CTkLabel(self, text="Prix (€)").pack(anchor="w", padx=20, pady=(10, 2))
        ctk.CTkEntry(self, textvariable=self._var_prix, width=320).pack(padx=20)

        ctk.CTkCheckBox(self, text="Tarif gratuit", variable=self._var_gratuit).pack(
            anchor="w", padx=20, pady=10
        )

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=(6, 16))
        ctk.CTkButton(frame_btn, text="Valider", width=100, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        self.result = {
            "nom": self._var_nom.get().strip(),
            "prix": self._var_prix.get().strip(),
            "est_gratuit": self._var_gratuit.get(),
        }
        self.destroy()


class _DialogVente(ctk.CTkToplevel):
    """Dialogue d'enregistrement d'une vente billetterie."""

    def __init__(self, parent: Any, evenement_id: int, tarifs: list[dict]) -> None:
        super().__init__(parent)
        self.title("Enregistrer une vente")
        self.geometry("560x580")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._tarifs = tarifs
        self._evenement_id = evenement_id

        self._var_date = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._var_canal = tk.StringVar(value="Sur place")
        self._var_mode = tk.StringVar(value="Espèces")
        self._var_nom_tireur = tk.StringVar()
        self._var_commentaire = tk.StringVar()
        self._qtés: list[tk.StringVar] = []

        self._build()

    def _build(self) -> None:
        fonts = app_theme.FONTS

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=160, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field(
            "Date *", lambda p: ctk.CTkEntry(p, textvariable=self._var_date, width=180)
        )
        field(
            "Canal *",
            lambda p: ctk.CTkOptionMenu(
                p, values=list(CANAUX.values()), variable=self._var_canal, width=180
            ),
        )
        self._combo_mode = field(
            "Mode paiement *",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(MODES_PAIEMENT.values()),
                variable=self._var_mode,
                command=self._on_mode_change,
                width=180,
            ),
        )
        self._frame_tireur = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_tireur.pack(fill="x", pady=3)
        ctk.CTkLabel(
            self._frame_tireur, text="Nom du tireur", width=160, anchor="e"
        ).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(
            self._frame_tireur, textvariable=self._var_nom_tireur, width=180
        ).pack(side="left")
        self._frame_tireur.pack_forget()

        sep = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep.pack(fill="x", pady=6)

        ctk.CTkLabel(scroll, text="Tarifs", font=fonts.get("bold")).pack(
            anchor="w", pady=(0, 4)
        )

        for tarif in self._tarifs:
            var_qte = tk.StringVar(value="0")
            self._qtés.append(var_qte)
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(
                f,
                text=f"{tarif['nom']}  ({tarif['prix']:.2f} €)",
                width=220,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(f, text="Qté :").pack(side="left", padx=(8, 4))
            ctk.CTkEntry(f, textvariable=var_qte, width=60).pack(side="left")
            var_qte.trace_add("write", self._actualiser_total)

        sep2 = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep2.pack(fill="x", pady=6)

        self._lbl_total = ctk.CTkLabel(scroll, text="Montant total : 0,00 €")
        self._lbl_total.pack(anchor="w")
        self._lbl_frais = ctk.CTkLabel(scroll, text="", text_color="#888")
        self._lbl_frais.pack(anchor="w")
        self._lbl_net = ctk.CTkLabel(scroll, text="")
        self._lbl_net.pack(anchor="w")

        sep3 = ctk.CTkFrame(scroll, height=2, fg_color="#444")
        sep3.pack(fill="x", pady=6)

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=4)
        ctk.CTkButton(frame_btn, text="Valider", width=100, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _on_mode_change(self, val: str) -> None:
        if val == "Chèque":
            self._frame_tireur.pack(fill="x", pady=3)
        else:
            self._frame_tireur.pack_forget()
        self._actualiser_total()

    def _actualiser_total(self, *_) -> None:
        total = 0.0
        for tarif, var in zip(self._tarifs, self._qtés):
            try:
                qte = int(var.get())
                total += qte * float(tarif["prix"])
            except (ValueError, TypeError):
                pass

        taux_str = get_parametre("taux_sumup") or "1.75"
        taux = float(taux_str)
        mode = MODES_INV.get(self._var_mode.get(), "especes")
        frais = calculer_frais_sumup(total, taux) if mode in {"sumup", "carte"} else 0.0
        net = total - frais

        self._lbl_total.configure(
            text=f"Montant total : {total:,.2f} €".replace(",", " ").replace(".", ",")
        )
        if mode in {"sumup", "carte"}:
            self._lbl_frais.configure(
                text=f"Frais SumUp ({taux}%) : {frais:,.2f} €".replace(
                    ",", " "
                ).replace(".", ",")
            )
        else:
            self._lbl_frais.configure(text="")
        self._lbl_net.configure(
            text=f"Montant net : {net:,.2f} €".replace(",", " ").replace(".", ",")
        )

    def _valider(self) -> None:
        lignes = []
        for tarif, var in zip(self._tarifs, self._qtés):
            try:
                qte = int(var.get())
            except (ValueError, TypeError):
                qte = 0
            lignes.append(
                {
                    "tarif_id": tarif["id"],
                    "tarif_nom": tarif["nom"],
                    "quantite": qte,
                    "prix_unitaire": tarif["prix"],
                }
            )

        mode = MODES_INV.get(self._var_mode.get(), "especes")
        erreurs = valider_vente(lignes, mode)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return

        self.result = {
            "date": self._var_date.get().strip(),
            "canal": CANAUX_INV.get(self._var_canal.get(), "sur_place"),
            "mode_paiement": mode,
            "nom_tireur": self._var_nom_tireur.get().strip() or None,
            "commentaire": self._var_commentaire.get().strip() or None,
            "lignes": lignes,
        }
        self.destroy()


class _DialogDepense(ctk.CTkToplevel):
    """Dialogue de création/édition d'une dépense."""

    def __init__(self, parent: Any, depense: dict | None = None) -> None:
        super().__init__(parent)
        self.title("Dépense")
        self.geometry("460x440")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._depense = depense

        self._var_libelle = tk.StringVar(value=depense["libelle"] if depense else "")
        self._var_montant = tk.StringVar(
            value=f"{depense['montant']:.2f}".replace(".", ",") if depense else ""
        )
        self._var_date = tk.StringVar(
            value=depense["date"] if depense else date.today().strftime("%Y-%m-%d")
        )
        self._var_categorie = tk.StringVar(
            value=depense.get("categorie") or "" if depense else ""
        )
        self._var_mode = tk.StringVar(
            value=(
                MODES_DEPENSE.get(depense.get("mode_paiement") or "", "—")
                if depense
                else "—"
            )
        )
        self._var_commentaire = tk.StringVar(
            value=depense.get("commentaire") or "" if depense else ""
        )
        self._fournisseurs: list[dict] = []
        self._fournisseur_id: int | None = (
            depense.get("fournisseur_id") if depense else None
        )

        try:
            self._fournisseurs = get_all_fournisseurs()
        except Exception:
            pass

        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=140, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field(
            "Libellé *",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_libelle, width=240),
        )
        field(
            "Montant *",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_montant, width=240),
        )
        field(
            "Date *",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_date, width=240, placeholder_text="AAAA-MM-JJ"
            ),
        )
        field(
            "Catégorie",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_categorie, width=240),
        )

        # Fournisseur
        f_four = ctk.CTkFrame(scroll, fg_color="transparent")
        f_four.pack(fill="x", pady=3)
        ctk.CTkLabel(f_four, text="Fournisseur", width=140, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        noms = ["— Aucun —"] + [f["nom"] for f in self._fournisseurs]
        self._combo_fournisseur = ctk.CTkOptionMenu(f_four, values=noms, width=240)
        if self._fournisseur_id:
            four = next(
                (f for f in self._fournisseurs if f["id"] == self._fournisseur_id), None
            )
            self._combo_fournisseur.set(four["nom"] if four else "— Aucun —")
        else:
            self._combo_fournisseur.set("— Aucun —")
        self._combo_fournisseur.pack(side="left")

        field(
            "Mode paiement",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(MODES_DEPENSE.values()),
                variable=self._var_mode,
                width=240,
            ),
        )
        field(
            "Commentaire",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_commentaire, width=240),
        )

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=(12, 4))
        ctk.CTkButton(frame_btn, text="Valider", width=100, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        libelle = self._var_libelle.get().strip()
        if not libelle:
            afficher_erreur(self, "Erreur", "Le libellé est obligatoire.")
            return
        montant_str = self._var_montant.get().strip().replace(",", ".")
        try:
            montant = float(montant_str)
        except ValueError:
            afficher_erreur(self, "Erreur", "Le montant doit être un nombre valide.")
            return
        date_val = self._var_date.get().strip()
        if not date_val:
            afficher_erreur(self, "Erreur", "La date est obligatoire.")
            return

        sel_four = self._combo_fournisseur.get()
        fournisseur_id: int | None = None
        if sel_four != "— Aucun —":
            four = next((f for f in self._fournisseurs if f["nom"] == sel_four), None)
            if four:
                fournisseur_id = four["id"]

        mode_label = self._var_mode.get()
        mode_inv = {v: k for k, v in MODES_DEPENSE.items()}
        mode = mode_inv.get(mode_label, None) or None

        self.result = {
            "libelle": libelle,
            "montant": montant,
            "date": date_val,
            "categorie": self._var_categorie.get().strip() or None,
            "fournisseur_id": fournisseur_id,
            "mode_paiement": mode,
            "commentaire": self._var_commentaire.get().strip() or None,
        }
        self.destroy()


class _DialogBenevole(ctk.CTkToplevel):
    """Dialogue de création/édition d'un bénévole."""

    def __init__(
        self,
        parent: Any,
        membres: list[dict],
        benevole: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Bénévole")
        self.geometry("460x460")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._membres = membres
        self._benevole = benevole

        # Type (membre / externe)
        is_membre = bool(benevole and benevole.get("membre_id")) if benevole else True
        self._var_type = tk.StringVar(value="Membre" if is_membre else "Externe")
        self._var_membre = tk.StringVar()
        self._var_nom_ext = tk.StringVar(
            value=benevole.get("nom_externe") or "" if benevole else ""
        )
        self._var_prenom_ext = tk.StringVar(
            value=benevole.get("prenom_externe") or "" if benevole else ""
        )
        self._var_role = tk.StringVar(
            value=benevole.get("role") or "" if benevole else ""
        )
        self._var_h_debut = tk.StringVar(
            value=benevole.get("heure_debut") or "" if benevole else ""
        )
        self._var_h_fin = tk.StringVar(
            value=benevole.get("heure_fin") or "" if benevole else ""
        )
        self._var_statut = tk.StringVar(
            value=(
                STATUTS_BENEVOLE.get(benevole.get("statut", "confirme"), "Confirmé")
                if benevole
                else "Confirmé"
            )
        )
        self._var_commentaire = tk.StringVar(
            value=benevole.get("commentaire") or "" if benevole else ""
        )

        # Pré-sélection membre
        if benevole and benevole.get("membre_id"):
            mem = next((m for m in membres if m["id"] == benevole["membre_id"]), None)
            if mem:
                self._var_membre.set(f"{mem['prenom']} {mem['nom']}")

        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        # Type
        f_type = ctk.CTkFrame(scroll, fg_color="transparent")
        f_type.pack(fill="x", pady=4)
        ctk.CTkLabel(f_type, text="Type", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkRadioButton(
            f_type,
            text="Membre",
            variable=self._var_type,
            value="Membre",
            command=self._on_type_change,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            f_type,
            text="Externe",
            variable=self._var_type,
            value="Externe",
            command=self._on_type_change,
        ).pack(side="left")

        # Bloc membre
        self._frame_membre = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_membre.pack(fill="x", pady=3)
        ctk.CTkLabel(self._frame_membre, text="Membre", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        noms_membres = [f"{m['prenom']} {m['nom']}" for m in self._membres]
        self._combo_membre = ctk.CTkOptionMenu(
            self._frame_membre, values=noms_membres or ["—"], width=240
        )
        if self._var_membre.get() and self._var_membre.get() in noms_membres:
            self._combo_membre.set(self._var_membre.get())
        elif noms_membres:
            self._combo_membre.set(noms_membres[0])
        self._combo_membre.pack(side="left")

        # Bloc externe
        self._frame_externe = ctk.CTkFrame(scroll, fg_color="transparent")

        f_prenom = ctk.CTkFrame(self._frame_externe, fg_color="transparent")
        f_prenom.pack(fill="x", pady=2)
        ctk.CTkLabel(f_prenom, text="Prénom", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(f_prenom, textvariable=self._var_prenom_ext, width=240).pack(
            side="left"
        )

        f_nom = ctk.CTkFrame(self._frame_externe, fg_color="transparent")
        f_nom.pack(fill="x", pady=2)
        ctk.CTkLabel(f_nom, text="Nom", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(f_nom, textvariable=self._var_nom_ext, width=240).pack(side="left")

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=130, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field("Rôle", lambda p: ctk.CTkEntry(p, textvariable=self._var_role, width=240))
        field(
            "Heure début",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_h_debut, width=100, placeholder_text="HH:MM"
            ),
        )
        field(
            "Heure fin",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_h_fin, width=100, placeholder_text="HH:MM"
            ),
        )
        field(
            "Statut",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(STATUTS_BENEVOLE.values()),
                variable=self._var_statut,
                width=180,
            ),
        )
        field(
            "Commentaire",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_commentaire, width=240),
        )

        self._on_type_change()

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=(12, 4))
        ctk.CTkButton(frame_btn, text="Valider", width=100, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _on_type_change(self) -> None:
        if self._var_type.get() == "Membre":
            self._frame_membre.pack(
                fill="x", pady=3, after=self._frame_membre.master.winfo_children()[1]
            )
            self._frame_externe.pack_forget()
        else:
            self._frame_membre.pack_forget()
            self._frame_externe.pack(
                fill="x", pady=3, after=self._frame_externe.master.winfo_children()[1]
            )

    def _valider(self) -> None:
        statut_label = self._var_statut.get()
        statut = STATUTS_BEN_INV.get(statut_label, "confirme")

        if self._var_type.get() == "Membre":
            sel = self._combo_membre.get()
            mem = next(
                (m for m in self._membres if f"{m['prenom']} {m['nom']}" == sel), None
            )
            if not mem:
                afficher_erreur(self, "Erreur", "Veuillez sélectionner un membre.")
                return
            self.result = {
                "membre_id": mem["id"],
                "nom_externe": None,
                "prenom_externe": None,
                "role": self._var_role.get().strip() or None,
                "heure_debut": self._var_h_debut.get().strip() or None,
                "heure_fin": self._var_h_fin.get().strip() or None,
                "statut": statut,
                "commentaire": self._var_commentaire.get().strip() or None,
            }
        else:
            self.result = {
                "membre_id": None,
                "nom_externe": self._var_nom_ext.get().strip() or None,
                "prenom_externe": self._var_prenom_ext.get().strip() or None,
                "role": self._var_role.get().strip() or None,
                "heure_debut": self._var_h_debut.get().strip() or None,
                "heure_fin": self._var_h_fin.get().strip() or None,
                "statut": statut,
                "commentaire": self._var_commentaire.get().strip() or None,
            }
        self.destroy()


class _DialogMotif(ctk.CTkToplevel):
    """Dialogue pour saisir un motif d'annulation."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Motif d'annulation")
        self.geometry("380x180")
        self.resizable(False, False)
        self.transient(parent)
        self.motif: str = ""
        self._var = tk.StringVar()

        ctk.CTkLabel(self, text="Motif (optionnel) :").pack(
            anchor="w", padx=20, pady=(16, 4)
        )
        ctk.CTkEntry(self, textvariable=self._var, width=320).pack(padx=20)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(pady=16)
        ctk.CTkButton(frame_btn, text="Confirmer", width=110, command=self._ok).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _ok(self) -> None:
        self.motif = self._var.get().strip()
        self.destroy()
