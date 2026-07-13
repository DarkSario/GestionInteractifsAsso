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
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkOptionMenu = CTkSegmentedButton = CTkBaseClass = CTkToplevel = CTkScrollableFrame = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from core.tresorerie import formater_montant
from db.models.membres import get_all_membres
from db.models.tresorerie import (
    add_operation,
    delete_operation,
    get_all_categories,
    get_all_comptes,
    get_operation_by_id,
    get_operations,
    get_stats_tresorerie,
    update_operation,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info, demander_confirmation
from ui.components.form_dialog import FormDialog


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




def _normaliser_mode_paiement(value: str | None) -> str:
    brut = str(value or "autre").strip()
    if not brut:
        return "autre"
    for label, code in _MOYENS_PAIEMENT.items():
        if brut.lower() == label.lower() or brut.lower() == code.lower():
            return code
    alias = {
        "cb": "carte",
        "carte bancaire": "carte",
        "espece": "especes",
        "espèce": "especes",
        "espèces": "especes",
    }
    return alias.get(brut.lower(), "autre")

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
        mode_paiement=_normaliser_mode_paiement(formulaire.get("mode_paiement")),
        numero_facture=None,
        evenement_id=None,
        fournisseur_id=None,
        statut=str(formulaire.get("statut") or "valide").strip().lower() or "valide",
        est_automatique=0,
        source_module="manuel",
        source_id=None,
        commentaire=(str(formulaire.get("commentaire") or "").strip() or None),
        avance_par_membre_id=formulaire.get("avance_par_membre_id"),
        remboursement_statut=str(formulaire.get("remboursement_statut") or "non_applicable").strip().lower() or "non_applicable",
    )


