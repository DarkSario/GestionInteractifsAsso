"""Onglet Opérations du module Trésorerie."""

from __future__ import annotations

from datetime import datetime
try:
    from tkinter import ttk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class ttk:  # type: ignore[override]
        Treeview = Scrollbar = object
from typing import Any

try:
    import customtkinter as ctk
except ModuleNotFoundError:  # pragma: no cover - environnement sans Tk
    class _DummyVar:
        def __init__(self, value=None):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    class _DummyWidget:
        def __init__(self, *_args, **_kwargs):
            pass

        def pack(self, *_args, **_kwargs):
            pass

        def pack_forget(self, *_args, **_kwargs):
            pass

        def pack_propagate(self, *_args, **_kwargs):
            pass

        def configure(self, *_args, **_kwargs):
            pass

        def winfo_manager(self):
            return ""

    class _DummyCTk:
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkOptionMenu = CTkSegmentedButton = CTkBaseClass = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from core.tresorerie import formater_montant
from db.models.tresorerie import (
    add_operation,
    get_all_categories,
    get_all_comptes,
    get_operations,
    get_stats_tresorerie,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


COULEURS = {
    "recette": "#2e7d32",
    "depense": "#b71c1c",
    "virement_interne": "#1565c0",
}
_MOYENS_PAIEMENT = {
    "Espèces": "especes",
    "Chèque": "cheque",
    "Virement": "virement",
    "Carte": "carte",
    "SumUp": "sumup",
    "Autre": "autre",
}
_STATUTS = {
    "En attente": "en_attente",
    "Payé": "valide",
    "Annulé": "annule",
}


def _periode_contient_cloture() -> bool:
    """Retourne True si des opérations rapprochées signalent une période clôturée."""
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS nb FROM tresorerie_operations WHERE statut = 'rapproche'"
            ).fetchone()
        finally:
            conn.close()
        return (row["nb"] if row else 0) > 0
    except Exception:
        return False


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _normaliser_date(value: str | None) -> str:
    brut = (value or "").strip()
    if not brut:
        return datetime.now().strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(brut, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return brut


def _label_statut(statut: str | None) -> str:
    for label, code in _STATUTS.items():
        if code == statut:
            return label
    return statut or ""


def _libelle_montant_operation(operation: dict[str, Any]) -> str:
    montant = float(operation.get("montant") or 0)
    type_op = operation.get("type_operation")
    signe = (
        "+"
        if type_op == "recette"
        or (type_op == "virement_interne" and operation.get("source_module") == "virement_entrant")
        else "-"
    )
    return f"{signe}{formater_montant(montant)}"


def enregistrer_operation_depuis_formulaire(formulaire: dict[str, Any]) -> int:
    comptes = get_all_comptes(actif_only=True)
    if not comptes:
        raise ValueError("Aucun compte actif disponible.")

    type_operation = str(formulaire.get("type_operation") or "depense").strip().lower()
    categories = get_all_categories(type_operation)
    categorie_id = formulaire.get("categorie_id")
    if categorie_id is None:
        categorie_nom = str(formulaire.get("categorie") or "").strip().lower()
        categorie = next((c for c in categories if str(c.get("nom") or "").strip().lower() == categorie_nom), None)
        categorie_id = int(categorie["id"]) if categorie else (int(categories[0]["id"]) if categories else None)

    compte_id = int(formulaire.get("compte_id") or comptes[0]["id"])
    return add_operation(
        compte_id=compte_id,
        type_operation=type_operation,
        libelle=str(formulaire.get("libelle") or "").strip(),
        montant=_parse_float(formulaire.get("montant")),
        date_operation=_normaliser_date(str(formulaire.get("date_operation") or "")),
        categorie_id=categorie_id,
        mode_paiement=str(formulaire.get("mode_paiement") or "autre").strip().lower() or "autre",
        numero_facture=None,
        evenement_id=None,
        fournisseur_id=None,
        statut=str(formulaire.get("statut") or "valide").strip().lower() or "valide",
        est_automatique=0,
        source_module="manuel",
        source_id=None,
        commentaire=(str(formulaire.get("commentaire") or "").strip() or None),
    )


class _OperationsTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._root = root
        self._comptes = get_all_comptes(actif_only=True)
        self._categories: list[dict[str, Any]] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(header, text="📋 Opérations", font=fonts.get("subtitle")).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Recette",
            width=110,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=lambda: self._ouvrir_formulaire("recette"),
        ).pack(side="right")
        ctk.CTkButton(
            header,
            text="+ Dépense",
            width=110,
            command=lambda: self._ouvrir_formulaire("depense"),
        ).pack(side="right", padx=(0, 8))

        if _periode_contient_cloture():
            bandeau = ctk.CTkFrame(self, fg_color="#fff3e0", corner_radius=6)
            bandeau.pack(fill="x", padx=12, pady=(0, 4))
            ctk.CTkLabel(
                bandeau,
                text="🔒 Période clôturée — Les opérations affichées sont en lecture seule",
                font=fonts.get("bold"),
                text_color="#e65100",
            ).pack(padx=12, pady=6)

        contenu = ctk.CTkFrame(self, fg_color="transparent")
        contenu.pack(fill="both", expand=True, padx=12, pady=6)

        self._frame_liste = ctk.CTkFrame(contenu)
        self._frame_liste.pack(side="left", fill="both", expand=True)
        self._frame_formulaire = ctk.CTkFrame(contenu, width=360)
        self._frame_formulaire.pack_propagate(False)

        self._tree = ttk.Treeview(
            self._frame_liste,
            columns=("date", "libelle", "categorie", "montant", "statut"),
            show="headings",
            height=14,
        )
        for col, label, width, anchor in [
            ("date", "Date", 110, "center"),
            ("libelle", "Libellé", 280, "w"),
            ("categorie", "Catégorie", 150, "w"),
            ("montant", "Montant", 120, "e"),
            ("statut", "Statut", 110, "center"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)
        for key, color in COULEURS.items():
            self._tree.tag_configure(key, foreground=color)

        scrollbar = ttk.Scrollbar(self._frame_liste, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._lbl_stats = ctk.CTkLabel(self, text="")
        self._lbl_stats.pack(anchor="w", padx=12, pady=(0, 10))

        self._build_formulaire()

    def _build_formulaire(self) -> None:
        self._var_type = ctk.StringVar(value="depense")
        self._var_libelle = ctk.StringVar()
        self._var_montant = ctk.StringVar(value="0,00")
        self._var_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._var_categorie = ctk.StringVar(value="")
        self._var_moyen = ctk.StringVar(value="Virement")
        self._var_statut = ctk.StringVar(value="Payé")
        self._var_compte = ctk.StringVar(value=self._comptes[0]["nom"] if self._comptes else "")
        self._var_commentaire = ctk.StringVar()

        ctk.CTkLabel(
            self._frame_formulaire,
            text="💸 Nouvelle opération",
            font=app_theme.FONTS.get("subtitle"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        bloc_type = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
        bloc_type.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(bloc_type, text="Type").pack(anchor="w")
        ctk.CTkSegmentedButton(
            bloc_type,
            values=["depense", "recette"],
            variable=self._var_type,
            command=lambda _value: self._refresh_categories(),
        ).pack(fill="x", pady=(4, 0))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Libellé", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_libelle))
        champ("Montant (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_montant))
        champ("Date", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_date))
        self._menu_categorie = ctk.CTkOptionMenu(self._frame_formulaire, values=[""], variable=self._var_categorie)
        champ("Catégorie", self._menu_categorie)
        champ(
            "Moyen de paiement",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=list(_MOYENS_PAIEMENT),
                variable=self._var_moyen,
            ),
        )
        champ(
            "Statut",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=list(_STATUTS),
                variable=self._var_statut,
            ),
        )
        champ(
            "Compte",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=[c["nom"] for c in self._comptes] or [""],
                variable=self._var_compte,
            ),
        )
        champ("Commentaire", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_commentaire))

        actions = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(16, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer).pack(side="right")

        self._refresh_categories()

    def _refresh_categories(self) -> None:
        self._categories = get_all_categories(self._var_type.get())
        noms = [c.get("nom") or "" for c in self._categories] or [""]
        self._menu_categorie.configure(values=noms)
        self._var_categorie.set(noms[0])

    def _ouvrir_formulaire(self, type_operation: str) -> None:
        if not self._comptes:
            afficher_info(self, "Opérations", "Créez d'abord un compte actif.")
            return
        self._var_type.set(type_operation)
        self._var_libelle.set("Recette" if type_operation == "recette" else "Dépense")
        self._var_montant.set("0,00")
        self._var_date.set(datetime.now().strftime("%Y-%m-%d"))
        self._var_moyen.set("Virement")
        self._var_statut.set("Payé")
        self._var_compte.set(self._comptes[0]["nom"])
        self._var_commentaire.set("")
        self._refresh_categories()
        if not self._frame_formulaire.winfo_manager():
            self._frame_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire(self) -> None:
        self._frame_formulaire.pack_forget()

    def _enregistrer(self) -> None:
        try:
            enregistrer_operation_depuis_formulaire(
                {
                    "type_operation": self._var_type.get(),
                    "libelle": self._var_libelle.get(),
                    "montant": self._var_montant.get(),
                    "date_operation": self._var_date.get(),
                    "categorie": self._var_categorie.get(),
                    "mode_paiement": _MOYENS_PAIEMENT.get(self._var_moyen.get(), "autre"),
                    "statut": _STATUTS.get(self._var_statut.get(), "valide"),
                    "compte_id": next(
                        (int(c["id"]) for c in self._comptes if c["nom"] == self._var_compte.get()),
                        None,
                    ),
                    "commentaire": self._var_commentaire.get(),
                }
            )
        except ValueError as exc:
            afficher_erreur(self, "Opérations", str(exc))
            return
        self.refresh()
        self._fermer_formulaire()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        operations = get_operations()
        for operation in operations:
            type_op = operation.get("type_operation")
            self._tree.insert(
                "",
                "end",
                iid=str(operation.get("id") or ""),
                values=(
                    operation.get("date_operation") or "",
                    operation.get("libelle") or "",
                    operation.get("categorie_nom") or "—",
                    _libelle_montant_operation(operation),
                    _label_statut(operation.get("statut")),
                ),
                tags=(type_op,),
            )

        stats = get_stats_tresorerie()
        self._lbl_stats.configure(
            text=(
                f"Recettes : +{formater_montant(stats['total_recettes'])}  |  "
                f"Dépenses : -{formater_montant(stats['total_depenses'])}  |  "
                f"Solde période : {formater_montant(stats['solde'])}"
            ),
            font=app_theme.FONTS.get("bold"),
        )


def build_tab_operations(parent: ctk.CTkFrame, root: Any) -> None:
    for widget in parent.winfo_children():
        widget.destroy()
    tab = _OperationsTab(parent, root)
    tab.pack(fill="both", expand=True)
