"""Onglet Opérations du module Trésorerie."""

from __future__ import annotations

from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import formater_montant
from db.models.tresorerie import get_operations, get_stats_tresorerie
from ui import theme as app_theme


COULEURS = {
    "recette": "#2e7d32",
    "depense": "#b71c1c",
    "virement_interne": "#1565c0",
}


def build_tab_operations(parent: ctk.CTkFrame, _root: Any) -> None:
    fonts = app_theme.FONTS
    colors = app_theme.COLORS

    frame_header = ctk.CTkFrame(parent, fg_color="transparent")
    frame_header.pack(fill="x", padx=12, pady=(10, 6))

    ctk.CTkLabel(frame_header, text="📋 Opérations", font=fonts.get("subtitle")).pack(side="left")

    ctk.CTkButton(
        frame_header,
        text="+ Recette",
        width=110,
        fg_color=colors.get("primary", "#1f6aa5"),
        hover_color=colors.get("secondary", "#144870"),
        command=lambda: None,
    ).pack(side="right")

    ctk.CTkButton(
        frame_header,
        text="+ Dépense",
        width=110,
        command=lambda: None,
    ).pack(side="right", padx=(0, 8))

    table_frame = ctk.CTkFrame(parent)
    table_frame.pack(fill="both", expand=True, padx=12, pady=6)

    tree = ttk.Treeview(
        table_frame,
        columns=("date", "libelle", "categorie", "montant", "statut"),
        show="headings",
        height=14,
    )
    tree.heading("date", text="Date")
    tree.heading("libelle", text="Libellé")
    tree.heading("categorie", text="Catégorie")
    tree.heading("montant", text="Montant")
    tree.heading("statut", text="Statut")

    tree.column("date", width=110, anchor="center")
    tree.column("libelle", width=360)
    tree.column("categorie", width=190)
    tree.column("montant", width=130, anchor="e")
    tree.column("statut", width=90, anchor="center")

    for key, color in COULEURS.items():
        tree.tag_configure(key, foreground=color)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    operations = get_operations()
    for operation in operations:
        montant = float(operation.get("montant") or 0)
        type_op = operation.get("type_operation")
        signe = (
            "+"
            if type_op == "recette"
            or (type_op == "virement_interne" and operation.get("source_module") == "virement_entrant")
            else "-"
        )

        tree.insert(
            "",
            "end",
            values=(
                operation.get("date_operation") or "",
                operation.get("libelle") or "",
                operation.get("categorie_nom") or "—",
                f"{signe}{formater_montant(montant)}",
                operation.get("statut") or "",
            ),
            tags=(type_op,),
        )

    stats = get_stats_tresorerie()
    ctk.CTkLabel(
        parent,
        text=(
            f"Recettes : +{formater_montant(stats['total_recettes'])}  |  "
            f"Dépenses : -{formater_montant(stats['total_depenses'])}  |  "
            f"Solde période : {formater_montant(stats['solde'])}"
        ),
        font=fonts.get("bold"),
    ).pack(anchor="w", padx=12, pady=(0, 10))
