"""Onglet de gestion des caisses d'un événement."""

from __future__ import annotations

import sqlite3
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
        self._db_error_shown = False

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

    @staticmethod
    def _db_error_message(action: str, exc: Exception) -> str:
        base = (
            "Le module Caisses n'est pas disponible car la base n'est pas initialisée "
            "correctement. Vérifiez l'ouverture de la base et relancez les migrations."
        )
        if isinstance(exc, RuntimeError):
            return f"{base}\n\nDétail : {exc}"
        if isinstance(exc, sqlite3.OperationalError) and "no such table" in str(exc).lower():
            return (
                f"{base}\n\nTable manquante détectée ({exc}). "
                "Les migrations 0021/0022 doivent être appliquées."
            )
        return f"Impossible de {action}.\n\nDétail : {exc}"

    def _gerer_erreur_db(self, action: str, exc: Exception, unique: bool = False) -> None:
        logger.exception("CaissesEvenementView: échec '%s': %s", action, exc)
        if unique and self._db_error_shown:
            return
        if unique:
            self._db_error_shown = True
        afficher_erreur(self, "Caisses", self._db_error_message(action, exc))

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

        try:
            logger.info(
                "CaissesEvenementView: refresh des caisses (evenement_id=%s)",
                self._evenement_id,
            )
            caisses = lister_caisses_evenement(self._evenement_id)
        except Exception as exc:  # noqa: BLE001
            self._menu_caisses.configure(values=["—"])
            self._var_caisse.set("—")
            self._caisse_options = {}
            self._caisse_id = None
            self._gerer_erreur_db("charger les caisses", exc, unique=True)
            return
        self._db_error_shown = False
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
        logger.info("CaissesEvenementView: chargement caisse_id=%s", caisse_id)
        try:
            caisse = get_caisse(caisse_id)
        except Exception as exc:  # noqa: BLE001
            self._gerer_erreur_db("charger la caisse sélectionnée", exc)
            return
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
        try:
            caisse = get_caisse(self._caisse_id)
        except Exception as exc:  # noqa: BLE001
            self._gerer_erreur_db("charger la caisse à renommer", exc)
            return
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
        try:
            deleted = supprimer_caisse(self._caisse_id)
        except Exception as exc:  # noqa: BLE001
            self._gerer_erreur_db("supprimer la caisse", exc)
            return
        if deleted:
            self._caisse_id = None
            self.refresh()
            self._notifier_refresh_parent()

    def _tree_for_type(self, type_ouverture: str) -> ttk.Treeview:
        return self._tree_debut if type_ouverture == "debut" else self._tree_fin

    def _ajouter_ligne(self, type_ouverture: str) -> None:
        if not self._check_caisse():
            return
        logger.debug(
            "Ouverture dialog ligne caisse (action=ajout, caisse_id=%s, type=%s)",
            self._caisse_id,
            type_ouverture,
        )
        dialog = _DialogLigneCaisse(self, title="Ajouter ligne", ligne=None)
        self.wait_window(dialog)
        if not dialog.result:
            logger.debug(
                "Dialog ligne caisse fermé sans résultat (action=ajout, caisse_id=%s, type=%s)",
                self._caisse_id,
                type_ouverture,
            )
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
        logger.debug(
            "Ouverture dialog ligne caisse (action=edition, ligne_id=%s, type=%s)",
            ligne_id,
            type_ouverture,
        )
        dialog = _DialogLigneCaisse(self, title="Modifier ligne", ligne=ligne)
        self.wait_window(dialog)
        if not dialog.result:
            logger.debug(
                "Dialog ligne caisse fermé sans résultat (action=edition, ligne_id=%s, type=%s)",
                ligne_id,
                type_ouverture,
            )
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
        try:
            deleted = supprimer_ligne_caisse(int(sel[0]))
        except Exception as exc:  # noqa: BLE001
            self._gerer_erreur_db("supprimer la ligne", exc)
            return
        if deleted:
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
        owner = self._resolve_owner(parent)
        super().__init__(owner)
        self.title(title)
        self.geometry("480x420")
        self.resizable(False, False)
        self.result: dict | None = None
        self._owner = owner

        self._preset_warning = ""
        self._designations = self._charger_designations()
        self._preset_options = [
            "Saisie libre",
            *[self._format_designation_label(d) for d in self._designations],
        ]
        self._designation_by_index: list[dict | None] = [None, *self._designations]
        self._designation_index = self._find_initial_designation_index(ligne)
        self._designation_var = tk.StringVar(
            value=(ligne or {}).get("designation") or ""
        )
        self._designation_preset_var = tk.StringVar(
            value=self._preset_options[self._designation_index]
        )
        self._montant_var = tk.StringVar(
            value=str((ligne or {}).get("montant_unitaire") or "0")
        )
        self._quantite_var = tk.StringVar(
            value=str((ligne or {}).get("quantite") or "1")
        )

        self._build()
        self._sync_designation_state()
        deiconify = getattr(self, "deiconify", None)
        if callable(deiconify):
            deiconify()
        self.transient(owner)
        self.update_idletasks()
        self.lift()
        self.grab_set()
        self.focus_set()
        logger.debug(
            "DialogLigneCaisse affiché (titre=%s, parent=%s, owner=%s)",
            title,
            type(parent).__name__,
            type(owner).__name__,
        )

    @staticmethod
    def _resolve_owner(parent: Any) -> Any:
        if parent is None:
            return parent
        resolver = getattr(parent, "winfo_toplevel", None)
        if callable(resolver):
            try:
                owner = resolver()
                if owner is not None:
                    return owner
            except Exception as exc:  # noqa: BLE001
                logger.debug("DialogLigneCaisse: winfo_toplevel indisponible: %s", exc)
        return parent

    @staticmethod
    def _format_designation_label(designation: dict) -> str:
        return f"{designation.get('nom') or ''} — {float(designation.get('montant_unitaire') or 0):.2f} €"

    def _find_initial_designation_index(self, ligne: dict | None) -> int:
        designation_id = (ligne or {}).get("designation_id")
        designation_nom = str((ligne or {}).get("designation") or "").strip()
        try:
            designation_montant = round(
                float((ligne or {}).get("montant_unitaire") or 0), 2
            )
        except (TypeError, ValueError):
            designation_montant = 0.0
        if designation_id:
            for idx, designation in enumerate(self._designation_by_index[1:], start=1):
                if int(designation.get("id") or 0) == int(designation_id):
                    return idx
        if designation_nom:
            for idx, designation in enumerate(self._designation_by_index[1:], start=1):
                if (
                    str(designation.get("nom") or "").strip() == designation_nom
                    and round(float(designation.get("montant_unitaire") or 0), 2)
                    == designation_montant
                ):
                    return idx
        return 0

    def _charger_designations(self) -> list[dict]:
        try:
            designations = lister_designations_caisse(actif_only=True)
            if designations:
                return designations
            self._preset_warning = (
                "Aucun préset actif disponible. Utilisez la saisie libre."
            )
            return []
        except sqlite3.Error as exc:
            logger.warning("Impossible de charger les présets de caisse : %s", exc)
            self._preset_warning = (
                "Impossible de charger les présets. Utilisez la saisie libre."
            )
            return []

    def _build(self) -> None:
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=(18, 0))

        ctk.CTkLabel(form, text="Préset").pack(anchor="w", pady=(0, 2))
        self._preset_menu = ttk.Combobox(
            form,
            values=self._preset_options,
            variable=self._designation_preset_var,
            state="readonly",
            width=42,
        )
        self._preset_menu.pack(fill="x")
        self._preset_menu.current(self._designation_index)
        self._preset_menu.bind("<<ComboboxSelected>>", self._on_designation_change)

        if self._preset_warning:
            ctk.CTkLabel(
                form,
                text=self._preset_warning,
                text_color="#d97706",
                wraplength=420,
                justify="left",
            ).pack(anchor="w", pady=(8, 0))

        ctk.CTkLabel(form, text="Désignation *").pack(anchor="w", pady=(16, 2))
        self._designation_entry = ctk.CTkEntry(
            form, textvariable=self._designation_var, width=360
        )
        self._designation_entry.pack(fill="x")

        ctk.CTkLabel(form, text="Montant unitaire (€) *").pack(
            anchor="w", pady=(10, 2)
        )
        self._montant_entry = ctk.CTkEntry(
            form, textvariable=self._montant_var, width=360
        )
        self._montant_entry.pack(fill="x")

        ctk.CTkLabel(form, text="Quantité *").pack(anchor="w", pady=(10, 2))
        self._quantite_entry = ctk.CTkEntry(
            form, textvariable=self._quantite_var, width=360
        )
        self._quantite_entry.pack(fill="x")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(16, 20))
        ctk.CTkButton(
            actions,
            text="Annuler",
            width=120,
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy,
        ).pack(side="right")
        ctk.CTkButton(
            actions, text="Enregistrer", width=140, command=self._valider
        ).pack(
            side="right", padx=(0, 10)
        )

    def _designation_selectionnee(self) -> dict | None:
        return self._designation_by_index[self._designation_index]

    def _sync_designation_state(self) -> None:
        designation = self._designation_selectionnee()
        self._designation_entry.configure(state="disabled" if designation else "normal")

    def _on_designation_change(self, _event: object = None) -> None:
        self._designation_index = max(self._preset_menu.current(), 0)
        designation = self._designation_selectionnee()
        self._sync_designation_state()
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
        designation_preset = self._designation_selectionnee()
        designation_id = int(designation_preset["id"]) if designation_preset else None
        self.result = {
            "designation": designation,
            "montant_unitaire": montant,
            "quantite": quantite,
            "designation_id": designation_id,
        }
        self.destroy()
