"""Fenêtre d'export CSV des opérations de trésorerie."""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from db.models.tresorerie import get_operations
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class ExportCSVTresorerieDialog(ctk.CTkToplevel):
    """Fenêtre d'export CSV des opérations de trésorerie par exercice ou période."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("📊 Export CSV Trésorerie")
        self.geometry("560x460")
        self.minsize(500, 400)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        annee_en_cours = datetime.now().year

        self._type_periode_var = ctk.StringVar(value="exercice")
        self._annee_var = ctk.StringVar(value=str(annee_en_cours))
        self._date_debut_var = ctk.StringVar(value=f"{annee_en_cours}-01-01")
        self._date_fin_var = ctk.StringVar(value=f"{annee_en_cours}-12-31")
        self._inclure_annules_var = ctk.BooleanVar(value=False)
        self._dossier_var = ctk.StringVar(value=os.path.expanduser("~"))
        self._nom_fichier_var = ctk.StringVar(
            value=f"tresorerie_{annee_en_cours}_{datetime.now().strftime('%Y-%m-%d')}.csv"
        )

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(scroll, text="📊 Export CSV Trésorerie", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        # ── Période ───────────────────────────────────────────────────────────
        frame_periode = ctk.CTkFrame(scroll)
        frame_periode.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_periode, text="Période", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        annees = [str(y) for y in range(datetime.now().year - 4, datetime.now().year + 2)]

        row_annee = ctk.CTkFrame(frame_periode, fg_color="transparent")
        row_annee.pack(fill="x", padx=12, pady=2)
        ctk.CTkRadioButton(
            row_annee, text="Année", variable=self._type_periode_var, value="exercice", width=120,
        ).pack(side="left")
        ctk.CTkOptionMenu(
            row_annee, values=annees, variable=self._annee_var, width=120,
        ).pack(side="left", padx=(8, 0))

        row_libre = ctk.CTkFrame(frame_periode, fg_color="transparent")
        row_libre.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkRadioButton(
            row_libre, text="Période libre", variable=self._type_periode_var, value="libre", width=120,
        ).pack(side="left")
        ctk.CTkLabel(row_libre, text="Du", width=30).pack(side="left", padx=(8, 0))
        ctk.CTkEntry(row_libre, textvariable=self._date_debut_var, width=110).pack(side="left", padx=4)
        ctk.CTkLabel(row_libre, text="au").pack(side="left", padx=4)
        ctk.CTkEntry(row_libre, textvariable=self._date_fin_var, width=110).pack(side="left", padx=4)

        # ── Options ───────────────────────────────────────────────────────────
        frame_opts = ctk.CTkFrame(scroll)
        frame_opts.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(frame_opts, text="Options", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        ctk.CTkCheckBox(
            frame_opts, text="Inclure les opérations annulées", variable=self._inclure_annules_var,
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # ── Destination ───────────────────────────────────────────────────────
        frame_dest = ctk.CTkFrame(scroll)
        frame_dest.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(frame_dest, text="Destination", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        row_dossier = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_dossier.pack(fill="x", padx=12, pady=4)
        ctk.CTkEntry(row_dossier, textvariable=self._dossier_var, width=350).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(row_dossier, text="📁 Choisir", width=110, command=self._choisir_dossier).pack(
            side="left", padx=(8, 0)
        )

        row_nom = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_nom.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_nom, text="Nom du fichier", width=120, anchor="w").pack(side="left")
        ctk.CTkEntry(row_nom, textvariable=self._nom_fichier_var).pack(side="left", fill="x", expand=True)

        # ── Boutons ───────────────────────────────────────────────────────────
        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(6, 16))
        ctk.CTkButton(frame_btn, text="Annuler", width=110, fg_color="grey", command=self.destroy).pack(side="left")
        ctk.CTkButton(
            frame_btn, text="📊 Exporter CSV", width=180, command=self._exporter,
        ).pack(side="right")

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _exporter(self) -> None:
        dossier = self._dossier_var.get().strip()
        nom_fichier = self._nom_fichier_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier valide.")
            return
        if not nom_fichier:
            afficher_erreur(self, "Nom manquant", "Veuillez renseigner un nom de fichier.")
            return

        type_periode = self._type_periode_var.get()
        if type_periode == "exercice":
            annee = self._annee_var.get()
            date_debut = f"{annee}-01-01"
            date_fin = f"{annee}-12-31"
        else:
            date_debut = self._date_debut_var.get().strip()
            date_fin = self._date_fin_var.get().strip()

        statut = None if self._inclure_annules_var.get() else "valide"

        try:
            operations = get_operations(
                date_debut=date_debut or None,
                date_fin=date_fin or None,
                statut=statut,
                exclude_non_comptable=True,
            )
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de charger les opérations :\n{exc}")
            return

        chemin = os.path.join(dossier, nom_fichier)
        try:
            _ecrire_csv(operations, chemin)
        except Exception as exc:
            afficher_erreur(self, "Erreur d'écriture", f"Impossible d'écrire le fichier :\n{exc}")
            return

        afficher_info(
            self,
            "Export réussi",
            f"{len(operations)} opération(s) exportée(s) :\n{chemin}",
        )
        self.destroy()


# ── Sources non comptables à exclure même si exclude_non_comptable=False ───────
_SOURCES_TRACABILITE = {"depot_especes", "remise_cheque"}


def _ecrire_csv(operations: list[dict], chemin: str) -> None:
    """Écrit les opérations dans un fichier CSV UTF-8 BOM compatible Excel français."""
    colonnes = ["Date", "Libellé", "Catégorie", "Type", "Montant", "Mode paiement", "Statut", "Compte"]

    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(colonnes)
        for op in operations:
            source = op.get("source_module") or ""
            if source in _SOURCES_TRACABILITE:
                continue

            montant_raw = float(op.get("montant") or 0)
            montant_str = f"{montant_raw:.2f}".replace(".", ",")

            writer.writerow([
                op.get("date_operation") or "",
                op.get("libelle") or "",
                op.get("categorie_nom") or "",
                _libelle_type(op.get("type_operation") or ""),
                montant_str,
                op.get("mode_paiement") or "",
                _libelle_statut(op.get("statut") or ""),
                op.get("compte_nom") or "",
            ])


def _libelle_type(type_op: str) -> str:
    return {
        "recette": "Recette",
        "depense": "Dépense",
        "virement_interne": "Virement interne",
    }.get(type_op, type_op)


def _libelle_statut(statut: str) -> str:
    return {
        "valide": "Validé",
        "annule": "Annulé",
        "en_attente": "En attente",
    }.get(statut, statut)
