"""Tests ciblés du formulaire membre avec cotisation rapide."""

from __future__ import annotations

import importlib
import sys
import types


class _Widget:
    def __init__(self, *_args, **_kwargs) -> None:
        return None

    def grid(self, *_args, **_kwargs) -> None:
        return None

    def pack(self, *_args, **_kwargs) -> None:
        return None

    def configure(self, **kwargs) -> None:
        self.kwargs = kwargs


class _ErrorLabel:
    def __init__(self) -> None:
        self.text = ""

    def configure(self, **kwargs) -> None:
        self.text = kwargs.get("text", self.text)


def _load_module(monkeypatch):
    fake_ctk = types.ModuleType("customtkinter")
    fake_ctk.CTkToplevel = _Widget
    fake_ctk.CTkLabel = _Widget
    fake_ctk.CTkEntry = _Widget
    fake_ctk.CTkFrame = _Widget
    fake_ctk.CTkButton = _Widget
    fake_ctk.CTkOptionMenu = _Widget
    fake_ctk.CTkTextbox = _Widget
    fake_ctk.StringVar = lambda value=None: types.SimpleNamespace(get=lambda: value)
    monkeypatch.setitem(sys.modules, "customtkinter", fake_ctk)

    fake_cotisations = types.ModuleType("ui.modules.membres.cotisations")
    fake_cotisations.MiniFormulaireCotisationRapide = _Widget
    monkeypatch.setitem(sys.modules, "ui.modules.membres.cotisations", fake_cotisations)

    sys.modules.pop("ui.modules.membres.formulaire", None)
    return importlib.import_module("ui.modules.membres.formulaire")


def test_soumettre_sauve_la_cotisation_rapide(monkeypatch) -> None:
    module = _load_module(monkeypatch)
    adherent_ids: list[int] = []
    cotisations: list[tuple[int, dict]] = []

    monkeypatch.setattr(module, "valider_membre", lambda *_args: [])
    monkeypatch.setattr(module, "add_membre", lambda *_args: 42)

    form = module.FormulaireMembreModal.__new__(module.FormulaireMembreModal)
    form._est_edition = False
    form._membre = None
    form._cotisation_rapide_initiale = None
    form._error_labels = {"nom": _ErrorLabel(), "cotisation_rapide": _ErrorLabel()}
    form._lire_valeur = lambda champ: {
        "nom": "Durand",
        "prenom": "Alice",
        "email": "",
        "telephone": "",
        "statut": "Membre",
        "date_adhesion": "2026-01-01",
        "commentaire": "",
    }[champ]
    form._cotisation_rapide = types.SimpleNamespace(
        cotisation_active=lambda: True,
        lire_saisie=lambda: (
            {"annee": 2026, "montant": 20.0, "statut": "payee"},
            None,
        )
    )
    form._sauver_cotisation_rapide = lambda adherent_id, payload: (
        adherent_ids.append(adherent_id),
        cotisations.append((adherent_id, payload)),
        True,
    )[-1]
    form.destroyed = False
    form.destroy = lambda: setattr(form, "destroyed", True)

    form._soumettre()

    assert adherent_ids == [42]
    assert cotisations == [(42, {"annee": 2026, "montant": 20.0, "statut": "payee"})]
    assert form.destroyed is True


def test_soumettre_bloque_si_cotisation_rapide_invalide(monkeypatch) -> None:
    module = _load_module(monkeypatch)
    appels_add: list[bool] = []

    monkeypatch.setattr(module, "valider_membre", lambda *_args: [])
    monkeypatch.setattr(
        module,
        "add_membre",
        lambda *_args: (appels_add.append(True), 10)[1],
    )

    form = module.FormulaireMembreModal.__new__(module.FormulaireMembreModal)
    form._est_edition = False
    form._membre = None
    form._cotisation_rapide_initiale = None
    form._error_labels = {"nom": _ErrorLabel(), "cotisation_rapide": _ErrorLabel()}
    form._lire_valeur = lambda champ: {
        "nom": "Durand",
        "prenom": "Alice",
        "email": "",
        "telephone": "",
        "statut": "Membre",
        "date_adhesion": "2026-01-01",
        "commentaire": "",
    }[champ]
    form._cotisation_rapide = types.SimpleNamespace(
        cotisation_active=lambda: True,
        lire_saisie=lambda: (None, "L'année de cotisation doit être un entier.")
    )
    form._sauver_cotisation_rapide = lambda *_args: True
    form.destroy = lambda: None

    form._soumettre()

    assert appels_add == []
    assert (
        form._error_labels["cotisation_rapide"].text
        == "L'année de cotisation doit être un entier."
    )


def test_soumettre_garde_la_fenetre_ouverte_si_cotisation_rapide_echoue(monkeypatch) -> None:
    module = _load_module(monkeypatch)

    monkeypatch.setattr(module, "valider_membre", lambda *_args: [])
    monkeypatch.setattr(module, "add_membre", lambda *_args: 12)

    form = module.FormulaireMembreModal.__new__(module.FormulaireMembreModal)
    form._est_edition = False
    form._membre = None
    form._cotisation_rapide_initiale = None
    form._error_labels = {"nom": _ErrorLabel(), "cotisation_rapide": _ErrorLabel()}
    form._lire_valeur = lambda champ: {
        "nom": "Durand",
        "prenom": "Alice",
        "email": "",
        "telephone": "",
        "statut": "Membre",
        "date_adhesion": "2026-01-01",
        "commentaire": "",
    }[champ]
    form._cotisation_rapide = types.SimpleNamespace(
        cotisation_active=lambda: True,
        lire_saisie=lambda: (
            {"annee": 2026, "montant": 20.0, "statut": "payee"},
            None,
        ),
    )
    form._sauver_cotisation_rapide = lambda *_args: False
    form.destroyed = False
    form.destroy = lambda: setattr(form, "destroyed", True)

    form._soumettre()

    assert form.destroyed is False


def test_sauver_cotisation_rapide_met_a_jour_la_cotisation_existante(monkeypatch) -> None:
    module = _load_module(monkeypatch)
    maj_calls: list[tuple[int, dict]] = []

    monkeypatch.setattr(
        module,
        "get_cotisations_adherent",
        lambda _adherent_id: [{"id": 7, "annee": 2026, "montant": 10.0, "statut": "en_attente"}],
    )
    monkeypatch.setattr(
        module,
        "update_cotisation",
        lambda cotisation_id, **kwargs: (maj_calls.append((cotisation_id, kwargs)), True)[1],
    )

    form = module.FormulaireMembreModal.__new__(module.FormulaireMembreModal)
    form._cotisation_rapide_initiale = None
    form._error_labels = {"cotisation_rapide": _ErrorLabel()}

    ok = form._sauver_cotisation_rapide(
        3,
        {"annee": 2026, "montant": 15.0, "statut": "payee"},
    )

    assert ok is True
    assert maj_calls == [
        (
            7,
            {
                "annee": 2026,
                "montant": 15.0,
                "statut": "payee",
            },
        )
    ]
