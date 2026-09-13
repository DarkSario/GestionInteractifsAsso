"""Tests ciblés du formulaire global des cotisations."""

from __future__ import annotations

import importlib
import sys
import types


class _Var:
    def __init__(self, value=None) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class _BaseWidget:
    def __init__(self, parent=None, **kwargs) -> None:
        self.parent = parent
        self.kwargs = kwargs
        self.children: list[_BaseWidget] = []
        self.destroyed = False
        if parent is not None and hasattr(parent, "children"):
            parent.children.append(self)

    def pack(self, *_args, **kwargs) -> None:
        self.pack_kwargs = kwargs

    def grid(self, *_args, **kwargs) -> None:
        self.grid_kwargs = kwargs

    def bind(self, *_args, **_kwargs) -> None:
        return None

    def configure(self, **kwargs) -> None:
        self.kwargs.update(kwargs)

    def destroy(self) -> None:
        self.destroyed = True

    def title(self, value: str) -> None:
        self.title_value = value

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def resizable(self, *_args) -> None:
        return None

    def transient(self, *_args) -> None:
        return None

    def grab_set(self) -> None:
        return None

    def focus(self) -> None:
        return None

    def grid_columnconfigure(self, *_args, **_kwargs) -> None:
        return None


class _Style:
    def configure(self, *_args, **_kwargs) -> None:
        return None

    def map(self, *_args, **_kwargs) -> None:
        return None

    def theme_use(self, *_args, **_kwargs) -> None:
        return None


def _load_module_with_ui_stubs(monkeypatch):
    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_ttk.Treeview = _BaseWidget
    fake_ttk.Scrollbar = _BaseWidget
    fake_ttk.Style = _Style

    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = _Var
    fake_tk.IntVar = _Var
    fake_tk.BooleanVar = _Var
    fake_tk.Frame = _BaseWidget
    fake_tk.ttk = fake_ttk

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkToplevel = _BaseWidget
    fake_ctk.CTkLabel = _BaseWidget
    fake_ctk.CTkEntry = _BaseWidget
    fake_ctk.CTkFrame = _BaseWidget
    fake_ctk.CTkButton = _BaseWidget
    fake_ctk.CTkOptionMenu = _BaseWidget
    fake_ctk.CTkScrollableFrame = _BaseWidget
    fake_ctk.CTkFont = _BaseWidget
    fake_ctk.StringVar = _Var
    fake_ctk.IntVar = _Var
    fake_ctk.Variable = _Var
    fake_ctk.get_appearance_mode = lambda: "Light"
    fake_ctk.set_appearance_mode = lambda *_args, **_kwargs: None
    fake_ctk.set_default_color_theme = lambda *_args, **_kwargs: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    sys.modules.pop("ui.theme", None)
    sys.modules.pop("ui.modules.membres.cotisations", None)
    return importlib.import_module("ui.modules.membres.cotisations")


def test_formulaire_global_associe_l_adherent_selectionne(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(
        module,
        "get_all_membres",
        lambda include_archives=False: [{"id": 7, "nom": "Martin", "prenom": "Alice"}],
    )
    monkeypatch.setattr(module, "get_montant_cotisation_defaut", lambda: 12.5)
    enregistrements: list[tuple[int, dict]] = []
    rappels: list[bool] = []

    def _fake_add_cotisation(adherent_id: int, **kwargs):
        enregistrements.append((adherent_id, kwargs))
        return 15

    monkeypatch.setattr(module, "add_cotisation", _fake_add_cotisation)

    dialog = module._FormulaireCotisation(_BaseWidget(), on_save=lambda: rappels.append(True))
    dialog._membre_var.set("7 — Alice Martin")
    dialog._annee_var.set("2026")
    dialog._montant_var.set("15")
    dialog._statut_var.set("payee")
    dialog._enregistrer()

    assert enregistrements == [
        (
            7,
            {
                "annee": 2026,
                "montant": 15.0,
                "statut": "payee",
                "date_paiement": None,
                "mode_paiement": None,
                "commentaire": None,
            },
        )
    ]
    assert rappels == [True]
    assert dialog.destroyed is True


def test_formulaire_global_affiche_erreur_si_ajout_echoue(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(
        module,
        "get_all_membres",
        lambda include_archives=False: [{"id": 3, "nom": "Dupont", "prenom": "Bob"}],
    )
    monkeypatch.setattr(module, "get_montant_cotisation_defaut", lambda: 0.0)
    monkeypatch.setattr(module, "add_cotisation", lambda adherent_id, **kwargs: 0)
    erreurs: list[tuple[str, str]] = []
    rappels: list[bool] = []
    monkeypatch.setattr(
        module,
        "afficher_erreur",
        lambda _parent, titre, message: erreurs.append((titre, message)),
    )

    dialog = module._FormulaireCotisation(_BaseWidget(), on_save=lambda: rappels.append(True))
    dialog._membre_var.set("3 — Bob Dupont")
    dialog._enregistrer()

    assert dialog.destroyed is False
    assert rappels == []
    assert erreurs == [
        (
            "Erreur",
            "Impossible d'ajouter la cotisation. Vérifiez la base de données et réessayez.",
        )
    ]


def test_formulaire_global_affiche_erreur_si_les_adherents_ne_chargent_pas(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    erreurs: list[tuple[str, str]] = []
    monkeypatch.setattr(
        module,
        "get_all_membres",
        lambda include_archives=False: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    monkeypatch.setattr(
        module,
        "afficher_erreur",
        lambda _parent, titre, message: erreurs.append((titre, message)),
    )

    dialog = module._FormulaireCotisation(_BaseWidget())

    assert dialog.destroyed is True
    assert erreurs == [
        (
            "Erreur",
            "Impossible de charger la liste des adhérents pour créer une cotisation.",
        )
    ]


def test_formulaire_edition_affiche_erreur_si_modification_echoue(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(module, "update_cotisation", lambda _cotisation_id, **_kwargs: False)
    erreurs: list[tuple[str, str]] = []
    rappels: list[bool] = []
    monkeypatch.setattr(
        module,
        "afficher_erreur",
        lambda _parent, titre, message: erreurs.append((titre, message)),
    )

    dialog = module._FormulaireCotisation(
        _BaseWidget(),
        cotisation={
            "id": 42,
            "adherent_id": 7,
            "annee": 2026,
            "montant": 12.5,
            "statut": "payee",
            "date_paiement": "",
            "mode_paiement": "",
            "commentaire": "",
        },
        on_save=lambda: rappels.append(True),
    )
    dialog._enregistrer()

    assert dialog.destroyed is False
    assert rappels == []
    assert erreurs == [
        (
            "Erreur",
            "Impossible d'enregistrer les modifications de la cotisation.",
        )
    ]
