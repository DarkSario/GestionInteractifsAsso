"""Tests ciblés pour le dialogue bénévole et le dialogue des modules dans la fiche événement."""

from __future__ import annotations

import logging
import sys
import types


class _DummyVar:
    def __init__(self, value=None) -> None:
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class _DummyWidget:
    def __init__(self, parent=None, **kwargs) -> None:
        self.parent = parent
        self.master = parent
        self.kwargs = kwargs
        self.children: list[_DummyWidget] = []
        self.destroyed = False
        self._pack_called = False
        self._pack_forget_called = False
        if parent is not None and hasattr(parent, "children"):
            parent.children.append(self)

    def pack(self, *_args, **kwargs) -> None:
        self._pack_called = True

    def pack_forget(self) -> None:
        self._pack_forget_called = True

    def grid(self, *_args, **kwargs) -> None:
        pass

    def bind(self, *_args, **kwargs) -> None:
        pass

    def configure(self, **kwargs) -> None:
        self.kwargs.update(kwargs)

    def destroy(self) -> None:
        self.destroyed = True

    def title(self, value: str) -> None:
        self.title_value = value

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def minsize(self, *args) -> None:
        pass

    def resizable(self, *args) -> None:
        pass

    def transient(self, *args) -> None:
        pass

    def grab_set(self) -> None:
        pass

    def winfo_children(self) -> list[_DummyWidget]:
        return self.children


class _DummyOptionMenu(_DummyWidget):
    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.values = kwargs.get("values", [])
        self.variable = kwargs.get("variable")

    def get(self):
        if self.variable:
            return self.variable.get()
        return self.values[0] if self.values else ""

    def set(self, val):
        if self.variable:
            self.variable.set(val)


def _load_fiche_module_with_ui_stubs(monkeypatch):
    fake_ttk = types.ModuleType("tkinter.ttk")
    fake_ttk.Treeview = _DummyWidget
    fake_ttk.Scrollbar = _DummyWidget
    fake_ttk.Combobox = _DummyOptionMenu
    fake_ttk.Style = _DummyWidget

    fake_simpledialog = types.ModuleType("tkinter.simpledialog")
    fake_simpledialog.askstring = lambda *args, **kwargs: None

    fake_filedialog = types.ModuleType("tkinter.filedialog")
    fake_filedialog.asksaveasfilename = lambda *args, **kwargs: ""
    fake_filedialog.askopenfilename = lambda *args, **kwargs: ""

    fake_messagebox = types.ModuleType("tkinter.messagebox")
    fake_messagebox.showinfo = lambda *args, **kwargs: None
    fake_messagebox.showerror = lambda *args, **kwargs: None
    fake_messagebox.askyesno = lambda *args, **kwargs: True

    fake_tk = types.ModuleType("tkinter")
    fake_tk.StringVar = _DummyVar
    fake_tk.BooleanVar = _DummyVar
    fake_tk.IntVar = _DummyVar
    fake_tk.DoubleVar = _DummyVar
    fake_tk.Toplevel = _DummyWidget
    fake_tk.Frame = _DummyWidget
    fake_tk.Label = _DummyWidget
    fake_tk.Entry = _DummyWidget
    fake_tk.Button = _DummyWidget
    fake_tk.Checkbutton = _DummyWidget
    fake_tk.Menu = _DummyWidget
    fake_tk.ttk = fake_ttk
    fake_tk.simpledialog = fake_simpledialog
    fake_tk.filedialog = fake_filedialog
    fake_tk.messagebox = fake_messagebox

    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkToplevel = _DummyWidget
    fake_ctk.CTkFrame = _DummyWidget
    fake_ctk.CTkScrollableFrame = _DummyWidget
    fake_ctk.CTkLabel = _DummyWidget
    fake_ctk.CTkEntry = _DummyWidget
    fake_ctk.CTkButton = _DummyWidget
    fake_ctk.CTkOptionMenu = _DummyOptionMenu
    fake_ctk.CTkCheckBox = _DummyWidget
    fake_ctk.CTkRadioButton = _DummyWidget
    fake_ctk.CTkTabview = _DummyWidget
    fake_ctk.CTkFont = _DummyWidget
    fake_ctk.StringVar = _DummyVar
    fake_ctk.BooleanVar = _DummyVar
    fake_ctk.IntVar = _DummyVar
    fake_ctk.DoubleVar = _DummyVar
    fake_ctk.set_appearance_mode = lambda *a: None
    fake_ctk.set_default_color_theme = lambda *a: None

    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", fake_ttk)
    monkeypatch.setitem(sys.modules, "tkinter.simpledialog", fake_simpledialog)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", fake_filedialog)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", fake_messagebox)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    for mod in list(sys.modules.keys()):
        if mod.startswith("ui."):
            sys.modules.pop(mod, None)

    import importlib
    return importlib.import_module("ui.modules.evenements.fiche")


def test_dialog_benevole_instantiation_nouveau(monkeypatch):
    """Vérifie que _DialogBenevole s'instancie sans lever d'AttributeError sur les anciens champs d'avance de frais."""
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    parent = _DummyWidget()
    membres = [
        {"id": 1, "nom": "Dupont", "prenom": "Jean"},
        {"id": 2, "nom": "Martin", "prenom": "Sophie"},
    ]
    dialog = fiche._DialogBenevole(parent, membres=membres, benevole=None)

    assert dialog is not None
    assert not hasattr(dialog, "_var_avance_par")
    assert not hasattr(dialog, "_var_remboursement")
    assert dialog._var_type.get() == "Membre"
    assert dialog.result is None


