"""Tests pour la navigation et la configuration dans l'application principale."""

from __future__ import annotations

import importlib
import sys
import types
import pytest
from db.connection import get_connection, set_db_file
from db.migrations.runner import run_migrations


class DummyVar:
    def __init__(self, value=None) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self._text = kwargs.get("text", "")
        self.title_val = ""
        self._exists = True
        self.kwargs = kwargs

    def pack(self, *args, **kwargs):
        pass

    def configure(self, **kwargs):
        if not hasattr(self, "kwargs"):
            self.kwargs = {}
        if "text" in kwargs:
            self._text = kwargs["text"]
        self.kwargs.update(kwargs)

    def cget(self, key):
        if key == "text":
            return self._text
        return ""

    def winfo_exists(self):
        return self._exists

    def destroy(self):
        self._exists = False

    def title(self, val=None):
        if val is not None:
            self.title_val = val
        return self.title_val

    def geometry(self, val):
        pass

    def minsize(self, *args):
        pass

    def bind(self, *args, **kwargs):
        pass

    def after(self, ms, fn):
        return "after#1"

    def after_cancel(self, aid):
        pass


class DummyMenu:
    def __init__(self, *args, **kwargs):
        self.entries = []

    def add_command(self, **kwargs):
        self.entries.append(kwargs)

    def add_separator(self):
        self.entries.append({"separator": True})

    def add_cascade(self, **kwargs):
        self.entries.append(kwargs)


class DummyFont:
    def __init__(self, *args, **kwargs):
        pass


def _setup_stubs(monkeypatch):
    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = DummyVar
    fake_tk.BooleanVar = DummyVar
    fake_tk.IntVar = DummyVar
    fake_tk.DoubleVar = DummyVar
    fake_tk.Menu = DummyMenu
    fake_tk.Frame = DummyWidget
    fake_tk.Label = DummyWidget

    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_ttk.Treeview = DummyWidget
    fake_ttk.Scrollbar = DummyWidget
    fake_ttk.Style = DummyWidget
    fake_tk.ttk = fake_ttk

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTk = DummyWidget
    fake_ctk.CTkToplevel = DummyWidget
    fake_ctk.CTkFrame = DummyWidget
    fake_ctk.CTkLabel = DummyWidget
    fake_ctk.CTkButton = DummyWidget
    fake_ctk.CTkEntry = DummyWidget
    fake_ctk.CTkScrollableFrame = DummyWidget
    fake_ctk.CTkFont = DummyFont
    fake_ctk.StringVar = DummyVar
    fake_ctk.BooleanVar = DummyVar
    fake_ctk.IntVar = DummyVar
    fake_ctk.DoubleVar = DummyVar
    fake_ctk.set_appearance_mode = lambda *a, **k: None
    fake_ctk.set_default_color_theme = lambda *a, **k: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)


@pytest.fixture
def dummy_app(monkeypatch, tmp_db):
    """Instancie MainApp avec des mocks légers pour l'environnement headless."""
    set_db_file(str(tmp_db))
    run_migrations()

    _setup_stubs(monkeypatch)

    sys.modules.pop("ui.app", None)
    app_module = importlib.import_module("ui.app")
    MainApp = app_module.MainApp

    app = MainApp.__new__(MainApp)
    DummyWidget.__init__(app)
    app.title_val = ""

    def set_title(val=None):
        if val is not None:
            app.title_val = val
        return app.title_val

    app.title = set_title
    app._config = app._load_config()
    app._dashboard_frame = None
    app._after_sauvegarde_id = None
    app._build_status_bar()

    yield app, MainApp
    set_db_file("")


def test_naviguer_evenement_with_id_opens_fiche(dummy_app, monkeypatch):
    app, MainApp = dummy_app
    opened = {}

    def mock_ouvrir_evenement_fiche(self, evenement_id=None):
        opened["id"] = evenement_id

    def mock_ouvrir_evenements(self):
        opened["list"] = True

    monkeypatch.setattr(MainApp, "_ouvrir_evenement_fiche", mock_ouvrir_evenement_fiche)
    monkeypatch.setattr(MainApp, "_ouvrir_evenements", mock_ouvrir_evenements)

    # Avec ID -> fiche spécifique
    app._naviguer("evenement", 42)
    assert opened.get("id") == 42
    assert "list" not in opened

    # Sans ID -> liste des événements
    opened.clear()
    app._naviguer("evenement", None)
    assert opened.get("list") is True
    assert "id" not in opened


def test_naviguer_evenement_with_zero_id_opens_fiche(dummy_app, monkeypatch):
    app, MainApp = dummy_app
    opened = {}
    monkeypatch.setattr(
        MainApp,
        "_ouvrir_evenement_fiche",
        lambda self, evenement_id=None: opened.setdefault("id", evenement_id),
    )

    app._naviguer("evenement", 0)

    assert opened == {"id": 0}


def test_actualiser_configuration_refreshes_ui(dummy_app):
    app, _ = dummy_app
    conn = get_connection()
    try:
        conn.execute("DELETE FROM config")
        conn.execute(
            """
            INSERT INTO config (nom_asso, exercice, solde_ouverture)
            VALUES ('Asso Les Amis du Jeu', '2026-2027', 1500.50)
            """
        )
        conn.commit()
    finally:
        conn.close()

    app.actualiser_configuration()

    assert "Asso Les Amis du Jeu" in app.title_val
    assert "2026-2027" in app._status_balance_label._text
    assert "1 500,50 €" in app._status_balance_label._text


def test_ouvrir_config_asso_refreshes_after_dialog_closes(dummy_app, monkeypatch):
    app, _ = dummy_app
    opened = {}
    refreshes = []

    class ConfigDialog(DummyWidget):
        def __init__(self, parent):
            super().__init__(parent)
            opened["parent"] = parent
            opened["dialog"] = self

        def grab_set(self):
            opened["grabbed"] = True

    dialog_module = types.ModuleType(
        "ui.modules.evenements.config_asso_dialog"
    )
    dialog_module.ConfigAssoDialog = ConfigDialog
    monkeypatch.setitem(
        sys.modules, "ui.modules.evenements.config_asso_dialog", dialog_module
    )
    monkeypatch.setattr(
        app,
        "wait_window",
        lambda dialog: opened.setdefault("waited", dialog),
        raising=False,
    )
    monkeypatch.setattr(app, "actualiser_configuration", lambda: refreshes.append(True))

    app._ouvrir_config_asso()

    assert opened["parent"] is app
    assert opened["grabbed"] is True
    assert opened["waited"] is opened["dialog"]
    assert refreshes == [True]


def test_build_menu_exposes_asso_config_and_help(dummy_app, monkeypatch):
    app, _ = dummy_app
    import tkinter as tk

    created_menus = []

    def tracking_menu(*args, **kwargs):
        m = DummyMenu(*args, **kwargs)
        created_menus.append(m)
        return m

    monkeypatch.setattr(tk, "Menu", tracking_menu)
    app._build_menu()

    all_labels = [
        entry.get("label")
        for m in created_menus
        for entry in m.entries
        if "label" in entry
    ]

    assert "🏛️ Informations de l'association" in all_labels
    assert "📖 Manuel d'utilisation" in all_labels
    assert "ℹ️ À propos" in all_labels
