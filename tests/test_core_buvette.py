"""Tests du module métier core/buvette.py."""

from core.buvette import (
    calculer_net_caisses,
    valider_article_buvette,
    valider_caisse,
    valider_inventaire_lignes,
)


def test_valider_article_buvette_valide() -> None:
    erreurs = valider_article_buvette("Coca 33cL", "1,50", 1, 1)
    assert erreurs == []


def test_valider_article_buvette_erreurs() -> None:
    erreurs = valider_article_buvette("", "abc", None, None)
    assert len(erreurs) >= 3


def test_valider_caisse_valide() -> None:
    erreurs = valider_caisse("Caisse Bar", "50", "300")
    assert erreurs == []


def test_calculer_net_caisses() -> None:
    resultat = calculer_net_caisses(
        [
            {"fond_de_caisse": 50, "total_brut": 380},
            {"fond_de_caisse": 30, "total_brut": 210},
        ]
    )
    assert resultat["total_brut"] == 590
    assert resultat["total_fond_caisse"] == 80
    assert resultat["recette_nette"] == 510


def test_valider_inventaire_lignes_detecte_erreur() -> None:
    erreurs = valider_inventaire_lignes(
        [{"article_id": 1, "quantite_comptee": "abc"}]
    )
    assert erreurs
