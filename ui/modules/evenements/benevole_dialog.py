"""Dialogue de création et modification d'un bénévole événementiel."""

from __future__ import annotations

from typing import Any
import tkinter as tk

import customtkinter as ctk

from ui.components.dialogs import afficher_erreur
from ui.modules.evenements.constantes import STATUTS_BENEVOLE, STATUTS_BEN_INV


class _DialogBenevole(ctk.CTkToplevel):
    """Dialogue de création/édition d'un bénévole."""

    def __init__(
        self,
        parent: Any,
        membres: list[dict],
        benevole: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.title("Bénévole")
        self.geometry("460x460")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None
        self._membres = membres
        self._benevole = benevole

        # Type (membre / externe)
        is_membre = bool(benevole and benevole.get("membre_id")) if benevole else True
        self._var_type = tk.StringVar(value="Membre" if is_membre else "Externe")
        self._var_membre = tk.StringVar()
        self._var_nom_ext = tk.StringVar(
            value=benevole.get("nom_externe") or "" if benevole else ""
        )
        self._var_prenom_ext = tk.StringVar(
            value=benevole.get("prenom_externe") or "" if benevole else ""
        )
        self._var_role = tk.StringVar(
            value=benevole.get("role") or "" if benevole else ""
        )
        self._var_h_debut = tk.StringVar(
            value=benevole.get("heure_debut") or "" if benevole else ""
        )
        self._var_h_fin = tk.StringVar(
            value=benevole.get("heure_fin") or "" if benevole else ""
        )
        self._var_statut = tk.StringVar(
            value=(
                STATUTS_BENEVOLE.get(benevole.get("statut", "confirme"), "Confirmé")
                if benevole
                else "Confirmé"
            )
        )
        self._var_commentaire = tk.StringVar(
            value=benevole.get("commentaire") or "" if benevole else ""
        )

        # Pré-sélection membre
        if benevole and benevole.get("membre_id"):
            mem = next((m for m in membres if m["id"] == benevole["membre_id"]), None)
            if mem:
                self._var_membre.set(f"{mem['prenom']} {mem['nom']}")

        self._build()

    def _build(self) -> None:
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=16, pady=10)

        # Type
        f_type = ctk.CTkFrame(scroll, fg_color="transparent")
        f_type.pack(fill="x", pady=4)
        ctk.CTkLabel(f_type, text="Type", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkRadioButton(
            f_type,
            text="Membre",
            variable=self._var_type,
            value="Membre",
            command=self._on_type_change,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkRadioButton(
            f_type,
            text="Externe",
            variable=self._var_type,
            value="Externe",
            command=self._on_type_change,
        ).pack(side="left")

        # Bloc membre
        self._frame_membre = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_membre.pack(fill="x", pady=3)
        ctk.CTkLabel(self._frame_membre, text="Membre", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        noms_membres = [f"{m['prenom']} {m['nom']}" for m in self._membres]
        self._combo_membre = ctk.CTkOptionMenu(
            self._frame_membre, values=noms_membres or ["—"], width=240
        )
        if self._var_membre.get() and self._var_membre.get() in noms_membres:
            self._combo_membre.set(self._var_membre.get())
        elif noms_membres:
            self._combo_membre.set(noms_membres[0])
        self._combo_membre.pack(side="left")

        # Bloc externe
        self._frame_externe = ctk.CTkFrame(scroll, fg_color="transparent")

        f_prenom = ctk.CTkFrame(self._frame_externe, fg_color="transparent")
        f_prenom.pack(fill="x", pady=2)
        ctk.CTkLabel(f_prenom, text="Prénom", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(f_prenom, textvariable=self._var_prenom_ext, width=240).pack(
            side="left"
        )

        f_nom = ctk.CTkFrame(self._frame_externe, fg_color="transparent")
        f_nom.pack(fill="x", pady=2)
        ctk.CTkLabel(f_nom, text="Nom", width=130, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkEntry(f_nom, textvariable=self._var_nom_ext, width=240).pack(side="left")

        def field(label, widget_fn):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=130, anchor="e").pack(
                side="left", padx=(0, 8)
            )
            w = widget_fn(f)
            w.pack(side="left")
            return w

        field("Rôle", lambda p: ctk.CTkEntry(p, textvariable=self._var_role, width=240))
        field(
            "Heure début",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_h_debut, width=100, placeholder_text="HH:MM"
            ),
        )
        field(
            "Heure fin",
            lambda p: ctk.CTkEntry(
                p, textvariable=self._var_h_fin, width=100, placeholder_text="HH:MM"
            ),
        )
        field(
            "Statut",
            lambda p: ctk.CTkOptionMenu(
                p,
                values=list(STATUTS_BENEVOLE.values()),
                variable=self._var_statut,
                width=180,
            ),
        )
        field(
            "Commentaire",
            lambda p: ctk.CTkEntry(p, textvariable=self._var_commentaire, width=240),
        )

        self._on_type_change()

        frame_btn = ctk.CTkFrame(scroll, fg_color="transparent")
        frame_btn.pack(pady=(12, 4))
        ctk.CTkButton(frame_btn, text="Enregistrer", width=110, command=self._valider).pack(
            side="left", padx=8
        )
        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=8)

    def _on_type_change(self) -> None:
        if self._var_type.get() == "Membre":
            self._frame_membre.pack(
                fill="x", pady=3, after=self._frame_membre.master.winfo_children()[1]
            )
            self._frame_externe.pack_forget()
        else:
            self._frame_membre.pack_forget()
            self._frame_externe.pack(
                fill="x", pady=3, after=self._frame_externe.master.winfo_children()[1]
            )

    def _valider(self) -> None:
        statut_label = self._var_statut.get()
        statut = STATUTS_BEN_INV.get(statut_label, "confirme")

        if self._var_type.get() == "Membre":
            sel = self._combo_membre.get()
            mem = next(
                (m for m in self._membres if f"{m['prenom']} {m['nom']}" == sel), None
            )
            if not mem:
                afficher_erreur(self, "Erreur", "Veuillez sélectionner un membre.")
                return
            self.result = {
                "membre_id": mem["id"],
                "nom_externe": None,
                "prenom_externe": None,
                "role": self._var_role.get().strip() or None,
                "heure_debut": self._var_h_debut.get().strip() or None,
                "heure_fin": self._var_h_fin.get().strip() or None,
                "statut": statut,
                "commentaire": self._var_commentaire.get().strip() or None,
            }
        else:
            self.result = {
                "membre_id": None,
                "nom_externe": self._var_nom_ext.get().strip() or None,
                "prenom_externe": self._var_prenom_ext.get().strip() or None,
                "role": self._var_role.get().strip() or None,
                "heure_debut": self._var_h_debut.get().strip() or None,
                "heure_fin": self._var_h_fin.get().strip() or None,
                "statut": statut,
                "commentaire": self._var_commentaire.get().strip() or None,
            }
        self.destroy()
