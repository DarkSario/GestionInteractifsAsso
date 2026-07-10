"""Onglet récapitulatif des achats buvette depuis le stock."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.connection import get_connection


class OngletAchatsBuvette(ctk.CTkFrame):
    """Affiche les achats taggés Buvette groupés par facture."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._tree = ttk.Treeview(
            frame,
            columns=("facture", "date", "fournisseur", "nb", "total"),
            show="headings",
        )
        for col, txt, width in (
            ("facture", "Facture", 180),
            ("date", "Date", 120),
            ("fournisseur", "Fournisseur", 220),
            ("nb", "Nb articles", 110),
            ("total", "Total TTC", 120),
        ):
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=width, anchor="center" if col in {"date", "nb"} else "w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _charger(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(l.numero_facture), ''), 'Sans facture') AS facture,
                       MIN(l.date_achat) AS date_achat,
                       COALESCE(f.nom, '—') AS fournisseur,
                       COUNT(l.id) AS nb_articles,
                       COALESCE(SUM(l.quantite_initiale * l.prix_unitaire_ttc), 0) AS total_ttc
                FROM stock_lots l
                LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id
                WHERE EXISTS (
                    SELECT 1
                    FROM stock_lot_tags lt
                    JOIN stock_tags t ON t.id = lt.tag_id
                    WHERE lt.lot_id = l.id AND t.nom = 'Buvette'
                )
                GROUP BY facture, fournisseur
                ORDER BY date(date_achat) DESC, facture ASC
                """
            ).fetchall()
        finally:
            conn.close()

        self._tree.delete(*self._tree.get_children())
        for row in rows:
            self._tree.insert(
                "",
                "end",
                values=(
                    row["facture"],
                    row["date_achat"] or "—",
                    row["fournisseur"],
                    int(row["nb_articles"] or 0),
                    f"{float(row['total_ttc'] or 0):.2f} €",
                ),
            )
