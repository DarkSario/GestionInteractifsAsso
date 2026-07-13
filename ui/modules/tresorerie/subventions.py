"""Onglet Subventions du module Trésorerie."""

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
        CTkFrame = CTkLabel = CTkButton = CTkEntry = CTkOptionMenu = CTkBaseClass = _DummyWidget
        StringVar = _DummyVar

    ctk = _DummyCTk()

from core.tresorerie import formater_montant
from db.models.tresorerie import (
    accorder_subvention,
    add_subvention,
    get_all_comptes,
    get_all_subventions,
    get_stats_subventions,
    update_subvention,
)
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


_DATE_FORMAT = "%Y-%m-%d"
_STATUTS_LABELS = {
    "en_attente": "En attente",
    "accordee": "Obtenue",
    "refusee": "Refusée",
    "partielle": "Partielle",
    "annulee": "Annulée",
}
_STATUTS_INV = {value: key for key, value in _STATUTS_LABELS.items()}


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _normaliser_date(value: str | None) -> str | None:
    brut = (value or "").strip()
    if not brut:
        return None
    for fmt in (_DATE_FORMAT, "%d/%m/%Y"):
        try:
            return datetime.strptime(brut, fmt).strftime(_DATE_FORMAT)
        except ValueError:
            continue
    return brut


def _date_formulaire_ou_aujourdhui(value: str | None) -> str:
    date_normalisee = _normaliser_date(value)
    return date_normalisee or datetime.now().strftime(_DATE_FORMAT)


def _annee_depuis_date(value: str) -> int:
    try:
        return datetime.strptime(value, _DATE_FORMAT).year
    except ValueError:
        return datetime.now().year


def enregistrer_subvention_depuis_formulaire(
    formulaire: dict[str, Any],
    subvention_id: int | None = None,
) -> int:
    organisme = str(formulaire.get("organisme") or "").strip()
    if not organisme:
        raise ValueError("L'organisme est obligatoire.")

    objet = str(formulaire.get("objet") or "").strip() or "Demande libre"
    date_demande = _date_formulaire_ou_aujourdhui(str(formulaire.get("date_demande") or ""))
    montant_demande = _parse_float(formulaire.get("montant_demande"))
    montant_obtenu = _parse_float(formulaire.get("montant_obtenu"))
    date_obtention = _normaliser_date(str(formulaire.get("date_obtention") or ""))
    statut = str(formulaire.get("statut") or "en_attente").strip().lower()
    commentaire = str(formulaire.get("commentaire") or "").strip() or None
    compte_id = formulaire.get("compte_id")

    annee = _annee_depuis_date(date_demande)
    if subvention_id is None:
        subvention_id = add_subvention(
            organisme=organisme,
            type_organisme="autre",
            annee=annee,
            objet=objet,
            montant_demande=montant_demande,
            date_demande=date_demande,
            commentaire=commentaire,
        )

    update_subvention(
        subvention_id,
        organisme=organisme,
        annee=annee,
        objet=objet,
        montant_demande=montant_demande,
        montant_obtenu=montant_obtenu,
        statut=statut,
        date_demande=date_demande,
        date_decision=date_obtention,
        date_versement=date_obtention,
        commentaire=commentaire,
    )

    # Créer automatiquement une opération de recette si la subvention est accordée
    # et qu'un compte est sélectionné et qu'il n'existe pas encore d'opération associée
    if statut == "accordee" and montant_obtenu > 0 and compte_id:
        subvention_existante = next(
            (s for s in get_all_subventions() if int(s["id"]) == int(subvention_id)),
            None,
        )
        if subvention_existante and not subvention_existante.get("operation_id"):
            accorder_subvention(
                subvention_id=int(subvention_id),
                montant_obtenu=montant_obtenu,
                date_decision=date_obtention or date_demande,
                date_versement=date_obtention or date_demande,
                compte_id=int(compte_id),
            )

    return int(subvention_id)


