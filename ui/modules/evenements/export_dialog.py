"""Dialogue d'export d'un événement (PDF et Excel).

Appelé depuis la fiche événement via le bouton "📤 Exporter".
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from core.exports import (
    export_bilan_evenement_excel,
    export_bilan_evenement_pdf,
    export_liste_benevoles_excel,
    export_liste_benevoles_pdf,
    export_pv_tirage_pdf,
    generer_nom_fichier,
    slugifier_nom,
)
from db.models.evenements import get_evenement_by_id, get_parametre
from db.models.tombola import get_lots_evenement
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur


class ExportDialog(ctk.CTkToplevel):
    """Fenêtre modale d'export d'un événement."""

    def __init__(self, parent: Any, evenement_id: int) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._evenement = get_evenement_by_id(evenement_id)

        nom_ev = (self._evenement or {}).get("nom") or f"Événement #{evenement_id}"
        self.title(f"📤 Exporter — {nom_ev}")
        self.geometry("540x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Variables
        self._var_pdf_bilan = ctk.BooleanVar(value=True)
        self._var_excel_bilan = ctk.BooleanVar(value=True)
        self._var_pdf_pv = ctk.BooleanVar(value=False)
        self._var_pdf_benevoles = ctk.BooleanVar(value=False)
        self._var_excel_benevoles = ctk.BooleanVar(value=False)
        self._dossier_var = ctk.StringVar(value=os.path.expanduser("~"))

        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        nom_ev = (self._evenement or {}).get("nom") or f"Événement #{self._evenement_id}"

        ctk.CTkLabel(
            self,
            text=f"📤 Exporter l'événement — {nom_ev}",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            self,
            text="Que souhaitez-vous exporter ?",
            font=fonts.get("normal"),
        ).pack(anchor="w", padx=20, pady=(0, 6))

        frame_options = ctk.CTkFrame(self, fg_color="transparent")
        frame_options.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkCheckBox(frame_options, text="Bilan complet (PDF)", variable=self._var_pdf_bilan).pack(
            anchor="w", pady=2
        )
        ctk.CTkCheckBox(frame_options, text="Bilan complet (Excel)", variable=self._var_excel_bilan).pack(
            anchor="w", pady=2
        )

        # PV tirage : disponible seulement si des lots existent
        lots = get_lots_evenement(self._evenement_id)
        cb_pv = ctk.CTkCheckBox(
            frame_options,
            text="PV de tirage tombola (PDF)",
            variable=self._var_pdf_pv,
        )
        if not lots:
            cb_pv.configure(state="disabled")
            self._var_pdf_pv.set(False)
        cb_pv.pack(anchor="w", pady=2)

        ctk.CTkCheckBox(
            frame_options, text="Liste des bénévoles (PDF)", variable=self._var_pdf_benevoles
        ).pack(anchor="w", pady=2)
        ctk.CTkCheckBox(
            frame_options, text="Liste des bénévoles (Excel)", variable=self._var_excel_benevoles
        ).pack(anchor="w", pady=2)

        # Dossier destination
        ctk.CTkLabel(
            self,
            text="Dossier de destination :",
            font=fonts.get("normal"),
        ).pack(anchor="w", padx=20, pady=(4, 2))

        frame_dossier = ctk.CTkFrame(self, fg_color="transparent")
        frame_dossier.pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkEntry(frame_dossier, textvariable=self._dossier_var, width=360).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            frame_dossier,
            text="📁 Choisir",
            width=100,
            command=self._choisir_dossier,
        ).pack(side="left", padx=(6, 0))

        # Avertissement config asso
        asso_nom = get_parametre("asso_nom") or ""
        if not asso_nom.strip():
            frame_warn = ctk.CTkFrame(self, fg_color="#fff3cd", corner_radius=6)
            frame_warn.pack(fill="x", padx=20, pady=(0, 6))
            ctk.CTkLabel(
                frame_warn,
                text="⚠️  Infos association non configurées",
                text_color="#856404",
                font=fonts.get("small"),
            ).pack(side="left", padx=8, pady=4)
            ctk.CTkButton(
                frame_warn,
                text="⚙️ Configurer",
                width=110,
                height=26,
                command=self._ouvrir_config_asso,
            ).pack(side="right", padx=8, pady=4)

        # Boutons
        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=20, pady=(4, 16), side="bottom")
        ctk.CTkButton(f_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy).pack(
            side="left"
        )
        ctk.CTkButton(
            f_btn,
            text="📤 Exporter",
            width=140,
            command=self._exporter,
        ).pack(side="right")

    def _choisir_dossier(self) -> None:
        """Ouvre un sélecteur de dossier."""
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get(),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _ouvrir_config_asso(self) -> None:
        """Ouvre le dialogue de configuration de l'association."""
        from ui.modules.evenements.config_asso_dialog import ConfigAssoDialog

        dialog = ConfigAssoDialog(self)
        self.wait_window(dialog)

    def _exporter(self) -> None:
        """Lance les exports sélectionnés."""
        dossier = self._dossier_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier de destination valide.")
            return

        if not any([
            self._var_pdf_bilan.get(),
            self._var_excel_bilan.get(),
            self._var_pdf_pv.get(),
            self._var_pdf_benevoles.get(),
            self._var_excel_benevoles.get(),
        ]):
            afficher_erreur(self, "Aucun export", "Veuillez sélectionner au moins un format à exporter.")
            return

        nom_ev = (self._evenement or {}).get("nom") or f"evenement_{self._evenement_id}"
        date_str = datetime.now().strftime("%Y%m%d")
        fichiers_generes: list[str] = []
        erreurs: list[str] = []

        if self._var_pdf_bilan.get():
            nom = generer_nom_fichier(nom_ev, date_str, "pdf")
            chemin = os.path.join(dossier, nom)
            if export_bilan_evenement_pdf(self._evenement_id, chemin):
                fichiers_generes.append(nom)
            else:
                erreurs.append(f"Échec export PDF bilan : {nom}")

        if self._var_excel_bilan.get():
            nom = generer_nom_fichier(nom_ev, date_str, "xlsx")
            chemin = os.path.join(dossier, nom)
            if export_bilan_evenement_excel(self._evenement_id, chemin):
                fichiers_generes.append(nom)
            else:
                erreurs.append(f"Échec export Excel bilan : {nom}")

        if self._var_pdf_pv.get():
            slug = slugifier_nom(nom_ev)
            nom = f"pv_tirage_{slug}_{date_str}.pdf"
            chemin = os.path.join(dossier, nom)
            if export_pv_tirage_pdf(self._evenement_id, chemin):
                fichiers_generes.append(nom)
            else:
                erreurs.append(f"Échec export PV tirage : {nom}")

        if self._var_pdf_benevoles.get():
            slug = slugifier_nom(nom_ev)
            nom = f"benevoles_{slug}_{date_str}.pdf"
            chemin = os.path.join(dossier, nom)
            if export_liste_benevoles_pdf(self._evenement_id, chemin):
                fichiers_generes.append(nom)
            else:
                erreurs.append(f"Échec export bénévoles PDF : {nom}")

        if self._var_excel_benevoles.get():
            slug = slugifier_nom(nom_ev)
            nom = f"benevoles_{slug}_{date_str}.xlsx"
            chemin = os.path.join(dossier, nom)
            if export_liste_benevoles_excel(self._evenement_id, chemin):
                fichiers_generes.append(nom)
            else:
                erreurs.append(f"Échec export bénévoles Excel : {nom}")

        if erreurs:
            msg_erreur = "\n".join(erreurs)
            afficher_erreur(
                self,
                "Erreurs lors de l'export",
                f"Certains exports ont échoué :\n{msg_erreur}\n\nVérifiez les permissions du dossier.",
            )

        if fichiers_generes:
            self._afficher_succes(dossier, fichiers_generes)

    def _afficher_succes(self, dossier: str, fichiers: list[str]) -> None:
        """Affiche la fenêtre de succès après export."""
        self.destroy()
        _DialogSuccesExport(self.master, dossier, fichiers)