class _DialogOperation(FormDialog):
    """Fenêtre popup pour créer ou modifier une opération de trésorerie."""

    def __init__(
        self,
        parent: Any,
        type_operation: str = "depense",
        operation: dict[str, Any] | None = None,
        on_enregistre=None,
    ) -> None:
        super().__init__(
            parent,
            titre="✏️ Modifier l'opération" if operation else "💸 Nouvelle opération",
            largeur=600,
            hauteur=700,
        )

        self._operation = operation
        self._on_enregistre = on_enregistre
        self._comptes = get_all_comptes(actif_only=True)
        self._membres = get_all_membres()
        self._categories: list[dict[str, Any]] = []

        self._var_type = ctk.StringVar(value=type_operation if not operation else operation.get("type_operation", "depense"))
        self._var_libelle = ctk.StringVar()
        self._var_montant = ctk.StringVar(value="0,00")
        self._var_date = ctk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._var_categorie = ctk.StringVar(value="")
        self._var_moyen = ctk.StringVar(value="Virement")
        self._var_statut = ctk.StringVar(value="Payé")
        self._var_compte = ctk.StringVar(value=self._comptes[0]["nom"] if self._comptes else "")
        self._var_commentaire = ctk.StringVar()
        self._var_avance_par = ctk.StringVar(value="— Aucun —")
        self._var_remboursement = ctk.StringVar(value="Non applicable")

        self._build_ui()
        if operation:
            self._pre_remplir(operation)
        else:
            self._refresh_categories()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS

        titre_texte = "✏️ Modifier l'opération" if self._operation else "💸 Nouvelle opération"
        ctk.CTkLabel(self.frame_content, text=titre_texte, font=fonts.get("subtitle")).pack(
            anchor="w", padx=20, pady=(16, 8)
        )

        frame_scroll = ctk.CTkFrame(self.frame_content, fg_color="transparent")
        frame_scroll.pack(fill="both", expand=True, padx=12, pady=4)

        bloc_type = ctk.CTkFrame(frame_scroll, fg_color="transparent")
        bloc_type.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(bloc_type, text="Type").pack(anchor="w")
        ctk.CTkSegmentedButton(
            bloc_type,
            values=["depense", "recette"],
            variable=self._var_type,
            command=lambda _value: self._refresh_categories(),
        ).pack(fill="x", pady=(4, 0))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(frame_scroll, fg_color="transparent")
            bloc.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Libellé", ctk.CTkEntry(frame_scroll, textvariable=self._var_libelle))
        champ("Montant (€)", ctk.CTkEntry(frame_scroll, textvariable=self._var_montant))
        champ("Date", ctk.CTkEntry(frame_scroll, textvariable=self._var_date))
        self._menu_categorie = ctk.CTkOptionMenu(frame_scroll, values=[""], variable=self._var_categorie)
        champ("Catégorie", self._menu_categorie)
        champ(
            "Moyen de paiement",
            ctk.CTkOptionMenu(frame_scroll, values=list(_MOYENS_PAIEMENT), variable=self._var_moyen),
        )
        champ(
            "Statut",
            ctk.CTkOptionMenu(frame_scroll, values=list(_STATUTS), variable=self._var_statut),
        )
        champ(
            "Compte",
            ctk.CTkOptionMenu(
                frame_scroll,
                values=[c["nom"] for c in self._comptes] or [""],
                variable=self._var_compte,
            ),
        )
        membres_values = ["— Aucun —"] + [f"{m['nom']} {m['prenom']}".strip() for m in self._membres]
        champ("Avancé par", ctk.CTkOptionMenu(frame_scroll, values=membres_values, variable=self._var_avance_par))
        champ("Statut remboursement", ctk.CTkOptionMenu(frame_scroll, values=["Non applicable", "En attente"], variable=self._var_remboursement))
        champ("Commentaire", ctk.CTkEntry(frame_scroll, textvariable=self._var_commentaire))

        self._refresh_categories()

    def _refresh_categories(self) -> None:
        self._categories = get_all_categories(self._var_type.get())
        noms = [c.get("nom") or "" for c in self._categories] or [""]
        self._menu_categorie.configure(values=noms)
        self._var_categorie.set(noms[0])

    def _pre_remplir(self, operation: dict[str, Any]) -> None:
        type_op = operation.get("type_operation", "depense")
        self._var_type.set(type_op)
        self._refresh_categories()
        self._var_libelle.set(operation.get("libelle") or "")
        montant = float(operation.get("montant") or 0)
        self._var_montant.set(f"{montant:,.2f}".replace(",", " ").replace(".", ","))
        self._var_date.set(operation.get("date_operation") or datetime.now().strftime("%Y-%m-%d"))
        moyen_code = operation.get("mode_paiement") or "autre"
        moyen_label = next((k for k, v in _MOYENS_PAIEMENT.items() if v == moyen_code), "Virement")
        self._var_moyen.set(moyen_label)
        statut_code = operation.get("statut") or "valide"
        statut_label = next((k for k, v in _STATUTS.items() if v == statut_code), "Payé")
        self._var_statut.set(statut_label)
        compte_nom = operation.get("compte_nom") or (self._comptes[0]["nom"] if self._comptes else "")
        self._var_compte.set(compte_nom)
        self._var_commentaire.set(operation.get("commentaire") or "")
        avance_nom = f"{operation.get('avance_par_nom') or ''} {operation.get('avance_par_prenom') or ''}".strip()
        self._var_avance_par.set(avance_nom or "— Aucun —")
        self._var_remboursement.set("En attente" if operation.get("remboursement_statut") == "en_attente" else "Non applicable")
        cat_nom = operation.get("categorie_nom") or ""
        if cat_nom and cat_nom in [c.get("nom") or "" for c in self._categories]:
            self._var_categorie.set(cat_nom)

    def _enregistrer(self) -> None:
        membre = next(
            (m for m in self._membres if f"{m['nom']} {m['prenom']}".strip() == self._var_avance_par.get()),
            None,
        )
        type_op = self._var_type.get()
        formulaire = {
            "type_operation": type_op,
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
            "avance_par_membre_id": int(membre["id"]) if membre else None,
            "remboursement_statut": "en_attente" if self._var_remboursement.get() == "En attente" and membre else "non_applicable",
        }
        if type_op != "depense":
            formulaire["avance_par_membre_id"] = None
            formulaire["remboursement_statut"] = "non_applicable"

        try:
            if self._operation is not None:
                categories = get_all_categories(formulaire["type_operation"])
                cat_nom = formulaire["categorie"]
                cat = next((c for c in categories if (c.get("nom") or "") == cat_nom), None)
                cat_id = int(cat["id"]) if cat else None
                update_operation(
                    int(self._operation["id"]),
                    type_operation=formulaire["type_operation"],
                    libelle=formulaire["libelle"],
                    montant=_parse_float(formulaire["montant"]),
                    date_operation=_normaliser_date(formulaire["date_operation"]),
                    categorie_id=cat_id,
                    mode_paiement=formulaire["mode_paiement"],
                    statut=formulaire["statut"],
                    compte_id=formulaire["compte_id"],
                    commentaire=formulaire["commentaire"] or None,
                    avance_par_membre_id=formulaire["avance_par_membre_id"],
                    remboursement_statut=formulaire["remboursement_statut"],
                )
            else:
                enregistrer_operation_depuis_formulaire(formulaire)
        except Exception as exc:
            afficher_erreur(self, "Opérations", str(exc))
            return

        if self._on_enregistre:
            self._on_enregistre()
        self.destroy()

    def _on_valider(self) -> None:
        self._enregistrer()


