"""Onglet coûts buvette par événement."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.inventaire import calculer_cout_buvette_evenement
from db.connection import get_connection
from ui.components.dialogs import afficher_info


class OngletCoutsEvenement(ctk.CTkFrame):
    """Calcul et affichage des coûts buvette par événement."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._events: list[dict] = []
        self._event_var = tk.StringVar(value="")
        self._build_ui()
        self._charger_evenements()
        self._charger_couts()

    def _build_ui(self) -> None:
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=10)

        self._menu = ctk.CTkOptionMenu(head, values=[""], variable=self._event_var)
        self._menu.pack(side="left")
        ctk.CTkButton(head, text="🔄 Calculer", command=self._calculer).pack(side="left", padx=8)

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame,
            columns=("event", "date", "cout", "statut"),
            show="headings",
        )
        for col, txt, width in (
            ("event", "Événement", 300),
            ("date", "Date", 140),
            ("cout", "Coût TTC", 140),
            ("statut", "Statut", 120),
        ):
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=width, anchor="center" if col != "event" else "w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _charger_evenements(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, nom FROM evenements ORDER BY date_debut DESC, id DESC"
            ).fetchall()
        finally:
            conn.close()
        self._events = [dict(r) for r in rows]
        labels = [e["nom"] for e in self._events] or [""]
        self._menu.configure(values=labels)
        if labels:
            self._event_var.set(labels[0])

    def _calculer(self) -> None:
        event = next((e for e in self._events if e["nom"] == self._event_var.get()), None)
        if not event:
            return
        result = calculer_cout_buvette_evenement(int(event["id"]))
        afficher_info(
            self,
            "Coût buvette",
            f"Coût TTC calculé : {float(result.get('cout_ttc') or 0):.2f} €",
        )
        self._charger_couts()

    def _charger_couts(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT e.nom AS evenement_nom, c.created_at, c.cout_total_ttc, c.statut
                FROM buvette_couts_evenement c
                JOIN evenements e ON e.id = c.evenement_id
                ORDER BY datetime(c.created_at) DESC, c.id DESC
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
                    row["evenement_nom"],
                    row["created_at"] or "",
                    f"{float(row['cout_total_ttc'] or 0):.2f} €",
                    row["statut"],
                ),
            )
