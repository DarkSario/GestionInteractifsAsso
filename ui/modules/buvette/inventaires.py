"""Onglet Inventaires du module Buvette."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.buvette import valider_inventaire_lignes
from db.connection import get_connection
from db.models.buvette import (
    add_ligne_inventaire,
    create_inventaire,
    get_all_inventaires,
    get_articles_buvette_for_select,
    get_lignes_inventaire,
    update_stock_article_buvette,
)
from ui.components.dialogs import afficher_erreur, afficher_info


_TYPES_INVENTAIRE = {
    "Avant événement": "avant_evenement",
    "Après événement": "apres_evenement",
    "Hors événement": "hors_evenement",
}


class OngletInventaires(ctk.CTkFrame):
    """Gestion des inventaires buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._inventaires: list[dict] = []

        self._build_ui()
        self._charger_inventaires()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(top, text="+ Nouvel inventaire", command=self._nouvel_inventaire).pack(
            side="left"
        )

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame_table,
            columns=("date", "type", "event", "id"),
            show="headings",
        )
        self._tree.heading("date", text="Date")
        self._tree.heading("type", text="Type")
        self._tree.heading("event", text="Événement")
        self._tree.heading("id", text="ID")

        self._tree.column("date", width=130)
        self._tree.column("type", width=190)
        self._tree.column("event", width=340)
        self._tree.column("id", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ctk.CTkButton(self, text="👁️ Voir", command=self._voir_inventaire).pack(
            anchor="w", padx=10, pady=(0, 10)
        )

    def _charger_inventaires(self) -> None:
        self._inventaires = get_all_inventaires(limit=100)
        self._tree.delete(*self._tree.get_children())

        labels = {
            "avant_evenement": "Avant événement",
            "apres_evenement": "Après événement",
            "hors_evenement": "Hors événement",
        }

        for inventaire in self._inventaires:
            self._tree.insert(
                "",
                "end",
                iid=str(inventaire["id"]),
                values=(
                    self._fmt_date(inventaire.get("date")),
                    labels.get(inventaire.get("type"), inventaire.get("type", "")),
                    inventaire.get("evenement_nom") or "—",
                    inventaire["id"],
                ),
            )

    def _nouvel_inventaire(self) -> None:
        form = _FormulaireInventaire(self)
        self.wait_window(form)
        self._charger_inventaires()

    def _voir_inventaire(self) -> None:
        selection = self._tree.selection()
        if not selection:
            afficher_info(self, "Inventaires", "Sélectionnez un inventaire à consulter.")
            return

        inventaire_id = int(selection[0])
        lignes = get_lignes_inventaire(inventaire_id)

        fen = ctk.CTkToplevel(self)
        fen.title(f"Inventaire #{inventaire_id}")
        fen.geometry("760x460")
        fen.transient(self)

        tree = ttk.Treeview(
            fen,
            columns=("article", "qte_theo", "qte_comptee", "ecart"),
            show="headings",
        )
        tree.heading("article", text="Article")
        tree.heading("qte_theo", text="Qté théorique")
        tree.heading("qte_comptee", text="Qté comptée")
        tree.heading("ecart", text="Écart")

        tree.column("article", width=280)
        tree.column("qte_theo", width=130, anchor="center")
        tree.column("qte_comptee", width=130, anchor="center")
        tree.column("ecart", width=100, anchor="center")

        tree.tag_configure("negatif", foreground="#ff4444")
        for ligne in lignes:
            tag = "negatif" if (ligne.get("ecart") or 0) < 0 else ""
            tree.insert(
                "",
                "end",
                values=(
                    ligne.get("article_nom") or "",
                    ligne.get("quantite_theorique") or 0,
                    ligne.get("quantite_comptee") or 0,
                    ligne.get("ecart") or 0,
                ),
                tags=(tag,),
            )

        tree.pack(fill="both", expand=True, padx=12, pady=12)

    @staticmethod
    def _fmt_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value


class _FormulaireInventaire(ctk.CTkToplevel):
    """Formulaire de saisie d'un inventaire buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Nouvel inventaire buvette")
        self.geometry("900x650")
        self.transient(parent)
        self.grab_set()

        self._evenements = self._charger_evenements()
        self._articles = get_articles_buvette_for_select()
        self._entries: dict[int, tk.StringVar] = {}

        self._date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._type_var = tk.StringVar(value="Avant événement")
        self._event_var = tk.StringVar(value="— Aucun —")
        self._comment_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self) -> None:
        head = ctk.CTkFrame(self)
        head.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(head, text="Date").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(head, textvariable=self._date_var, width=140).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(head, text="Type").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ctk.CTkOptionMenu(head, values=list(_TYPES_INVENTAIRE.keys()), variable=self._type_var).grid(
            row=0, column=3, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(head, text="Événement").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkOptionMenu(
            head,
            values=["— Aucun —"] + [e["nom"] for e in self._evenements],
            variable=self._event_var,
            width=300,
        ).grid(row=1, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(head, text="Commentaire").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(head, textvariable=self._comment_var, width=520).grid(
            row=2, column=1, columnspan=3, sticky="w", padx=8, pady=6
        )

        frame_list = ctk.CTkScrollableFrame(self)
        frame_list.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        ctk.CTkLabel(frame_list, text="Article", width=360, anchor="w").grid(
            row=0, column=0, padx=6, pady=6, sticky="w"
        )
        ctk.CTkLabel(frame_list, text="Qté théorique", width=120).grid(
            row=0, column=1, padx=6, pady=6
        )
        ctk.CTkLabel(frame_list, text="Qté comptée", width=120).grid(
            row=0, column=2, padx=6, pady=6
        )

        for i, article in enumerate(self._articles, start=1):
            var = tk.StringVar(value=str(article.get("stock_actuel") or 0))
            self._entries[article["id"]] = var

            ctk.CTkLabel(frame_list, text=article.get("nom") or "", anchor="w", width=360).grid(
                row=i, column=0, sticky="w", padx=6, pady=4
            )
            ctk.CTkLabel(frame_list, text=str(article.get("stock_actuel") or 0), width=120).grid(
                row=i, column=1, padx=6, pady=4
            )
            ctk.CTkEntry(frame_list, textvariable=var, width=120).grid(
                row=i, column=2, padx=6, pady=4
            )

        ctk.CTkButton(self, text="Enregistrer l'inventaire", command=self._save).pack(
            anchor="e", padx=12, pady=(0, 12)
        )

    def _save(self) -> None:
        type_db = _TYPES_INVENTAIRE.get(self._type_var.get(), "hors_evenement")
        event = next((e for e in self._evenements if e["nom"] == self._event_var.get()), None)
        event_id = event["id"] if event and type_db != "hors_evenement" else None

        lignes = []
        for article in self._articles:
            lignes.append(
                {
                    "article_id": article["id"],
                    "quantite_theorique": int(article.get("stock_actuel") or 0),
                    "quantite_comptee": self._entries[article["id"]].get().strip(),
                }
            )

        erreurs = valider_inventaire_lignes(lignes)
        if erreurs:
            afficher_erreur(self, "Validation", "\n".join(erreurs))
            return

        inventaire_id = create_inventaire(
            self._date_var.get().strip(),
            type_db,
            event_id,
            self._comment_var.get().strip(),
        )

        for ligne in lignes:
            qte_comptee = int(ligne["quantite_comptee"])
            add_ligne_inventaire(
                inventaire_id,
                ligne["article_id"],
                ligne["quantite_theorique"],
                qte_comptee,
            )
            update_stock_article_buvette(ligne["article_id"], qte_comptee)

        self.destroy()

    def _charger_evenements(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, nom FROM evenements ORDER BY nom ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
