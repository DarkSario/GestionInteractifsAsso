"""Onglet Comptes du module Trésorerie."""

from __future__ import annotations

from tkinter import simpledialog
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import formater_montant
from db.models.tresorerie import add_compte, get_all_comptes
from ui import theme as app_theme
from ui.modules.tresorerie.virement_dialog import VirementDialog


def build_tab_comptes(parent: ctk.CTkFrame, root: Any) -> None:
    fonts = app_theme.FONTS
    colors = app_theme.COLORS

    frame_header = ctk.CTkFrame(parent, fg_color="transparent")
    frame_header.pack(fill="x", padx=12, pady=(10, 6))

    ctk.CTkLabel(
        frame_header,
        text="💰 Comptes bancaires",
        font=fonts.get("subtitle"),
    ).pack(side="left")

    ctk.CTkButton(
        frame_header,
        text="+ Ajouter un compte",
        width=170,
        fg_color=colors.get("primary", "#1f6aa5"),
        hover_color=colors.get("secondary", "#144870"),
        command=lambda: _ajouter_compte(parent, root),
    ).pack(side="right")

    table_frame = ctk.CTkFrame(parent)
    table_frame.pack(fill="both", expand=True, padx=12, pady=6)

    tree = ttk.Treeview(
        table_frame,
        columns=("nom", "type", "solde", "principal"),
        show="headings",
        height=14,
    )
    tree.heading("nom", text="Nom")
    tree.heading("type", text="Type")
    tree.heading("solde", text="Solde")
    tree.heading("principal", text="Principal")

    tree.column("nom", width=280)
    tree.column("type", width=130, anchor="center")
    tree.column("solde", width=150, anchor="e")
    tree.column("principal", width=90, anchor="center")

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    comptes = get_all_comptes(actif_only=False)
    total = 0.0
    for compte in comptes:
        solde = float(compte.get("solde_actuel") or 0)
        total += solde
        etoile = "★" if int(compte.get("est_principal") or 0) else ""
        tree.insert(
            "",
            "end",
            values=(
                compte.get("nom") or "",
                str(compte.get("type_compte") or "").capitalize(),
                formater_montant(solde),
                etoile,
            ),
        )

    frame_footer = ctk.CTkFrame(parent, fg_color="transparent")
    frame_footer.pack(fill="x", padx=12, pady=(2, 10))

    ctk.CTkLabel(
        frame_footer,
        text=f"Total tous comptes : {formater_montant(total)}",
        font=fonts.get("bold"),
    ).pack(side="left")

    ctk.CTkButton(
        frame_footer,
        text="↔️ Virement interne",
        width=160,
        command=lambda: VirementDialog(root),
    ).pack(side="right")


def _ajouter_compte(parent: ctk.CTkFrame, root: Any) -> None:
    nom = simpledialog.askstring("Nouveau compte", "Nom du compte :", parent=root)
    if not nom:
        return
    type_compte = simpledialog.askstring(
        "Nouveau compte",
        "Type (bancaire/livret/sumup/caisse/autre) :",
        parent=root,
        initialvalue="bancaire",
    )
    type_compte = (type_compte or "bancaire").strip().lower()
    if type_compte not in {"bancaire", "livret", "sumup", "caisse", "autre"}:
        type_compte = "bancaire"
    solde_str = simpledialog.askstring("Nouveau compte", "Solde initial (€) :", parent=root, initialvalue="0")
    try:
        solde = float((solde_str or "0").replace(",", "."))
    except ValueError:
        solde = 0.0
    add_compte(nom.strip(), type_compte, solde, 0, 1 if type_compte == "caisse" else 0, "", "", 0)
    for widget in parent.winfo_children():
        widget.destroy()
    build_tab_comptes(parent, root)
