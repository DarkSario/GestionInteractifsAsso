"""Dialogue d'export universel — Phase 9."""

from __future__ import annotations

import os
from datetime import datetime
from tkinter import filedialog
from typing import Any, Callable

import customtkinter as ctk

from db.models.parametres_globaux import get_parametre
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class ExportDialog(ctk.CTkToplevel):
    """Dialogue d'export universel (PDF / Excel / CSV)."""

    def __init__(
        self,
        parent,
        titre: str,
        prefixe_fichier: str,
        callback_pdf=None,
        callback_excel=None,
        callback_csv=None,
        avec_page_garde: bool = True,
        avec_graphiques: bool = False,
    ) -> None:
        super().__init__(parent)
        self._titre = titre
        self._prefixe = prefixe_fichier
        self._callback_pdf = callback_pdf
        self._callback_excel = callback_excel
        self._callback_csv = callback_csv
        self._avec_page_garde = avec_page_garde
        self._avec_graphiques = avec_graphiques

        self.title(f"📤 Exporter — {titre}")
        self.geometry("620x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        formats_disponibles = [
            fmt for fmt, cb in (
                ("pdf", callback_pdf),
                ("excel", callback_excel),
                ("csv", callback_csv),
            ) if cb is not None
        ]
        self._formats_disponibles = formats_disponibles
        format_defaut = formats_disponibles[0] if formats_disponibles else "pdf"

        self._format_var = ctk.StringVar(value=format_defaut)
        self._graphiques_var = ctk.BooleanVar(value=False)
        self._page_garde_var = ctk.BooleanVar(value=avec_page_garde)
        self._orientation_var = ctk.StringVar(value="portrait")
        self._dossier_var = ctk.StringVar(
            value=get_parametre("export_dossier_defaut", "") or os.path.expanduser("~")
        )
        self._nom_fichier_var = ctk.StringVar(value=self._nom_fichier_defaut(format_defaut))

        self._build_ui()
        self._update_pdf_options()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(self, text=f"📤 Exporter — {self._titre}", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        frame_formats = ctk.CTkFrame(self)
        frame_formats.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(frame_formats, text="Format", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        for text, value, callback in (
            ("PDF", "pdf", self._callback_pdf),
            ("Excel", "excel", self._callback_excel),
            ("CSV", "csv", self._callback_csv),
        ):
            ctk.CTkRadioButton(
                frame_formats,
                text=text,
                variable=self._format_var,
                value=value,
                state="normal" if callback else "disabled",
                command=self._on_format_change,
            ).pack(anchor="w", padx=16, pady=3)

        self._frame_pdf = ctk.CTkFrame(self)
        self._frame_pdf.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(self._frame_pdf, text="Options PDF", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )
        ctk.CTkCheckBox(
            self._frame_pdf,
            text="Inclure les graphiques",
            variable=self._graphiques_var,
            state="normal" if self._avec_graphiques else "disabled",
        ).pack(anchor="w", padx=16, pady=3)
        ctk.CTkCheckBox(
            self._frame_pdf,
            text="Page de garde",
            variable=self._page_garde_var,
        ).pack(anchor="w", padx=16, pady=3)

        frame_orientation = ctk.CTkFrame(self._frame_pdf, fg_color="transparent")
        frame_orientation.pack(fill="x", padx=16, pady=(6, 10))
        ctk.CTkLabel(frame_orientation, text="Orientation :", width=100, anchor="w").pack(side="left")
        ctk.CTkRadioButton(
            frame_orientation,
            text="Portrait",
            variable=self._orientation_var,
            value="portrait",
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            frame_orientation,
            text="Paysage",
            variable=self._orientation_var,
            value="paysage",
        ).pack(side="left")

        frame_dest = ctk.CTkFrame(self)
        frame_dest.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(frame_dest, text="Destination", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        row_dossier = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_dossier.pack(fill="x", padx=12, pady=4)
        ctk.CTkEntry(row_dossier, textvariable=self._dossier_var, width=420).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(row_dossier, text="📁 Choisir", width=110, command=self._choisir_dossier).pack(
            side="left", padx=(8, 0)
        )

        row_nom = ctk.CTkFrame(frame_dest, fg_color="transparent")
        row_nom.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_nom, text="Nom du fichier", width=110, anchor="w").pack(side="left")
        ctk.CTkEntry(row_nom, textvariable=self._nom_fichier_var).pack(side="left", fill="x", expand=True)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(6, 16), side="bottom")
        ctk.CTkButton(frame_btn, text="Annuler", width=110, fg_color="grey", command=self.destroy).pack(side="left")
        self._btn_exporter = ctk.CTkButton(frame_btn, text="📤 Exporter", width=150, command=self._exporter)
        self._btn_exporter.pack(side="right")
        if not self._formats_disponibles:
            self._btn_exporter.configure(state="disabled")

    def _nom_fichier_defaut(self, fmt: str) -> str:
        ext = self._extension_pour_format(fmt)
        return f"{self._prefixe}_{datetime.now().strftime('%Y-%m-%d')}.{ext}"

    @staticmethod
    def _extension_pour_format(fmt: str) -> str:
        return {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}.get(fmt, "dat")

    def _on_format_change(self) -> None:
        self._update_pdf_options()
        current = self._nom_fichier_var.get().strip()
        ext = self._extension_pour_format(self._format_var.get())
        if not current:
            self._nom_fichier_var.set(self._nom_fichier_defaut(self._format_var.get()))
            return
        base, _sep, _old_ext = current.rpartition(".")
        if base:
            self._nom_fichier_var.set(f"{base}.{ext}")
        else:
            self._nom_fichier_var.set(self._nom_fichier_defaut(self._format_var.get()))

    def _update_pdf_options(self) -> None:
        if self._format_var.get() == "pdf":
            self._frame_pdf.pack(fill="x", padx=20, pady=(0, 12))
        else:
            self._frame_pdf.pack_forget()

    def _choisir_dossier(self) -> None:
        dossier = filedialog.askdirectory(
            parent=self,
            title="Choisir le dossier de destination",
            initialdir=self._dossier_var.get() or os.path.expanduser("~"),
        )
        if dossier:
            self._dossier_var.set(dossier)

    def _appeler_callback(self, callback: Callable[..., Any] | None, chemin: str) -> Any:
        if callback is None:
            return False
        if self._format_var.get() == "pdf":
            try:
                return callback(
                    chemin,
                    page_garde=self._page_garde_var.get(),
                    inclure_graphiques=self._graphiques_var.get(),
                    orientation=self._orientation_var.get(),
                )
            except TypeError:
                return callback(chemin)
        return callback(chemin)

    def _exporter(self) -> None:
        if not self._formats_disponibles:
            afficher_erreur(self, "Aucun format", "Aucun export n'est disponible pour ce dialogue.")
            return

        dossier = self._dossier_var.get().strip()
        nom_fichier = self._nom_fichier_var.get().strip()
        if not dossier or not os.path.isdir(dossier):
            afficher_erreur(self, "Dossier invalide", "Veuillez sélectionner un dossier valide.")
            return
        if not nom_fichier:
            afficher_erreur(self, "Nom manquant", "Veuillez renseigner un nom de fichier.")
            return

        chemin = os.path.join(dossier, nom_fichier)
        format_selectionne = self._format_var.get()
        callback = {
            "pdf": self._callback_pdf,
            "excel": self._callback_excel,
            "csv": self._callback_csv,
        }.get(format_selectionne)
        try:
            ok = self._appeler_callback(callback, chemin)
        except Exception as exc:
            afficher_erreur(self, "Erreur d'export", str(exc))
            return

        if ok:
            afficher_info(self, "Export réussi", f"Fichier généré :\n{chemin}")
            self.destroy()
        else:
            afficher_erreur(self, "Échec de l'export", "Le fichier n'a pas pu être généré.")
