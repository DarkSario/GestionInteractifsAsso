"""Sous-onglet Dépôt d'espèces du module Trésorerie."""

from __future__ import annotations

from datetime import datetime
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.connection import get_connection
from db.models.tresorerie import add_operation, get_all_comptes
from ui import theme as app_theme


def build_tab_depot_especes(parent: ctk.CTkFrame, _root: Any) -> None:
    fonts = app_theme.FONTS
    ctk.CTkLabel(parent, text="💵 Dépôt d'espèces", font=fonts.get("subtitle")).pack(
        anchor="w", padx=12, pady=(10, 6)
    )

    form = ctk.CTkFrame(parent)
    form.pack(fill="x", padx=12, pady=(0, 8))
    var_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    var_montant = ctk.StringVar(value="0")
    comptes = get_all_comptes(actif_only=True)
    labels_comptes = [c["nom"] for c in comptes] or ["Compte courant"]
    var_compte = ctk.StringVar(value=labels_comptes[0])
    var_origine = ctk.StringVar(value="Caisse")
    var_reference = ctk.StringVar(value="")
    var_commentaire = ctk.StringVar(value="")

    champs = [
        ("Date", ctk.CTkEntry(form, textvariable=var_date, width=160)),
        ("Montant (€)", ctk.CTkEntry(form, textvariable=var_montant, width=160)),
        ("Compte destination", ctk.CTkComboBox(form, values=labels_comptes, variable=var_compte, width=240)),
        ("Origine", ctk.CTkEntry(form, textvariable=var_origine, width=240)),
        ("Référence", ctk.CTkEntry(form, textvariable=var_reference, width=180)),
        ("Commentaire", ctk.CTkEntry(form, textvariable=var_commentaire, width=280)),
    ]
    for i, (label, widget) in enumerate(champs):
        ctk.CTkLabel(form, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=4)
        widget.grid(row=i, column=1, sticky="w", padx=8, pady=4)

    def enregistrer() -> None:
        try:
            montant = float(var_montant.get().replace(",", "."))
        except ValueError:
            return
        compte = next((c for c in comptes if c["nom"] == var_compte.get()), comptes[0] if comptes else None)
        if not compte:
            return
        comment_parts = [
            f"Origine: {var_origine.get().strip()}",
            var_reference.get().strip(),
            var_commentaire.get().strip(),
        ]
        commentaire = " | ".join(part for part in comment_parts if part)
        add_operation(
            compte_id=int(compte["id"]),
            type_operation="recette",
            libelle="Dépôt d'espèces",
            montant=montant,
            date_operation=var_date.get().strip(),
            categorie_id=None,
            mode_paiement="especes",
            numero_facture=var_reference.get().strip() or None,
            evenement_id=None,
            fournisseur_id=None,
            statut="valide",
            est_automatique=0,
            source_module="depot_especes",
            source_id=None,
            commentaire=commentaire or None,
        )
        refresh_historique()

    ctk.CTkButton(form, text="💾 Enregistrer", command=enregistrer).grid(row=len(champs), column=1, sticky="e", padx=8, pady=10)

    frame_table = ctk.CTkFrame(parent)
    frame_table.pack(fill="both", expand=True, padx=12, pady=(0, 10))
    tree = ttk.Treeview(frame_table, columns=("date", "compte", "montant", "commentaire"), show="headings", height=10)
    tree.heading("date", text="Date")
    tree.heading("compte", text="Compte")
    tree.heading("montant", text="Montant")
    tree.heading("commentaire", text="Commentaire")
    tree.column("date", width=110, anchor="center")
    tree.column("compte", width=180)
    tree.column("montant", width=120, anchor="e")
    tree.column("commentaire", width=460)
    tree.pack(fill="both", expand=True, side="left")
    scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    def refresh_historique() -> None:
        tree.delete(*tree.get_children())
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT o.date_operation, b.nom AS compte_nom, o.montant, o.commentaire
                FROM tresorerie_operations o
                LEFT JOIN comptes_bancaires b ON b.id = o.compte_id
                WHERE o.source_module = 'depot_especes'
                ORDER BY o.date_operation DESC, o.id DESC
                """
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    row["date_operation"] or "",
                    row["compte_nom"] or "—",
                    f"{float(row['montant'] or 0):,.2f} €".replace(",", " ").replace(".", ","),
                    row["commentaire"] or "",
                ),
            )

    refresh_historique()
