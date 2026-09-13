"""Formulaire modal d'ajout et de modification d'un membre."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from core.cotisations import get_annee_courante
from core.membres import get_statuts_disponibles, valider_membre
from db.models.cotisations import add_cotisation, get_cotisations_adherent, update_cotisation
from db.models.membres import add_membre, update_membre
from ui.modules.membres.cotisations import MiniFormulaireCotisationRapide
from ui import theme as app_theme
from utils.logger import get_logger

logger = get_logger(__name__)


class FormulaireMembreModal(ctk.CTkToplevel):
    """Fenêtre modale de saisie d'un membre (création ou modification)."""

    def __init__(self, parent: Any, membre: dict | None = None) -> None:
        super().__init__(parent)
        self._membre = membre
        self._est_edition = membre is not None

        if self._est_edition:
            nom_complet = f"{membre.get('prenom', '')} {membre.get('nom', '')}".strip()
            self.title(f"Modifier — {nom_complet}")
        else:
            self.title("Ajouter un membre")

        self.resizable(False, False)
        self.transient(parent)

        self._build_ui()
        if self._est_edition:
            self._preremplir()

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # Conteneur principal avec padding
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        titre = "Modifier le membre" if self._est_edition else "Ajouter un membre"
        ctk.CTkLabel(
            frame,
            text=titre,
            font=fonts.get("subtitle"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        # ── Champs de saisie ─────────────────────────────────────────────────
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkOptionMenu | ctk.CTkTextbox] = {}
        self._error_labels: dict[str, ctk.CTkLabel] = {}
        self._cotisation_rapide_initiale: dict | None = None

        champs = [
            ("nom", "Nom *", "entry"),
            ("prenom", "Prénom *", "entry"),
            ("email", "Email", "entry"),
            ("telephone", "Téléphone", "entry"),
            ("statut", "Statut *", "combobox"),
            ("date_adhesion", "Date d'adhésion", "date"),
            ("commentaire", "Commentaire", "textbox"),
        ]

        row = 1
        for champ_id, label_text, widget_type in champs:
            ctk.CTkLabel(
                frame,
                text=label_text,
                font=fonts.get("normal"),
                anchor="w",
                width=130,
            ).grid(row=row, column=0, sticky="nw", pady=(8, 0))

            if widget_type == "entry":
                widget = ctk.CTkEntry(frame, width=320, font=fonts.get("normal"))
                widget.grid(row=row, column=1, sticky="ew", pady=(8, 0))
                self._entries[champ_id] = widget

            elif widget_type == "combobox":
                statuts = get_statuts_disponibles()
                widget = ctk.CTkOptionMenu(
                    frame,
                    values=statuts,
                    width=320,
                    font=fonts.get("normal"),
                )
                widget.set(statuts[0])
                widget.grid(row=row, column=1, sticky="ew", pady=(8, 0))
                self._entries[champ_id] = widget

            elif widget_type == "date":
                try:
                    from tkcalendar import DateEntry

                    widget = DateEntry(
                        frame,
                        width=20,
                        date_pattern="yyyy-mm-dd",
                        font=("Arial", 12),
                    )
                    widget.grid(row=row, column=1, sticky="w", pady=(8, 0))
                    self._entries[champ_id] = widget
                except ImportError:
                    # Fallback sur une simple entrée texte
                    widget = ctk.CTkEntry(
                        frame,
                        width=320,
                        font=fonts.get("normal"),
                        placeholder_text="AAAA-MM-JJ",
                    )
                    widget.grid(row=row, column=1, sticky="ew", pady=(8, 0))
                    self._entries[champ_id] = widget

            elif widget_type == "textbox":
                widget = ctk.CTkTextbox(frame, width=320, height=80, font=fonts.get("normal"))
                widget.grid(row=row, column=1, sticky="ew", pady=(8, 0))
                self._entries[champ_id] = widget

            row += 1

            # Ligne d'erreur sous chaque champ
            err_label = ctk.CTkLabel(
                frame,
                text="",
                font=fonts.get("small"),
                text_color="#e05050",
                anchor="w",
            )
            err_label.grid(row=row, column=1, sticky="w")
            self._error_labels[champ_id] = err_label
            row += 1

        # ── Boutons ───────────────────────────────────────────────────────────
        ctk.CTkFrame(frame, height=1, fg_color="#555555").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(8, 6)
        )
        row += 1

        self._cotisation_rapide_initiale = self._cotisation_courante()
        self._cotisation_rapide = MiniFormulaireCotisationRapide(
            frame, cotisation=self._cotisation_rapide_initiale
        )
        self._cotisation_rapide.grid(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
        self._error_labels["cotisation_rapide"] = ctk.CTkLabel(
            frame,
            text="",
            font=fonts.get("small"),
            text_color="#e05050",
            anchor="w",
        )
        self._error_labels["cotisation_rapide"].grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        frame_buttons = ctk.CTkFrame(frame, fg_color="transparent")
        frame_buttons.grid(row=row, column=0, columnspan=2, pady=(20, 0))

        ctk.CTkButton(
            frame_buttons,
            text="Enregistrer",
            width=130,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._soumettre,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            frame_buttons,
            text="Annuler",
            width=100,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=10)

    # ── Préremplissage ────────────────────────────────────────────────────────

    def _preremplir(self) -> None:
        m = self._membre
        champ_valeurs = {
            "nom": m.get("nom", ""),
            "prenom": m.get("prenom", ""),
            "email": m.get("email", "") or "",
            "telephone": m.get("telephone", "") or "",
            "commentaire": m.get("commentaire", "") or "",
        }
        for champ_id, valeur in champ_valeurs.items():
            widget = self._entries.get(champ_id)
            if widget is None:
                continue
            if isinstance(widget, ctk.CTkTextbox):
                widget.delete("1.0", "end")
                widget.insert("1.0", valeur)
            elif isinstance(widget, ctk.CTkEntry):
                widget.delete(0, "end")
                widget.insert(0, valeur)

        # Statut
        statut_widget = self._entries.get("statut")
        if statut_widget and isinstance(statut_widget, ctk.CTkOptionMenu):
            statut_val = m.get("statut", "")
            if statut_val in get_statuts_disponibles():
                statut_widget.set(statut_val)

        # Date d'adhésion
        date_widget = self._entries.get("date_adhesion")
        date_val = m.get("date_adhesion", "") or ""
        if date_val and date_widget is not None:
            try:
                from tkcalendar import DateEntry

                if isinstance(date_widget, DateEntry):
                    date_widget.set_date(date_val)
                else:
                    if isinstance(date_widget, ctk.CTkEntry):
                        date_widget.delete(0, "end")
                        date_widget.insert(0, date_val)
            except ImportError:
                if isinstance(date_widget, ctk.CTkEntry):
                    date_widget.delete(0, "end")
                    date_widget.insert(0, date_val)

    # ── Soumission ────────────────────────────────────────────────────────────

    def _lire_valeur(self, champ_id: str) -> str:
        widget = self._entries.get(champ_id)
        if widget is None:
            return ""
        if isinstance(widget, ctk.CTkTextbox):
            return widget.get("1.0", "end").strip()
        if isinstance(widget, ctk.CTkOptionMenu):
            return widget.get()
        try:
            from tkcalendar import DateEntry

            if isinstance(widget, DateEntry):
                return widget.get_date().strftime("%Y-%m-%d")
        except ImportError:
            pass
        if isinstance(widget, ctk.CTkEntry):
            return widget.get().strip()
        return ""

    def _effacer_erreurs(self) -> None:
        for label in self._error_labels.values():
            label.configure(text="")

    def _cotisation_courante(self) -> dict | None:
        if not self._est_edition:
            return None
        adherent_id = int(self._membre.get("id") or 0)
        if adherent_id <= 0:
            return None
        annee = get_annee_courante()
        cotisations = get_cotisations_adherent(adherent_id)
        return next((c for c in cotisations if int(c.get("annee") or 0) == annee), None)

    def _sauver_cotisation_rapide(self, adherent_id: int, cotisation: dict) -> bool:
        cotisation_existante = None
        if (
            self._cotisation_rapide_initiale
            and int(self._cotisation_rapide_initiale.get("adherent_id") or adherent_id)
            == adherent_id
            and int(self._cotisation_rapide_initiale.get("annee") or 0)
            == int(cotisation["annee"])
        ):
            cotisation_existante = self._cotisation_rapide_initiale
        if cotisation_existante is None:
            cotisations = get_cotisations_adherent(adherent_id)
            cotisation_existante = next(
                (c for c in cotisations if int(c.get("annee") or 0) == int(cotisation["annee"])),
                None,
            )
        if cotisation_existante:
            ok = update_cotisation(
                cotisation_existante["id"],
                annee=cotisation["annee"],
                montant=cotisation["montant"],
                statut=cotisation["statut"],
            )
            if ok:
                self._cotisation_rapide_initiale = {
                    **cotisation_existante,
                    "adherent_id": adherent_id,
                    **cotisation,
                }
                return True
            self._error_labels["cotisation_rapide"].configure(
                text="Impossible de mettre à jour la cotisation rapide."
            )
            return False
        cotisation_id = add_cotisation(
            adherent_id=adherent_id,
            annee=cotisation["annee"],
            montant=cotisation["montant"],
            statut=cotisation["statut"],
        )
        if isinstance(cotisation_id, int) and cotisation_id > 0:
            self._cotisation_rapide_initiale = {
                "id": cotisation_id,
                "adherent_id": adherent_id,
                **cotisation,
            }
            return True
        self._error_labels["cotisation_rapide"].configure(
            text="Impossible d'ajouter la cotisation rapide."
        )
        return False

    def _soumettre(self) -> None:
        self._effacer_erreurs()

        nom = self._lire_valeur("nom")
        prenom = self._lire_valeur("prenom")
        email = self._lire_valeur("email")
        telephone = self._lire_valeur("telephone")
        statut = self._lire_valeur("statut")
        date_adhesion = self._lire_valeur("date_adhesion")
        commentaire = self._lire_valeur("commentaire")

        erreurs = valider_membre(nom, prenom, email, telephone, statut, date_adhesion)

        if erreurs:
            for champ, message in erreurs:
                if champ in self._error_labels:
                    self._error_labels[champ].configure(text=message)
            return
        cotisation_rapide = None
        if self._cotisation_rapide.cotisation_active():
            cotisation_rapide, erreur_cotisation = self._cotisation_rapide.lire_saisie()
            if erreur_cotisation:
                self._error_labels["cotisation_rapide"].configure(text=erreur_cotisation)
                return

        adherent_id: int | None = None
        try:
            if self._est_edition:
                adherent_id = int(self._membre["id"])
                ok = update_membre(
                    adherent_id,
                    nom,
                    prenom,
                    email,
                    telephone,
                    statut,
                    date_adhesion,
                    commentaire,
                )
                if not ok:
                    self._error_labels["nom"].configure(
                        text="Impossible de mettre à jour ce membre."
                    )
                    return
                logger.info("Membre modifié : id=%s", adherent_id)
            else:
                adherent_id = add_membre(
                    nom, prenom, email, telephone, statut, date_adhesion, commentaire
                )
                if not isinstance(adherent_id, int) or adherent_id <= 0:
                    self._error_labels["nom"].configure(
                        text="Impossible d'ajouter ce membre."
                    )
                    return
                self._membre = {
                    "id": adherent_id,
                    "nom": nom,
                    "prenom": prenom,
                    "email": email,
                    "telephone": telephone,
                    "statut": statut,
                    "date_adhesion": date_adhesion,
                    "commentaire": commentaire,
                }
                self._est_edition = True
                logger.info("Membre ajouté : id=%s", adherent_id)
        except Exception as exc:
            logger.exception("Erreur lors de la sauvegarde du membre : %s", exc)
            self._error_labels["nom"].configure(text=f"Erreur : {exc}")
            return

        if cotisation_rapide and adherent_id and not self._sauver_cotisation_rapide(
            adherent_id, cotisation_rapide
        ):
            logger.warning(
                "Membre enregistré sans cotisation rapide (adherent_id=%s)", adherent_id
            )
            return

        self.destroy()
