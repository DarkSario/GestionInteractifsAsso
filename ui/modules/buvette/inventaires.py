"""Onglet inventaires FIFO avant/après événement."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.inventaire import (
    creer_inventaire,
    get_inventaires,
    get_lignes_inventaire,
    saisir_ligne_inventaire,
    valider_inventaire,
)
from db.models.evenements import get_evenements_for_select
from ui.components.dialogs import afficher_erreur, afficher_info
from utils.logger import get_logger

logger = get_logger(__name__)


class OngletInventaires(ctk.CTkFrame):
    """Liste des inventaires et actions de saisie/validation."""

    TYPES = {
        "Avant événement": "avant_evenement",
        "Après événement": "apres_evenement",
        "Ponctuel": "ponctuel",
    }

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self._inventaires: list[dict] = []
        self._build_ui()
        self._charger()

    def _build_ui(self) -> None:
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(head, text="+ Nouvel inventaire", command=self._nouveau).pack(side="left")
        ctk.CTkButton(head, text="✏️ Saisir", command=self._saisir).pack(side="left", padx=8)
        ctk.CTkButton(head, text="✅ Valider définitivement", command=self._valider).pack(side="left", padx=8)

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._tree = ttk.Treeview(
            frame,
            columns=("id", "type", "event", "date", "statut"),
            show="headings",
        )
        for col, txt, width in (
            ("id", "ID", 80),
            ("type", "Type", 180),
            ("event", "Événement", 260),
            ("date", "Date", 140),
            ("statut", "Statut", 120),
        ):
            self._tree.heading(col, text=txt)
            self._tree.column(col, width=width, anchor="center" if col in {"id", "date", "statut"} else "w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _charger(self) -> None:
        self._inventaires = get_inventaires()
        self._tree.delete(*self._tree.get_children())
        labels = {v: k for k, v in self.TYPES.items()}
        for inv in self._inventaires:
            self._tree.insert(
                "",
                "end",
                iid=str(inv["id"]),
                values=(
                    inv["id"],
                    labels.get(inv.get("type_inventaire"), inv.get("type_inventaire", "")),
                    inv.get("evenement_nom") or "—",
                    inv.get("date_inventaire") or "",
                    inv.get("statut") or "",
                ),
            )

    def _nouveau(self) -> None:
        dialog = _DialogNouvelInventaire(self)
        self.wait_window(dialog)
        self._charger()

    def _selected_id(self) -> int | None:
        sel = self._tree.selection()
        return int(sel[0]) if sel else None

    def _saisir(self) -> None:
        inventaire_id = self._selected_id()
        if inventaire_id is None:
            afficher_info(self, "Inventaires", "Sélectionnez un inventaire.")
            return
        dialog = _DialogSaisieInventaire(self, inventaire_id)
        self.wait_window(dialog)
        self._charger()

    def _valider(self) -> None:
        inventaire_id = self._selected_id()
        if inventaire_id is None:
            afficher_info(self, "Inventaires", "Sélectionnez un inventaire.")
            return
        result = valider_inventaire(inventaire_id)
        afficher_info(
            self,
            "Inventaire",
            (
                f"Inventaire validé : {result['nb_lignes']} ligne(s)\n"
                f"Valeur totale des écarts : {result['ecart_total_valeur']:.2f} €"
            ),
        )
        self._charger()


class _DialogNouvelInventaire(ctk.CTkToplevel):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("Nouvel inventaire")
        self.transient(parent)
        self.grab_set()

        self._events = get_evenements_for_select()
        self._type_var = tk.StringVar(value="Avant événement")
        self._event_var = tk.StringVar(value="— Aucun —")

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="Type").grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkOptionMenu(frame, values=list(OngletInventaires.TYPES.keys()), variable=self._type_var).grid(row=0, column=1, sticky="ew", pady=6)

        ctk.CTkLabel(frame, text="Événement").grid(row=1, column=0, sticky="w", pady=6)
        ctk.CTkOptionMenu(frame, values=["— Aucun —"] + [e["nom"] for e in self._events], variable=self._event_var).grid(row=1, column=1, sticky="ew", pady=6)

        ctk.CTkButton(frame, text="Créer", command=self._save).grid(row=2, column=1, sticky="e", pady=(10, 0))
        frame.grid_columnconfigure(1, weight=1)

    def _save(self) -> None:
        event = next((e for e in self._events if e["nom"] == self._event_var.get()), None)
        event_id = event["id"] if event else None
        creer_inventaire(event_id, OngletInventaires.TYPES[self._type_var.get()])
        self.destroy()


class _DialogSaisieInventaire(ctk.CTkToplevel):
    def __init__(self, parent: Any, inventaire_id: int) -> None:
        super().__init__(parent)
        self.title(f"Saisie inventaire #{inventaire_id}")
        self.geometry("1000x560")
        self.transient(parent)
        self.grab_set()

        self._inventaire_id = inventaire_id
        self._lignes = get_lignes_inventaire(inventaire_id)
        self._vars: dict[int, tk.StringVar] = {}

        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        for i, txt in enumerate(["Article", "Lot", "Qté théorique", "Qté réelle"]):
            ctk.CTkLabel(header, text=txt).grid(row=0, column=i, padx=6, sticky="w")

        for idx, ligne in enumerate(self._lignes, start=1):
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=ligne.get("article") or "").grid(row=0, column=0, padx=6, sticky="w")
            ctk.CTkLabel(row, text=ligne.get("lot") or "—").grid(row=0, column=1, padx=6, sticky="w")
            ctk.CTkLabel(row, text=str(int(ligne.get("qte_theorique") or 0))).grid(row=0, column=2, padx=6, sticky="w")
            var = tk.StringVar(value=str(int(ligne.get("qte_reelle") or 0)))
            self._vars[int(ligne["id"])] = var
            ctk.CTkEntry(row, textvariable=var, width=120).grid(row=0, column=3, padx=6, sticky="w")

        ctk.CTkButton(self, text="Enregistrer la saisie", command=self._save).pack(anchor="e", padx=12, pady=(0, 12))

    def _save(self) -> None:
        try:
            for ligne in self._lignes:
                ligne_id = int(ligne["id"])
                qte = int((self._vars[ligne_id].get() or "0").strip())
                saisir_ligne_inventaire(
                    self._inventaire_id,
                    int(ligne["article_id"]),
                    int(ligne["lot_id"]) if ligne.get("lot_id") else None,
                    qte,
                )
        except ValueError:
            afficher_erreur(self, "Erreur", "La quantité réelle doit être un nombre entier.")
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur saisie inventaire : %s", exc)
            afficher_erreur(self, "Erreur", f"Échec de l'enregistrement de l'inventaire : {exc}")
            return
        self.destroy()
