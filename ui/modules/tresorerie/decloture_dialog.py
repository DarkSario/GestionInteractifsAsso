"""Dialogue de déclôture d'exercice (Phase 6b)."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from db.models.cloture import decloturer_exercice
from db.models.securite import (
    reset_mot_de_passe_via_master,
    verifier_mot_de_passe_decloture,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


class DeclotureDialog(ctk.CTkToplevel):
    """Dialogue de déclôture d'un exercice, protégé par mot de passe."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        self._exercice = exercice
        nom = exercice.get("nom", "")
        self.title(f"🔓 Déclôturer l'exercice {nom}")
        self.geometry("460x340")
        self.resizable(False, False)
        self.transient(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS
        ex = self._exercice

        ctk.CTkLabel(
            self,
            text=f"🔓 Déclôturer l'exercice {ex.get('nom', '')}",
            font=fonts.get("subtitle"),
        ).pack(padx=20, pady=(16, 6))

        # Avertissement
        avert_frame = ctk.CTkFrame(self, fg_color="#fff3e0")
        avert_frame.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(
            avert_frame,
            text=(
                "⚠️ Action protégée\n\n"
                "La déclôture permettra de modifier les opérations\n"
                "de cet exercice. Cette action est enregistrée\n"
                "dans le journal."
            ),
            font=fonts.get("normal"),
            text_color="#e65100",
            justify="left",
        ).pack(padx=10, pady=10)

        # Saisie mot de passe
        ctk.CTkLabel(self, text="Mot de passe *", font=fonts.get("normal")).pack(
            anchor="w", padx=20
        )
        self._mdp_entry = ctk.CTkEntry(self, show="•", placeholder_text="Mot de passe de déclôture")
        self._mdp_entry.pack(fill="x", padx=20, pady=(4, 4))
        self._mdp_entry.bind("<Return>", lambda _: self._decloturer())

        # Lien code master
        ctk.CTkButton(
            self,
            text="🔑 Utiliser le code master",
            width=220,
            fg_color="transparent",
            hover_color="#e0e0e0",
            text_color=colors.get("primary", "#1f6aa5"),
            command=self._ouvrir_code_master,
        ).pack(pady=(2, 12))

        # Boutons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
            command=self.destroy
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="🔓 Déclôturer",
            width=140,
            fg_color="#e65100",
            hover_color="#bf360c",
            command=self._decloturer,
        ).pack(side="left", padx=8)

    def _decloturer(self) -> None:
        """Vérifie le mot de passe et effectue la déclôture."""
        mdp = self._mdp_entry.get()
        if not verifier_mot_de_passe_decloture(mdp):
            afficher_erreur(self, "Mot de passe incorrect", "Le mot de passe saisi est incorrect.")
            self._mdp_entry.delete(0, "end")
            return

        ok = decloturer_exercice(int(self._exercice["id"]))
        if ok:
            afficher_info(self, "Déclôture effectuée", "L'exercice a été déclôturé avec succès.")
            self.destroy()
        else:
            afficher_erreur(self, "Erreur", "La déclôture a échoué. Veuillez réessayer.")

    def _ouvrir_code_master(self) -> None:
        """Ouvre le dialogue de récupération par code master."""
        dialog = _CodeMasterDialog(self, self._exercice)
        dialog.grab_set()
        self.wait_window(dialog)
        if dialog.decloture_effectuee:
            self.destroy()


class _CodeMasterDialog(ctk.CTkToplevel):
    """Dialogue de récupération par code master."""

    def __init__(self, parent: Any, exercice: dict) -> None:
        super().__init__(parent)
        self.title("🔑 Récupération par code master")
        self.geometry("420x260")
        self.resizable(False, False)
        self.transient(parent)
        self._exercice = exercice
        self.decloture_effectuee = False
        self._build_ui()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        ctk.CTkLabel(
            self, text="🔑 Récupération par code master", font=fonts.get("subtitle")
        ).pack(padx=20, pady=(16, 8))

        ctk.CTkLabel(
            self,
            text=(
                "→ Si le code est correct : déclôture ET génère\n"
                "  un nouveau mot de passe aléatoire sécurisé"
            ),
            font=fonts.get("normal"),
            justify="left",
        ).pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(self, text="Code master *", font=fonts.get("normal")).pack(
            anchor="w", padx=20
        )
        self._code_entry = ctk.CTkEntry(self, show="•", placeholder_text="Code master")
        self._code_entry.pack(fill="x", padx=20, pady=(4, 16))
        self._code_entry.bind("<Return>", lambda _: self._valider())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))
        ctk.CTkButton(
            btn_frame, text="Annuler", width=110, fg_color="gray", hover_color="#555",
            command=self.destroy
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_frame,
            text="✅ Valider",
            width=110,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._valider,
        ).pack(side="left", padx=8)

    def _valider(self) -> None:
        code = self._code_entry.get()
        ok, val = reset_mot_de_passe_via_master(code)
        if not ok:
            afficher_erreur(self, "Code incorrect", val or "Code master invalide.")
            self._code_entry.delete(0, "end")
            return

        # Code correct : effectuer la déclôture
        decloturer_exercice(int(self._exercice["id"]))
        self.decloture_effectuee = True
        afficher_info(
            self,
            "Opération réussie",
            f"L'exercice a été déclôturé.\n"
            f"Nouveau mot de passe de déclôture : {val}\n"
            "Conservez-le précieusement.",
        )
        self.destroy()
