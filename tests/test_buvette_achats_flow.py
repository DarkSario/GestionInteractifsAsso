"""Tests ciblés du parcours d'ajout des achats buvette."""

from __future__ import annotations

import importlib
import sys
import types
from typing import ClassVar


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

    def minsize(self, *_args) -> None:
        return None

    def transient(self, *_args) -> None:
        return None

    def grab_set(self) -> None:
        self.grab_called = True

    def wait_window(self, window) -> None:
        self.waited_window = window

    def grid_columnconfigure(self, *_args, **_kwargs) -> None:
        return None


class _Button(_BaseWidget):
    instances: ClassVar[list[_Button]] = []

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        type(self).instances.append(self)


class _Tabview(_BaseWidget):
    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.tabs: dict[str, _BaseWidget] = {}
        self.selected = None

    def add(self, name: str) -> None:
        self.tabs[name] = _BaseWidget(self)

    def tab(self, name: str) -> _BaseWidget:
        return self.tabs[name]

    def set(self, name: str) -> None:
        self.selected = name


class _Style:
    def configure(self, *_args, **_kwargs) -> None:
        return None

    def map(self, *_args, **_kwargs) -> None:
        return None

    def theme_use(self, *_args, **_kwargs) -> None:
        return None


class _FakeAchats(_BaseWidget):
    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


class _RefreshableWidget(_BaseWidget):
    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.refresh_calls = 0

    def refresh(self) -> None:
        self.refresh_calls += 1


def _install_ui_stubs(monkeypatch) -> None:
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
    fake_ctk.CTkButton = _Button
    fake_ctk.CTkOptionMenu = _BaseWidget
    fake_ctk.CTkScrollableFrame = _BaseWidget
    fake_ctk.CTkCheckBox = _BaseWidget
    fake_ctk.CTkTextbox = _BaseWidget
    fake_ctk.CTkTabview = _Tabview
    fake_ctk.CTkFont = _BaseWidget
    fake_ctk.StringVar = _Var
    fake_ctk.IntVar = _Var
    fake_ctk.get_appearance_mode = lambda: "Light"
    fake_ctk.set_appearance_mode = lambda *_args, **_kwargs: None
    fake_ctk.set_default_color_theme = lambda *_args, **_kwargs: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)


def test_formulaire_entree_preselectionne_le_tag_buvette(monkeypatch) -> None:
    _install_ui_stubs(monkeypatch)
    sys.modules.pop("ui.theme", None)
    sys.modules.pop("ui.modules.stock.formulaire_entree", None)
    module = importlib.import_module("ui.modules.stock.formulaire_entree")
    monkeypatch.setattr(module, "get_articles_for_select", lambda: [{"id": 1, "nom": "Coca"}])
    monkeypatch.setattr(module, "get_fournisseurs_for_select", list)
    monkeypatch.setattr(
        module,
        "get_tags",
        lambda: [{"id": 1, "nom": "Buvette"}, {"id": 2, "nom": "Matériel"}],
    )

    dialog = module.FormulaireEntreeMarchandise(
        _BaseWidget(),
        preselected_tag_names={"Buvette"},
    )

    assert dialog._tag_vars[1].get() is True
    assert dialog._tag_vars[2].get() is False


def test_liste_buvette_expose_le_flux_d_ajout_achat(monkeypatch) -> None:
    _install_ui_stubs(monkeypatch)
    _Button.instances = []

    fake_achats_module = types.ModuleType("ui.modules.buvette.achats_buvette")
    fake_achats_module.OngletAchatsBuvette = _FakeAchats
    fake_inv_module = types.ModuleType("ui.modules.buvette.inventaires")
    fake_inv_module.OngletInventaires = _BaseWidget
    fake_couts_module = types.ModuleType("ui.modules.buvette.couts_evenement")
    fake_couts_module.OngletCoutsEvenement = _BaseWidget
    fake_bilan_module = types.ModuleType("ui.modules.buvette.bilan_annuel")
    fake_bilan_module.OngletBilanAnnuel = _RefreshableWidget

    created_forms: list[tuple[object, set[str] | None]] = []

    class _FakeForm(_BaseWidget):
        def __init__(self, parent=None, preselected_tag_names=None) -> None:
            super().__init__(parent)
            created_forms.append((parent, preselected_tag_names))
            self.saved = True

    fake_stock_module = types.ModuleType("ui.modules.stock.formulaire_entree")
    fake_stock_module.FormulaireEntreeMarchandise = _FakeForm

    monkeypatch.setitem(sys.modules, "ui.modules.buvette.achats_buvette", fake_achats_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.inventaires", fake_inv_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.couts_evenement", fake_couts_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.bilan_annuel", fake_bilan_module)
    monkeypatch.setitem(sys.modules, "ui.modules.stock.formulaire_entree", fake_stock_module)

    sys.modules.pop("ui.theme", None)
    sys.modules.pop("ui.modules.buvette.liste", None)
    module = importlib.import_module("ui.modules.buvette.liste")

    window = module.ListeBuvette(_BaseWidget())
    textes = [button.kwargs.get("text") for button in _Button.instances]

    assert "➕ Ajouter un achat buvette" in textes

    window._ouvrir_ajout_achat_buvette()

    assert created_forms == [(window, {"Buvette"})]
    assert window._tabs.selected == "📋 Achats buvette"
    assert window._onglet_achats.refresh_calls == 1
    assert window._onglet_bilan.refresh_calls == 1


def test_liste_buvette_n_actualise_pas_si_le_formulaire_est_annule(monkeypatch) -> None:
    _install_ui_stubs(monkeypatch)

    fake_achats_module = types.ModuleType("ui.modules.buvette.achats_buvette")
    fake_achats_module.OngletAchatsBuvette = _FakeAchats
    fake_inv_module = types.ModuleType("ui.modules.buvette.inventaires")
    fake_inv_module.OngletInventaires = _BaseWidget
    fake_couts_module = types.ModuleType("ui.modules.buvette.couts_evenement")
    fake_couts_module.OngletCoutsEvenement = _BaseWidget
    fake_bilan_module = types.ModuleType("ui.modules.buvette.bilan_annuel")
    fake_bilan_module.OngletBilanAnnuel = _RefreshableWidget

    class _FakeForm(_BaseWidget):
        def __init__(self, parent=None, preselected_tag_names=None) -> None:
            super().__init__(parent)
            self.saved = False

    fake_stock_module = types.ModuleType("ui.modules.stock.formulaire_entree")
    fake_stock_module.FormulaireEntreeMarchandise = _FakeForm

    monkeypatch.setitem(sys.modules, "ui.modules.buvette.achats_buvette", fake_achats_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.inventaires", fake_inv_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.couts_evenement", fake_couts_module)
    monkeypatch.setitem(sys.modules, "ui.modules.buvette.bilan_annuel", fake_bilan_module)
    monkeypatch.setitem(sys.modules, "ui.modules.stock.formulaire_entree", fake_stock_module)

    sys.modules.pop("ui.theme", None)
    sys.modules.pop("ui.modules.buvette.liste", None)
    module = importlib.import_module("ui.modules.buvette.liste")

    window = module.ListeBuvette(_BaseWidget())
    window._ouvrir_ajout_achat_buvette()

    assert window._tabs.selected is None
    assert window._onglet_achats.refresh_calls == 0
    assert window._onglet_bilan.refresh_calls == 0
