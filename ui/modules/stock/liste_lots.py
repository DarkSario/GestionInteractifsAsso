"""Vue des lots en stock pour un article."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.stock_v2 import get_lots_fifo, get_lots_par_article, get_stock_theorique


class ListeLotsArticle(ctk.CTkToplevel):
    """Affiche les lots d'un article et le prochain lot FIFO."""

    def __init__(self, parent: Any, article: dict) -> None:
        super().__init__(parent)
        self._article = article
        self.title(f"📦 {article.get('nom', '')} — Lots en stock")
        self.geometry("860x520")
        self.transient(parent)

        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self._tree = ttk.Treeview(
            frame,
            columns=("id", "lot", "achat", "peremption", "qte", "prix", "statut"),
            show="headings",
        )
        for col, text, width in (
            ("id", "ID", 60),
            ("lot", "N° Lot", 130),
            ("achat", "Date achat", 110),
            ("peremption", "Date pér.", 110),
            ("qte", "Qté rest.", 90),
            ("prix", "Prix TTC", 100),
            ("statut", "Statut", 100),
        ):
            self._tree.heading(col, text=text)
            self._tree.column(col, width=width, anchor="center" if col in {"id", "qte"} else "w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._lbl_total = ctk.CTkLabel(self, text="")
        self._lbl_total.pack(fill="x", padx=12, pady=(0, 6))
        self._lbl_fifo = ctk.CTkLabel(self, text="")
        self._lbl_fifo.pack(fill="x", padx=12, pady=(0, 12))

    def _charger(self) -> None:
        article_id = int(self._article["id"])
        lots = get_lots_par_article(article_id)
        fifo = get_lots_fifo(article_id)

        self._tree.delete(*self._tree.get_children())
        for lot in lots:
            self._tree.insert(
                "",
                "end",
                values=(
                    lot.get("id"),
                    lot.get("numero_lot") or "—",
                    lot.get("date_achat") or "—",
                    lot.get("date_peremption") or "—",
                    int(lot.get("quantite_restante") or 0),
                    f"{float(lot.get('prix_unitaire_ttc') or 0):.2f} €",
                    lot.get("statut") or "",
                ),
            )

        total = get_stock_theorique(article_id)
        self._lbl_total.configure(text=f"Stock total théorique : {total} unités")
        if fifo:
            lot = fifo[0]
            self._lbl_fifo.configure(
                text=(
                    f"Prochain lot FIFO : {lot.get('numero_lot') or '—'} "
                    f"({int(lot.get('quantite_restante') or 0)} restantes à "
                    f"{float(lot.get('prix_unitaire_ttc') or 0):.2f} €)"
                )
            )
        else:
            self._lbl_fifo.configure(text="Prochain lot FIFO : aucun lot actif")
