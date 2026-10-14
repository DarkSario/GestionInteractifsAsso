from __future__ import annotations

from types import SimpleNamespace

import pytest

from ui.modules.tresorerie import operations


def test_verification_cloture_journalisee_et_inconnue_en_cas_erreur(
    monkeypatch, caplog
):
    from db import connection

    def fail_to_connect():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(connection, "get_connection", fail_to_connect)

    with caplog.at_level("ERROR", logger=operations.logger.name):
        result = operations._periode_contient_cloture()

    assert result is None
    assert "Impossible de vérifier l'état de clôture de la trésorerie." in caplog.text


def test_charger_mouvements_signale_une_erreur_et_la_journalise(
    monkeypatch, caplog
):
    pytest.importorskip("_tkinter")
    from ui.modules.stock import mouvements

    messages = []

    class Tree:
        def delete(self, *_items):
            pass

        def get_children(self):
            return []

    def fail_to_load(_article_id):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(mouvements, "get_article_by_id", fail_to_load)
    instance = object.__new__(mouvements.MouvementsStock)
    instance._article = {"id": 42, "nom": "Matériel"}
    instance._tree = Tree()
    instance._label_stock = SimpleNamespace(configure=lambda **_kwargs: None)
    monkeypatch.setattr(
        mouvements,
        "afficher_erreur",
        lambda _parent, title, message: messages.append((title, message)),
    )

    with caplog.at_level("ERROR", logger=mouvements.logger.name):
        instance._charger_mouvements()

    assert instance._mouvements == []
    assert "article 42" in caplog.text
    assert messages and messages[0][0] == "Mouvements de stock"
    assert "Matériel" in messages[0][1]


def test_formulaire_article_signale_les_referentiels_indisponibles(
    monkeypatch, caplog
):
    pytest.importorskip("_tkinter")
    from ui.modules.stock import formulaire_article

    def fail_to_load():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(formulaire_article, "get_all_categories", fail_to_load)
    monkeypatch.setattr(formulaire_article, "get_all_unites", fail_to_load)
    monkeypatch.setattr(
        formulaire_article, "get_fournisseurs_for_select", fail_to_load
    )
    messages = []
    monkeypatch.setattr(
        formulaire_article,
        "afficher_erreur",
        lambda _parent, title, message: messages.append((title, message)),
    )
    instance = object.__new__(formulaire_article.FormulaireArticle)

    with caplog.at_level("ERROR", logger=formulaire_article.logger.name):
        instance._charger_referentiels()

    assert instance._categories == []
    assert instance._unites == []
    assert instance._fournisseurs == []
    assert "Impossible de charger les catégories" in caplog.text
    assert messages == [
        (
            "Référentiels du stock",
            "Impossible de charger : catégories, unités, fournisseurs.",
        )
    ]
