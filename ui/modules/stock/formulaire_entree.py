"""Formulaire d'entrée de marchandise avec gestion des lots et tags."""

from __future__ import annotations

from datetime import date
import tkinter as tk
from typing import Any

import customtkinter as ctk

from core.stock_v2 import add_lot, get_tags
from db.models.fournisseurs import get_fournisseurs_for_select
from db.models.stock import add_mouvement, get_articles_for_select
from ui.components.dialogs import afficher_erreur, afficher_info
from utils.logger import get_logger

logger = get_logger(__name__)

# Type de mouvement pour une entrée de marchandise (index 0 de TYPES_MOUVEMENTS)
_TYPE_ENTREE_ACHAT = "Entrée — Achat"


class FormulaireEntreeMarchandise(ctk.CTkToplevel):
    """Saisie d'une entrée de marchandise en lot."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("📦 Entrée de marchandise")
        self.geometry("780x620")
        self.transient(parent)

        self._articles = get_articles_for_select()
        self._fournisseurs = get_fournisseurs_for_select()
        self._article_labels = {f"{a['id']} — {a['nom']}": a for a in self._articles}
        self._fournisseur_labels = {f"{f['id']} — {f['nom']}": f for f in self._fournisseurs}
        self._tags = get_tags()
        self._tag_vars: dict[int, tk.BooleanVar] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        self._article_var = ctk.StringVar(
            value=next(iter(self._article_labels), "")
        )
        self._quantite_var = ctk.StringVar(value="1")
        self._prix_ht_var = ctk.StringVar(value="0")
        self._prix_ttc_var = ctk.StringVar(value="0")
        self._tva_var = ctk.StringVar(value="20")
        self._facture_var = ctk.StringVar()
        self._lot_var = ctk.StringVar()
        self._date_achat_var = ctk.StringVar(value=date.today().isoformat())
        self._date_peremption_var = ctk.StringVar()
        self._fournisseur_var = ctk.StringVar(value="— Aucun —")

        row = 0
        ctk.CTkLabel(frame, text="Article").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(
            frame,
            values=list(self._article_labels.keys()) or [""],
            variable=self._article_var,
        ).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Quantité").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._quantite_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Prix unitaire HT (€)").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._prix_ht_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="TVA (%)").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._tva_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Prix unitaire TTC (€)").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._prix_ttc_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Fournisseur").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkOptionMenu(
            frame,
            values=["— Aucun —"] + list(self._fournisseur_labels.keys()),
            variable=self._fournisseur_var,
        ).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="N° Facture").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._facture_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="N° Lot").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._lot_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Date achat (AAAA-MM-JJ)").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._date_achat_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Date péremption (optionnel)").grid(row=row, column=0, sticky="w", pady=5)
        ctk.CTkEntry(frame, textvariable=self._date_peremption_var).grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ctk.CTkLabel(frame, text="Tags").grid(row=row, column=0, sticky="nw", pady=5)
        tags_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tags_frame.grid(row=row, column=1, sticky="w", pady=5)
        for tag in self._tags:
            var = tk.BooleanVar(value=False)
            self._tag_vars[int(tag["id"])] = var
            ctk.CTkCheckBox(tags_frame, text=tag["nom"], variable=var).pack(side="left", padx=(0, 8))
        row += 1

        ctk.CTkButton(frame, text="💾 Enregistrer", command=self._enregistrer).grid(row=row, column=1, sticky="e", pady=12)
        frame.grid_columnconfigure(1, weight=1)

    def _enregistrer(self) -> None:
        try:
            article = self._article_labels.get(self._article_var.get())
            if not article:
                afficher_erreur(self, "Erreur", "Article introuvable.")
                return

            fournisseur = self._fournisseur_labels.get(self._fournisseur_var.get())
            quantite = int(self._quantite_var.get() or 0)
            prix_ttc = self._parse_float(self._prix_ttc_var.get())
            lot_id = add_lot(
                article_id=article["id"],
                quantite=quantite,
                prix_ht=self._parse_float(self._prix_ht_var.get()),
                prix_ttc=prix_ttc,
                tva_taux=self._parse_float(self._tva_var.get()),
                fournisseur_id=fournisseur["id"] if fournisseur else None,
                numero_facture=self._facture_var.get(),
                numero_lot=self._lot_var.get(),
                date_achat=self._date_achat_var.get(),
                date_peremption=self._date_peremption_var.get(),
                commentaire="",
                tag_ids=[tag_id for tag_id, var in self._tag_vars.items() if var.get()],
            )
            # Créer un mouvement dans mouvements_stock pour synchroniser l'affichage
            if quantite > 0:
                add_mouvement(
                    stock_id=article["id"],
                    date=self._date_achat_var.get() or date.today().isoformat(),
                    type_mouvement=_TYPE_ENTREE_ACHAT,
                    quantite=quantite,
                    prix_unitaire=prix_ttc if prix_ttc > 0 else None,
                    fournisseur_id=fournisseur["id"] if fournisseur else None,
                    evenement_id=None,
                    numero_facture=self._facture_var.get() or None,
                    commentaire=f"Lot #{lot_id}" if lot_id else None,
                )
        except ValueError:
            afficher_erreur(
                self,
                "Erreur",
                "Vérifiez les champs numériques (quantité, prix, TVA).",
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erreur entrée de marchandise : %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer l'entrée : {exc}")
            return

        afficher_info(self, "Stock", f"Lot créé avec succès (ID {lot_id}).")
        self.destroy()

    @staticmethod
    def _parse_float(value: str | None) -> float:
        return float((value or "0").replace(",", "."))
