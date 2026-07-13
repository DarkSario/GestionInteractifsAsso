"""Fenêtre de paramètres globaux de l'application (Phase 7).

Cinq onglets :
- 🏢 Association  : Infos asso + exercice courant
- 💰 Financier    : Taux SumUp, comptes, modes de paiement
- 📅 Événements   : Classes scolaires + types d'événements
- 🖥️ Système      : Thème, sauvegarde auto, dossiers
- 📄 Exports & PDF: Paramètres PDF et polices
"""

from __future__ import annotations

import os
from datetime import datetime
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from core.bilan_ag import reset_template_bilan
from core.recus_fiscaux import (
    VARIABLES_TEMPLATE_ATTESTATION,
    VARIABLES_TEMPLATE_CERFA,
    VARIABLES_TEMPLATE_REMBOURSEMENT,
    get_template_attestation,
    get_template_cerfa,
    get_template_remboursement,
    reset_template_attestation,
    reset_template_cerfa,
    reset_template_remboursement,
    save_template_attestation,
    save_template_cerfa,
    save_template_remboursement,
)
from core.parametres import (
    get_config_financiere,
    get_config_systeme,
    get_infos_asso,
    set_config_financiere,
    set_config_systeme,
    set_infos_asso,
    valider_nom_liste,
)
from db.models.parametres_globaux import (
    get_parametre,
    set_parametre,
    add_classe,
    add_type_evenement,
    delete_classe,
    delete_type_evenement,
    get_all_classes,
    get_all_modes_paiement,
    get_all_types_evenements,
    toggle_classe,
    toggle_mode_paiement,
    toggle_type_evenement,
    update_classe,
    update_type_evenement,
)
from db.models.polices import get_all_polices
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from utils.backup import sauvegarder_maintenant
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from tkcolorpicker import askcolor as _askcolor
except ImportError:
    from tkinter.colorchooser import askcolor as _askcolor


