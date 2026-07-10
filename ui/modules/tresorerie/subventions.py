"""Onglet Subventions du module Trésorerie."""

from __future__ import annotations

from datetime import datetime
from tkinter import simpledialog
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import formater_montant
from db.models.tresorerie import add_subvention, get_all_subventions, get_stats_subventions
from ui import theme as app_theme


def build_tab_subventions(parent: ctk.CTkFrame, _root: Any) -> None:
    fonts = app_theme.FONTS
    colors = app_theme.COLORS

    frame_header = ctk.CTkFrame(parent, fg_color="transparent")
    frame_header.pack(fill="x", padx=12, pady=(10, 6))

    ctk.CTkLabel(
        frame_header,
        text="🎁 Subventions",
        font=fonts.get("subtitle"),
    ).pack(side="left")

    ctk.CTkButton(
        frame_header,
        text="+ Nouvelle demande",
        width=170,
        fg_color=colors.get("primary", "#1f6aa5"),
        hover_color=colors.get("secondary", "#144870"),
        command=lambda: _ajouter_subvention(parent, _root),
    ).pack(side="right")

    table_frame = ctk.CTkFrame(parent)
    table_frame.pack(fill="both", expand=True, padx=12, pady=6)

    tree = ttk.Treeview(
        table_frame,
        columns=("organisme", "objet", "demande", "obtenu", "statut"),
        show="headings",
        height=14,
    )

    tree.heading("organisme", text="Organisme")
    tree.heading("objet", text="Objet")
    tree.heading("demande", text="Demandé")
    tree.heading("obtenu", text="Obtenu")
    tree.heading("statut", text="Statut")

    tree.column("organisme", width=220)
    tree.column("objet", width=280)
    tree.column("demande", width=130, anchor="e")
    tree.column("obtenu", width=130, anchor="e")
    tree.column("statut", width=120, anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for subvention in get_all_subventions():
        tree.insert(
            "",
            "end",
            values=(
                subvention.get("organisme") or "",
                subvention.get("objet") or "",
                formater_montant(float(subvention.get("montant_demande") or 0)),
                formater_montant(float(subvention.get("montant_obtenu") or 0)),
                subvention.get("statut") or "",
            ),
        )

    stats = get_stats_subventions()
    ctk.CTkLabel(
        parent,
        text=(
            f"Total demandé : {formater_montant(stats['total_demande'])}  |  "
            f"Total obtenu : {formater_montant(stats['total_obtenu'])}"
        ),
        font=fonts.get("bold"),
    ).pack(anchor="w", padx=12, pady=(0, 10))


def _ajouter_subvention(parent: ctk.CTkFrame, root: Any) -> None:
    organisme = simpledialog.askstring("Nouvelle subvention", "Organisme :", parent=root)
    if not organisme:
        return
    montant_str = simpledialog.askstring(
        "Nouvelle subvention", "Montant demandé (€) :", parent=root, initialvalue="0"
    )
    try:
        montant = float((montant_str or "0").replace(",", "."))
    except ValueError:
        montant = 0.0
    add_subvention(
        organisme=organisme.strip(),
        type_organisme="autre",
        annee=datetime.now().year,
        objet="Demande libre",
        montant_demande=montant,
        date_demande=datetime.now().strftime("%Y-%m-%d"),
        commentaire=None,
    )
    for widget in parent.winfo_children():
        widget.destroy()
    build_tab_subventions(parent, root)
