"""Onglet Remises de chèques du module Trésorerie."""

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

from core.tresorerie import formater_montant, slug_reference_remise
from db.models.tresorerie import add_remise_cheque, get_all_comptes, get_remises
from ui import theme as app_theme
from ui.components.dialogs import afficher_erreur, afficher_info


_DATE_FORMAT = "%Y-%m-%d"


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(value: str | float | int | None) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".").strip() or 0))
    except (TypeError, ValueError):
        return 0


def _normaliser_date(value: str | None) -> str:
    brut = (value or "").strip()
    if not brut:
        return datetime.now().strftime(_DATE_FORMAT)
    for fmt in (_DATE_FORMAT, "%d/%m/%Y"):
        try:
            return datetime.strptime(brut, fmt).strftime(_DATE_FORMAT)
        except ValueError:
            continue
    return brut


def enregistrer_remise_depuis_formulaire(formulaire: dict[str, Any]) -> int:
    comptes = get_all_comptes(actif_only=True)
    if not comptes:
        raise ValueError("Aucun compte actif disponible.")

    compte_id = int(formulaire.get("compte_id") or comptes[0]["id"])
    compte = next((c for c in comptes if int(c["id"]) == compte_id), comptes[0])
    date_remise = _normaliser_date(str(formulaire.get("date_remise") or ""))
    reference = (str(formulaire.get("reference") or "").strip() or slug_reference_remise(date_remise, compte.get("nom") or "Compte"))

    return add_remise_cheque(
        compte_id=compte_id,
        date_remise=date_remise,
        reference=reference,
        commentaire=(str(formulaire.get("commentaire") or "").strip() or None),
        nombre_cheques=_parse_int(formulaire.get("nombre_cheques")),
        montant_total=_parse_float(formulaire.get("montant_total")),
        numero_bordereau=(str(formulaire.get("numero_bordereau") or "").strip() or None),
    )


class _RemisesTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._tresorerie_root = root
        self._comptes = get_all_comptes(actif_only=True)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="🏦 Remises de chèques",
            font=fonts.get("subtitle"),
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ Nouvelle remise",
            width=170,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire,
        ).pack(side="right")

        contenu = ctk.CTkFrame(self, fg_color="transparent")
        contenu.pack(fill="both", expand=True, padx=12, pady=6)

        self._frame_liste = ctk.CTkFrame(contenu)
        self._frame_liste.pack(side="left", fill="both", expand=True)

        self._frame_formulaire = ctk.CTkFrame(contenu, width=340)
        self._frame_formulaire.pack_propagate(False)

        self._tree = ttk.Treeview(
            self._frame_liste,
            columns=("date", "compte", "nb", "montant", "bordereau", "statut"),
            show="headings",
            height=14,
        )
        for col, label, width, anchor in [
            ("date", "Date", 110, "center"),
            ("compte", "Compte", 190, "w"),
            ("nb", "Nb chèques", 100, "center"),
            ("montant", "Montant", 120, "e"),
            ("bordereau", "Bordereau", 150, "w"),
            ("statut", "Statut", 100, "center"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(self._frame_liste, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._build_formulaire()

    def _build_formulaire(self) -> None:
        self._var_date = ctk.StringVar(value=datetime.now().strftime(_DATE_FORMAT))
        compte_defaut = self._comptes[0]["nom"] if self._comptes else ""
        self._var_compte = ctk.StringVar(value=compte_defaut)
        self._var_nombre = ctk.StringVar(value="0")
        self._var_montant = ctk.StringVar(value="0,00")
        self._var_bordereau = ctk.StringVar()
        self._var_commentaire = ctk.StringVar()

        ctk.CTkLabel(
            self._frame_formulaire,
            text="🏦 Nouvelle remise de chèques",
            font=app_theme.FONTS.get("subtitle"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Date remise", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_date))
        champ(
            "Banque / Compte",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=[c["nom"] for c in self._comptes] or [""],
                variable=self._var_compte,
            ),
        )
        champ("Nombre chèques", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_nombre))
        champ("Montant total (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_montant))
        champ("N° Bordereau", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_bordereau))
        champ("Commentaire", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_commentaire))

        actions = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(16, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer).pack(side="right")

    def _ouvrir_formulaire(self) -> None:
        if not self._comptes:
            afficher_info(self, "Remises", "Créez d'abord un compte actif.")
            return
        self._var_date.set(datetime.now().strftime(_DATE_FORMAT))
        self._var_compte.set(self._comptes[0]["nom"])
        self._var_nombre.set("0")
        self._var_montant.set("0,00")
        self._var_bordereau.set("")
        self._var_commentaire.set("")
        if not self._frame_formulaire.winfo_manager():
            self._frame_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire(self) -> None:
        self._frame_formulaire.pack_forget()

    def _enregistrer(self) -> None:
        try:
            enregistrer_remise_depuis_formulaire(
                {
                    "date_remise": self._var_date.get(),
                    "compte_id": next(
                        (int(c["id"]) for c in self._comptes if c["nom"] == self._var_compte.get()),
                        None,
                    ),
                    "nombre_cheques": self._var_nombre.get(),
                    "montant_total": self._var_montant.get(),
                    "numero_bordereau": self._var_bordereau.get(),
                    "commentaire": self._var_commentaire.get(),
                }
            )
        except ValueError as exc:
            afficher_erreur(self, "Remises", str(exc))
            return
        self.refresh()
        self._fermer_formulaire()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for remise in get_remises():
            self._tree.insert(
                "",
                "end",
                iid=str(remise.get("id") or ""),
                values=(
                    remise.get("date_remise") or "",
                    remise.get("compte_nom") or "",
                    remise.get("nombre_cheques") or 0,
                    formater_montant(float(remise.get("montant_total") or 0)),
                    remise.get("numero_bordereau") or "—",
                    remise.get("statut") or "",
                ),
            )


def build_tab_remises(parent: ctk.CTkFrame, root: Any) -> None:
    for widget in parent.winfo_children():
        widget.destroy()
    tab = _RemisesTab(parent, root)
    tab.pack(fill="both", expand=True)
