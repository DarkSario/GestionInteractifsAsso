"""Onglet Comptes du module Trésorerie."""

from __future__ import annotations

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
from db.models.tresorerie import add_compte, get_all_comptes
from ui import theme as app_theme
from ui.modules.tresorerie.virement_dialog import VirementDialog


_TYPES_COMPTE = {
    "Bancaire": "bancaire",
    "Livret": "livret",
    "SumUp": "sumup",
    "Caisse": "caisse",
    "Autre": "autre",
}


def _parse_float(value: str | float | int | None) -> float:
    try:
        return float(str(value or "0").replace(",", ".").strip() or 0)
    except (TypeError, ValueError):
        return 0.0


def enregistrer_compte_depuis_formulaire(formulaire: dict[str, Any]) -> int:
    type_compte = str(formulaire.get("type_compte") or "bancaire").strip().lower()
    return add_compte(
        str(formulaire.get("nom") or "").strip(),
        type_compte,
        _parse_float(formulaire.get("solde_initial")),
        0,
        1 if type_compte == "caisse" else 0,
        "",
        "",
        0,
    )


class _ComptesTab(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkFrame, root: Any) -> None:
        super().__init__(parent)
        self._root = root
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        fonts = app_theme.FONTS
        colors = app_theme.COLORS

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(header, text="💰 Comptes bancaires", font=fonts.get("subtitle")).pack(side="left")
        ctk.CTkButton(
            header,
            text="+ Ajouter un compte",
            width=170,
            fg_color=colors.get("primary", "#1f6aa5"),
            hover_color=colors.get("secondary", "#144870"),
            command=self._ouvrir_formulaire,
        ).pack(side="right")

        contenu = ctk.CTkFrame(self, fg_color="transparent")
        contenu.pack(fill="both", expand=True, padx=12, pady=6)

        self._frame_liste = ctk.CTkFrame(contenu)
        self._frame_liste.pack(side="left", fill="both", expand=True)
        self._frame_formulaire = ctk.CTkFrame(contenu, width=320)
        self._frame_formulaire.pack_propagate(False)

        self._tree = ttk.Treeview(
            self._frame_liste,
            columns=("nom", "type", "solde", "principal"),
            show="headings",
            height=14,
        )
        for col, label, width, anchor in [
            ("nom", "Nom", 260, "w"),
            ("type", "Type", 120, "center"),
            ("solde", "Solde", 140, "e"),
            ("principal", "Principal", 90, "center"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)

        scrollbar = ttk.Scrollbar(self._frame_liste, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=12, pady=(2, 10))
        self._lbl_total = ctk.CTkLabel(footer, text="", font=fonts.get("bold"))
        self._lbl_total.pack(side="left")
        ctk.CTkButton(
            footer,
            text="↔️ Virement interne",
            width=160,
            command=lambda: VirementDialog(self._root),
        ).pack(side="right")

        self._build_formulaire()

    def _build_formulaire(self) -> None:
        self._var_nom = ctk.StringVar()
        self._var_type = ctk.StringVar(value="Bancaire")
        self._var_solde = ctk.StringVar(value="0,00")

        ctk.CTkLabel(
            self._frame_formulaire,
            text="💰 Nouveau compte",
            font=app_theme.FONTS.get("subtitle"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        def champ(label: str, widget: ctk.CTkBaseClass) -> None:
            bloc = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
            bloc.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(bloc, text=label).pack(anchor="w")
            widget.pack(fill="x", pady=(4, 0))

        champ("Nom du compte", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_nom))
        champ(
            "Type",
            ctk.CTkOptionMenu(
                self._frame_formulaire,
                values=list(_TYPES_COMPTE),
                variable=self._var_type,
            ),
        )
        champ("Solde initial (€)", ctk.CTkEntry(self._frame_formulaire, textvariable=self._var_solde))

        actions = ctk.CTkFrame(self._frame_formulaire, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(16, 16))
        ctk.CTkButton(actions, text="Annuler", fg_color="gray", hover_color="#555", command=self._fermer_formulaire).pack(side="left")
        ctk.CTkButton(actions, text="💾 Enregistrer", command=self._enregistrer).pack(side="right")

    def _ouvrir_formulaire(self) -> None:
        self._var_nom.set("")
        self._var_type.set("Bancaire")
        self._var_solde.set("0,00")
        if not self._frame_formulaire.winfo_manager():
            self._frame_formulaire.pack(side="right", fill="y", padx=(12, 0))

    def _fermer_formulaire(self) -> None:
        self._frame_formulaire.pack_forget()

    def _enregistrer(self) -> None:
        enregistrer_compte_depuis_formulaire(
            {
                "nom": self._var_nom.get(),
                "type_compte": _TYPES_COMPTE.get(self._var_type.get(), "bancaire"),
                "solde_initial": self._var_solde.get(),
            }
        )
        self.refresh()
        self._fermer_formulaire()

    def refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        comptes = get_all_comptes(actif_only=False)
        total = 0.0
        for compte in comptes:
            solde = float(compte.get("solde_actuel") or 0)
            total += solde
            self._tree.insert(
                "",
                "end",
                iid=str(compte.get("id") or ""),
                values=(
                    compte.get("nom") or "",
                    str(compte.get("type_compte") or "").capitalize(),
                    formater_montant(solde),
                    "★" if int(compte.get("est_principal") or 0) else "",
                ),
            )
        self._lbl_total.configure(text=f"Total tous comptes : {formater_montant(total)}")


def build_tab_comptes(parent: ctk.CTkFrame, root: Any) -> None:
    for widget in parent.winfo_children():
        widget.destroy()
    tab = _ComptesTab(parent, root)
    tab.pack(fill="both", expand=True)