class _OperationsTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._tresorerie_root = root
        self._comptes = get_all_comptes(actif_only=True)
        self._categories: list[dict[str, Any]] = []
        self._operation_en_edition: int | None = None
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
        ctk.CTkButton(
            header,
            text="✏️ Modifier",
            width=110,
            fg_color="gray",
            hover_color="#555",
            command=self._modifier_operation,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            header,
            text="🗑️ Supprimer",
            width=110,
            fg_color="#b71c1c",
            hover_color="#7f0000",
            command=self._supprimer_operation,
        ).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            header,
            text="🔄 Actualiser",
            width=120,
            fg_color="gray",
            hover_color="#555",
            command=self.refresh,
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

        self._tree = ttk.Treeview(
            contenu,
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

        scrollbar = ttk.Scrollbar(contenu, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._lbl_stats = ctk.CTkLabel(self, text="")
        self._lbl_stats.pack(anchor="w", padx=12, pady=(0, 10))

    def _ouvrir_formulaire(self, type_operation: str) -> None:
        if not self._comptes:
            afficher_info(self, "Opérations", "Créez d'abord un compte actif.")
            return
        popup = _DialogOperation(
            self,
            type_operation=type_operation,
            on_enregistre=self.refresh,
        )
        self.wait_window(popup)

    def _modifier_operation(self) -> None:
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Opérations", "Sélectionnez une opération à modifier.")
            return
        try:
            operation_id = int(selected[0])
        except (TypeError, ValueError):
            return
        operation = get_operation_by_id(operation_id)
        if not operation:
            afficher_erreur(self, "Opérations", "Opération introuvable.")
            return
        if int(operation.get("est_automatique") or 0) == 1:
            afficher_info(self, "Opérations", "Les opérations automatiques ne peuvent pas être modifiées.")
            return
        popup = _DialogOperation(
            self,
            operation=operation,
            on_enregistre=self.refresh,
        )
        self.wait_window(popup)

    def _supprimer_operation(self) -> None:
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Opérations", "Sélectionnez une opération à supprimer.")
            return
        try:
            operation_id = int(selected[0])
        except (TypeError, ValueError):
            return
        operation = get_operation_by_id(operation_id)
        if not operation:
            afficher_erreur(self, "Opérations", "Opération introuvable.")
            return
        if int(operation.get("est_automatique") or 0) == 1:
            afficher_info(self, "Opérations", "Les opérations automatiques ne peuvent pas être supprimées.")
            return
        if not demander_confirmation(
            self,
            "Supprimer l'opération",
            f"Supprimer définitivement l'opération « {operation.get('libelle') or ''} » ?\n"
            "Cette action est irréversible.",
        ):
            return
        ok = delete_operation(operation_id)
        if ok:
            self.refresh()
        else:
            afficher_erreur(self, "Opérations", "Impossible de supprimer cette opération.")

    def refresh(self) -> None:
        try:
            if not self.winfo_exists():
                return
            self._tree.delete(*self._tree.get_children())
        except Exception:
            return
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


# Alias de compatibilité pour les imports/tests historiques.
_FormulaireOperationPopup = _DialogOperation
