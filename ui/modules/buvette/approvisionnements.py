"""Onglet Approvisionnements du module Buvette."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from db.connection import get_connection
from db.models.buvette import (
    add_ligne_approvisionnement,
    create_approvisionnement,
    finaliser_approvisionnement,
    get_approvisionnement_by_id,
    get_articles_buvette_for_select,
    get_lignes_approvisionnement,
)
from db.models.fournisseurs import get_fournisseurs_for_select
from ui.components.dialogs import afficher_erreur, afficher_info


class OngletApprovisionnements(ctk.CTkFrame):
    """Gestion des approvisionnements buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._build_ui()
        self._charger_table()

    def _build_ui(self) -> None:
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(head, text="+ Nouvel approvisionnement", command=self._nouveau).pack(
            side="left"
        )

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame_table,
            columns=("id", "date", "event", "fournisseur", "montant", "statut"),
            show="headings",
        )
        for col, title, width in (
            ("id", "ID", 70),
            ("date", "Date", 120),
            ("event", "Événement", 230),
            ("fournisseur", "Fournisseur", 230),
            ("montant", "Montant", 120),
            ("statut", "Statut", 120),
        ):
            self._tree.heading(col, text=title)
            self._tree.column(col, width=width, anchor="center" if col in {"id", "date", "statut"} else "w")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ctk.CTkButton(self, text="👁️ Voir", command=self._voir).pack(anchor="w", padx=10, pady=(0, 10))

    def _charger_table(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT a.id, a.date, e.nom AS evenement_nom, f.nom AS fournisseur_nom,
                       a.montant_total, a.finalise
                FROM approvisionnements_buvette a
                LEFT JOIN evenements e ON e.id = a.evenement_id
                LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id
                ORDER BY a.date DESC, a.id DESC
                """
            ).fetchall()
            data = [dict(r) for r in rows]
        finally:
            conn.close()

        self._tree.delete(*self._tree.get_children())
        for row in data:
            self._tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    self._fmt_date(row.get("date")),
                    row.get("evenement_nom") or "—",
                    row.get("fournisseur_nom") or "—",
                    self._fmt_euro(row.get("montant_total")),
                    "Finalisé" if row.get("finalise") else "Brouillon",
                ),
            )

    def _nouveau(self) -> None:
        form = _FormulaireApprovisionnement(self)
        self.wait_window(form)
        self._charger_table()

    def _voir(self) -> None:
        sel = self._tree.selection()
        if not sel:
            afficher_info(self, "Approvisionnements", "Sélectionnez un approvisionnement.")
            return

        appro_id = int(sel[0])
        entete = get_approvisionnement_by_id(appro_id)
        lignes = get_lignes_approvisionnement(appro_id)

        fen = ctk.CTkToplevel(self)
        fen.title(f"Approvisionnement #{appro_id}")
        fen.geometry("800x520")
        fen.transient(self)

        texte = (
            f"Date : {self._fmt_date(entete.get('date'))}\n"
            f"Événement : {entete.get('evenement_nom') or '—'}\n"
            f"Fournisseur : {entete.get('fournisseur_nom') or '—'}\n"
            f"Statut : {'Finalisé' if entete.get('finalise') else 'Brouillon'}\n"
            f"Montant total : {self._fmt_euro(entete.get('montant_total'))}"
        )
        ctk.CTkLabel(fen, text=texte, justify="left", anchor="w").pack(fill="x", padx=12, pady=12)

        tree = ttk.Treeview(
            fen,
            columns=("article", "quantite", "prix", "total"),
            show="headings",
        )
        tree.heading("article", text="Article")
        tree.heading("quantite", text="Qté")
        tree.heading("prix", text="Prix unitaire")
        tree.heading("total", text="Total")

        tree.column("article", width=320)
        tree.column("quantite", width=80, anchor="center")
        tree.column("prix", width=140, anchor="e")
        tree.column("total", width=140, anchor="e")

        for l in lignes:
            tree.insert(
                "",
                "end",
                values=(
                    l.get("article_nom") or "",
                    l.get("quantite") or 0,
                    self._fmt_euro(l.get("prix_unitaire")),
                    self._fmt_euro(l.get("total_ligne")),
                ),
            )

        tree.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    @staticmethod
    def _fmt_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value

    @staticmethod
    def _fmt_euro(value: Any) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")


class _FormulaireApprovisionnement(ctk.CTkToplevel):
    """Formulaire 2 étapes d'approvisionnement buvette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Nouvel approvisionnement")
        self.geometry("940x680")
        self.transient(parent)
        self.grab_set()

        self._events = self._charger_evenements()
        self._fournisseurs = get_fournisseurs_for_select()
        self._articles = get_articles_buvette_for_select()
        self._lignes: list[dict[str, Any]] = []

        self._date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._event_var = tk.StringVar(value="— Aucun —")
        self._fournisseur_var = tk.StringVar(value="— Aucun —")
        self._comment_var = tk.StringVar()

        self._build_ui()
        self._ajouter_ligne()

    def _build_ui(self) -> None:
        entete = ctk.CTkFrame(self)
        entete.pack(fill="x", padx=12, pady=12)

        ctk.CTkLabel(entete, text="Date").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(entete, textvariable=self._date_var, width=140).grid(
            row=0, column=1, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(entete, text="Événement").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ctk.CTkOptionMenu(
            entete,
            values=["— Aucun —"] + [e["nom"] for e in self._events],
            variable=self._event_var,
            width=280,
        ).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(entete, text="Fournisseur").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ctk.CTkOptionMenu(
            entete,
            values=["— Aucun —"] + [f["nom"] for f in self._fournisseurs],
            variable=self._fournisseur_var,
            width=280,
        ).grid(row=1, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(entete, text="Commentaire").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ctk.CTkEntry(entete, textvariable=self._comment_var, width=280).grid(
            row=1, column=3, sticky="w", padx=8, pady=6
        )

        self._frame_lignes = ctk.CTkScrollableFrame(self)
        self._frame_lignes.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        ctk.CTkButton(self, text="+ Ajouter une ligne", command=self._ajouter_ligne).pack(
            anchor="w", padx=12, pady=(0, 8)
        )

        ctk.CTkButton(self, text="Valider", command=self._valider).pack(
            anchor="e", padx=12, pady=(0, 12)
        )

    def _ajouter_ligne(self) -> None:
        index = len(self._lignes)

        article_var = tk.StringVar(value=self._articles[0]["nom"] if self._articles else "")
        qte_var = tk.StringVar(value="1")
        prix_var = tk.StringVar(value="0")

        frame = ctk.CTkFrame(self._frame_lignes)
        frame.pack(fill="x", padx=4, pady=4)

        ctk.CTkOptionMenu(
            frame,
            values=[a["nom"] for a in self._articles] or [""],
            variable=article_var,
            width=360,
        ).pack(side="left", padx=6, pady=6)

        ctk.CTkEntry(frame, textvariable=qte_var, width=90, placeholder_text="Qté").pack(
            side="left", padx=6, pady=6
        )
        ctk.CTkEntry(frame, textvariable=prix_var, width=120, placeholder_text="Prix unitaire").pack(
            side="left", padx=6, pady=6
        )

        self._lignes.append(
            {
                "frame": frame,
                "article_var": article_var,
                "qte_var": qte_var,
                "prix_var": prix_var,
                "index": index,
            }
        )

    def _valider(self) -> None:
        if not self._articles:
            afficher_erreur(self, "Approvisionnement", "Aucun article buvette actif.")
            return

        event = next((e for e in self._events if e["nom"] == self._event_var.get()), None)
        fournisseur = next(
            (f for f in self._fournisseurs if f["nom"] == self._fournisseur_var.get()),
            None,
        )

        try:
            appro_id = create_approvisionnement(
                self._date_var.get().strip(),
                event["id"] if event else None,
                fournisseur["id"] if fournisseur else None,
                self._comment_var.get().strip(),
            )

            for ligne in self._lignes:
                article = next(
                    (a for a in self._articles if a["nom"] == ligne["article_var"].get()),
                    None,
                )
                if not article:
                    continue

                quantite = int(ligne["qte_var"].get().strip())
                prix = float(ligne["prix_var"].get().strip().replace(",", "."))
                if quantite <= 0:
                    continue
                add_ligne_approvisionnement(appro_id, article["id"], quantite, prix)

            ok = finaliser_approvisionnement(appro_id)
            if not ok:
                afficher_erreur(
                    self,
                    "Approvisionnement",
                    "Impossible de finaliser l'approvisionnement. Vérifiez les lignes saisies.",
                )
                return

            self.destroy()
        except Exception as exc:
            afficher_erreur(self, "Approvisionnement", f"Erreur pendant la validation :\n{exc}")

    def _charger_evenements(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, nom FROM evenements ORDER BY nom ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