class _SubventionsTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._tresorerie_root = root
        self._subvention_selectionnee: int | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(header, text="🎁 Subventions", font=fonts.get("subtitle")).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Nouvelle demande",
            width=170,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire,
        ).pack(side="right")
        ctk.CTkButton(
            header,
            text="✏️ Modifier",
            width=120,
            command=self._modifier_selection,
        ).pack(side="right", padx=(0, 8))

        contenu = ctk.CTkFrame(self, fg_color="transparent")
        contenu.pack(fill="both", expand=True, padx=12, pady=6)

        self._frame_liste = ctk.CTkFrame(contenu)
        self._frame_liste.pack(side="left", fill="both", expand=True)

        self._frame_formulaire = ctk.CTkFrame(contenu, width=360)
        self._frame_formulaire.pack_propagate(False)

        self._tree = ttk.Treeview(
            self._frame_liste,
            columns=("organisme", "objet", "demande", "obtenu", "statut"),
            show="headings",
            height=14,
        )
        for col, label, width, anchor in [
            ("organisme", "Organisme", 180, "w"),
            ("objet", "Objet", 220, "w"),
            ("demande", "Demandé", 110, "e"),
            ("obtenu", "Obtenu", 110, "e"),
            ("statut", "Statut", 110, "center"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(self._frame_liste, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._lbl_stats = ctk.CTkLabel(self, text="")
        self._lbl_stats.pack(anchor="w", padx=12, pady=(0, 10))

        self._build_formulaire()

    def _build_formulaire(self) -> None:
        self._var_organisme = ctk.StringVar()
        self._var_objet = ctk.StringVar()
        self._var_demande = ctk.StringVar(value="0,00")
        self._var_obtenu = ctk.StringVar(value="0,00")
        self._var_date_demande = ctk.StringVar(value=datetime.now().strftime(_DATE_FORMAT))
        self._var_date_obtention = ctk.StringVar()
        self._var_statut = ctk.StringVar(value="En attente")
        self._var_commentaire = ctk.StringVar()
        self._comptes = get_all_comptes(actif_only=True)
        compte_defaut = self._comptes[0]["nom"] if self._comptes else ""
        self._var_compte = ctk.StringVar(value=compte_defaut)

        self._titre_formulaire = ctk.CTkLabel(
            self._frame_formulaire,
            text="🏛️ Subvention",
            font=app_theme.FONTS.get("subtitle"),
        )
        self._titre_formulaire.pack(anchor="w", padx=16, pady=(16, 12))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Organisme", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_organisme))
        champ("Objet", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_objet))
        champ("Montant demandé (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_demande))
        champ("Montant obtenu (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_obtenu))
        champ("Date demande", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_date_demande))
        champ("Date obtention", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_date_obtention))
        champ(
            "Statut",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=["En attente", "Obtenue", "Refusée", "Partielle", "Annulée"],
                variable=self._var_statut,
            ),
        )
        champ(
            "Compte (si obtenue)",
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

    def _ouvrir_formulaire(self, subvention: dict[str, Any] | None = None) -> None:
        data = subvention or {}
        date_du_jour = datetime.now().strftime(_DATE_FORMAT)
        self._subvention_selectionnee = int(subvention["id"]) if subvention else None
        self._titre_formulaire.configure(text="🏛️ Modifier la subvention" if subvention else "🏛️ Subvention")
        self._var_organisme.set(data.get("organisme") or "")
        self._var_objet.set(data.get("objet") or "")
        self._var_demande.set(f"{float(data.get('montant_demande') or 0):.2f}".replace(".", ","))
        self._var_obtenu.set(f"{float(data.get('montant_obtenu') or 0):.2f}".replace(".", ","))
        self._var_date_demande.set(data.get("date_demande") or date_du_jour)
        self._var_date_obtention.set(data.get("date_decision") or data.get("date_versement") or "")
        self._var_statut.set(_STATUTS_LABELS.get(data.get("statut") or "en_attente", "En attente"))
        self._var_commentaire.set(data.get("commentaire") or "")
        # Pré-remplir le compte si déjà associé
        if data.get("compte_id") and self._comptes:
            compte = next((c for c in self._comptes if int(c["id"]) == int(data["compte_id"])), None)
            if compte:
                self._var_compte.set(compte["nom"])
        if not self._frame_formulaire.winfo_manager():
            self._frame_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire(self) -> None:
        self._subvention_selectionnee = None
        self._frame_formulaire.pack_forget()

    def _modifier_selection(self) -> None:
        selected = self._tree.selection()
        if not selected:
            afficher_info(self, "Subventions", "Sélectionnez une subvention à modifier.")
            return
        subvention_id = int(selected[0])
        subvention = next((s for s in get_all_subventions() if int(s["id"]) == subvention_id), None)
        if not subvention:
            return
        self._ouvrir_formulaire(subvention)

    def _enregistrer(self) -> None:
        compte_id = next(
            (int(c["id"]) for c in self._comptes if c["nom"] == self._var_compte.get()),
            None,
        )
        try:
            enregistrer_subvention_depuis_formulaire(
                {
                    "organisme": self._var_organisme.get(),
                    "objet": self._var_objet.get(),
                    "montant_demande": self._var_demande.get(),
                    "montant_obtenu": self._var_obtenu.get(),
                    "date_demande": self._var_date_demande.get(),
                    "date_obtention": self._var_date_obtention.get(),
                    "statut": _STATUTS_INV.get(self._var_statut.get(), "en_attente"),
                    "commentaire": self._var_commentaire.get(),
                    "compte_id": compte_id,
                },
                subvention_id=self._subvention_selectionnee,
            )
        except ValueError as exc:
            afficher_erreur(self, "Subventions", str(exc))
            return
        self.refresh()
        self._fermer_formulaire()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        subventions = get_all_subventions()
        for subvention in subventions:
            self._tree.insert(
                "",
                "end",
                iid=str(subvention["id"]),
                values=(
                    subvention.get("organisme") or "",
                    subvention.get("objet") or "",
                    formater_montant(float(subvention.get("montant_demande") or 0)),
                    formater_montant(float(subvention.get("montant_obtenu") or 0)),
                    _STATUTS_LABELS.get(subvention.get("statut") or "", subvention.get("statut") or ""),
                ),
            )

        stats = get_stats_subventions()
        self._lbl_stats.configure(
            text=(
                f"Total demandé : {formater_montant(stats['total_demande'])}  |  "
                f"Total obtenu : {formater_montant(stats['total_obtenu'])}"
            ),
            font=app_theme.FONTS.get("bold"),
        )


def build_tab_subventions(parent: ctk.CTkFrame, root: Any) -> None:
    for widget in parent.winfo_children():
        widget.destroy()
    tab = _SubventionsTab(parent, root)
    tab.pack(fill="both", expand=True)
