"""Formulaire modal d'ajout et de modification d'un article du stock."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from core.stock import valider_article
from db.models.categories import get_all_categories
from db.models.fournisseurs import (
    add_fournisseur,
    get_fournisseurs_for_select,
    search_or_create_fournisseur,
)
from db.models.stock import add_article, add_mouvement, update_article
from db.models.unites import get_all_unites
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur
from utils.logger import get_logger

logger = get_logger(__name__)


class FormulaireArticle(ctk.CTkToplevel):
    """Fenêtre modale de saisie d'un article (création ou modification)."""

    def __init__(self, parent: Any, article: dict | None = None) -> None:
        super().__init__(parent)
        self._article = article
        self._est_edition = article is not None

        if self._est_edition:
            self.title(f"Modifier — {article.get('nom', '')}")
        else:
            self.title("Ajouter un article")

        self.resizable(False, False)
        self.transient(parent)

        # Données des listes déroulantes
        self._categories: list[dict] = []
        self._unites: list[dict] = []
        self._fournisseurs: list[dict] = []

        self._categorie_var = ctk.StringVar()
        self._unite_var = ctk.StringVar()
        self._fournisseur_var = ctk.StringVar()

        self._charger_referentiels()
        self._build_ui()

        if self._est_edition:
            self._preremplir()

    # ── Chargement des référentiels ───────────────────────────────────────────

    def _charger_referentiels(self) -> None:
        try:
            self._categories = get_all_categories()
        except Exception:
            self._categories = []
        try:
            self._unites = get_all_unites()
        except Exception:
            self._unites = []
        try:
            self._fournisseurs = get_fournisseurs_for_select()
        except Exception:
            self._fournisseurs = []

    def _get_cat_labels(self) -> list[str]:
        labels = []
        for c in self._categories:
            if c.get("parent_nom"):
                labels.append(f"{c['parent_nom']} > {c['nom']}")
            else:
                labels.append(c["nom"])
        return labels

    def _get_unite_labels(self) -> list[str]:
        return [u["nom"] for u in self._unites]

    def _get_fourn_labels(self) -> list[str]:
        return ["— Aucun —"] + [f["nom"] for f in self._fournisseurs]

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=25, pady=20)

        titre = "Modifier l'article" if self._est_edition else "Ajouter un article"
        ctk.CTkLabel(
            frame, text=titre, font=fonts.get("subtitle")
        ).grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky="w")

        self._error_labels: dict[str, ctk.CTkLabel] = {}
        row = 1

        # Nom
        ctk.CTkLabel(frame, text="Nom *", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_nom = ctk.CTkEntry(frame, width=340, font=fonts.get("normal"))
        self._entry_nom.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        self._error_labels["nom"] = self._make_error_label(frame, row)
        row += 1

        # Catégorie
        cat_labels = self._get_cat_labels()
        ctk.CTkLabel(frame, text="Catégorie *", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._combo_categorie = ctk.CTkOptionMenu(
            frame,
            values=cat_labels if cat_labels else ["— Aucune —"],
            variable=self._categorie_var,
            width=340,
            font=fonts.get("normal"),
        )
        if cat_labels:
            self._categorie_var.set(cat_labels[0])
        self._combo_categorie.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        self._error_labels["categorie_id"] = self._make_error_label(frame, row)
        row += 1

        # Unité
        unite_labels = self._get_unite_labels()
        ctk.CTkLabel(frame, text="Unité *", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._combo_unite = ctk.CTkOptionMenu(
            frame,
            values=unite_labels if unite_labels else ["— Aucune —"],
            variable=self._unite_var,
            width=340,
            font=fonts.get("normal"),
        )
        if unite_labels:
            self._unite_var.set(unite_labels[0])
        self._combo_unite.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        self._error_labels["unite_id"] = self._make_error_label(frame, row)
        row += 1

        # Fournisseur habituel + bouton ajouter
        fourn_labels = self._get_fourn_labels()
        ctk.CTkLabel(frame, text="Fournisseur habituel", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._combo_fournisseur = ctk.CTkOptionMenu(
            frame,
            values=fourn_labels,
            variable=self._fournisseur_var,
            width=290,
            font=fonts.get("normal"),
        )
        self._fournisseur_var.set(fourn_labels[0])
        self._combo_fournisseur.grid(row=row, column=1, sticky="ew", pady=(8, 0))
        ctk.CTkButton(
            frame,
            text="➕",
            width=40,
            font=fonts.get("normal"),
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ajouter_fournisseur_rapide,
        ).grid(row=row, column=2, sticky="w", padx=(5, 0), pady=(8, 0))
        row += 1
        row += 1  # pas d'erreur pour fournisseur

        # Quantité initiale (seulement en création)
        if not self._est_edition:
            ctk.CTkLabel(frame, text="Quantité initiale *", font=fonts.get("normal"), anchor="w", width=160).grid(
                row=row, column=0, sticky="nw", pady=(8, 0)
            )
            self._entry_quantite = ctk.CTkEntry(frame, width=120, font=fonts.get("normal"))
            self._entry_quantite.insert(0, "0")
            self._entry_quantite.grid(row=row, column=1, sticky="w", pady=(8, 0))
            row += 1
            self._error_labels["quantite"] = self._make_error_label(frame, row)
            row += 1

        # Seuil d'alerte
        ctk.CTkLabel(frame, text="Seuil d'alerte", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_seuil = ctk.CTkEntry(frame, width=120, font=fonts.get("normal"))
        self._entry_seuil.insert(0, "0")
        self._entry_seuil.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1
        self._error_labels["seuil_alerte"] = self._make_error_label(frame, row)
        row += 1

        # Prix d'achat
        ctk.CTkLabel(frame, text="Prix d'achat (€)", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_prix = ctk.CTkEntry(frame, width=120, font=fonts.get("normal"))
        self._entry_prix.insert(0, "0.00")
        self._entry_prix.grid(row=row, column=1, sticky="w", pady=(8, 0))
        row += 1
        self._error_labels["prix_achat"] = self._make_error_label(frame, row)
        row += 1

        # Numéro de lot
        ctk.CTkLabel(frame, text="Numéro de lot", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_lot = ctk.CTkEntry(frame, width=340, font=fonts.get("normal"))
        self._entry_lot.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        row += 1

        # Commentaire
        ctk.CTkLabel(frame, text="Commentaire", font=fonts.get("normal"), anchor="w", width=160).grid(
            row=row, column=0, sticky="nw", pady=(8, 0)
        )
        self._entry_commentaire = ctk.CTkTextbox(frame, width=340, height=70, font=fonts.get("normal"))
        self._entry_commentaire.grid(row=row, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        row += 1
        row += 1

        # Boutons
        frame_btn = ctk.CTkFrame(frame, fg_color="transparent")
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

    def _make_error_label(self, parent: ctk.CTkFrame, row: int) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            parent,
            text="",
            font=app_theme.FONTS.get("small"),
            text_color="#e05050",
            anchor="w",
        )
        label.grid(row=row, column=1, columnspan=2, sticky="w")
        return label

    # ── Préremplissage ────────────────────────────────────────────────────────

    def _preremplir(self) -> None:
        a = self._article

        self._entry_nom.delete(0, "end")
        self._entry_nom.insert(0, a.get("nom", ""))

        # Catégorie
        cat_labels = self._get_cat_labels()
        cat_nom = a.get("categorie_nom", "")
        parent_nom = None
        for c in self._categories:
            if c["id"] == a.get("categorie_id"):
                parent_nom = c.get("parent_nom")
                cat_nom = c["nom"]
                break
        if parent_nom:
            label_cat = f"{parent_nom} > {cat_nom}"
        else:
            label_cat = cat_nom
        if label_cat in cat_labels:
            self._categorie_var.set(label_cat)

        # Unité
        unite_nom = a.get("unite_nom", "")
        unite_labels = self._get_unite_labels()
        if unite_nom in unite_labels:
            self._unite_var.set(unite_nom)

        # Fournisseur
        fourn_nom = a.get("fournisseur_nom", "")
        fourn_labels = self._get_fourn_labels()
        if fourn_nom and fourn_nom in fourn_labels:
            self._fournisseur_var.set(fourn_nom)

        # Seuil / prix
        self._entry_seuil.delete(0, "end")
        self._entry_seuil.insert(0, str(a.get("seuil_alerte", 0)))

        self._entry_prix.delete(0, "end")
        self._entry_prix.insert(0, str(a.get("prix_achat", 0.0)))

        # Lot
        self._entry_lot.delete(0, "end")
        self._entry_lot.insert(0, a.get("lot", "") or "")

        # Commentaire
        self._entry_commentaire.delete("1.0", "end")
        self._entry_commentaire.insert("1.0", a.get("commentaire", "") or "")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _ajouter_fournisseur_rapide(self) -> None:
        from ui.modules.stock.referentiels import _DialogFournisseur

        def _sauver(nom, telephone, email, commentaire):
            try:
                new_id = add_fournisseur(nom, telephone, email, commentaire)
                self._fournisseurs = get_fournisseurs_for_select()
                fourn_labels = self._get_fourn_labels()
                self._combo_fournisseur.configure(values=fourn_labels)
                self._fournisseur_var.set(nom)
                logger.info("Fournisseur ajouté depuis formulaire article : id=%s", new_id)
            except Exception as exc:
                afficher_erreur(self, "Erreur", str(exc))

        _DialogFournisseur(self, fournisseur=None, on_valider=_sauver)

    def _effacer_erreurs(self) -> None:
        for label in self._error_labels.values():
            label.configure(text="")

    def _get_categorie_id(self) -> int | None:
        label = self._categorie_var.get()
        for c in self._categories:
            parent_nom = c.get("parent_nom")
            if parent_nom:
                full = f"{parent_nom} > {c['nom']}"
            else:
                full = c["nom"]
            if full == label:
                return c["id"]
        return None

    def _get_unite_id(self) -> int | None:
        nom = self._unite_var.get()
        for u in self._unites:
            if u["nom"] == nom:
                return u["id"]
        return None

    def _get_fournisseur_id(self) -> int | None:
        nom = self._fournisseur_var.get()
        if nom == "— Aucun —":
            return None
        for f in self._fournisseurs:
            if f["nom"] == nom:
                return f["id"]
        return None

    def _soumettre(self) -> None:
        self._effacer_erreurs()

        nom = self._entry_nom.get().strip()
        categorie_id = self._get_categorie_id()
        unite_id = self._get_unite_id()
        fournisseur_id = self._get_fournisseur_id()
        quantite_str = self._entry_quantite.get().strip() if not self._est_edition else "0"
        seuil_str = self._entry_seuil.get().strip()
        prix_str = self._entry_prix.get().strip()
        lot = self._entry_lot.get().strip()
        commentaire = self._entry_commentaire.get("1.0", "end").strip()

        erreurs = valider_article(nom, categorie_id, unite_id, quantite_str, seuil_str, prix_str)

        if erreurs:
            for champ, message in erreurs:
                if champ in self._error_labels:
                    self._error_labels[champ].configure(text=message)
            return

        try:
            quantite = int(quantite_str) if quantite_str else 0
            seuil = int(seuil_str) if seuil_str else 0
            prix = float(prix_str.replace(",", ".")) if prix_str else 0.0

            if self._est_edition:
                update_article(
                    self._article["id"],
                    nom,
                    categorie_id,
                    unite_id,
                    fournisseur_id,
                    seuil,
                    prix,
                    lot or None,
                    commentaire or None,
                )
            else:
                article_id = add_article(
                    nom,
                    categorie_id,
                    unite_id,
                    fournisseur_id,
                    quantite,
                    seuil,
                    prix,
                    lot or None,
                    commentaire or None,
                )
                # Créer un mouvement initial si quantité > 0
                if quantite > 0:
                    from core.stock import TYPES_MOUVEMENTS
                    from datetime import date
                    add_mouvement(
                        stock_id=article_id,
                        date=date.today().strftime("%Y-%m-%d"),
                        type_mouvement=TYPES_MOUVEMENTS[0],  # "Entrée — Achat"
                        quantite=quantite,
                        prix_unitaire=prix if prix > 0 else None,
                        fournisseur_id=fournisseur_id,
                        evenement_id=None,
                        numero_facture=None,
                        commentaire="Stock initial",
                    )
        except Exception as exc:
            logger.exception("Erreur lors de la sauvegarde de l'article : %s", exc)
            afficher_erreur(self, "Erreur", f"Impossible d'enregistrer l'article.\n{exc}")
            return

        self.destroy()
