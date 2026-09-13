"""Tests ciblés du dialog de création/édition des désignations de caisses."""

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


class _Button(_BaseWidget):
    instances: list["_Button"] = []

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        type(self).instances.append(self)


def _load_module_with_ui_stubs(monkeypatch):
    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_ttk.Treeview = _BaseWidget
    fake_ttk.Scrollbar = _BaseWidget

    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = _Var
    fake_tk.BooleanVar = _Var
    fake_tk.ttk = fake_ttk

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkToplevel = _BaseWidget
    fake_ctk.CTkLabel = _BaseWidget
    fake_ctk.CTkEntry = _BaseWidget
    fake_ctk.CTkFrame = _BaseWidget
    fake_ctk.CTkCheckBox = _BaseWidget
    fake_ctk.CTkButton = _Button
    fake_ctk.CTkFont = _BaseWidget
    fake_ctk.set_appearance_mode = lambda *_args, **_kwargs: None
    fake_ctk.set_default_color_theme = lambda *_args, **_kwargs: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    sys.modules.pop("ui.modules.administration.caisse_designations", None)
    _Button.instances = []
    return importlib.import_module("ui.modules.administration.caisse_designations")


def test_dialog_affiche_boutons_actions_stylises(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)

    dialog = module._DialogDesignationCaisse(_BaseWidget(), "Nouvelle désignation", None)

    boutons = {button.kwargs.get("text"): button for button in _Button.instances}
    assert dialog.geometry_value == "460x380"
    assert "Enregistrer" in boutons
    assert boutons["Enregistrer"].kwargs.get("width") == 140
    assert "Annuler" in boutons
    assert boutons["Annuler"].kwargs.get("width") == 120
    assert boutons["Annuler"].kwargs.get("fg_color") == "#6c757d"


def test_dialog_refuse_montant_vide(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    erreurs: list[tuple[str, str]] = []
    monkeypatch.setattr(
        module,
        "afficher_erreur",
        lambda _parent, titre, message: erreurs.append((titre, message)),
    )

    dialog = module._DialogDesignationCaisse(_BaseWidget(), "Nouvelle désignation", None)
    dialog._nom_var.set("Jetons")
    dialog._montant_var.set("")
    dialog._valider()

    assert dialog.result is None
    assert erreurs == [
        ("Désignations de caisses", "Le montant unitaire est obligatoire.")
    ]


def test_dialog_edition_sans_montant_initialise_un_champ_vide(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)

    dialog = module._DialogDesignationCaisse(
        _BaseWidget(),
        "Modifier la désignation",
        {"nom": "Jetons", "montant_unitaire": None},
    )

    assert dialog._montant_var.get() == ""


def test_dialog_enregistre_designation_valide(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    dialog = module._DialogDesignationCaisse(_BaseWidget(), "Nouvelle désignation", None)

    dialog._nom_var.set("Jetons")
    dialog._montant_var.set("2,50")
    dialog._description_var.set("Monnaie interne")
    dialog._ordre_var.set("12")
    dialog._actif_var.set(True)
    dialog._valider()

    assert dialog.result == {
        "nom": "Jetons",
        "montant_unitaire": 2.5,
        "description": "Monnaie interne",
        "ordre": 12,
        "actif": True,
    }
    assert dialog.destroyed is True