class ParametresApp(ctk.CTkToplevel):
    """Fenêtre principale des paramètres de l'application."""

    def __init__(self, parent: Any) -> None:
        super().__init__(parent)
        self.title("⚙️ Paramètres de l'application")
        self.geometry("820x640")
        self.minsize(700, 580)
        self.transient(parent)
        self.grab_set()

        self._parent = parent
        self._build_ui()

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        ctk.CTkLabel(
            self,
            text="⚙️ Paramètres de l'application",
            font=fonts.get("title"),
        ).pack(anchor="w", padx=20, pady=(16, 8))

        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        self._tabview.add("🏢 Association")
        self._tabview.add("💰 Financier")
        self._tabview.add("📅 Événements")
        self._tabview.add("🖥️ Système")
        self._tabview.add("📄 Exports & PDF")

        self._build_tab_asso()
        self._build_tab_financier()
        self._build_tab_evenements()
        self._build_tab_systeme()
        self._build_tab_exports_pdf()

    # ── Onglet Association ────────────────────────────────────────────────────

    def _build_tab_asso(self) -> None:
        tab = self._tabview.tab("🏢 Association")
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Section : Informations de l'association
        ctk.CTkLabel(frame, text="Informations de l'association", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(8, 4)
        )

        self._asso_champs: dict[str, ctk.CTkEntry] = {}
        champs = [
            ("nom", "Nom *"),
            ("adresse", "Adresse"),
            ("telephone", "Téléphone"),
            ("email", "Email"),
        ]
        for cle, label in champs:
            f = ctk.CTkFrame(frame, fg_color="transparent")
            f.pack(fill="x", pady=3)
            ctk.CTkLabel(f, text=label, width=150, anchor="ne").pack(side="left", padx=(0, 8))
            entry = ctk.CTkEntry(f, width=420)
            entry.pack(side="left", fill="x", expand=True)
            self._asso_champs[cle] = entry

        # Logo de l'association
        ctk.CTkLabel(frame, text="Logo de l'association", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )

        self._logo_path_var = ctk.StringVar()
        self._logo_position_var = ctk.StringVar(value="gauche")
        self._logo_taille_var = ctk.StringVar(value="moyenne")

        f_logo_row = ctk.CTkFrame(frame, fg_color="transparent")
        f_logo_row.pack(fill="x", pady=3)
        ctk.CTkLabel(f_logo_row, text="Fichier logo", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f_logo_row, textvariable=self._logo_path_var, width=300).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(f_logo_row, text="📁 Choisir", width=90, command=self._choisir_logo).pack(
            side="left", padx=(4, 0)
        )
        ctk.CTkButton(f_logo_row, text="🗑️ Suppr.", width=80, fg_color="#8b1a1a",
                      hover_color="#6b1414", command=self._supprimer_logo).pack(
            side="left", padx=(4, 0)
        )

        ctk.CTkLabel(
            frame,
            text="Formats acceptés : PNG, JPG — max 2 Mo",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=(158, 0))

        f_pos = ctk.CTkFrame(frame, fg_color="transparent")
        f_pos.pack(fill="x", pady=3)
        ctk.CTkLabel(f_pos, text="Position dans les exports", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        for val, lib in [("gauche", "Haut gauche"), ("centre", "Haut centre"), ("droite", "Haut droite")]:
            ctk.CTkRadioButton(f_pos, text=lib, variable=self._logo_position_var, value=val).pack(
                side="left", padx=(0, 12)
            )

        f_taille = ctk.CTkFrame(frame, fg_color="transparent")
        f_taille.pack(fill="x", pady=3)
        ctk.CTkLabel(f_taille, text="Taille dans les exports", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        for val, lib in [("petite", "Petite"), ("moyenne", "Moyenne"), ("grande", "Grande")]:
            ctk.CTkRadioButton(f_taille, text=lib, variable=self._logo_taille_var, value=val).pack(
                side="left", padx=(0, 12)
            )

        # Séparateur — Exercice scolaire courant
        ctk.CTkLabel(
            frame, text="Exercice scolaire courant", font=fonts.get("subtitle")
        ).pack(anchor="w", pady=(16, 4))

        f_dates = ctk.CTkFrame(frame, fg_color="transparent")
        f_dates.pack(fill="x", pady=3)
        ctk.CTkLabel(f_dates, text="Début", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._exercice_debut = ctk.CTkEntry(f_dates, width=120, placeholder_text="01/09/2025")
        self._exercice_debut.pack(side="left")
        ctk.CTkLabel(f_dates, text="→  Fin", width=60).pack(side="left", padx=4)
        self._exercice_fin = ctk.CTkEntry(f_dates, width=120, placeholder_text="31/08/2026")
        self._exercice_fin.pack(side="left")

        # Boutons
        f_btn = ctk.CTkFrame(frame, fg_color="transparent")
        f_btn.pack(fill="x", pady=(12, 4))
        ctk.CTkButton(
            f_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            f_btn, text="💾 Enregistrer", width=150, command=self._enregistrer_asso
        ).pack(side="right")

        self._charger_asso()

    def _charger_asso(self) -> None:
        infos = get_infos_asso()
        for cle, entry in self._asso_champs.items():
            entry.delete(0, "end")
            entry.insert(0, infos.get(cle, ""))
        self._logo_path_var.set(infos.get("logo_path", ""))

        # Logo config
        try:
            from core.logo import get_logo_config
            logo_cfg = get_logo_config()
            self._logo_path_var.set(logo_cfg.get("path") or infos.get("logo_path", ""))
            self._logo_position_var.set(logo_cfg.get("position", "gauche"))
            self._logo_taille_var.set(logo_cfg.get("taille", "moyenne"))
        except Exception as exc:
            logger.warning("Impossible de charger la config logo : %s", exc)

        # Exercice courant depuis la table config/exercices
        try:
            from db.connection import get_connection

            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT date_debut, date_fin FROM exercices WHERE statut = 'ouvert' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
            if row:
                self._exercice_debut.delete(0, "end")
                self._exercice_debut.insert(0, self._fmt_date(row["date_debut"]))
                self._exercice_fin.delete(0, "end")
                self._exercice_fin.insert(0, self._fmt_date(row["date_fin"]))
        except Exception as exc:
            logger.warning("Impossible de charger l'exercice courant : %s", exc)

    def _choisir_logo(self) -> None:
        chemin = filedialog.askopenfilename(
            parent=self,
            title="Choisir le logo de l'association",
            filetypes=[("Images", "*.png *.jpg *.jpeg"), ("Tous les fichiers", "*.*")],
        )
        if chemin:
            try:
                if os.path.getsize(chemin) > 2 * 1024 * 1024:
                    afficher_erreur(self, "Fichier trop grand", "Le logo ne doit pas dépasser 2 Mo.")
                    return
            except OSError:
                pass
            try:
                from core.logo import set_logo
                if set_logo(chemin):
                    self._logo_path_var.set(chemin)
                else:
                    afficher_erreur(self, "Erreur", "Impossible de copier le logo.")
            except Exception:
                self._logo_path_var.set(chemin)

    def _supprimer_logo(self) -> None:
        if not demander_confirmation(self, "Supprimer le logo", "Voulez-vous vraiment supprimer le logo ?"):
            return
        try:
            from core.logo import supprimer_logo
            supprimer_logo()
            self._logo_path_var.set("")
            afficher_info(self, "Succès", "Logo supprimé.")
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de supprimer le logo : {exc}")

    def _enregistrer_asso(self) -> None:
        erreurs = set_infos_asso(
            nom=self._asso_champs["nom"].get(),
            adresse=self._asso_champs["adresse"].get(),
            telephone=self._asso_champs["telephone"].get(),
            email=self._asso_champs["email"].get(),
            logo_path=self._logo_path_var.get(),
        )
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return

        # Enregistrer config logo
        try:
            from core.logo import set_logo_config
            set_logo_config(
                position=self._logo_position_var.get(),
                taille=self._logo_taille_var.get(),
            )
        except Exception as exc:
            logger.warning("Impossible d'enregistrer la config logo : %s", exc)

        afficher_info(self, "Succès", "Les informations de l'association ont été enregistrées.")

    # ── Onglet Financier ──────────────────────────────────────────────────────

    def _build_tab_financier(self) -> None:
        tab = self._tabview.tab("💰 Financier")
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Taux SumUp
        ctk.CTkLabel(frame, text="Taux de commission SumUp", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(8, 4)
        )
        f_taux = ctk.CTkFrame(frame, fg_color="transparent")
        f_taux.pack(fill="x", pady=3)
        ctk.CTkLabel(f_taux, text="Taux (%) *", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._taux_sumup_entry = ctk.CTkEntry(f_taux, width=100)
        self._taux_sumup_entry.pack(side="left")

        # Comptes par défaut
        ctk.CTkLabel(frame, text="Comptes par défaut", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )

        self._comptes_options: list[str] = ["— Aucun —"]
        self._comptes_ids: list[str] = [""]
        try:
            from db.models.tresorerie import get_all_comptes

            comptes = get_all_comptes(actif_only=True)
            for c in comptes:
                self._comptes_options.append(c["nom"])
                self._comptes_ids.append(str(c["id"]))
        except Exception as exc:
            logger.warning("Impossible de charger la liste des comptes : %s", exc)
        f_cp = ctk.CTkFrame(frame, fg_color="transparent")
        f_cp.pack(fill="x", pady=3)
        ctk.CTkLabel(f_cp, text="Compte principal", width=150, anchor="ne").pack(
            side="left", padx=(0, 8)
        )
        self._compte_principal_var = ctk.StringVar(value=self._comptes_options[0])
        self._combo_compte_principal = ctk.CTkOptionMenu(
            f_cp, variable=self._compte_principal_var, values=self._comptes_options, width=240
        )
        self._combo_compte_principal.pack(side="left")

        f_cc = ctk.CTkFrame(frame, fg_color="transparent")
        f_cc.pack(fill="x", pady=3)
        ctk.CTkLabel(f_cc, text="Caisse espèces", width=150, anchor="ne").pack(
            side="left", padx=(0, 8)
        )
        self._compte_caisse_var = ctk.StringVar(value=self._comptes_options[0])
        self._combo_compte_caisse = ctk.CTkOptionMenu(
            f_cc, variable=self._compte_caisse_var, values=self._comptes_options, width=240
        )
        self._combo_compte_caisse.pack(side="left")

        # Modes de paiement
        ctk.CTkLabel(frame, text="Modes de paiement actifs", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )

        self._modes_vars: dict[int, ctk.BooleanVar] = {}
        self._modes_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._modes_frame.pack(fill="x", pady=4)

        # Cotisations
        ctk.CTkLabel(frame, text="Cotisations adhérents", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )
        f_cot = ctk.CTkFrame(frame, fg_color="transparent")
        f_cot.pack(fill="x", pady=3)
        ctk.CTkLabel(f_cot, text="Montant par défaut (€)", width=150, anchor="ne").pack(
            side="left", padx=(0, 8)
        )
        self._cotisation_montant_entry = ctk.CTkEntry(f_cot, width=100)
        self._cotisation_montant_entry.pack(side="left")
        ctk.CTkLabel(
            frame,
            text="0 = cotisation offerte automatiquement",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=(158, 0))

        # Boutons
        f_btn = ctk.CTkFrame(frame, fg_color="transparent")
        f_btn.pack(fill="x", pady=(12, 4))
        ctk.CTkButton(
            f_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            f_btn, text="💾 Enregistrer", width=150, command=self._enregistrer_financier
        ).pack(side="right")

        self._charger_financier()

    def _charger_financier(self) -> None:
        config = get_config_financiere()

        self._taux_sumup_entry.delete(0, "end")
        taux = config.get("taux_sumup", "1.75").replace(".", ",")
        self._taux_sumup_entry.insert(0, taux)

        # Sélection compte principal
        cp_id = config.get("compte_principal_id", "")
        if cp_id in self._comptes_ids:
            idx = self._comptes_ids.index(cp_id)
            self._compte_principal_var.set(self._comptes_options[idx])

        # Sélection caisse
        cc_id = config.get("compte_caisse_id", "")
        if cc_id in self._comptes_ids:
            idx = self._comptes_ids.index(cc_id)
            self._compte_caisse_var.set(self._comptes_options[idx])

        # Modes de paiement
        for w in self._modes_frame.winfo_children():
            w.destroy()
        self._modes_vars.clear()

        modes = get_all_modes_paiement()
        for i, mode in enumerate(modes):
            var = ctk.BooleanVar(value=bool(mode["actif"]))
            self._modes_vars[mode["id"]] = var
            ctk.CTkCheckBox(
                self._modes_frame,
                text=mode["libelle"],
                variable=var,
                command=lambda mid=mode["id"], v=var: self._toggle_mode(mid, v),
            ).grid(row=i // 3, column=i % 3, padx=10, pady=4, sticky="w")

        # Montant cotisation par défaut
        try:
            from core.cotisations import get_montant_cotisation_defaut

            montant_defaut = get_montant_cotisation_defaut()
            self._cotisation_montant_entry.delete(0, "end")
            self._cotisation_montant_entry.insert(0, f"{montant_defaut:.2f}")
        except Exception as exc:
            logger.warning("Impossible de charger le montant cotisation : %s", exc)

    def _toggle_mode(self, mode_id: int, var: ctk.BooleanVar) -> None:
        ok = toggle_mode_paiement(mode_id)
        if not ok:
            # Annuler le changement visuel si bloqué
            var.set(not var.get())
            afficher_erreur(
                self,
                "Modification impossible",
                "Impossible de désactiver ce mode de paiement : il doit rester au moins un mode actif.",
            )

    def _enregistrer_financier(self) -> None:
        taux_str = self._taux_sumup_entry.get().strip().replace(",", ".")
        try:
            taux = float(taux_str)
            if taux < 0 or taux > 100:
                raise ValueError
        except ValueError:
            afficher_erreur(self, "Erreur", "Le taux SumUp doit être un nombre entre 0 et 100.")
            return

        # Récupérer les IDs sélectionnés
        cp_nom = self._compte_principal_var.get()
        cc_nom = self._compte_caisse_var.get()
        cp_id = ""
        cc_id = ""
        if cp_nom in self._comptes_options:
            idx = self._comptes_options.index(cp_nom)
            cp_id = self._comptes_ids[idx]
        if cc_nom in self._comptes_options:
            idx = self._comptes_options.index(cc_nom)
            cc_id = self._comptes_ids[idx]

        set_config_financiere(
            taux_sumup=str(taux),
            compte_principal_id=cp_id,
            compte_caisse_id=cc_id,
        )

        # Montant cotisation par défaut
        montant_cot_str = self._cotisation_montant_entry.get().strip().replace(",", ".")
        try:
            montant_cot = float(montant_cot_str)
            if montant_cot < 0:
                raise ValueError
            from core.cotisations import set_montant_cotisation_defaut
            set_montant_cotisation_defaut(montant_cot)
        except ValueError:
            afficher_erreur(self, "Erreur", "Le montant de cotisation doit être un nombre positif ou nul.")
            return

        afficher_info(self, "Succès", "Les paramètres financiers ont été enregistrés.")

    # ── Onglet Événements ─────────────────────────────────────────────────────

    def _build_tab_evenements(self) -> None:
        tab = self._tabview.tab("📅 Événements")
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Classes scolaires
        f_titre_classes = ctk.CTkFrame(frame, fg_color="transparent")
        f_titre_classes.pack(fill="x", pady=(8, 2))
        ctk.CTkLabel(
            f_titre_classes, text="Classes scolaires", font=fonts.get("subtitle")
        ).pack(side="left")
        ctk.CTkButton(
            f_titre_classes,
            text="+ Ajouter",
            width=90,
            height=28,
            command=self._ajouter_classe,
        ).pack(side="right")

        self._frame_classes = ctk.CTkScrollableFrame(frame, height=180)
        self._frame_classes.pack(fill="x", pady=(0, 8))

        # Types d'événements
        f_titre_types = ctk.CTkFrame(frame, fg_color="transparent")
        f_titre_types.pack(fill="x", pady=(8, 2))
        ctk.CTkLabel(
            f_titre_types, text="Types d'événements", font=fonts.get("subtitle")
        ).pack(side="left")
        ctk.CTkButton(
            f_titre_types,
            text="+ Ajouter",
            width=90,
            height=28,
            command=self._ajouter_type,
        ).pack(side="right")

        self._frame_types = ctk.CTkScrollableFrame(frame, height=180)
        self._frame_types.pack(fill="x", pady=(0, 8))

        self._rafraichir_classes()
        self._rafraichir_types()

    def _rafraichir_classes(self) -> None:
        for w in self._frame_classes.winfo_children():
            w.destroy()

        fonts = app_theme.FONTS
        classes = get_all_classes()

        if not classes:
            ctk.CTkLabel(
                self._frame_classes, text="Aucune classe définie.", font=fonts.get("small")
            ).pack(anchor="w", padx=8, pady=4)
            return

        # En-tête
        header = ctk.CTkFrame(self._frame_classes, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(header, text="Nom", width=120, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=0, padx=4
        )
        ctk.CTkLabel(header, text="Ordre", width=60, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=1, padx=4
        )
        ctk.CTkLabel(header, text="Actif", width=60, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=2, padx=4
        )

        for cls in classes:
            row = ctk.CTkFrame(self._frame_classes, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            couleur = None if cls["actif"] else "grey"
            ctk.CTkLabel(row, text=cls["nom"], width=120, anchor="w", text_color=couleur).grid(
                row=0, column=0, padx=4
            )
            ctk.CTkLabel(
                row, text=str(cls["ordre"]), width=60, anchor="w", text_color=couleur
            ).grid(row=0, column=1, padx=4)

            actif_var = ctk.BooleanVar(value=bool(cls["actif"]))
            ctk.CTkCheckBox(
                row,
                text="",
                variable=actif_var,
                width=40,
                command=lambda cid=cls["id"]: self._basculer_classe(cid),
            ).grid(row=0, column=2, padx=4)

            ctk.CTkButton(
                row,
                text="✏️",
                width=36,
                height=26,
                command=lambda c=cls: self._modifier_classe(c),
            ).grid(row=0, column=3, padx=2)
            ctk.CTkButton(
                row,
                text="🗑️",
                width=36,
                height=26,
                fg_color="#c0392b",
                hover_color="#922b21",
                command=lambda cid=cls["id"], cnom=cls["nom"]: self._supprimer_classe(cid, cnom),
            ).grid(row=0, column=4, padx=2)

    def _rafraichir_types(self) -> None:
        for w in self._frame_types.winfo_children():
            w.destroy()

        fonts = app_theme.FONTS
        types = get_all_types_evenements()

        if not types:
            ctk.CTkLabel(
                self._frame_types, text="Aucun type défini.", font=fonts.get("small")
            ).pack(anchor="w", padx=8, pady=4)
            return

        # En-tête
        header = ctk.CTkFrame(self._frame_types, fg_color="transparent")
        header.pack(fill="x", padx=4, pady=(0, 2))
        ctk.CTkLabel(header, text="Nom", width=200, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=0, padx=4
        )
        ctk.CTkLabel(header, text="Ordre", width=60, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=1, padx=4
        )
        ctk.CTkLabel(header, text="Actif", width=60, font=fonts.get("bold"), anchor="w").grid(
            row=0, column=2, padx=4
        )

        for tp in types:
            row = ctk.CTkFrame(self._frame_types, fg_color="transparent")
            row.pack(fill="x", padx=4, pady=1)
            couleur = None if tp["actif"] else "grey"
            ctk.CTkLabel(row, text=tp["nom"], width=200, anchor="w", text_color=couleur).grid(
                row=0, column=0, padx=4
            )
            ctk.CTkLabel(
                row, text=str(tp["ordre"]), width=60, anchor="w", text_color=couleur
            ).grid(row=0, column=1, padx=4)

            actif_var = ctk.BooleanVar(value=bool(tp["actif"]))
            ctk.CTkCheckBox(
                row,
                text="",
                variable=actif_var,
                width=40,
                command=lambda tid=tp["id"]: self._basculer_type(tid),
            ).grid(row=0, column=2, padx=4)

            ctk.CTkButton(
                row,
                text="✏️",
                width=36,
                height=26,
                command=lambda t=tp: self._modifier_type(t),
            ).grid(row=0, column=3, padx=2)
            ctk.CTkButton(
                row,
                text="🗑️",
                width=36,
                height=26,
                fg_color="#c0392b",
                hover_color="#922b21",
                command=lambda tid=tp["id"], tnom=tp["nom"]: self._supprimer_type(tid, tnom),
            ).grid(row=0, column=4, padx=2)

    # Actions classes
    def _ajouter_classe(self) -> None:
        _DialogAjoutItem(
            self,
            titre="Ajouter une classe scolaire",
            label_nom="Nom de la classe",
            on_valider=lambda nom, ordre: self._creer_classe(nom, ordre),
        )

    def _creer_classe(self, nom: str, ordre: int) -> bool:
        erreurs = valider_nom_liste(nom)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return False
        new_id = add_classe(nom, ordre)
        if not new_id:
            afficher_erreur(self, "Erreur", "Impossible d'ajouter la classe (nom déjà existant ?).")
            return False
        self._rafraichir_classes()
        return True

    def _modifier_classe(self, classe: dict) -> None:
        _DialogAjoutItem(
            self,
            titre="Modifier la classe scolaire",
            label_nom="Nom de la classe",
            nom_initial=classe["nom"],
            ordre_initial=classe["ordre"],
            on_valider=lambda nom, ordre: self._sauver_classe(classe["id"], nom, ordre),
        )

    def _sauver_classe(self, classe_id: int, nom: str, ordre: int) -> bool:
        erreurs = valider_nom_liste(nom)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return False
        ok = update_classe(classe_id, nom, ordre)
        if ok:
            self._rafraichir_classes()
        return ok

    def _basculer_classe(self, classe_id: int) -> None:
        toggle_classe(classe_id)
        self._rafraichir_classes()

    def _supprimer_classe(self, classe_id: int, nom: str) -> None:
        if not demander_confirmation(
            self,
            "Supprimer la classe",
            f"Voulez-vous vraiment supprimer la classe « {nom} » ?",
        ):
            return
        ok = delete_classe(classe_id)
        if ok:
            self._rafraichir_classes()
        else:
            afficher_erreur(
                self,
                "Suppression impossible",
                f"La classe « {nom} » est utilisée dans des événements et ne peut pas être supprimée.",
            )

    # Actions types d'événements
    def _ajouter_type(self) -> None:
        _DialogAjoutItem(
            self,
            titre="Ajouter un type d'événement",
            label_nom="Nom du type",
            on_valider=lambda nom, ordre: self._creer_type(nom, ordre),
        )

    def _creer_type(self, nom: str, ordre: int) -> bool:
        erreurs = valider_nom_liste(nom)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return False
        new_id = add_type_evenement(nom, ordre)
        if not new_id:
            afficher_erreur(
                self, "Erreur", "Impossible d'ajouter le type (nom déjà existant ?)."
            )
            return False
        self._rafraichir_types()
        return True

    def _modifier_type(self, tp: dict) -> None:
        _DialogAjoutItem(
            self,
            titre="Modifier le type d'événement",
            label_nom="Nom du type",
            nom_initial=tp["nom"],
            ordre_initial=tp["ordre"],
            on_valider=lambda nom, ordre: self._sauver_type(tp["id"], nom, ordre),
        )

    def _sauver_type(self, type_id: int, nom: str, ordre: int) -> bool:
        erreurs = valider_nom_liste(nom)
        if erreurs:
            afficher_erreur(self, "Erreur", "\n".join(erreurs))
            return False
        ok = update_type_evenement(type_id, nom, ordre)
        if ok:
            self._rafraichir_types()
        return ok

    def _basculer_type(self, type_id: int) -> None:
        toggle_type_evenement(type_id)
        self._rafraichir_types()

    def _supprimer_type(self, type_id: int, nom: str) -> None:
        if not demander_confirmation(
            self,
            "Supprimer le type",
            f"Voulez-vous vraiment supprimer le type « {nom} » ?",
        ):
            return
        ok = delete_type_evenement(type_id)
        if ok:
            self._rafraichir_types()
        else:
            afficher_erreur(
                self,
                "Suppression impossible",
                f"Le type « {nom} » ne peut pas être supprimé.",
            )

    # ── Onglet Système ────────────────────────────────────────────────────────

    def _build_tab_systeme(self) -> None:
        tab = self._tabview.tab("🖥️ Système")
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Thème
        ctk.CTkLabel(frame, text="Thème de l'interface", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(8, 4)
        )

        self._theme_mode_var = ctk.StringVar(value="dark")
        f_theme = ctk.CTkFrame(frame, fg_color="transparent")
        f_theme.pack(anchor="w", pady=4)
        ctk.CTkRadioButton(
            f_theme, text="🌙 Sombre", variable=self._theme_mode_var, value="dark"
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            f_theme, text="☀️ Clair", variable=self._theme_mode_var, value="light"
        ).pack(side="left")

        # Sauvegarde automatique
        ctk.CTkLabel(frame, text="Sauvegarde automatique", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )

        self._sauvegarde_auto_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            frame,
            text="Activer la sauvegarde automatique",
            variable=self._sauvegarde_auto_var,
        ).pack(anchor="w", pady=2)

        f_freq = ctk.CTkFrame(frame, fg_color="transparent")
        f_freq.pack(fill="x", pady=3)
        ctk.CTkLabel(f_freq, text="Fréquence", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._sauvegarde_freq_entry = ctk.CTkEntry(f_freq, width=80)
        self._sauvegarde_freq_entry.pack(side="left")
        ctk.CTkLabel(f_freq, text="jours").pack(side="left", padx=(6, 0))

        f_bkp = ctk.CTkFrame(frame, fg_color="transparent")
        f_bkp.pack(fill="x", pady=3)
        ctk.CTkLabel(f_bkp, text="Dossier", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._sauvegarde_dossier_var = ctk.StringVar()
        ctk.CTkEntry(f_bkp, textvariable=self._sauvegarde_dossier_var, width=360).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            f_bkp, text="📁", width=40, command=self._choisir_dossier_sauvegarde
        ).pack(side="left", padx=(4, 0))

        self._derniere_sauvegarde_label = ctk.CTkLabel(
            frame, text="Dernière sauvegarde : —", font=fonts.get("small"), text_color="grey"
        )
        self._derniere_sauvegarde_label.pack(anchor="w", padx=(158, 0))

        ctk.CTkButton(
            frame,
            text="💾 Sauvegarder maintenant",
            width=220,
            command=self._sauvegarder_maintenant,
        ).pack(anchor="w", padx=(158, 0), pady=(8, 4))

        # Exports
        ctk.CTkLabel(frame, text="Exports", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )
        f_exp = ctk.CTkFrame(frame, fg_color="transparent")
        f_exp.pack(fill="x", pady=3)
        ctk.CTkLabel(f_exp, text="Dossier par défaut", width=150, anchor="ne").pack(
            side="left", padx=(0, 8)
        )
        self._export_dossier_var = ctk.StringVar()
        ctk.CTkEntry(f_exp, textvariable=self._export_dossier_var, width=360).pack(
            side="left", fill="x", expand=True
        )
        ctk.CTkButton(
            f_exp, text="📁", width=40, command=self._choisir_dossier_export
        ).pack(side="left", padx=(4, 0))

        # Boutons
        f_btn = ctk.CTkFrame(frame, fg_color="transparent")
        f_btn.pack(fill="x", pady=(12, 4))
        ctk.CTkButton(
            f_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            f_btn, text="💾 Enregistrer", width=150, command=self._enregistrer_systeme
        ).pack(side="right")

        self._charger_systeme()

    def _charger_systeme(self) -> None:
        config = get_config_systeme()

        self._theme_mode_var.set(config.get("theme_mode", "dark"))
        self._sauvegarde_auto_var.set(config.get("sauvegarde_auto", "0") == "1")
        self._sauvegarde_freq_entry.delete(0, "end")
        self._sauvegarde_freq_entry.insert(0, config.get("sauvegarde_frequence", "7"))
        self._sauvegarde_dossier_var.set(config.get("sauvegarde_dossier", ""))
        self._export_dossier_var.set(config.get("export_dossier_defaut", ""))

        derniere = config.get("derniere_sauvegarde", "")
        if derniere:
            self._derniere_sauvegarde_label.configure(text=self._format_texte_derniere_sauvegarde(derniere))

    def _choisir_dossier_sauvegarde(self) -> None:
        dossier = filedialog.askdirectory(parent=self, title="Choisir le dossier de sauvegarde")
        if dossier:
            self._sauvegarde_dossier_var.set(dossier)

    def _choisir_dossier_export(self) -> None:
        dossier = filedialog.askdirectory(parent=self, title="Choisir le dossier d'export par défaut")
        if dossier:
            self._export_dossier_var.set(dossier)

    def _sauvegarder_maintenant(self) -> None:
        resultat = sauvegarder_maintenant()
        if not resultat["succes"]:
            afficher_erreur(self, "Erreur de sauvegarde", resultat["message"])
            return

        derniere = get_config_systeme().get("derniere_sauvegarde", "")
        if derniere:
            self._derniere_sauvegarde_label.configure(
                text=self._format_texte_derniere_sauvegarde(derniere)
            )

        afficher_info(
            self,
            "Sauvegarde réussie",
            f"Base de données sauvegardée :\n{resultat['chemin']}",
        )

    def _enregistrer_systeme(self) -> None:
        theme_mode = self._theme_mode_var.get()
        sauvegarde_auto = "1" if self._sauvegarde_auto_var.get() else "0"
        freq_str = self._sauvegarde_freq_entry.get().strip()
        try:
            freq = int(freq_str)
            if freq < 1:
                raise ValueError
        except ValueError:
            afficher_erreur(self, "Erreur", "La fréquence de sauvegarde doit être un entier positif.")
            return

        set_config_systeme(
            theme_mode=theme_mode,
            sauvegarde_auto=sauvegarde_auto,
            sauvegarde_frequence=str(freq),
            sauvegarde_dossier=self._sauvegarde_dossier_var.get().strip(),
            export_dossier_defaut=self._export_dossier_var.get().strip(),
        )

        # Appliquer le thème immédiatement
        ctk.set_appearance_mode(theme_mode)
        from ui import theme as app_theme_mod

        theme_data = app_theme_mod.get_theme()
        theme_data["appearance_mode"] = theme_mode
        app_theme_mod.save_theme(theme_data)
        app_theme_mod.load_theme()

        afficher_info(self, "Succès", "Les paramètres système ont été enregistrés.")

    @staticmethod
    def _format_texte_derniere_sauvegarde(valeur: str) -> str:
        try:
            dt = datetime.fromisoformat(valeur)
            return f"Dernière sauvegarde : {dt.strftime('%d/%m/%Y à %Hh%M')}"
        except ValueError:
            return f"Dernière sauvegarde : {valeur}"



    # ── Onglet Exports & PDF ───────────────────────────────────────────────────

    def _build_tab_exports_pdf(self) -> None:
        tab = self._tabview.tab("📄 Exports & PDF")
        fonts = app_theme.FONTS

        frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        ctk.CTkLabel(frame, text="Paramètres PDF", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(8, 4)
        )

        self._pdf_polices = get_all_polices(actif_only=True)
        valeurs_polices = [police["nom"] for police in self._pdf_polices] or ["Helvetica"]

        self._pdf_police_titre_var = ctk.StringVar(
            value=get_parametre("pdf_police_titre", valeurs_polices[0])
        )
        self._pdf_police_corps_var = ctk.StringVar(
            value=get_parametre("pdf_police_corps", valeurs_polices[0])
        )
        self._pdf_taille_base_var = ctk.StringVar(value=get_parametre("pdf_taille_base", "11"))
        self._pdf_couleur_accent_var = ctk.StringVar(
            value=get_parametre("pdf_couleur_accent", "#1f6aa5")
        )
        self._type_recu_don_var = ctk.StringVar(value=("Cerfa 11580" if get_parametre("type_recu_don", "cerfa") == "cerfa" else "Attestation simple"))
        self._num_habilitation_var = ctk.StringVar(value=get_parametre("num_habilitation_fiscale", ""))
        self._numero_depart_recu_var = ctk.StringVar(value=get_parametre("recu_don_num_depart", f"{datetime.now().year}-001"))

        f_titre = ctk.CTkFrame(frame, fg_color="transparent")
        f_titre.pack(fill="x", pady=3)
        ctk.CTkLabel(f_titre, text="Police titres", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._combo_pdf_police_titre = ctk.CTkOptionMenu(
            f_titre,
            variable=self._pdf_police_titre_var,
            values=valeurs_polices,
            width=240,
        )
        self._combo_pdf_police_titre.pack(side="left")

        f_corps = ctk.CTkFrame(frame, fg_color="transparent")
        f_corps.pack(fill="x", pady=3)
        ctk.CTkLabel(f_corps, text="Police corps", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._combo_pdf_police_corps = ctk.CTkOptionMenu(
            f_corps,
            variable=self._pdf_police_corps_var,
            values=valeurs_polices,
            width=240,
        )
        self._combo_pdf_police_corps.pack(side="left")

        f_taille = ctk.CTkFrame(frame, fg_color="transparent")
        f_taille.pack(fill="x", pady=3)
        ctk.CTkLabel(f_taille, text="Taille base", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._pdf_taille_base_entry = ctk.CTkEntry(
            f_taille,
            textvariable=self._pdf_taille_base_var,
            width=120,
        )
        self._pdf_taille_base_entry.pack(side="left")

        f_couleur = ctk.CTkFrame(frame, fg_color="transparent")
        f_couleur.pack(fill="x", pady=3)
        ctk.CTkLabel(f_couleur, text="Couleur accent", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        self._pdf_couleur_entry = ctk.CTkEntry(
            f_couleur,
            textvariable=self._pdf_couleur_accent_var,
            width=160,
        )
        self._pdf_couleur_entry.pack(side="left")
        self._pdf_couleur_btn = ctk.CTkButton(
            f_couleur,
            text="🎨 Choisir",
            width=110,
            command=self._choisir_couleur_pdf,
        )
        self._pdf_couleur_btn.pack(side="left", padx=(6, 0))

        ctk.CTkButton(
            frame,
            text="🖋️ Gérer les polices...",
            width=180,
            command=self._ouvrir_polices_pdf,
        ).pack(anchor="w", padx=(158, 0), pady=(8, 0))

        # ── Thème des exports ──────────────────────────────────────────────────
        ctk.CTkLabel(frame, text="Thème des exports", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )

        from core.theme_export import get_theme_export as _get_theme
        _theme = _get_theme()

        self._export_couleur_principale_var = ctk.StringVar(
            value=_theme.get("couleur_principale", "#1f6aa5")
        )
        self._export_couleur_secondaire_var = ctk.StringVar(
            value=_theme.get("couleur_secondaire", "#144870")
        )
        self._export_style_tableaux_var = ctk.StringVar(
            value=_theme.get("style_tableaux", "moderne")
        )

        # Couleur principale
        f_cprinc = ctk.CTkFrame(frame, fg_color="transparent")
        f_cprinc.pack(fill="x", pady=3)
        ctk.CTkLabel(f_cprinc, text="Couleur principale", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f_cprinc, textvariable=self._export_couleur_principale_var, width=120).pack(side="left")
        self._export_couleur_principale_btn = ctk.CTkButton(
            f_cprinc, text="🎨", width=50,
            command=lambda: self._choisir_couleur_export("principale"),
        )
        self._export_couleur_principale_btn.pack(side="left", padx=(4, 0))

        # Couleur secondaire
        f_csec = ctk.CTkFrame(frame, fg_color="transparent")
        f_csec.pack(fill="x", pady=3)
        ctk.CTkLabel(f_csec, text="Couleur secondaire", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f_csec, textvariable=self._export_couleur_secondaire_var, width=120).pack(side="left")
        self._export_couleur_secondaire_btn = ctk.CTkButton(
            f_csec, text="🎨", width=50,
            command=lambda: self._choisir_couleur_export("secondaire"),
        )
        self._export_couleur_secondaire_btn.pack(side="left", padx=(4, 0))

        # Style tableaux
        f_style = ctk.CTkFrame(frame, fg_color="transparent")
        f_style.pack(fill="x", pady=3)
        ctk.CTkLabel(f_style, text="Style des tableaux", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        for val, lib in [("moderne", "Moderne"), ("classique", "Classique"), ("minimaliste", "Minimaliste")]:
            ctk.CTkRadioButton(
                f_style, text=lib, variable=self._export_style_tableaux_var, value=val
            ).pack(side="left", padx=(0, 12))

        self._maj_apercu_couleurs_export()

        # Modèle Bilan AG
        ctk.CTkLabel(frame, text="Bilan AG", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(16, 4)
        )
        ctk.CTkLabel(
            frame,
            text="Personnalisez le template Markdown du Bilan AG.",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w")
        f_bilan = ctk.CTkFrame(frame, fg_color="transparent")
        f_bilan.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(
            f_bilan,
            text="✏️ Modifier le modèle Bilan AG",
            width=240,
            command=self._ouvrir_editeur_template_bilan,
        ).pack(side="left")
        ctk.CTkButton(
            f_bilan,
            text="🔄 Restaurer le modèle par défaut",
            width=240,
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._restaurer_template_bilan,
        ).pack(side="left", padx=(8, 0))


        ctk.CTkLabel(frame, text="Reçus de dons", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(18, 4)
        )
        f_type_recu = ctk.CTkFrame(frame, fg_color="transparent")
        f_type_recu.pack(fill="x", pady=3)
        ctk.CTkLabel(f_type_recu, text="Type de reçu par défaut", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkOptionMenu(
            f_type_recu,
            values=["Cerfa 11580", "Attestation simple"],
            variable=self._type_recu_don_var,
            width=240,
        ).pack(side="left")

        f_habilitation = ctk.CTkFrame(frame, fg_color="transparent")
        f_habilitation.pack(fill="x", pady=3)
        ctk.CTkLabel(f_habilitation, text="N° habilitation fiscale", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f_habilitation, textvariable=self._num_habilitation_var, width=240).pack(side="left")

        f_depart = ctk.CTkFrame(frame, fg_color="transparent")
        f_depart.pack(fill="x", pady=3)
        ctk.CTkLabel(f_depart, text="N° départ des reçus", width=150, anchor="ne").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f_depart, textvariable=self._numero_depart_recu_var, width=240).pack(side="left")

        f_recu = ctk.CTkFrame(frame, fg_color="transparent")
        f_recu.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(f_recu, text="✏️ Modifier template Cerfa 11580", width=240, command=self._ouvrir_editeur_template_cerfa).pack(side="left")
        ctk.CTkButton(f_recu, text="✏️ Modifier template Attestation simple", width=260, command=self._ouvrir_editeur_template_attestation).pack(side="left", padx=(8, 0))

        f_recu2 = ctk.CTkFrame(frame, fg_color="transparent")
        f_recu2.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(f_recu2, text="🔄 Restaurer Cerfa par défaut", width=240, fg_color="#8b1a1a", hover_color="#6b1414", command=self._restaurer_template_cerfa).pack(side="left")
        ctk.CTkButton(f_recu2, text="🔄 Restaurer Attestation par défaut", width=260, fg_color="#8b1a1a", hover_color="#6b1414", command=self._restaurer_template_attestation).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(frame, text="Remboursements de frais", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(18, 4)
        )
        f_remb = ctk.CTkFrame(frame, fg_color="transparent")
        f_remb.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(f_remb, text="✏️ Modifier template Remboursement", width=270, command=self._ouvrir_editeur_template_remboursement).pack(side="left")
        ctk.CTkButton(f_remb, text="🔄 Restaurer Remboursement par défaut", width=300, fg_color="#8b1a1a", hover_color="#6b1414", command=self._restaurer_template_remboursement).pack(side="left", padx=(8, 0))

        # ── Templates Dossier Subvention ────────────────────────────────────
        ctk.CTkLabel(frame, text="Templates Dossier Subvention", font=fonts.get("subtitle")).pack(
            anchor="w", pady=(18, 4)
        )
        ctk.CTkLabel(
            frame,
            text="Personnalisez les sections textuelles du dossier de subvention.",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w")

        _templates_subv = [
            ("presentation", "✏️ Présentation association"),
            ("mot_president", "✏️ Mot du Président"),
            ("projet", "✏️ Description du projet"),
            ("objectifs", "✏️ Objectifs & indicateurs"),
            ("statuts", "✏️ Statuts association"),
            ("budget_projet", "✏️ Budget prévisionnel projet"),
        ]
        for i in range(0, len(_templates_subv), 2):
            f_row = ctk.CTkFrame(frame, fg_color="transparent")
            f_row.pack(anchor="w", pady=(4, 0))
            cle1, lib1 = _templates_subv[i]
            ctk.CTkButton(
                f_row, text=lib1, width=230,
                command=lambda k=cle1: self._ouvrir_editeur_template_subvention(k),
            ).pack(side="left")
            if i + 1 < len(_templates_subv):
                cle2, lib2 = _templates_subv[i + 1]
                ctk.CTkButton(
                    f_row, text=lib2, width=230,
                    command=lambda k=cle2: self._ouvrir_editeur_template_subvention(k),
                ).pack(side="left", padx=(8, 0))

        f_subv_reset = ctk.CTkFrame(frame, fg_color="transparent")
        f_subv_reset.pack(anchor="w", pady=(6, 0))
        ctk.CTkButton(
            f_subv_reset,
            text="🔄 Restaurer tous les templates par défaut",
            width=300,
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._restaurer_tous_templates_subvention,
        ).pack(side="left")

        f_btn = ctk.CTkFrame(frame, fg_color="transparent")
        f_btn.pack(fill="x", pady=(14, 4))
        ctk.CTkButton(
            f_btn,
            text="💾 Enregistrer",
            width=150,
            command=self._enregistrer_pdf,
        ).pack(side="right")

        self._maj_apercu_couleur_pdf()

    def _choisir_couleur_pdf(self) -> None:
        result = _askcolor(color=self._pdf_couleur_accent_var.get(), parent=self)
        couleur = result[1] if result else None
        if couleur:
            self._pdf_couleur_accent_var.set(couleur)
            self._maj_apercu_couleur_pdf()

    def _maj_apercu_couleur_pdf(self) -> None:
        try:
            self._pdf_couleur_btn.configure(fg_color=self._pdf_couleur_accent_var.get())
        except Exception:
            self._pdf_couleur_btn.configure(
                fg_color=app_theme.COLORS.get("primary", "#1f6aa5")
            )

    def _choisir_couleur_export(self, type_couleur: str) -> None:
        if type_couleur == "principale":
            var = self._export_couleur_principale_var
            btn = self._export_couleur_principale_btn
        else:
            var = self._export_couleur_secondaire_var
            btn = self._export_couleur_secondaire_btn
        result = _askcolor(color=var.get(), parent=self)
        couleur = result[1] if result else None
        if couleur:
            var.set(couleur)
            self._maj_apercu_couleurs_export()

    def _maj_apercu_couleurs_export(self) -> None:
        try:
            self._export_couleur_principale_btn.configure(
                fg_color=self._export_couleur_principale_var.get()
            )
        except Exception:
            pass
        try:
            self._export_couleur_secondaire_btn.configure(
                fg_color=self._export_couleur_secondaire_var.get()
            )
        except Exception:
            pass

    def _ouvrir_polices_pdf(self) -> None:
        from ui.modules.administration.polices import GestionPolices

        dialog = GestionPolices(self)
        self.wait_window(dialog)
        self._pdf_polices = get_all_polices(actif_only=True)
        valeurs_polices = [police["nom"] for police in self._pdf_polices] or ["Helvetica"]
        self._combo_pdf_police_titre.configure(values=valeurs_polices)
        self._combo_pdf_police_corps.configure(values=valeurs_polices)
        if self._pdf_police_titre_var.get() not in valeurs_polices:
            self._pdf_police_titre_var.set(valeurs_polices[0])
        if self._pdf_police_corps_var.get() not in valeurs_polices:
            self._pdf_police_corps_var.set(valeurs_polices[0])

    def _ouvrir_editeur_template_bilan(self) -> None:
        from ui.modules.administration.editeur_template_bilan import EditeurTemplateBilan

        editeur = EditeurTemplateBilan(self)
        self.wait_window(editeur)

    def _ouvrir_editeur_template_cerfa(self) -> None:
        self._ouvrir_editeur_template_document(
            titre="✏️ Modifier template Cerfa 11580",
            variables=VARIABLES_TEMPLATE_CERFA,
            charger=get_template_cerfa,
            sauvegarder=save_template_cerfa,
            restaurer=reset_template_cerfa,
        )

    def _ouvrir_editeur_template_attestation(self) -> None:
        self._ouvrir_editeur_template_document(
            titre="✏️ Modifier template Attestation simple",
            variables=VARIABLES_TEMPLATE_ATTESTATION,
            charger=get_template_attestation,
            sauvegarder=save_template_attestation,
            restaurer=reset_template_attestation,
        )

    def _ouvrir_editeur_template_remboursement(self) -> None:
        self._ouvrir_editeur_template_document(
            titre="✏️ Modifier template Remboursement de frais",
            variables=VARIABLES_TEMPLATE_REMBOURSEMENT,
            charger=get_template_remboursement,
            sauvegarder=save_template_remboursement,
            restaurer=reset_template_remboursement,
        )

    def _ouvrir_editeur_template_document(self, titre: str, variables, charger, sauvegarder, restaurer) -> None:
        editeur = _EditeurTemplateDocument(self, titre, variables, charger, sauvegarder, restaurer)
        self.wait_window(editeur)

    def _restaurer_template_cerfa(self) -> None:
        self._restaurer_template_generique("template Cerfa 11580", reset_template_cerfa)

    def _restaurer_template_attestation(self) -> None:
        self._restaurer_template_generique("template Attestation simple", reset_template_attestation)

    def _restaurer_template_remboursement(self) -> None:
        self._restaurer_template_generique("template Remboursement", reset_template_remboursement)

    def _restaurer_template_generique(self, libelle: str, callback) -> None:
        if not demander_confirmation(
            self,
            "Restaurer le modèle par défaut",
            f"Toutes vos modifications de {libelle} seront perdues.\nVoulez-vous vraiment restaurer le modèle par défaut ?",
        ):
            return
        try:
            callback()
            afficher_info(self, "Succès", "Le modèle par défaut a été restauré.")
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de restaurer le modèle : {exc}")

    def _restaurer_template_bilan(self) -> None:
        if not demander_confirmation(
            self,
            "Restaurer le modèle par défaut",
            "Toutes vos modifications du modèle Bilan AG seront perdues.\n"
            "Voulez-vous vraiment restaurer le modèle par défaut ?",
        ):
            return
        try:
            reset_template_bilan()
            afficher_info(self, "Succès", "Le modèle Bilan AG par défaut a été restauré.")
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de restaurer le modèle : {exc}")

    def _enregistrer_pdf(self) -> None:
        try:
            taille = int(self._pdf_taille_base_var.get().strip())
            if taille <= 0:
                raise ValueError
        except ValueError:
            afficher_erreur(self, "Erreur", "La taille de base doit être un entier positif.")
            return

        set_parametre("pdf_police_titre", self._pdf_police_titre_var.get().strip())
        set_parametre("pdf_police_corps", self._pdf_police_corps_var.get().strip())
        set_parametre("pdf_taille_base", str(taille))
        set_parametre("pdf_couleur_accent", self._pdf_couleur_accent_var.get().strip())
        set_parametre("type_recu_don", "cerfa" if self._type_recu_don_var.get() == "Cerfa 11580" else "simple")
        set_parametre("num_habilitation_fiscale", self._num_habilitation_var.get().strip())
        set_parametre("recu_don_num_depart", self._numero_depart_recu_var.get().strip())

        # Thème des exports
        try:
            from core.theme_export import set_theme_export
            set_theme_export(
                couleur_principale=self._export_couleur_principale_var.get().strip(),
                couleur_secondaire=self._export_couleur_secondaire_var.get().strip(),
                style_tableaux=self._export_style_tableaux_var.get(),
            )
        except Exception as exc:
            logger.warning("Impossible d'enregistrer le thème des exports : %s", exc)

        afficher_info(self, "Succès", "Les paramètres PDF ont été enregistrés.")

    # ── Templates Dossier Subvention ──────────────────────────────────────────

    def _ouvrir_editeur_template_subvention(self, cle: str) -> None:
        """Ouvre l'éditeur pour un template du dossier de subvention."""
        from pathlib import Path

        _BASE_DIR = Path(__file__).parent.parent.parent.parent
        _CONFIG_DIR = _BASE_DIR / "config"

        noms = {
            "presentation": "dossier_subvention_presentation.md",
            "mot_president": "dossier_subvention_mot_president.md",
            "projet": "dossier_subvention_projet.md",
            "objectifs": "dossier_subvention_objectifs.md",
            "statuts": "dossier_subvention_statuts.md",
            "budget_projet": "dossier_subvention_budget_projet.md",
        }
        titres = {
            "presentation": "✏️ Présentation de l'association",
            "mot_president": "✏️ Mot du Président",
            "projet": "✏️ Description du projet",
            "objectifs": "✏️ Objectifs & indicateurs",
            "statuts": "✏️ Statuts de l'association",
            "budget_projet": "✏️ Budget prévisionnel projet",
        }

        nom = noms.get(cle)
        if not nom:
            return

        chemin = _CONFIG_DIR / nom
        chemin_defaut = _CONFIG_DIR / nom.replace(".md", ".default.md")

        contenu = ""
        if chemin.exists():
            try:
                contenu = chemin.read_text(encoding="utf-8")
            except Exception:
                pass
        elif chemin_defaut.exists():
            try:
                contenu = chemin_defaut.read_text(encoding="utf-8")
            except Exception:
                pass

        editeur = _EditeurTemplateSimple(
            self,
            titre=titres.get(cle, "✏️ Éditer"),
            contenu=contenu,
            chemin_sauvegarde=str(chemin),
            chemin_defaut=str(chemin_defaut),
        )
        self.wait_window(editeur)

    def _restaurer_tous_templates_subvention(self) -> None:
        if not demander_confirmation(
            self,
            "Restaurer tous les templates",
            "Toutes les modifications des templates Dossier Subvention seront perdues.\n"
            "Voulez-vous vraiment restaurer tous les templates par défaut ?",
        ):
            return
        from pathlib import Path
        import shutil

        _BASE_DIR = Path(__file__).parent.parent.parent.parent
        _CONFIG_DIR = _BASE_DIR / "config"

        noms = [
            "dossier_subvention_presentation.md",
            "dossier_subvention_mot_president.md",
            "dossier_subvention_projet.md",
            "dossier_subvention_objectifs.md",
            "dossier_subvention_statuts.md",
            "dossier_subvention_budget_projet.md",
        ]
        erreurs = []
        for nom in noms:
            src = _CONFIG_DIR / nom.replace(".md", ".default.md")
            dst = _CONFIG_DIR / nom
            try:
                if src.exists():
                    shutil.copy2(str(src), str(dst))
            except Exception as exc:
                erreurs.append(f"{nom}: {exc}")

        if erreurs:
            afficher_erreur(self, "Erreur partielle", "\n".join(erreurs))
        else:
            afficher_info(self, "Succès", "Tous les templates ont été restaurés par défaut.")

    # ── Utilitaires ───────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_date(value: str) -> str:
        if not value:
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value


# ── Dialogue d'ajout/modification ────────────────────────────────────────────


class _DialogAjoutItem(ctk.CTkToplevel):
    """Petite fenêtre modale pour ajouter ou modifier un élément de liste."""

    def __init__(
        self,
        parent: Any,
        titre: str,
        label_nom: str,
        on_valider,
        nom_initial: str = "",
        ordre_initial: int = 0,
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("380x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._on_valider = on_valider
        fonts = app_theme.FONTS

        ctk.CTkLabel(self, text=titre, font=fonts.get("subtitle")).pack(pady=(16, 10))

        f_nom = ctk.CTkFrame(self, fg_color="transparent")
        f_nom.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(f_nom, text=label_nom, width=120, anchor="ne").pack(side="left", padx=(0, 8))
        self._nom_entry = ctk.CTkEntry(f_nom, width=200)
        self._nom_entry.pack(side="left")
        self._nom_entry.insert(0, nom_initial)

        f_ordre = ctk.CTkFrame(self, fg_color="transparent")
        f_ordre.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(f_ordre, text="Ordre", width=120, anchor="ne").pack(side="left", padx=(0, 8))
        self._ordre_entry = ctk.CTkEntry(f_ordre, width=80)
        self._ordre_entry.pack(side="left")
        self._ordre_entry.insert(0, str(ordre_initial))

        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=20, pady=(12, 0))
        ctk.CTkButton(
            f_btn, text="Annuler", width=80, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(f_btn, text="✅ Valider", width=100, command=self._valider).pack(side="right")

    def _valider(self) -> None:
        nom = self._nom_entry.get().strip()
        try:
            ordre = int(self._ordre_entry.get().strip() or "0")
        except ValueError:
            ordre = 0
        ok = self._on_valider(nom, ordre)
        if ok:
            self.destroy()


# ── Éditeur de template document (Cerfa, Attestation, Remboursement) ─────────


class _EditeurTemplateDocument(ctk.CTkToplevel):
    """Fenêtre générique pour éditer un template Markdown (Cerfa, Attestation, Remboursement…).

    Signature : _EditeurTemplateDocument(parent, titre, variables, charger, sauvegarder, restaurer)
    - ``variables``   : liste de tuples ``(nom_variable, description)``
    - ``charger``     : callable() → str — retourne le contenu actuel
    - ``sauvegarder`` : callable(contenu: str) → sauvegarde
    - ``restaurer``   : callable() → remet le template par défaut
    """

    def __init__(
        self,
        parent: Any,
        titre: str,
        variables: list,
        charger,
        sauvegarder,
        restaurer,
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("1000x680")
        self.minsize(900, 600)
        self.transient(parent)
        self.grab_set()

        self._charger_fn = charger
        self._sauvegarder_fn = sauvegarder
        self._restaurer_fn = restaurer
        self._variables = variables

        self._build_ui(titre)
        self._charger_template()

    def _build_ui(self, titre: str) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(
            frame_header,
            text=titre,
            font=fonts.get("title"),
        ).pack(side="left")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=16, pady=4)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=1)
        frame_main.rowconfigure(0, weight=1)

        frame_editor = ctk.CTkFrame(frame_main)
        frame_editor.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            frame_editor,
            text="Contenu du template (Markdown)",
            font=fonts.get("bold"),
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(
            frame_editor,
            text="Utilisez {{variable}} pour insérer des données dynamiques.",
            font=fonts.get("small"),
            text_color="grey",
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(0, 4))
        self._textbox = ctk.CTkTextbox(
            frame_editor,
            font=("Courier New", 12),
            wrap="word",
        )
        self._textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        frame_vars = ctk.CTkFrame(frame_main)
        frame_vars.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            frame_vars,
            text="Variables disponibles",
            font=fonts.get("bold"),
            anchor="w",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        scroll_vars = ctk.CTkScrollableFrame(frame_vars, fg_color="transparent")
        scroll_vars.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        for nom, description in self._variables:
            f = ctk.CTkFrame(scroll_vars, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(
                f,
                text=f"{{{{{nom}}}}}",
                font=("Courier New", 11),
                text_color=colors.get("primary", "#1f6aa5"),
                anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                f,
                text=f"  {description}",
                font=fonts.get("small"),
                text_color="grey",
                anchor="w",
            ).pack(anchor="w")

        frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        frame_buttons.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkButton(
            frame_buttons,
            text="❌ Annuler",
            width=100,
            fg_color="grey",
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            frame_buttons,
            text="🔄 Restaurer le modèle par défaut",
            width=240,
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._restaurer_defaut,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            frame_buttons,
            text="💾 Enregistrer",
            width=150,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._enregistrer,
        ).pack(side="right")

    def _charger_template(self) -> None:
        try:
            contenu = self._charger_fn()
            self._textbox.delete("1.0", "end")
            self._textbox.insert("1.0", contenu)
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de charger le template : {exc}")

    def _enregistrer(self) -> None:
        contenu = self._textbox.get("1.0", "end")
        try:
            self._sauvegarder_fn(contenu)
            afficher_info(self, "Succès", "Le modèle a été enregistré.")
            self.destroy()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer le template : {exc}")

    def _restaurer_defaut(self) -> None:
        if not demander_confirmation(
            self,
            "Restaurer le modèle par défaut",
            "Toutes vos modifications seront perdues.\n"
            "Voulez-vous vraiment restaurer le modèle par défaut ?",
        ):
            return
        try:
            self._restaurer_fn()
            self._charger_template()
            afficher_info(self, "Succès", "Le modèle par défaut a été restauré.")
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de restaurer le template : {exc}")


# ── Éditeur de template simple (Dossier Subvention) ──────────────────────────


class _EditeurTemplateSimple(ctk.CTkToplevel):
    """Éditeur Markdown simple pour les templates du dossier de subvention."""

    def __init__(
        self,
        parent: Any,
        titre: str,
        contenu: str,
        chemin_sauvegarde: str,
        chemin_defaut: str,
    ) -> None:
        super().__init__(parent)
        self.title(titre)
        self.geometry("720x580")
        self.minsize(600, 480)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._chemin = chemin_sauvegarde
        self._chemin_defaut = chemin_defaut
        fonts = app_theme.FONTS

        ctk.CTkLabel(self, text=titre, font=fonts.get("title")).pack(
            anchor="w", padx=20, pady=(16, 8)
        )
        ctk.CTkLabel(
            self,
            text="Utilisez {{variable}} pour insérer des données dynamiques.",
            font=fonts.get("small"),
            text_color="grey",
        ).pack(anchor="w", padx=20)

        self._textbox = ctk.CTkTextbox(self, wrap="word", font=("Courier New", 12))
        self._textbox.pack(fill="both", expand=True, padx=20, pady=(8, 4))
        self._textbox.insert("1.0", contenu)

        frame_btn = ctk.CTkFrame(self, fg_color="transparent")
        frame_btn.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(
            frame_btn, text="Annuler", width=100, fg_color="grey", command=self.destroy
        ).pack(side="left")
        ctk.CTkButton(
            frame_btn, text="🔄 Restaurer défaut", width=160,
            fg_color="#8b1a1a", hover_color="#6b1414",
            command=self._restaurer_defaut,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            frame_btn, text="💾 Enregistrer", width=140, command=self._enregistrer
        ).pack(side="right")

    def _enregistrer(self) -> None:
        contenu = self._textbox.get("1.0", "end-1c")
        try:
            from pathlib import Path
            Path(self._chemin).parent.mkdir(parents=True, exist_ok=True)
            Path(self._chemin).write_text(contenu, encoding="utf-8")
            afficher_info(self, "Succès", "Le template a été enregistré.")
            self.destroy()
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer : {exc}")

    def _restaurer_defaut(self) -> None:
        if not demander_confirmation(
            self,
            "Restaurer le défaut",
            "Toutes vos modifications seront perdues. Continuer ?",
        ):
            return
        try:
            from pathlib import Path
            contenu = Path(self._chemin_defaut).read_text(encoding="utf-8")
            self._textbox.delete("1.0", "end")
            self._textbox.insert("1.0", contenu)
        except Exception as exc:
            afficher_erreur(self, "Erreur", f"Impossible de restaurer : {exc}")
