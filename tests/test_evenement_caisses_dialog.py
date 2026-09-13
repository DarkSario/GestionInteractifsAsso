"""Tests ciblés du dialog d'ajout/édition de ligne de caisse événement."""

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


class _Label(_BaseWidget):
    instances: list["_Label"] = []

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        type(self).instances.append(self)


class _Entry(_BaseWidget):
    instances: list["_Entry"] = []

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        type(self).instances.append(self)


class _Button(_BaseWidget):
    instances: list["_Button"] = []

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        type(self).instances.append(self)


class _Combobox(_BaseWidget):
    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.values = list(kwargs.get("values") or [])
        self.variable = kwargs.get("variable")
        self._current = 0

    def current(self, value=None):
        if value is None:
            return self._current
        self._current = value
        if self.variable is not None and 0 <= value < len(self.values):
            self.variable.set(self.values[value])
        return self._current


def _load_module_with_ui_stubs(monkeypatch):
    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_ttk.Treeview = _BaseWidget
    fake_ttk.Scrollbar = _BaseWidget
    fake_ttk.Combobox = _Combobox

    fake_simpledialog = types.SimpleNamespace(askstring=lambda *args, **kwargs: None)

    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = _Var
    fake_tk.BooleanVar = _Var
    fake_tk.simpledialog = fake_simpledialog
    fake_tk.ttk = fake_ttk

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkToplevel = _BaseWidget
    fake_ctk.CTkLabel = _Label
    fake_ctk.CTkEntry = _Entry
    fake_ctk.CTkFrame = _BaseWidget
    fake_ctk.CTkButton = _Button
    fake_ctk.CTkOptionMenu = _BaseWidget
    fake_ctk.CTkFont = _BaseWidget
    fake_ctk.set_appearance_mode = lambda *_args, **_kwargs: None
    fake_ctk.set_default_color_theme = lambda *_args, **_kwargs: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    sys.modules.pop("ui.modules.evenements.caisses", None)
    _Label.instances = []
    _Entry.instances = []
    _Button.instances = []
    return importlib.import_module("ui.modules.evenements.caisses")


def test_dialog_ligne_affiche_tous_les_champs_et_actions(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(
        module,
        "lister_designations_caisse",
        lambda actif_only=True: [{"id": 1, "nom": "Pièces 2€", "montant_unitaire": 2.0}],
    )

    dialog = module._DialogLigneCaisse(_BaseWidget(), "Ajouter ligne", None)

    labels = [label.kwargs.get("text") for label in _Label.instances]
    boutons = {button.kwargs.get("text"): button for button in _Button.instances}
    assert dialog.geometry_value == "480x420"
    assert "Préset" in labels
    assert "Désignation *" in labels
    assert "Montant unitaire (€) *" in labels
    assert "Quantité *" in labels
    assert "Enregistrer" in boutons
    assert boutons["Enregistrer"].kwargs.get("width") == 140
    assert "Annuler" in boutons
    assert boutons["Annuler"].kwargs.get("fg_color") == "#6c757d"


def test_dialog_ligne_selection_preset_remplit_champs(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(
        module,
        "lister_designations_caisse",
        lambda actif_only=True: [{"id": 7, "nom": "Billets 10€", "montant_unitaire": 10.0}],
    )

    dialog = module._DialogLigneCaisse(_BaseWidget(), "Ajouter ligne", None)
    dialog._preset_menu.current(1)
    dialog._on_designation_change()

    assert dialog._designation_var.get() == "Billets 10€"
    assert dialog._montant_var.get() == "10.00"
    assert dialog._designation_entry.kwargs.get("state") == "disabled"
    assert dialog._montant_entry.kwargs.get("state") == "disabled"


def test_dialog_ligne_signale_absence_de_presets_actifs(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(module, "lister_designations_caisse", lambda actif_only=True: [])

    dialog = module._DialogLigneCaisse(_BaseWidget(), "Ajouter ligne", None)

    assert dialog._preset_options == ["Saisie libre"]
    assert dialog._preset_warning == (
        "Aucun préset actif disponible. Utilisez la saisie libre."
    )


def test_dialog_ligne_signale_erreur_chargement_presets(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    avertissements: list[str] = []

    def _boom(*, actif_only=True):
        raise RuntimeError("db indisponible")

    monkeypatch.setattr(module, "lister_designations_caisse", _boom)
    monkeypatch.setattr(
        module.logger, "warning", lambda message, exc: avertissements.append(message % exc)
    )

    dialog = module._DialogLigneCaisse(_BaseWidget(), "Ajouter ligne", None)

    assert dialog._preset_options == ["Saisie libre"]
    assert dialog._preset_warning == (
        "Impossible de charger les présets. Utilisez la saisie libre."
    )
    assert avertissements == ["Impossible de charger les présets de caisse : db indisponible"]


def test_dialog_ligne_valide_avec_liaison_designation(monkeypatch) -> None:
    module = _load_module_with_ui_stubs(monkeypatch)
    monkeypatch.setattr(
        module,
        "lister_designations_caisse",
        lambda actif_only=True: [{"id": 5, "nom": "Chèques", "montant_unitaire": 0.0}],
    )

    dialog = module._DialogLigneCaisse(_BaseWidget(), "Ajouter ligne", None)
    dialog._preset_menu.current(1)
    dialog._on_designation_change()
    dialog._montant_var.set("24,50")
    dialog._quantite_var.set("2")
    dialog._valider()

    assert dialog.result == {
        "designation": "Chèques",
        "montant_unitaire": 24.5,
        "quantite": 2,
        "designation_id": 5,
    }
    assert dialog.destroyed is True
