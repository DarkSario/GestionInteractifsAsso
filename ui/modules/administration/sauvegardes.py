"""Fenêtre de gestion des sauvegardes."""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, ttk
from typing import Any

import customtkinter as ctk

from core.parametres import get_config_systeme, set_config_systeme
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from ui.modules.administration.import_export_dialog import ExportBaseDialog, ImportBaseDialog
from ui.modules.administration.restauration_dialog import RestaurationDialog
from utils.backup import (
    get_liste_sauvegardes,
    sauvegarder_maintenant,
    supprimer_sauvegarde,
)


class SauvegardesApp(ctk.CTkToplevel):
    """Fenêtre principale de gestion des sauvegardes."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("💾 Gestion des sauvegardes")
        self.geometry("980x680")
        self.minsize(860, 620)
        self.transient(parent)

        self._sauvegardes: list[dict] = []
        self._sauvegarde_auto_var = tk.BooleanVar(value=False)
        self._sauvegarde_frequence_var = tk.StringVar(value="7")
        self._sauvegarde_dossier_var = tk.StringVar()
        self._rotation_max_var = tk.StringVar(value="10")
        self._compression_var = tk.BooleanVar(value=True)
        self._inclure_config_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._charger_donnees()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="💾 Gestion des sauvegardes",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 10))

        self._frame_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._frame_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._build_bloc_configuration()
        self._build_bloc_historique()
        self._build_bloc_actions()

    def _build_bloc_configuration(self) -> None:
        fonts = app_theme.FONTS

        frame = ctk.CTkFrame(self._frame_scroll)
        frame.pack(fill="x", padx=4, pady=(0, 12))
        ctk.CTkLabel(
            frame,
            text="Sauvegarde automatique",
            font=fonts.get("subtitle"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        ctk.CTkCheckBox(
            frame,
            text="Activer la sauvegarde automatique",
            variable=self._sauvegarde_auto_var,
        ).pack(anchor="w", padx=16, pady=2)

        row_freq = ctk.CTkFrame(frame, fg_color="transparent")
        row_freq.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row_freq, text="Fréquence", width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(row_freq, textvariable=self._sauvegarde_frequence_var, width=90).pack(side="left")
        ctk.CTkLabel(row_freq, text="jours").pack(side="left", padx=(8, 0))

        row_dossier = ctk.CTkFrame(frame, fg_color="transparent")
        row_dossier.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row_dossier, text="Dossier", width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(row_dossier, textvariable=self._sauvegarde_dossier_var, width=500).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            row_dossier,
            text="📁 Choisir",
            width=110,
            command=self._choisir_dossier,
        ).pack(side="left", padx=(8, 0))

        row_rotation = ctk.CTkFrame(frame, fg_color="transparent")
        row_rotation.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(row_rotation, text="Garder les", width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(row_rotation, textvariable=self._rotation_max_var, width=90).pack(side="left")
        ctk.CTkLabel(row_rotation, text="dernières sauvegardes").pack(side="left", padx=(8, 0))

        ctk.CTkCheckBox(
            frame,
            text="Compresser les sauvegardes en .zip",
            variable=self._compression_var,
        ).pack(anchor="w", padx=16, pady=2)
        ctk.CTkCheckBox(
            frame,
            text="Inclure la configuration dans les archives .zip",
            variable=self._inclure_config_var,
        ).pack(anchor="w", padx=16, pady=2)

        self._derniere_sauvegarde_label = ctk.CTkLabel(
            frame,
            text="Dernière sauvegarde : —",
            font=fonts.get("small"),
            text_color="grey",
        )
        self._derniere_sauvegarde_label.pack(anchor="w", padx=16, pady=(8, 4))

        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkButton(
            frame_btn,
            text="💾 Enregistrer les réglages",
            width=190,
            command=self._enregistrer_reglages,
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn,
            text="💾 Sauvegarder maintenant",
            width=190,
            command=self._sauvegarder_maintenant,
        ).pack(side="right")

    def _build_bloc_historique(self) -> None:
        fonts = app_theme.FONTS

        frame = ctk.CTkFrame(self._frame_scroll)
        frame.pack(fill="both", expand=True, padx=4, pady=(0, 12))
        ctk.CTkLabel(
            frame,
            text="Historique des sauvegardes",
            font=fonts.get("subtitle"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        table_frame = tk.Frame(frame)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        colonnes = ("nom", "type", "taille", "date", "statut")
        self._tree = ttk.Treeview(table_frame, columns=colonnes, show="headings", height=12)
        self._tree.heading("nom", text="Nom fichier")
        self._tree.heading("type", text="Type")
        self._tree.heading("taille", text="Taille")
        self._tree.heading("date", text="Date")
        self._tree.heading("statut", text="Statut")

        self._tree.column("nom", width=360)
        self._tree.column("type", width=110, anchor="center")
        self._tree.column("taille", width=110, anchor="center")
        self._tree.column("date", width=170, anchor="center")
        self._tree.column("statut", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
        frame_btn.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(frame_btn, text="🔄 Actualiser", width=120, command=self._charger_historique).pack(
            side="left"
        )
        ctk.CTkButton(frame_btn, text="🔄 Restaurer", width=140, command=self._restaurer_selection).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(frame_btn, text="🗑️ Supprimer", width=140, command=self._supprimer_selection).pack(
            side="right"
        )

    def _build_bloc_actions(self) -> None:
        frame = ctk.CTkFrame(self._frame_scroll, fg_color="transparent")
        frame.pack(fill="x", padx=4, pady=(0, 12))

        ctk.CTkButton(frame, text="📤 Exporter la base", width=180, command=self._ouvrir_export).pack(
            side="left"
        )
        ctk.CTkButton(frame, text="📥 Importer une base", width=180, command=self._ouvrir_import).pack(
            side="left", padx=(8, 0)
        )

    def _charger_donnees(self) -> None:
        config = get_config_systeme()
        self._sauvegarde_auto_var.set(config.get("sauvegarde_auto", "0") == "1")
        self._sauvegarde_frequence_var.set(config.get("sauvegarde_frequence", "7"))
        self._sauvegarde_dossier_var.set(config.get("sauvegarde_dossier", ""))
        self._rotation_max_var.set(config.get("sauvegarde_rotation_max", "10"))
        self._compression_var.set(config.get("sauvegarde_compression", "1") == "1")
        self._inclure_config_var.set(config.get("sauvegarde_inclure_config", "1") == "1")

        derniere = config.get("derniere_sauvegarde", "")
        self._derniere_sauvegarde_label.configure(
            text=f"Dernière sauvegarde : {self._formater_derniere_sauvegarde(derniere)}"
        )
        self._charger_historique()

    def _charger_historique(self) -> None:
        self._sauvegardes = get_liste_sauvegardes()
        for item in self._tree.get_children():
            self._tree.delete(item)

        for sauvegarde in self._sauvegardes:
            self._tree.insert(
                "",
                "end",
                iid=str(sauvegarde["id"]),
                values=(
                    sauvegarde["nom_fichier"],
                    sauvegarde["type"],
                    sauvegarde["taille_formatee"],
                    sauvegarde["date_formatee"],
                    sauvegarde["statut"],
                ),
            )

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de sauvegarde",
            initialdir=self._sauvegarde_dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._sauvegarde_dossier_var.set(dossier)

    def _enregistrer_reglages(self, notify: bool = True) -> bool:
        try:
            frequence = int(self._sauvegarde_frequence_var.get().strip())
            rotation = int(self._rotation_max_var.get().strip())
            if frequence < 1 or rotation < 1:
                raise ValueError
        except ValueError:
            afficher_erreur(
                self,
                "Valeur invalide",
                "La fréquence et la rotation doivent être des entiers positifs.",
            )
            return False

        if not set_config_systeme(
            sauvegarde_auto="1" if self._sauvegarde_auto_var.get() else "0",
            sauvegarde_frequence=str(frequence),
            sauvegarde_dossier=self._sauvegarde_dossier_var.get().strip(),
            sauvegarde_rotation_max=str(rotation),
            sauvegarde_compression="1" if self._compression_var.get() else "0",
            sauvegarde_inclure_config="1" if self._inclure_config_var.get() else "0",
        ):
            afficher_erreur(self, "Erreur", "Les réglages n'ont pas pu être enregistrés.")
            return False

        if notify:
            afficher_info(self, "Réglages enregistrés", "Les paramètres de sauvegarde ont été mis à jour.")
        self._charger_donnees()
        return True

    def _sauvegarder_maintenant(self) -> None:
        if not self._enregistrer_reglages(notify=False):
            return
        resultat = sauvegarder_maintenant()
        if not resultat["succes"]:
            afficher_erreur(self, "Erreur de sauvegarde", resultat["message"])
            return

        afficher_info(self, "Sauvegarde réussie", f"Sauvegarde créée :\n{resultat['chemin']}")
        self._charger_donnees()

    def _restaurer_selection(self) -> None:
        sauvegarde = self._get_selection()
        if not sauvegarde:
            afficher_erreur(self, "Aucune sélection", "Veuillez sélectionner une sauvegarde.")
            return

        dialog = RestaurationDialog(self, sauvegarde)
        self.wait_window(dialog)
        self._charger_donnees()

    def _supprimer_selection(self) -> None:
        sauvegarde = self._get_selection()
        if not sauvegarde:
            afficher_erreur(self, "Aucune sélection", "Veuillez sélectionner une sauvegarde.")
            return
        if not demander_confirmation(
            self,
            "Supprimer la sauvegarde",
            f"Supprimer « {sauvegarde['nom_fichier']} » ?",
        ):
            return

        if not supprimer_sauvegarde(int(sauvegarde["id"])):
            afficher_erreur(self, "Suppression impossible", "La sauvegarde n'a pas pu être supprimée.")
            return

        self._charger_historique()

    def _ouvrir_export(self) -> None:
        dialog = ExportBaseDialog(self)
        self.wait_window(dialog)
        self._charger_donnees()

    def _ouvrir_import(self) -> None:
        dialog = ImportBaseDialog(self)
        self.wait_window(dialog)
        self._charger_donnees()

    def _get_selection(self) -> dict | None:
        selection = self._tree.selection()
        if not selection:
            return None
        sauvegarde_id = int(selection[0])
        return next((item for item in self._sauvegardes if item["id"] == sauvegarde_id), None)

    @staticmethod
    def _formater_derniere_sauvegarde(valeur: str) -> str:
        if not valeur:
            return "—"
        try:
            return datetime.fromisoformat(valeur).strftime("%d/%m/%Y à %Hh%M")
        except ValueError:
            return valeur
