"""Tests du module métier core/membres.py."""

import pytest

from core.membres import get_statuts_disponibles, valider_membre


def test_get_statuts_disponibles_returns_list() -> None:
    statuts = get_statuts_disponibles()
    assert isinstance(statuts, list)
    assert len(statuts) == 7


def test_get_statuts_disponibles_contient_president() -> None:
    statuts = get_statuts_disponibles()
    assert "Président(e)" in statuts


def test_get_statuts_disponibles_contient_membre() -> None:
    statuts = get_statuts_disponibles()
    assert "Membre" in statuts


def test_valider_membre_valide() -> None:
    erreurs = valider_membre(
        nom="Dupont",
        prenom="Marie",
        email="marie@example.com",
        telephone="0612345678",
        statut="Membre",
        date_adhesion="2024-01-01",
    )
    assert erreurs == []


def test_valider_membre_nom_manquant() -> None:
    erreurs = valider_membre(
        nom="",
        prenom="Marie",
        email="",
        telephone="",
        statut="Membre",
        date_adhesion="",
    )
    champs = [champ for champ, _ in erreurs]
    assert "nom" in champs


def test_valider_membre_prenom_manquant() -> None:
    erreurs = valider_membre(
        nom="Dupont",
        prenom="",
        email="",
        telephone="",
        statut="Membre",
        date_adhesion="",
    )
    champs = [champ for champ, _ in erreurs]
    assert "prenom" in champs


def test_valider_membre_email_invalide() -> None:
    erreurs = valider_membre(
        nom="Dupont",
        prenom="Marie",
        email="pas-un-email",
        telephone="",
        statut="Membre",
        date_adhesion="",
    )
    champs = [champ for champ, _ in erreurs]
    assert "email" in champs


def test_valider_membre_email_vide_autorise() -> None:
    erreurs = valider_membre(
        nom="Dupont",
        prenom="Marie",
        email="",
        telephone="",
        statut="Membre",
        date_adhesion="",
    )
    assert erreurs == []


def test_valider_membre_statut_invalide() -> None:
    erreurs = valider_membre(
        nom="Dupont",
        prenom="Marie",
        email="",
        telephone="",
        statut="Inconnu",
        date_adhesion="",
    )
    champs = [champ for champ, _ in erreurs]
    assert "statut" in champs


def test_valider_membre_plusieurs_erreurs() -> None:
    erreurs = valider_membre(
        nom="",
        prenom="",
        email="",
        telephone="",
        statut="Inconnu",
        date_adhesion="",
    )
    assert len(erreurs) >= 3
