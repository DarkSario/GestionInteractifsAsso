"""Onglet de gestion des caisses d'un événement."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk
from typing import Any

import customtkinter as ctk

from db.models.caisse_designations import lister_designations_caisse
from db.models.evenement_caisses import (
    ajouter_ligne_caisse,
    creer_caisse,
    get_caisse,
    lister_caisses_evenement,
    mettre_a_jour_caisse,
    modifier_ligne_caisse,
    supprimer_caisse,
    supprimer_ligne_caisse,
)
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class CaissesEvenementView(ctk.CTkFrame):
    """Vue de gestion des caisses début/fin d'un événement."""

    def __init__(
        self, parent: Any, evenement_id: int | None, callback_refresh=None
    ) -> None:
        super().__init__(parent)
        self._evenement_id = evenement_id
        self._callback_refresh = callback_refresh
        self._caisse_id: int | None = None
        self._caisse_options: dict[str, int] = {}
        self._lignes_by_id: dict[int, dict] = {}

        self._build_ui()
        self.refresh()

    def set_evenement_id(self, evenement_id: int | None) -> None:
        self._evenement_id = evenement_id
        self._caisse_id = None
        self.refresh()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(top, text="Caisse :", anchor="w").pack(side="left")
        self._var_caisse = tk.StringVar(value="—")
        self._menu_caisses = ctk.CTkOptionMenu(
            top,
            values=["—"],
            variable=self._var_caisse,
            command=self._on_select_caisse,
            width=280,
        )
        self._menu_caisses.pack(side="left", padx=(8, 8))

        ctk.CTkButton(
            top, text="+ Nouvelle caisse", command=self._nouvelle_caisse
        ).pack(side="left")
        ctk.CTkButton(top, text="✏️ Renommer", command=self._renommer_caisse).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkButton(
            top,
            text="🗑️ Supprimer caisse",
            command=self._supprimer_caisse_active,
            fg_color="#b71c1c",
            hover_color="#7f0000",
        ).pack(side="left", padx=(8, 0))

        self._tree_debut, self._lbl_total_debut = self._build_section(
            "DÉBUT DE CAISSE", "debut"
        )
        self._tree_fin, self._lbl_total_fin = self._build_section(
            "FIN DE CAISSE", "fin"
        )

        recap = ctk.CTkFrame(self)
        recap.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkLabel(recap, text="RÉCAPITULATIF", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        self._lbl_recap_debut = ctk.CTkLabel(recap, text="Total début : 0,00 €")
        self._lbl_recap_debut.pack(anchor="w", padx=10)
        self._lbl_recap_fin = ctk.CTkLabel(recap, text="Total fin : 0,00 €")
        self._lbl_recap_fin.pack(anchor="w", padx=10)
        self._lbl_recap_recette = ctk.CTkLabel(
            recap, text="RECETTE CAISSE : 0,00 €", font=ctk.CTkFont(weight="bold")
        )
        self._lbl_recap_recette.pack(anchor="w", padx=10, pady=(2, 8))

    def _build_section(
        self, titre: str, type_ouverture: str
    ) -> tuple[ttk.Treeview, ctk.CTkLabel]:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=(2, 4))
        ctk.CTkLabel(frame, text=titre, font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        table_frame = ctk.CTkFrame(frame, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=10)

        tree = ttk.Treeview(
            table_frame,
            columns=("designation", "montant_unitaire", "quantite", "total"),
            show="headings",
            height=6,
        )
        for col, txt, w in (
            ("designation", "Désignation", 260),
            ("montant_unitaire", "Montant unitaire", 140),
            ("quantite", "Quantité", 110),
            ("total", "Total", 120),
        ):
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="center" if col != "designation" else "w")
        tree.pack(side="left", fill="both", expand=True)
        tree.bind("<Double-1>", lambda _e, t=type_ouverture: self._modifier_ligne(t))

        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(4, 4))
        ctk.CTkButton(
            actions,
            text="+ Ajouter ligne",
            command=lambda t=type_ouverture: self._ajouter_ligne(t),
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="✏️ Modifier",
            command=lambda t=type_ouverture: self._modifier_ligne(t),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            actions,
            text="🗑️ Supprimer",
            command=lambda t=type_ouverture: self._supprimer_ligne(t),
            fg_color="#b71c1c",
            hover_color="#7f0000",
        ).pack(side="left", padx=(8, 0))

        lbl_total = ctk.CTkLabel(
            frame, text="TOTAL : 0,00 €", font=ctk.CTkFont(weight="bold")
        )
        lbl_total.pack(anchor="e", padx=12, pady=(0, 8))
        return tree, lbl_total

    def _fmt(self, value: float) -> str:
        return f"{float(value or 0):,.2f} €".replace(",", " ").replace(".", ",")

    def _check_evenement(self) -> bool:
        if self._evenement_id:
            return True
        afficher_info(self, "Caisses", "Veuillez d'abord sauvegarder l'événement.")
        return False

    def _check_caisse(self) -> bool:
        if self._caisse_id:
            return True
        afficher_info(self, "Caisses", "Veuillez d'abord sélectionner une caisse.")
        return False

    def refresh(self) -> None:
        self._tree_debut.delete(*self._tree_debut.get_children())
        self._tree_fin.delete(*self._tree_fin.get_children())
        self._lbl_total_debut.configure(text="TOTAL DÉBUT : 0,00 €")
        self._lbl_total_fin.configure(text="TOTAL FIN : 0,00 €")
        self._lbl_recap_debut.configure(text="Total début : 0,00 €")
        self._lbl_recap_fin.configure(text="Total fin : 0,00 €")
        self._lbl_recap_recette.configure(
            text="RECETTE CAISSE : 0,00 €", text_color=("black", "white")
        )

        if not self._evenement_id:
            self._menu_caisses.configure(values=["—"])
            self._var_caisse.set("—")
            self._caisse_options = {}
            return

        caisses = lister_caisses_evenement(self._evenement_id)
        labels = [f"{c['id']} — {c['nom']}" for c in caisses]
        self._caisse_options = {
            f"{c['id']} — {c['nom']}": int(c["id"]) for c in caisses
        }
        self._menu_caisses.configure(values=labels or ["—"])
        if not labels:
            self._var_caisse.set("—")
            self._caisse_id = None
            return

        if self._caisse_id and any(int(c["id"]) == self._caisse_id for c in caisses):
            selected = next(
                lbl
                for lbl, cid in self._caisse_options.items()
                if cid == self._caisse_id
            )
        else:
            selected = labels[0]
            self._caisse_id = self._caisse_options[selected]
        self._var_caisse.set(selected)
        self._charger_caisse(self._caisse_id)

    def _on_select_caisse(self, selected: str) -> None:
        self._caisse_id = self._caisse_options.get(selected)
        if self._caisse_id:
            self._charger_caisse(self._caisse_id)

    def _charger_caisse(self, caisse_id: int) -> None:
        caisse = get_caisse(caisse_id)
        if not caisse:
            return
        self._tree_debut.delete(*self._tree_debut.get_children())
        self._tree_fin.delete(*self._tree_fin.get_children())
        self._lignes_by_id = {}

        for ligne in caisse.get("lignes_debut", []):
            self._lignes_by_id[int(ligne["id"])] = ligne
            self._tree_debut.insert(
                "",
                "end",
                iid=str(ligne["id"]),
                values=(
                    ligne.get("designation") or "",
                    self._fmt(ligne.get("montant_unitaire") or 0),
                    int(ligne.get("quantite") or 0),
                    self._fmt(ligne.get("total") or 0),
                ),
            )
        for ligne in caisse.get("lignes_fin", []):
            self._lignes_by_id[int(ligne["id"])] = ligne
            self._tree_fin.insert(
                "",
                "end",
                iid=str(ligne["id"]),
                values=(
                    ligne.get("designation") or "",
                    self._fmt(ligne.get("montant_unitaire") or 0),
                    int(ligne.get("quantite") or 0),
                    self._fmt(ligne.get("total") or 0),
                ),
            )

        total_debut = float(caisse.get("total_debut") or 0)
        total_fin = float(caisse.get("total_fin") or 0)
        recette = float(caisse.get("recette") or 0)
        self._lbl_total_debut.configure(text=f"TOTAL DÉBUT : {self._fmt(total_debut)}")
        self._lbl_total_fin.configure(text=f"TOTAL FIN : {self._fmt(total_fin)}")
        self._lbl_recap_debut.configure(text=f"Total début : {self._fmt(total_debut)}")
        self._lbl_recap_fin.configure(text=f"Total fin : {self._fmt(total_fin)}")
        self._lbl_recap_recette.configure(
            text=f"RECETTE CAISSE : {self._fmt(recette)}",
            text_color="#28a745" if recette >= 0 else "#dc3545",
        )

    def _nouvelle_caisse(self) -> None:
        if not self._check_evenement():
            return
        nom = simpledialog.askstring(
            "Nouvelle caisse", "Nom de la caisse :", parent=self
        )
        if not nom:
            return
        nom = nom.strip()
        if not nom:
            return
        try:
            self._caisse_id = creer_caisse(self._evenement_id, nom)
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(self, "Caisses", f"Impossible de créer la caisse : {exc}")
            return
        self.refresh()
        self._notifier_refresh_parent()

    def _renommer_caisse(self) -> None:
        if not self._check_caisse():
            return
        caisse = get_caisse(self._caisse_id)
        current = (caisse or {}).get("nom") or ""
        nouveau_nom = simpledialog.askstring(
            "Renommer la caisse", "Nouveau nom :", initialvalue=current, parent=self
        )
        if not nouveau_nom:
            return
        nouveau_nom = nouveau_nom.strip()
        if not nouveau_nom:
            return
        try:
            mettre_a_jour_caisse(self._caisse_id, nom=nouveau_nom)
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(
                self, "Caisses", f"Impossible de renommer la caisse : {exc}"
            )
            return
        self.refresh()
        self._notifier_refresh_parent()

    def _supprimer_caisse_active(self) -> None:
        if not self._check_caisse():
            return
        if not demander_confirmation(
            self, "Supprimer", "Supprimer cette caisse et toutes ses lignes ?"
        ):
            return
        if supprimer_caisse(self._caisse_id):
            self._caisse_id = None
            self.refresh()
            self._notifier_refresh_parent()

    def _tree_for_type(self, type_ouverture: str) -> ttk.Treeview:
        return self._tree_debut if type_ouverture == "debut" else self._tree_fin

    def _ajouter_ligne(self, type_ouverture: str) -> None:
        if not self._check_caisse():
            return
        dialog = _DialogLigneCaisse(self, title="Ajouter ligne", ligne=None)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            ajouter_ligne_caisse(
                self._caisse_id,
                type_ouverture,
                dialog.result["designation"],
                dialog.result["montant_unitaire"],
                dialog.result["quantite"],
                designation_id=dialog.result.get("designation_id"),
            )
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(self, "Caisses", f"Impossible d'ajouter la ligne : {exc}")
            return
        self._charger_caisse(self._caisse_id)
        self._notifier_refresh_parent()

    def _modifier_ligne(self, type_ouverture: str) -> None:
        if not self._check_caisse():
            return
        tree = self._tree_for_type(type_ouverture)
        sel = tree.selection()
        if not sel:
            return
        ligne_id = int(sel[0])
        ligne = dict(self._lignes_by_id.get(ligne_id) or {})
        dialog = _DialogLigneCaisse(self, title="Modifier ligne", ligne=ligne)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            modifier_ligne_caisse(
                ligne_id,
                dialog.result["designation"],
                dialog.result["montant_unitaire"],
                dialog.result["quantite"],
                designation_id=dialog.result.get("designation_id"),
            )
        except Exception as exc:  # noqa: BLE001
            afficher_erreur(self, "Caisses", f"Impossible de modifier la ligne : {exc}")
            return
        self._charger_caisse(self._caisse_id)
        self._notifier_refresh_parent()

    def _supprimer_ligne(self, type_ouverture: str) -> None:
        if not self._check_caisse():
            return
        tree = self._tree_for_type(type_ouverture)
        sel = tree.selection()
        if not sel:
            return
        if not demander_confirmation(self, "Supprimer", "Supprimer cette ligne ?"):
            return
        if supprimer_ligne_caisse(int(sel[0])):
            self._charger_caisse(self._caisse_id)
            self._notifier_refresh_parent()

    def _notifier_refresh_parent(self) -> None:
        if callable(self._callback_refresh):
            try:
                self._callback_refresh()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "CaissesEvenementView: refresh parent callback failed: %s", exc
                )