class _DialogSuccesExport(ctk.CTkToplevel):
    """Dialogue affiché après un export réussi."""

    def __init__(self, parent: Any, dossier: str, fichiers: list[str]) -> None:
        super().__init__(parent)
        self._dossier = dossier
        self.title("✅ Export terminé")
        self.geometry("440x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        fonts = app_theme.FONTS

        ctk.CTkLabel(self, text="✅ Export terminé !", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 8)
        )
        ctk.CTkLabel(self, text="Fichiers générés :", font=fonts.get("bold")).pack(
            anchor="w", padx=20, pady=(0, 4)
        )

        frame_fichiers = ctk.CTkScrollableFrame(self, height=100, fg_color="transparent")
        frame_fichiers.pack(fill="x", padx=20, pady=(0, 8))
        for f in fichiers:
            ctk.CTkLabel(frame_fichiers, text=f"• {f}", anchor="w").pack(anchor="w")

        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=20, pady=(4, 16))
        ctk.CTkButton(
            f_btn,
            text="📂 Ouvrir le dossier",
            width=160,
            command=self._ouvrir_dossier,
        ).pack(side="left")
        ctk.CTkButton(f_btn, text="Fermer", width=100, fg_color="grey", command=self.destroy).pack(
            side="right"
        )

    def _ouvrir_dossier(self) -> None:
        """Ouvre le dossier dans l'explorateur de fichiers."""
        try:
            if sys.platform == "win32":
                os.startfile(self._dossier)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self._dossier])
            else:
                subprocess.Popen(["xdg-open", self._dossier])
        except Exception:
            pass
        self.destroy()
