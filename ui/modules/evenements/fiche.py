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
from db.models.membres import get_all_membres
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, afficher_succes, demander_confirmation
from ui.modules.evenements.budget_evenement import BudgetEvenementView
from ui.modules.evenements.caisses import CaissesEvenementView
from ui.modules.evenements.constantes import (
    CANAUX,
    CANAUX_INV,
    LABELS_STATUT,
    LIBELLES_MODULES,
    MODES_INV,
    MODES_PAIEMENT,
    MODULES_CREATION_INITIAUX,
    ONGLETS_MODULES,
    STATUTS_BENEVOLE,
    STATUTS_BEN_INV,
    STATUTS_EVENEMENT,
    STATUTS_LABELS,
)
from ui.modules.evenements.benevole_dialog import _DialogBenevole
from ui.modules.evenements.billetterie_dialogs import (
    _DialogMotif,
    _DialogTarif,
    _DialogVente,
)
from ui.modules.evenements.modules_dialog import _DialogModules
from ui.modules.evenements.depense_dialog import MODES_DEPENSE, _DialogDepense
from ui.modules.evenements.stands import StandsView
from ui.modules.evenements.tableaux import TableauxView
from ui.modules.evenements.tombola import TombolaView
from utils.logger import get_logger

logger = get_logger(__name__)


__all__ = [
    "CANAUX",
    "CANAUX_INV",
    "FicheEvenement",
    "LABELS_STATUT",
    "LIBELLES_MODULES",
    "MODES_INV",
    "MODES_PAIEMENT",
    "MODULES_CREATION_INITIAUX",
    "ONGLETS_MODULES",
    "STATUTS_BENEVOLE",
    "STATUTS_BEN_INV",
    "STATUTS_EVENEMENT",
    "STATUTS_LABELS",
    "_DialogBenevole",
    "_DialogDepense",
    "_DialogModules",
    "_DialogMotif",
    "_DialogTarif",
    "_DialogVente",
]


def serialiser_modules_depuis_cases(
    vars_modules: dict[str, tk.BooleanVar | bool],
) -> str:
    """Sérialise les modules actifs depuis des cases à cocher ou booléens."""
    modules = [
        module
        for module, var in vars_modules.items()
        if bool(var.get() if hasattr(var, "get") else var)
    ]
    return serialiser_modules_actifs(modules)


