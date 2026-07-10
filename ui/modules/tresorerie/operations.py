"""Onglet Opérations du module Trésorerie."""

from __future__ import annotations

from datetime import datetime
from tkinter import simpledialog
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.tresorerie import formater_montant
from db.models.tresorerie import (
    add_operation,
    get_all_categories,
    get_all_comptes,
    get_operations,
    get_stats_tresorerie,
)
from ui import theme as app_theme


COULEURS = {
    "recette": "#2e7d32",
    "depense": "#b71c1c",
    "virement_interne": "#1565c0",
}


def _periode_contient_cloture() -> bool:
    """Vérifie si des opérations rapprochées existent (période clôturée présente)."""
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS nb FROM tresorerie_operations WHERE statut = 'rapproche'"
            ).fetchone()
        finally:
            conn.close()
        return (row["nb"] if row else 0) > 0
    except Exception:
        return False


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
        command=lambda: _ajouter_operation(parent, _root, "recette"),
    ).pack(side="right")

    ctk.CTkButton(
        frame_header,
        text="+ Dépense",
        width=110,
        command=lambda: _ajouter_operation(parent, _root, "depense"),
    ).pack(side="right", padx=(0, 8))

    # Bandeau "Période clôturée" si applicable
    if _periode_contient_cloture():
        bandeau = ctk.CTkFrame(parent, fg_color="#fff3e0", corner_radius=6)
        bandeau.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(
            bandeau,
            text="🔒 Période clôturée — Les opérations affichées sont en lecture seule",
            font=fonts.get("bold"),
            text_color="#e65100",
        ).pack(padx=12, pady=6)

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


def _ajouter_operation(parent: ctk.CTkFrame, root: Any, operation_type: str) -> None:
    comptes = get_all_comptes(actif_only=True)
    if not comptes:
        return
    compte_id = int(comptes[0]["id"])
    libelle = simpledialog.askstring(
        "Nouvelle opération",
        "Libellé :",
        parent=root,
        initialvalue="Recette" if operation_type == "recette" else "Dépense",
    )
    if not libelle:
        return
    montant_str = simpledialog.askstring("Nouvelle opération", "Montant (€) :", parent=root, initialvalue="0")
    try:
        montant = float((montant_str or "0").replace(",", "."))
    except ValueError:
        return
    categories = get_all_categories(operation_type)
    categorie_id = int(categories[0]["id"]) if categories else None
    add_operation(
        compte_id=compte_id,
        type_operation=operation_type,
        libelle=libelle.strip(),
        montant=montant,
        date_operation=datetime.now().strftime("%Y-%m-%d"),
        categorie_id=categorie_id,
        mode_paiement="autre",
        numero_facture=None,
        evenement_id=None,
        fournisseur_id=None,
        statut="valide",
        est_automatique=0,
        source_module="manuel",
        source_id=None,
        commentaire=None,
    )
    for widget in parent.winfo_children():
        widget.destroy()
    build_tab_operations(parent, root)
