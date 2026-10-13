from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace


def test_dashboard_quick_access_navigates_to_modules_and_help(monkeypatch):
    buttons = []

    class Widget:
        def __init__(self, *args, **kwargs):
            self.command = kwargs.get("command")
            buttons.append(self)

        def pack(self, *args, **kwargs):
            pass

    fake_tk = types.ModuleType("tkinter")
    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkFrame = fake_ctk.CTkToplevel = Widget
    fake_ctk.CTkLabel = fake_ctk.CTkButton = Widget
    fake_ctk.CTkFont = lambda **kwargs: None
    fake_ctk.set_appearance_mode = lambda *args, **kwargs: None
    fake_ctk.set_default_color_theme = lambda *args, **kwargs: None

    cached_modules = {
        name: sys.modules.get(name)
        for name in (
            "ui.modules.dashboard.dashboard",
            "ui.modules.dashboard.widgets",
            "ui.components.dialogs",
            "ui.theme",
        )
    }
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)
    dashboard_ui = importlib.import_module("ui.modules.dashboard.dashboard")

    destinations = []
    dashboard = SimpleNamespace(
        _scroll=object(),
        _navigation_callback=destinations.append,
    )
    dashboard_ui.DashboardFrame._section_raccourcis(dashboard)

    for button in buttons:
        if button.command:
            button.command()

    assert destinations == [
        "evenements",
        "tresorerie",
        "buvette",
        "membres",
        "dons",
        "configuration_association",
        "manuel",
    ]

    for name, cached in cached_modules.items():
        if cached is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = cached