def _onglets_modules_a_masquer(modules_actifs: set[str]) -> list[str]:
    """Retourne les onglets associés à des modules désactivés."""
    if modules_actifs == set(MODULES_EVENEMENT_DISPONIBLES):
        return []
    return [
        nom_onglet
        for nom_onglet, modules_onglet in ONGLETS_MODULES.items()
        if not modules_actifs.intersection(modules_onglet)
    ]


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
        self._build_header()
        self._build_tabs()

    def _build_header(self) -> None:
        fonts = app_theme.FONTS

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

    def _build_tabs(self) -> None:
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
        self._tabs.add("🧾 Caisses")

        self._build_onglet_general(self._tabs.tab("📋 Général"))
        self._build_onglet_billetterie(self._tabs.tab("🎫 Billetterie"))
        self._build_onglet_depenses(self._tabs.tab("💸 Dépenses"))
        self._build_onglet_budget(self._tabs.tab("💰 Budget"))
        self._build_onglet_benevoles(self._tabs.tab("👥 Bénévoles"))
        self._build_onglet_tombola(self._tabs.tab("🎰 Tombola"))
        self._build_onglet_stands(self._tabs.tab("🏪 Stands"))
        self._build_onglet_tableaux(self._tabs.tab("📊 Tableaux"))
        self._build_onglet_caisses(self._tabs.tab("🧾 Caisses"))

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
            var = tk.BooleanVar(value=module in MODULES_CREATION_INITIAUX)
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

        self._lbl_recettes = ctk.CTkLabel(frame, text="Recettes globales : —")
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
            text="💾 Enregistrer",
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
        self._caisses_view.set_evenement_id(self._evenement_id)
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
            logger.exception("Impossible d'enregistrer l'événement %s.", self._evenement_id)
            afficher_erreur(self, "Erreur", str(exc))
            return

        self._evenement = get_evenement_by_id(self._evenement_id) if self._evenement_id else None
        self._actualiser_resume_financier()
        self._budget_view.set_evenement_id(self._evenement_id)
        self._tombola_view.set_evenement_id(self._evenement_id)
        self._stands_view.set_evenement_id(self._evenement_id)
        self._tableaux_view.set_evenement_id(self._evenement_id)
        self._caisses_view.set_evenement_id(self._evenement_id)
        self._appliquer_modules_actifs()

    def _appliquer_modules_actifs(self) -> None:
        if not self._evenement:
            return
        modules_actifs = set(
            modules_actifs_depuis_json(self._evenement.get("modules_actifs_json"))
        )
        for nom_onglet in _onglets_modules_a_masquer(modules_actifs):
            try:
                self._tabs.delete(nom_onglet)
            except Exception:
                logger.warning(
                    "Impossible de masquer l'onglet événement %s.",
                    nom_onglet,
                    exc_info=True,
                )
                continue

    def _ouvrir_modules(self) -> None:
        modules_actuels = [
            mod for mod, var in self._vars_modules.items() if var.get()
        ]
        dialog = _DialogModules(self, modules_actuels)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.result is not None:
            self._definir_modules_selection(dialog.result)
            if self._evenement_id:
                modules_json = serialiser_modules_depuis_cases(self._vars_modules)
                try:
                    update_evenement(self._evenement_id, modules_actifs_json=modules_json)
                    if self._evenement:
                        self._evenement["modules_actifs_json"] = modules_json
                    afficher_succes(
                        self,
                        "Modules",
                        "Les modules ont été mis à jour avec succès.\n"
                        "Enregistrez ou rouvrez la fiche pour appliquer l'affichage des onglets.",
                    )
                except Exception as exc:
                    logger.exception(
                        "Impossible d'enregistrer les modules de l'événement %s.",
                        self._evenement_id,
                    )
                    afficher_erreur(self, "Erreur", f"Impossible d'enregistrer les modules :\n{exc}")

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
                text=f"Recettes globales : {self._fmt(bilan['recettes_total'])}"
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
            logger.exception(
                "Impossible d'actualiser le résumé financier de l'événement %s.",
                self._evenement_id,
            )

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
            columns=("id", "libelle", "montant", "date", "fournisseur", "mode", "avance_par", "remboursement"),
            show="headings",
            height=16,
        )
        self._tree_depenses.heading("id", text="ID")
        self._tree_depenses.heading("libelle", text="Libellé")
        self._tree_depenses.heading("montant", text="Montant")
        self._tree_depenses.heading("date", text="Date")
        self._tree_depenses.heading("fournisseur", text="Fournisseur")
        self._tree_depenses.heading("mode", text="Paiement")
        self._tree_depenses.heading("avance_par", text="Avancé par")
        self._tree_depenses.heading("remboursement", text="Remboursement")

        self._tree_depenses.column("id", width=50, anchor="center", stretch=False)
        self._tree_depenses.column("libelle", width=280)
        self._tree_depenses.column("montant", width=110, anchor="e")
        self._tree_depenses.column("date", width=100, anchor="center")
        self._tree_depenses.column("fournisseur", width=160)
        self._tree_depenses.column("mode", width=100, anchor="center")
        self._tree_depenses.column("avance_par", width=180)
        self._tree_depenses.column("remboursement", width=130, anchor="center")

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
                    f"{d.get('avance_par_nom') or ''} {d.get('avance_par_prenom') or ''}".strip(),
                    {"en_attente": "🟡 En attente", "rembourse": "🟢 Remboursé", "non_applicable": "⚫ Non applicable"}.get(d.get('remboursement_statut') or 'non_applicable', "⚫ Non applicable"),
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
                avance_par_membre_id=dialog.result.get("avance_par_membre_id"),
                remboursement_statut=dialog.result.get("remboursement_statut") or "non_applicable",
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
                avance_par_membre_id=dialog.result.get("avance_par_membre_id"),
                remboursement_statut=dialog.result.get("remboursement_statut") or "non_applicable",
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

    def _build_onglet_caisses(self, parent: Any) -> None:
        try:
            self._caisses_view = CaissesEvenementView(
                parent,
                self._evenement_id,
                callback_refresh=self._actualiser_resume_financier,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Impossible d'initialiser l'onglet Caisses : %s", exc)
            self._caisses_view = _CaissesUnavailableView(parent, str(exc))
        self._caisses_view.pack(fill="both", expand=True)

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


class _CaissesUnavailableView(ctk.CTkFrame):
    """Fallback affiché quand le module Caisses ne peut pas s'initialiser."""

    def __init__(self, parent: Any, detail: str) -> None:
        super().__init__(parent)
        ctk.CTkLabel(
            self,
            text=(
                "Le module Caisses est indisponible.\n"
                "Vérifiez les migrations de base de données (0021/0022) puis relancez."
            ),
            justify="left",
            text_color="#dc3545",
        ).pack(anchor="w", padx=12, pady=(12, 6))
        ctk.CTkLabel(self, text=f"Détail : {detail}", justify="left").pack(
            anchor="w", padx=12, pady=(0, 12)
        )

    def set_evenement_id(self, _evenement_id: int | None) -> None:
        return
