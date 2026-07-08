"""Onglet Remises de chèques du module Trésorerie."""

from __future__ import annotations

from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import formater_montant
from db.models.tresorerie import get_remises
from ui import theme as app_theme


def build_tab_remises(parent: ctk.CTkFrame, _root: Any) -> None:
    fonts = app_theme.FONTS
    colors = app_theme.COLORS

    frame_header = ctk.CTkFrame(parent, fg_color="transparent")
    frame_header.pack(fill="x", padx=12, pady=(10, 6))

    ctk.CTkLabel(
        frame_header,
        text="🏦 Remises de chèques",
        font=fonts.get("subtitle"),
    ).pack(side="left")

    ctk.CTkButton(
        frame_header,
        text="+ Nouvelle remise",
        width=160,
        fg_color=colors.get("primary", "#1f6aa5"),
        hover_color=colors.get("secondary", "#144870"),
        command=lambda: None,
    ).pack(side="right")

    table_frame = ctk.CTkFrame(parent)
    table_frame.pack(fill="both", expand=True, padx=12, pady=6)

    tree = ttk.Treeview(
        table_frame,
        columns=("date", "reference", "compte", "nb", "montant", "statut"),
        show="headings",
        height=14,
    )

    tree.heading("date", text="Date")
    tree.heading("reference", text="Référence")
    tree.heading("compte", text="Compte")
    tree.heading("nb", text="Nb chèques")
    tree.heading("montant", text="Montant")
    tree.heading("statut", text="Statut")

    tree.column("date", width=110, anchor="center")
    tree.column("reference", width=170)
    tree.column("compte", width=170)
    tree.column("nb", width=110, anchor="center")
    tree.column("montant", width=130, anchor="e")
    tree.column("statut", width=110, anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for remise in get_remises():
        tree.insert(
            "",
            "end",
            values=(
                remise.get("date_remise") or "",
                remise.get("reference") or "",
                remise.get("compte_nom") or "",
                remise.get("nombre_cheques") or 0,
                formater_montant(float(remise.get("montant_total") or 0)),
                remise.get("statut") or "",
            ),
        )
