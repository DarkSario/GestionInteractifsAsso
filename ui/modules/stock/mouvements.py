"""Fenêtre des mouvements de stock pour un article."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from core.stock import (
    get_types_mouvements,
    is_type_achat,
    is_type_sortie_utilisation,
    valider_mouvement,
)
from db.models.fournisseurs import add_fournisseur, get_fournisseurs_for_select
from db.models.stock import (
    add_mouvement,
    delete_mouvement,
    get_article_by_id,
    get_mouvements_by_article,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, demander_confirmation
from utils.logger import get_logger

logger = get_logger(__name__)


class MouvementsStock(ctk.CTkToplevel):
    """Fenêtre d'historique et de saisie des mouvements d'un article."""

    def __init__(self, parent: Any, article: dict) -> None:
        super().__init__(parent)
        self._article = article
        self.title(f"📋 Mouvements — {article.get('nom', '')}")
        self.geometry("900x600")
        self.minsize(750, 450)
        self.transient(parent)

        self._mouvements: list[dict] = []
        self._build_ui()
        self._charger_mouvements()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        # En-tête
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            frame_header,
            text=f"📋 Mouvements — {self._article.get('nom', '')}",
            font=fonts.get("title"),
        ).pack(side="left")

        ctk.CTkButton(
            frame_header,
            text="+ Mouvement",
            width=130,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire_mouvement,
        ).pack(side="right")

        # Infos stock
        self._label_stock = ctk.CTkLabel(
            self,
            text="",
            font=fonts.get("normal"),
            anchor="w",
        )
        self._label_stock.pack(fill="x", padx=15, pady=(0, 5))

        # Tableau des mouvements
        frame_table = ctk.CTkFrame(self)
        frame_table.pack(fill="both", expand=True, padx=15, pady=5)

        self._tree = self._build_treeview(frame_table)

        # Actions
        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            frame_actions,
            text="🗑️ Supprimer",
            width=120,
            font=fonts.get("normal"),
            fg_color="#8b1a1a",
            hover_color="#6b1414",
            command=self._supprimer_mouvement,
        ).pack(side="left", padx=5)

    def _build_treeview(self, parent: ctk.CTkFrame) -> ttk.Treeview:
        columns = ("id", "date", "type", "quantite", "fournisseur", "evenement", "facture")

        style = ttk.Style()
        appearance = ctk.get_appearance_mode()
        bg = "#2b2b2b" if appearance == "Dark" else "#f0f0f0"
        fg = "#ffffff" if appearance == "Dark" else "#000000"
        heading_bg = "#1a1a2e" if appearance == "Dark" else "#d0d0d0"

        style.theme_use("default")
        style.configure(
            "Mouvements.Treeview",
            background=bg,
            foreground=fg,
            rowheight=28,
            fieldbackground=bg,
            font=("Arial", 12),
        )
        style.configure(
            "Mouvements.Treeview.Heading",
            background=heading_bg,
            foreground=fg,
            font=("Arial", 12, "bold"),
        )
        style.map(
            "Mouvements.Treeview",
            background=[("selected", "#1f6aa5")],
            foreground=[("selected", "#ffffff")],
        )

        frame_tree = tk.Frame(parent, bg=bg)
        frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(
            frame_tree,
            columns=columns,
            show="headings",
            style="Mouvements.Treeview",
            selectmode="browse",
        )

        tree.heading("id", text="ID")
        tree.heading("date", text="Date")
        tree.heading("type", text="Type")
        tree.heading("quantite", text="Qté")
        tree.heading("fournisseur", text="Fournisseur")
        tree.heading("evenement", text="Événement")
        tree.heading("facture", text="N° Facture")

        tree.column("id", width=50, anchor="center", stretch=False)
        tree.column("date", width=100, anchor="center")
        tree.column("type", width=200)
        tree.column("quantite", width=70, anchor="center")
        tree.column("fournisseur", width=150)
        tree.column("evenement", width=150)
        tree.column("facture", width=120)

        scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        return tree

    # ── Chargement ────────────────────────────────────────────────────────────

    def _charger_mouvements(self) -> None:
        try:
            article = get_article_by_id(self._article["id"])
            if article:
                self._article = article
            self._mouvements = get_mouvements_by_article(self._article["id"])
        except Exception as exc:
            logger.exception("Erreur chargement mouvements : %s", exc)
            self._mouvements = []

        # Mise à jour de l'étiquette de stock
        quantite = self._article.get("quantite", 0)
        unite_nom = self._article.get("unite_nom", "unité(s)")
        self._label_stock.configure(
            text=f"Stock actuel : {quantite} {unite_nom}"
        )

        self._tree.delete(*self._tree.get_children())
        for m in self._mouvements:
            qte = m.get("quantite", 0)
            qte_str = f"+{qte}" if qte > 0 else str(qte)
            self._tree.insert(
                "",
                "end",
                iid=str(m["id"]),
                values=(
                    m["id"],
                    self._formater_date(m.get("date", "")),
                    m.get("type", ""),
                    qte_str,
                    m.get("fournisseur_nom") or "",
                    m.get("evenement_nom") or "",
                    m.get("numero_facture") or "",
                ),
            )

    # ── Actions ───────────────────────────────────────────────────────────────

    def _get_mouvement_selectionne_id(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            return None
        return int(sel[0])

    def _ouvrir_formulaire_mouvement(self) -> None:
        form = _FormulaireMouvement(self, article=self._article)
        form.grab_set()
        self.wait_window(form)
        self._charger_mouvements()

    def _supprimer_mouvement(self) -> None:
        mvt_id = self._get_mouvement_selectionne_id()
        if mvt_id is None:
            return
        if demander_confirmation(
            self,
            "Supprimer le mouvement",
            "Supprimer ce mouvement ? Le stock sera recalculé en conséquence.",
        ):
            try:
                delete_mouvement(mvt_id)
                self._charger_mouvements()
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))

    @staticmethod
    def _formater_date(value: str | None) -> str:
        if not value:
            return ""
        try:
            from datetime import datetime
            return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return value or ""


# ── Formulaire nouveau mouvement ─────────────────────────────────────────────


class _FormulaireMouvement(ctk.CTkToplevel):
    """Dialog de saisie d'un nouveau mouvement."""

    def __init__(self, parent: Any, article: dict) -> None:
        super().__init__(parent)
        self._article = article
        self.title("Nouveau mouvement")
        self.resizable(False, False)
        self.transient(parent)

        self._type_var = ctk.StringVar()
        self._fournisseurs: list[dict] = []

        try:
            self._fournisseurs = get_fournisseurs_for_select()
        except Exception:
            self._fournisseurs = []

        self._build_ui()
        self._on_type_change()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        self._frame = ctk.CTkFrame(self, fg_color="transparent")
        self._frame.pack(fill="both", expand=True, padx=25, pady=20)

        row = 0

        ctk.CTkLabel(
            self._frame, text="Nouveau mouvement", font=fonts.get("subtitle")
        ).grid(row=row, column=0, columnspan=3, pady=(0, 15), sticky="w")
        row += 1

        # Type
        ctk.CTkLabel(self._frame, text="Type *", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        types = get_types_mouvements()
        self._type_var.set(types[0])
        self._combo_type = ctk.CTkOptionMenu(
            self._frame,
            values=types,
            variable=self._type_var,
            width=300,
            font=fonts.get("normal"),
            command=lambda _: self._on_type_change(),
        )
        self._combo_type.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1

        # Date
        ctk.CTkLabel(self._frame, text="Date *", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        try:
            from tkcalendar import DateEntry
            self._date_widget = DateEntry(
                self._frame, width=18, date_pattern="yyyy-mm-dd", font=("Arial", 12)
            )
            self._date_widget.set_date(date.today())
            self._date_widget.grid(row=row, column=1, sticky="w", pady=(8, 0))
            self._use_date_entry = True
        except ImportError:
            self._date_widget = ctk.CTkEntry(
                self._frame, width=180, font=fonts.get("normal"), placeholder_text="AAAA-MM-JJ"
            )
            self._date_widget.insert(0, date.today().strftime("%Y-%m-%d"))
            self._date_widget.grid(row=row, column=1, sticky="w", pady=(8, 0))
            self._use_date_entry = False
        row += 1
        self._err_date = self._make_err(row)
        row += 1

        # Quantité
        ctk.CTkLabel(self._frame, text="Quantité *", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_qte = ctk.CTkEntry(self._frame, width=120, font=fonts.get("normal"))
        self._entry_qte.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1
        self._err_qte = self._make_err(row)
        row += 1

        # Prix unitaire (achat seulement)
        self._row_prix = row
        ctk.CTkLabel(self._frame, text="Prix unitaire (€)", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_prix = ctk.CTkEntry(self._frame, width=120, font=fonts.get("normal"))
        self._entry_prix.insert(0, "0.00")
        self._entry_prix.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1
        self._err_prix = self._make_err(row)
        row += 1

        # Fournisseur (achat seulement)
        self._row_fourn = row
        fourn_labels = ["— Aucun —"] + [f["nom"] for f in self._fournisseurs]
        self._fourn_var = ctk.StringVar(value=fourn_labels[0])
        ctk.CTkLabel(self._frame, text="Fournisseur", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._combo_fourn = ctk.CTkOptionMenu(
            self._frame,
            values=fourn_labels,
            variable=self._fourn_var,
            width=260,
            font=fonts.get("normal"),
        )
        self._combo_fourn.grid(row=row, column=1, sticky="w", pady=(8, 0))
        ctk.CTkButton(
            self._frame,
            text="➕",
            width=40,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_fournisseur_rapide,
        ).grid(row=row, column=2, sticky="w", padx=(5, 0), pady=(8, 0))
        row += 1
        row += 1

        # N° Facture (achat seulement)
        self._row_facture = row
        ctk.CTkLabel(self._frame, text="N° Facture", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_facture = ctk.CTkEntry(self._frame, width=200, font=fonts.get("normal"))
        self._entry_facture.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1
        row += 1

        # Événement lié (sortie utilisation seulement)
        self._row_event = row
        self._evenements: list[dict] = []
        try:
            from db.connection import get_connection
            conn = get_connection()
            try:
                rows = conn.execute("SELECT id, nom FROM evenements ORDER BY nom ASC").fetchall()
                self._evenements = [dict(r) for r in rows]
            finally:
                conn.close()
        except Exception:
            self._evenements = []

        self._event_var = ctk.StringVar(value="— Aucun —")
        event_labels = ["— Aucun —"] + [e["nom"] for e in self._evenements]
        ctk.CTkLabel(self._frame, text="Événement lié", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._combo_event = ctk.CTkOptionMenu(
            self._frame,
            values=event_labels,
            variable=self._event_var,
            width=300,
            font=fonts.get("normal"),
        )
        self._combo_event.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        row += 1

        # Commentaire
        ctk.CTkLabel(self._frame, text="Commentaire", font=fonts.get("normal"), anchor="w", width=150).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_commentaire = ctk.CTkTextbox(self._frame, width=300, height=60, font=fonts.get("normal"))
        self._entry_commentaire.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        row += 1

        # Boutons
        frame_btn = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame_btn.grid(row=row, column=0, columnspan=3, pady=(15, 0))

        ctk.CTkButton(
            frame_btn,
            text="Enregistrer",
            width=130,
            font=fonts.get("bold"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._soumettre,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            frame_btn,
            text="Annuler",
            width=100,
            font=fonts.get("normal"),
            fg_color="gray",
            hover_color="#555",
            command=self.destroy,
        ).pack(side="left", padx=10)

        self.grab_set()

    def _make_err(self, row: int) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            self._frame,
            text="",
            font=app_theme.FONTS.get("small"),
            text_color="#e05050",
            anchor="w",
        )
        label.grid(row=row, column=1, columnspan=2, sticky="w")
        return label

    def _on_type_change(self) -> None:
        type_mvt = self._type_var.get()
        is_achat = is_type_achat(type_mvt)
        is_sortie_util = is_type_sortie_utilisation(type_mvt)

        # Afficher/masquer les champs achat
        for widget in self._frame.grid_slaves(row=self._row_prix):
            widget.grid_remove() if not is_achat else widget.grid()
        for widget in self._frame.grid_slaves(row=self._row_fourn):
            widget.grid_remove() if not is_achat else widget.grid()
        for widget in self._frame.grid_slaves(row=self._row_facture):
            widget.grid_remove() if not is_achat else widget.grid()

        # Afficher/masquer événement
        for widget in self._frame.grid_slaves(row=self._row_event):
            widget.grid_remove() if not is_sortie_util else widget.grid()

    def _ajouter_fournisseur_rapide(self) -> None:
        from ui.modules.stock.referentiels import _DialogFournisseur

        def _sauver(nom, telephone, email, commentaire):
            try:
                add_fournisseur(nom, telephone, email, commentaire)
                self._fournisseurs = get_fournisseurs_for_select()
                fourn_labels = ["— Aucun —"] + [f["nom"] for f in self._fournisseurs]
                self._combo_fourn.configure(values=fourn_labels)
                self._fourn_var.set(nom)
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))

        _DialogFournisseur(self, fournisseur=None, on_valider=_sauver)

    def _lire_date(self) -> str:
        if self._use_date_entry:
            try:
                return self._date_widget.get_date().strftime("%Y-%m-%d")
            except Exception:
                return ""
        return self._date_widget.get().strip()

    def _get_fournisseur_id(self) -> int | None:
        nom = self._fourn_var.get()
        if nom == "— Aucun —":
            return None
        for f in self._fournisseurs:
            if f["nom"] == nom:
                return f["id"]
        return None

    def _get_evenement_id(self) -> int | None:
        nom = self._event_var.get()
        if nom == "— Aucun —":
            return None
        for e in self._evenements:
            if e["nom"] == nom:
                return e["id"]
        return None

    def _soumettre(self) -> None:
        # Réinitialiser les erreurs
        for lbl in (self._err_date, self._err_qte, self._err_prix):
            lbl.configure(text="")

        type_mvt = self._type_var.get()
        date_str = self._lire_date()
        qte_str = self._entry_qte.get().strip()
        prix_str = self._entry_prix.get().strip()
        facture = self._entry_facture.get().strip()
        commentaire = self._entry_commentaire.get("1.0", "end").strip()
        fourn_id = self._get_fournisseur_id() if is_type_achat(type_mvt) else None
        event_id = self._get_evenement_id() if is_type_sortie_utilisation(type_mvt) else None

        erreurs = valider_mouvement(type_mvt, date_str, qte_str, prix_str)
        if erreurs:
            err_map = {
                "date": self._err_date,
                "quantite": self._err_qte,
                "prix_unitaire": self._err_prix,
            }
            for champ, message in erreurs:
                if champ in err_map:
                    err_map[champ].configure(text=message)
            return

        try:
            quantite = int(qte_str)
            prix = float(prix_str.replace(",", ".")) if prix_str else None

            add_mouvement(
                stock_id=self._article["id"],
                date=date_str,
                type_mouvement=type_mvt,
                quantite=quantite,
                prix_unitaire=prix if is_type_achat(type_mvt) and prix else None,
                fournisseur_id=fourn_id,
                evenement_id=event_id,
                numero_facture=facture or None,
                commentaire=commentaire or None,
            )
        except Exception as exc:
            logger.exception("Erreur lors de l'enregistrement du mouvement : %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer le mouvement.\n{exc}")
            return

        self.destroy()
