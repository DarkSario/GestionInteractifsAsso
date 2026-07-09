"""Gestion des polices PDF — Phase 9."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tkinter import filedialog, simpledialog

import customtkinter as ctk

from config.settings import CONFIG_DIR
from db.models.parametres_globaux import get_parametre, set_parametre
from db.models.polices import add_police, delete_police, get_all_polices, get_police_by_id
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation

try:
    from tkcolorpicker import askcolor as _askcolor
except ImportError:
    from tkinter.colorchooser import askcolor as _askcolor


class GestionPolices(ctk.CTkToplevel):
    """Fenêtre de gestion des polices PDF."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("🖋️ Polices PDF")
        self.geometry("760x620")
        self.minsize(700, 560)
        self.transient(parent)
        self.grab_set()

        self._polices: list[dict] = []
        self._police_titre_var = ctk.StringVar()
        self._police_corps_var = ctk.StringVar()
        self._taille_base_var = ctk.StringVar()
        self._couleur_var = ctk.StringVar()

        self._build_ui()
        self._charger_polices()
        self._charger_parametres()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        ctk.CTkLabel(self, text="🖋️ Polices PDF", font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 10)
        )

        ctk.CTkButton(
            self,
            text="+ Importer une police (.ttf / .otf)",
            width=240,
            command=self._importer_police,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        frame_liste = ctk.CTkFrame(self)
        frame_liste.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self._liste = ctk.CTkScrollableFrame(frame_liste, height=280)
        self._liste.pack(fill="both", expand=True, padx=8, pady=8)

        frame_params = ctk.CTkFrame(self)
        frame_params.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(frame_params, text="Paramètres PDF", font=fonts.get("subtitle")).pack(
            anchor="w", padx=12, pady=(10, 8)
        )

        self._combo_titre = self._ligne_option(frame_params, "Police titres :", self._police_titre_var)
        self._combo_corps = self._ligne_option(frame_params, "Police corps :", self._police_corps_var)

        row_taille = ctk.CTkFrame(frame_params, fg_color="transparent")
        row_taille.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row_taille, text="Taille base :", width=120, anchor="w").pack(side="left")
        ctk.CTkEntry(row_taille, textvariable=self._taille_base_var, width=100).pack(side="left")

        row_couleur = ctk.CTkFrame(frame_params, fg_color="transparent")
        row_couleur.pack(fill="x", padx=12, pady=(4, 12))
        ctk.CTkLabel(row_couleur, text="Couleur accent :", width=120, anchor="w").pack(side="left")
        ctk.CTkEntry(row_couleur, textvariable=self._couleur_var, width=160).pack(side="left")
        self._btn_couleur = ctk.CTkButton(
            row_couleur,
            text="🎨 Choisir",
            width=110,
            command=self._choisir_couleur,
        )
        self._btn_couleur.pack(side="left", padx=(8, 0))

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(frame_btn, text="Aperçu PDF", width=140, command=self._apercu_pdf).pack(side="left")
        ctk.CTkButton(frame_btn, text="💾 Enregistrer", width=140, command=self._enregistrer).pack(side="right")

    def _ligne_option(self, parent, label: str, variable: ctk.StringVar):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text=label, width=120, anchor="w").pack(side="left")
        combo = ctk.CTkOptionMenu(row, variable=variable, values=["Helvetica"], width=240)
        combo.pack(side="left")
        return combo

    def _charger_polices(self) -> None:
        self._polices = get_all_polices(actif_only=True)
        noms = [police["nom"] for police in self._polices] or ["Helvetica"]
        self._combo_titre.configure(values=noms)
        self._combo_corps.configure(values=noms)
        self._rafraichir_liste()

    def _charger_parametres(self) -> None:
        noms = [police["nom"] for police in self._polices] or ["Helvetica"]
        self._police_titre_var.set(get_parametre("pdf_police_titre", noms[0]))
        self._police_corps_var.set(get_parametre("pdf_police_corps", noms[0]))
        self._taille_base_var.set(get_parametre("pdf_taille_base", "11"))
        self._couleur_var.set(get_parametre("pdf_couleur_accent", "#1f6aa5"))
        self._maj_apercu_couleur()

    def _rafraichir_liste(self) -> None:
        for widget in self._liste.winfo_children():
            widget.destroy()

        fonts = app_theme.FONTS
        header = ctk.CTkFrame(self._liste, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(0, 4))
        for col, width in (("Nom", 180), ("Fichier", 220), ("Actif", 70), ("Actions", 110)):
            ctk.CTkLabel(header, text=col, width=width, anchor="w", font=fonts.get("bold")).pack(
                side="left", padx=4
            )

        for police in self._polices:
            row = ctk.CTkFrame(self._liste, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=2)
            ctk.CTkLabel(row, text=police.get("nom") or "", width=180, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=police.get("fichier") or "", width=220, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text="Oui" if police.get("actif") else "Non", width=70, anchor="w").pack(side="left", padx=4)
            ctk.CTkButton(
                row,
                text="🗑️ Supprimer",
                width=110,
                fg_color="#c0392b",
                hover_color="#922b21",
                state="disabled" if police.get("est_systeme") else "normal",
                command=lambda pid=police.get("id"): self._supprimer_police(int(pid)),
            ).pack(side="left", padx=4)

    def _importer_police(self) -> None:
        chemin = filedialog.askopenfilename(
            parent=self,
            title="Importer une police",
            filetypes=[("Polices", "*.ttf *.otf")],
        )
        if not chemin:
            return

        nom_affiche = simpledialog.askstring(
            "Nom de la police",
            "Nom à afficher pour cette police :",
            parent=self,
        )
        if not nom_affiche:
            return

        dossier_fonts = CONFIG_DIR / "fonts"
        dossier_fonts.mkdir(parents=True, exist_ok=True)
        source = Path(chemin)
        destination = dossier_fonts / source.name
        try:
            shutil.copy2(source, destination)
        except Exception as exc:
            afficher_erreur(self, "Import impossible", str(exc))
            return

        new_id = add_police(nom_affiche.strip(), destination.name, str(destination))
        if not new_id:
            afficher_erreur(self, "Import impossible", "La police n'a pas pu être enregistrée.")
            return
        self._charger_polices()
        afficher_info(self, "Police importée", f"Police ajoutée : {nom_affiche}")

    def _supprimer_police(self, police_id: int) -> None:
        police = get_police_by_id(police_id)
        if not police:
            return
        if not demander_confirmation(self, "Supprimer la police", f"Supprimer la police « {police.get('nom')} » ?"):
            return
        try:
            chemin = police.get("chemin") or ""
            if chemin and os.path.exists(chemin):
                os.remove(chemin)
        except OSError:
            pass
        if delete_police(police_id):
            self._charger_polices()

    def _choisir_couleur(self) -> None:
        result = _askcolor(color=self._couleur_var.get(), parent=self)
        couleur = result[1] if result else None
        if couleur:
            self._couleur_var.set(couleur)
            self._maj_apercu_couleur()

    def _maj_apercu_couleur(self) -> None:
        try:
            self._btn_couleur.configure(fg_color=self._couleur_var.get())
        except Exception:
            self._btn_couleur.configure(fg_color=app_theme.COLORS.get("primary", "#1f6aa5"))

    def _apercu_pdf(self) -> None:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            chemin = CONFIG_DIR / "apercu_polices.pdf"
            pdf = canvas.Canvas(str(chemin), pagesize=A4)
            pdf.setFont("Helvetica-Bold", 18)
            pdf.drawString(60, 780, "Aperçu PDF")
            pdf.setFont("Helvetica", 12)
            pdf.drawString(60, 750, f"Police titres : {self._police_titre_var.get()}")
            pdf.drawString(60, 730, f"Police corps : {self._police_corps_var.get()}")
            pdf.drawString(60, 710, f"Taille de base : {self._taille_base_var.get()}")
            pdf.drawString(60, 690, f"Couleur accent : {self._couleur_var.get()}")
            pdf.save()
            afficher_info(self, "Aperçu généré", f"Aperçu enregistré :\n{chemin}")
        except Exception as exc:
            afficher_erreur(self, "Aperçu impossible", str(exc))

    def _enregistrer(self) -> None:
        try:
            taille = int(self._taille_base_var.get().strip())
            if taille <= 0:
                raise ValueError
        except ValueError:
            afficher_erreur(self, "Valeur invalide", "La taille de base doit être un entier positif.")
            return

        set_parametre("pdf_police_titre", self._police_titre_var.get().strip())
        set_parametre("pdf_police_corps", self._police_corps_var.get().strip())
        set_parametre("pdf_taille_base", str(taille))
        set_parametre("pdf_couleur_accent", self._couleur_var.get().strip())
        afficher_info(self, "Succès", "Les paramètres PDF ont été enregistrés.")
