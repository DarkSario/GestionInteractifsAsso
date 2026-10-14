"""Construction des onglets de la fiche événement."""

from __future__ import annotations

from datetime import date
import tkinter as tk
from typing import Any

import customtkinter as ctk

from db.models.evenements import MODULES_EVENEMENT_DISPONIBLES
from ui import theme as app_theme
from ui.modules.evenements.constantes import (
    LABELS_STATUT,
    LIBELLES_MODULES,
    MODULES_CREATION_INITIAUX,
    ONGLETS_MODULES,
)


def _onglets_modules_a_masquer(modules_actifs: set[str]) -> list[str]:
    """Retourne les onglets associés à des modules désactivés."""
    if modules_actifs == set(MODULES_EVENEMENT_DISPONIBLES):
        return []
    return [
        nom_onglet
        for nom_onglet, modules_onglet in ONGLETS_MODULES.items()
        if not modules_actifs.intersection(modules_onglet)
    ]


class _OngletGeneralMixin:
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

        self._var_nom = tk.StringVar()
        row("Nom *", lambda p, **kw: ctk.CTkEntry(p, textvariable=self._var_nom, **kw))

        self._var_type = tk.StringVar()
        row("Type", lambda p, **kw: ctk.CTkEntry(p, textvariable=self._var_type, **kw))

        f_desc = ctk.CTkFrame(frame, fg_color="transparent")
        f_desc.pack(fill="x", pady=3)
        ctk.CTkLabel(f_desc, text="Description", width=180, anchor="ne").pack(
            side="left", padx=(0, 8), anchor="n", pady=2
        )
        self._txt_description = ctk.CTkTextbox(f_desc, height=80)
        self._txt_description.pack(side="left", fill="x", expand=True)

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

        self._var_statut = tk.StringVar(value="Planifié")
        row(
            "Statut",
            lambda p, **kw: ctk.CTkOptionMenu(
                p, values=list(LABELS_STATUT.values()), variable=self._var_statut, **kw
            ),
        )

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
            checkbox.grid(
                row=index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=4
            )

        f_bilan = ctk.CTkFrame(frame, fg_color="transparent")
        f_bilan.pack(fill="x", pady=3)
        ctk.CTkLabel(f_bilan, text="Bilan de fin", width=180, anchor="ne").pack(
            side="left", padx=(0, 8), anchor="n", pady=2
        )
        self._txt_bilan = ctk.CTkTextbox(f_bilan, height=80)
        self._txt_bilan.pack(side="left", fill="x", expand=True)

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

        sep2 = ctk.CTkFrame(frame, height=2, fg_color="#444")
        sep2.pack(fill="x", pady=8)

        ctk.CTkButton(
            frame,
            text="💾 Enregistrer",
            command=self._sauvegarder_general,
        ).pack(anchor="w")


def construire_onglets_fiche(fiche: Any) -> None:
    fiche._tabs = ctk.CTkTabview(fiche)
    fiche._tabs.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    onglets = (
        ("📋 Général", "_build_onglet_general"),
        ("🎫 Billetterie", "_build_onglet_billetterie"),
        ("💸 Dépenses", "_build_onglet_depenses"),
        ("💰 Budget", "_build_onglet_budget"),
        ("👥 Bénévoles", "_build_onglet_benevoles"),
        ("🎰 Tombola", "_build_onglet_tombola"),
        ("🏪 Stands", "_build_onglet_stands"),
        ("📊 Tableaux", "_build_onglet_tableaux"),
        ("🧾 Caisses", "_build_onglet_caisses"),
    )
    for nom, _ in onglets:
        fiche._tabs.add(nom)
    for nom, constructeur in onglets:
        getattr(fiche, constructeur)(fiche._tabs.tab(nom))