def test_dialog_benevole_instantiation_externe(monkeypatch):
    """Vérifie l'instanciation en mode bénévole externe."""
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    parent = _DummyWidget()
    benevole = {
        "id": 10,
        "membre_id": None,
        "nom_externe": "Curie",
        "prenom_externe": "Marie",
        "role": "Accueil",
        "heure_debut": "09:00",
        "heure_fin": "12:00",
        "statut": "confirme",
        "commentaire": "Disponible le matin",
    }
    dialog = fiche._DialogBenevole(parent, membres=[], benevole=benevole)

    assert dialog._var_type.get() == "Externe"
    assert dialog._var_nom_ext.get() == "Curie"
    assert dialog._var_prenom_ext.get() == "Marie"
    assert dialog._var_role.get() == "Accueil"


def test_dialog_benevole_valider_membre(monkeypatch):
    """Vérifie la validation pour un bénévole membre."""
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    parent = _DummyWidget()
    membres = [{"id": 42, "nom": "Durand", "prenom": "Paul"}]
    dialog = fiche._DialogBenevole(parent, membres=membres, benevole=None)

    dialog._var_type.set("Membre")
    dialog._combo_membre.set("Paul Durand")
    dialog._var_role.set("Barman")
    dialog._var_h_debut.set("14:00")
    dialog._var_h_fin.set("18:00")
    dialog._var_statut.set("Confirmé")
    dialog._var_commentaire.set("Poste buvette")

    dialog._valider()

    assert dialog.result is not None
    assert dialog.result["membre_id"] == 42
    assert dialog.result["nom_externe"] is None
    assert dialog.result["role"] == "Barman"
    assert dialog.result["statut"] == "confirme"
    assert dialog.destroyed is True


def test_dialog_benevole_valider_externe(monkeypatch):
    """Vérifie la validation pour un bénévole externe."""
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    parent = _DummyWidget()
    dialog = fiche._DialogBenevole(parent, membres=[], benevole=None)

    dialog._var_type.set("Externe")
    dialog._var_nom_ext.set("Lovelace")
    dialog._var_prenom_ext.set("Ada")
    dialog._var_role.set("Animation")
    dialog._var_statut.set("Désisté")

    dialog._valider()

    assert dialog.result is not None
    assert dialog.result["membre_id"] is None
    assert dialog.result["nom_externe"] == "Lovelace"
    assert dialog.result["prenom_externe"] == "Ada"
    assert dialog.result["role"] == "Animation"
    assert dialog.result["statut"] == "desiste"
    assert dialog.destroyed is True


def test_dialog_modules(monkeypatch):
    """Vérifie l'instanciation et la validation du dialogue de sélection des modules."""
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    parent = _DummyWidget()
    dialog = fiche._DialogModules(parent, modules_actuels=["billetterie", "caisses"])

    assert dialog._vars["billetterie"].get() is True
    assert dialog._vars["caisses"].get() is True
    assert dialog._vars["benevoles"].get() is False

    dialog._vars["benevoles"].set(True)
    dialog._vars["billetterie"].set(False)

    dialog._valider()

    assert dialog.result is not None
    assert "benevoles" in dialog.result
    assert "caisses" in dialog.result
    assert "billetterie" not in dialog.result
    assert dialog.destroyed is True


def test_onglets_modules_a_masquer(monkeypatch):
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    assert fiche._onglets_modules_a_masquer({"billetterie"}) == [
        "💸 Dépenses",
        "💰 Budget",
        "👥 Bénévoles",
        "🎰 Tombola",
        "🏪 Stands",
        "📊 Tableaux",
        "🧾 Caisses",
    ]
    assert (
        fiche._onglets_modules_a_masquer(set(fiche.MODULES_EVENEMENT_DISPONIBLES))
        == []
    )


def test_fiche_build_ui_delegue_entete_et_onglets(monkeypatch):
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)
    instance = object.__new__(fiche.FicheEvenement)
    appels = []
    instance._build_header = lambda: appels.append("header")
    instance._build_tabs = lambda: appels.append("tabs")

    instance._build_ui()

    assert appels == ["header", "tabs"]


def test_actualiser_resume_financier_logue_une_erreur(monkeypatch, caplog):
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    def fail_to_calculate(_evenement_id):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(fiche, "calculer_bilan_evenement", fail_to_calculate)
    instance = object.__new__(fiche.FicheEvenement)
    instance._evenement_id = 17

    with caplog.at_level(logging.ERROR, logger=fiche.logger.name):
        instance._actualiser_resume_financier()

    assert (
        "Impossible d'actualiser le résumé financier de l'événement 17." in caplog.text
    )


def test_charger_fournisseurs_logue_une_erreur(monkeypatch, caplog):
    fiche = _load_fiche_module_with_ui_stubs(monkeypatch)

    def fail_to_load():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(fiche, "get_all_fournisseurs", fail_to_load)
    with caplog.at_level(logging.ERROR, logger=fiche.logger.name):
        fournisseurs = fiche._DialogDepense._charger_fournisseurs()

    assert fournisseurs == []
    assert "Impossible de charger les fournisseurs" in caplog.text