class _DialogLigneCaisse(ctk.CTkToplevel):
    """Dialogue d'ajout/édition de ligne de caisse."""

    def __init__(self, parent: Any, title: str, ligne: dict | None) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("460x340")
        self.resizable(False, False)
        self.transient(parent)
        self.result: dict | None = None

        self._designations = lister_designations_caisse(actif_only=True)
        self._designations_by_label = {
            self._format_designation_label(designation): designation
            for designation in self._designations
        }
        initial_label = self._find_initial_designation_label(ligne)
        self._designation_var = tk.StringVar(
            value=(ligne or {}).get("designation") or ""
        )
        self._designation_preset_var = tk.StringVar(value=initial_label)
        self._montant_var = tk.StringVar(
            value=str((ligne or {}).get("montant_unitaire") or "0")
        )
        self._quantite_var = tk.StringVar(
            value=str((ligne or {}).get("quantite") or "1")
        )

        self._build()
        self.grab_set()
        self.focus()

    @staticmethod
    def _format_designation_label(designation: dict) -> str:
        return f"{designation.get('nom') or ''} — {float(designation.get('montant_unitaire') or 0):.2f} €"

    def _find_initial_designation_label(self, ligne: dict | None) -> str:
        designation_id = (ligne or {}).get("designation_id")
        designation_nom = str((ligne or {}).get("designation") or "").strip()
        if designation_id:
            for label, designation in self._designations_by_label.items():
                if int(designation.get("id") or 0) == int(designation_id):
                    return label
        if designation_nom:
            for label, designation in self._designations_by_label.items():
                if str(designation.get("nom") or "").strip() == designation_nom:
                    return label
        return "Saisie libre"

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Préset").pack(anchor="w", padx=20, pady=(16, 2))
        self._preset_menu = ctk.CTkOptionMenu(
            self,
            values=["Saisie libre", *self._designations_by_label.keys()],
            variable=self._designation_preset_var,
            command=self._on_designation_change,
            width=360,
        )
        self._preset_menu.pack(padx=20)

        ctk.CTkLabel(self, text="Désignation *").pack(anchor="w", padx=20, pady=(16, 2))
        ctk.CTkEntry(self, textvariable=self._designation_var, width=360).pack(padx=20)

        ctk.CTkLabel(self, text="Montant unitaire (€) *").pack(
            anchor="w", padx=20, pady=(10, 2)
        )
        ctk.CTkEntry(self, textvariable=self._montant_var, width=360).pack(padx=20)

        ctk.CTkLabel(self, text="Quantité *").pack(anchor="w", padx=20, pady=(10, 2))
        ctk.CTkEntry(self, textvariable=self._quantite_var, width=360).pack(padx=20)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=16)
        ctk.CTkButton(actions, text="Annuler", command=self.destroy).pack(side="right")
        ctk.CTkButton(actions, text="Valider", command=self._valider).pack(
            side="right", padx=(0, 8)
        )

    def _on_designation_change(self, selected: str) -> None:
        designation = self._designations_by_label.get(selected)
        if not designation:
            return
        self._designation_var.set(str(designation.get("nom") or ""))
        self._montant_var.set(f"{float(designation.get('montant_unitaire') or 0):.2f}")

    def _valider(self) -> None:
        designation = self._designation_var.get().strip()
        if not designation:
            afficher_erreur(self, "Ligne caisse", "La désignation est obligatoire.")
            return
        try:
            montant = float(self._montant_var.get().strip().replace(",", "."))
            quantite = int(self._quantite_var.get().strip())
        except ValueError:
            afficher_erreur(
                self,
                "Ligne caisse",
                "Montant unitaire et quantité doivent être numériques.",
            )
            return
        if montant < 0:
            afficher_erreur(
                self, "Ligne caisse", "Le montant unitaire doit être positif ou nul."
            )
            return
        if quantite < 0:
            afficher_erreur(
                self, "Ligne caisse", "La quantité doit être positive ou nulle."
            )
            return
        designation_preset = self._designations_by_label.get(
            self._designation_preset_var.get()
        )
        designation_id = (
            int(designation_preset["id"])
            if designation_preset
            and designation == str(designation_preset.get("nom") or "").strip()
            else None
        )
        self.result = {
            "designation": designation,
            "montant_unitaire": montant,
            "quantite": quantite,
            "designation_id": designation_id,
        }
        self.destroy()
