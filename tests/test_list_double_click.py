from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("module_name", "class_name"),
    (
        ("ui.modules.dons.liste", "ListeDons"),
        ("ui.modules.remboursements.liste", "ListeRemboursements"),
    ),
)
def test_double_click_opens_selected_item_for_edit(module_name, class_name, monkeypatch):
    class Widget:
        pass

    fake_tk = types.ModuleType("tkinter")
    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_tk.ttk = fake_ttk
    fake_tk.filedialog = types.ModuleType("tkinter.filedialog")
    fake_ctk = types.ModuleType("customtkinter")
    for name in (
        "CTkToplevel",
        "CTkFrame",
        "CTkLabel",
        "CTkButton",
        "CTkEntry",
        "CTkOptionMenu",
        "CTkSegmentedButton",
    ):
        setattr(fake_ctk, name, Widget)
    fake_ctk.CTkFont = lambda **kwargs: None

    module_names = (
        module_name,
        "ui.components.form_dialog",
        "ui.components.dialogs",
        "ui.theme",
    )
    cached_modules = {name: sys.modules.get(name) for name in module_names}
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fake_tk.filedialog)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)
    try:
        list_class = getattr(importlib.import_module(module_name), class_name)
        opened = []
        screen = SimpleNamespace(_modifier=lambda: opened.append(True))

        list_class._on_double_click(screen, None)

        assert opened == [True]
    finally:
        for name, cached in cached_modules.items():
            if cached is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = cached
