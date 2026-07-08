"""Onglet Caisses & Recettes du module Buvette."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.buvette import calculer_net_caisses, valider_caisse
from db.connection import get_connection
from db.models.buvette import (
    add_caisse,
    delete_caisse,
    enregistrer_recette_evenement,
    get_caisses_by_evenement,
    get_recettes_buvette,
    update_caisse,
)
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation


class OngletCaissesRecettes(ctk.CTkFrame):
    """Gestion des caisses événement et de la recette nette."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._events = self._charger_evenements()
        self._event_var = tk.StringVar(value=self._events[0]["nom"] if self._events else "—")
        self._caisses: list[dict] = []

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top, text="Événement :").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            top,
            values=[e["nom"] for e in self._events] or ["—"],
            variable=self._event_var,
            command=lambda _: self._refresh(),
            width=300,
        ).pack(side="left")

        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame_table,
            columns=("nom", "fond", "brut", "net"),
            show="headings",
        )
        self._tree.heading("nom", text="Caisse")
        self._tree.heading("fond", text="Fond caisse")
        self._tree.heading("brut", text="Total brut")
        self._tree.heading("net", text="Net")

        self._tree.column("nom", width=320)
        self._tree.column("fond", width=140, anchor="e")
        self._tree.column("brut", width=140, anchor="e")
        self._tree.column("net", width=140, anchor="e")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkButton(actions, text="+ Ajouter une caisse", command=self._ajouter).pack(side="left")
        ctk.CTkButton(actions, text="✏️ Modifier", command=self._modifier).pack(side="left", padx=8)
        ctk.CTkButton(actions, text="🗑️ Supprimer", command=self._supprimer).pack(side="left")

        self._label_totaux = ctk.CTkLabel(self, text="")
        self._label_totaux.pack(anchor="w", padx=10, pady=(0, 6))

        self._btn_valider = ctk.CTkButton(
            self,
            text="✅ Valider et enregistrer en trésorerie",
            command=self._valider_recette,
        )
        self._btn_valider.pack(anchor="w", padx=10, pady=(0, 10))

    def _refresh(self) -> None:
        evenement = self._event_selected()
        self._tree.delete(*self._tree.get_children())
        self._caisses = []
        if not evenement:
            self._label_totaux.configure(text="Aucun événement.")
            self._btn_valider.configure(state="disabled")
            return

        self._caisses = get_caisses_by_evenement(evenement["id"])
        for caisse in self._caisses:
            net = float(caisse.get("total_brut") or 0) - float(caisse.get("fond_de_caisse") or 0)
            self._tree.insert(
                "",
                "end",
                iid=str(caisse["id"]),
                values=(
                    caisse.get("nom") or "",
                    self._fmt_euro(caisse.get("fond_de_caisse")),
                    self._fmt_euro(caisse.get("total_brut")),
                    self._fmt_euro(net),
                ),
            )

        totaux = calculer_net_caisses(self._caisses)
        self._label_totaux.configure(
            text=(
                f"TOTAL fond de caisse : {self._fmt_euro(totaux['total_fond_caisse'])}   │   "
                f"TOTAL brut : {self._fmt_euro(totaux['total_brut'])}   │   "
                f"Recette nette : {self._fmt_euro(totaux['recette_nette'])}"
            )
        )

        recette_existante = next(
            (r for r in get_recettes_buvette(limit=500) if r.get("evenement_id") == evenement["id"]),
            None,
        )
        if recette_existante:
            self._btn_valider.configure(
                state="disabled",
                text=f"✅ Enregistré le {self._fmt_date(recette_existante.get('date'))}",
            )
        else:
            self._btn_valider.configure(state="normal", text="✅ Valider et enregistrer en trésorerie")

    def _ajouter(self) -> None:
        evenement = self._event_selected()
        if not evenement:
            afficher_info(self, "Caisses", "Créez d'abord un événement.")
            return

        form = _FormulaireCaisse(self, evenement_id=evenement["id"], caisse=None)
        self.wait_window(form)
        self._refresh()

    def _modifier(self) -> None:
        caisse = self._selected_caisse()
        if not caisse:
            afficher_info(self, "Caisses", "Sélectionnez une caisse à modifier.")
            return

        form = _FormulaireCaisse(self, evenement_id=caisse["evenement_id"], caisse=caisse)
        self.wait_window(form)
        self._refresh()

    def _supprimer(self) -> None:
        caisse = self._selected_caisse()
        if not caisse:
            afficher_info(self, "Caisses", "Sélectionnez une caisse à supprimer.")
            return

        if demander_confirmation(self, "Suppression", f"Supprimer la caisse « {caisse['nom']} » ?"):
            delete_caisse(caisse["id"])
            self._refresh()

    def _valider_recette(self) -> None:
        evenement = self._event_selected()
        if not evenement:
            return
        if not self._caisses:
            afficher_info(self, "Recette", "Ajoutez au moins une caisse avant validation.")
            return

        try:
            enregistrer_recette_evenement(evenement["id"])
        except Exception as exc:
            afficher_erreur(self, "Recette", f"Impossible d'enregistrer la recette :\n{exc}")
            return

        self._refresh()

    def _selected_caisse(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            return None
        caisse_id = int(sel[0])
        return next((c for c in self._caisses if c["id"] == caisse_id), None)

    def _event_selected(self) -> dict | None:
        return next((e for e in self._events if e["nom"] == self._event_var.get()), None)

    def _charger_evenements(self) -> list[dict]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, nom FROM evenements ORDER BY nom ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _fmt_euro(value: Any) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{amount:,.2f} €".replace(",", " ").replace(".", ",")

    @staticmethod
    def _fmt_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value


class _FormulaireCaisse(ctk.CTkToplevel):
    """Formulaire de saisie d'une caisse."""

    def __init__(self, parent: Any, evenement_id: int, caisse: dict | None) -> None:
        super().__init__(parent)
        self.title("Caisse")
        self.geometry("560x360")
        self.transient(parent)
        self.grab_set()

        self._evenement_id = evenement_id
        self._caisse = caisse

        self._nom_var = tk.StringVar(value=caisse.get("nom") if caisse else "")
        self._fond_var = tk.StringVar(value=self._to_str(caisse.get("fond_de_caisse") if caisse else 0))
        self._brut_var = tk.StringVar(value=self._to_str(caisse.get("total_brut") if caisse else 0))
        self._date_var = tk.StringVar(value=caisse.get("date") if caisse else datetime.now().strftime("%Y-%m-%d"))
        self._comment_var = tk.StringVar(value=caisse.get("commentaire") if caisse else "")

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        champs = [
            ("Nom *", self._nom_var),
            ("Fond de caisse *", self._fond_var),
            ("Total brut *", self._brut_var),
            ("Date", self._date_var),
            ("Commentaire", self._comment_var),
        ]

        for i, (label, var) in enumerate(champs):
            ctk.CTkLabel(frame, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=8)
            ctk.CTkEntry(frame, textvariable=var, width=320).grid(
                row=i, column=1, sticky="ew", padx=8, pady=8
            )

        ctk.CTkButton(frame, text="Enregistrer", command=self._save).grid(
            row=len(champs), column=1, sticky="e", padx=8, pady=8
        )

        frame.grid_columnconfigure(1, weight=1)

    def _save(self) -> None:
        erreurs = valider_caisse(self._nom_var.get(), self._fond_var.get(), self._brut_var.get())
        if erreurs:
            afficher_erreur(self, "Validation", "\n".join(erreurs))
            return

        nom = self._nom_var.get().strip()
        fond = float(self._fond_var.get().replace(",", "."))
        brut = float(self._brut_var.get().replace(",", "."))
        date = self._date_var.get().strip()
        commentaire = self._comment_var.get().strip()

        try:
            if self._caisse:
                update_caisse(self._caisse["id"], nom, fond, brut, date, commentaire)
            else:
                add_caisse(self._evenement_id, nom, fond, brut, date, commentaire)
        except Exception as exc:
            afficher_erreur(self, "Caisse", f"Impossible d'enregistrer la caisse :\n{exc}")
            return

        self.destroy()

    @staticmethod
    def _to_str(value: Any) -> str:
        try:
            amount = float(value or 0)
        except (TypeError, ValueError):
            amount = 0.0
        return f"{amount:.2f}".replace(".", ",")
