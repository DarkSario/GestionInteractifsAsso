"""Fonctions de validation des saisies utilisateur."""

import re
from datetime import datetime


def est_non_vide(valeur: str) -> bool:
    """Vérifie que la valeur n'est pas vide ou composée uniquement d'espaces."""
    return bool(valeur and valeur.strip())


def est_email_valide(email: str) -> bool:
    """Vérifie qu'une adresse e-mail est syntaxiquement valide."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip())) if email else False


def est_telephone_valide(telephone: str) -> bool:
    """Vérifie qu'un numéro de téléphone est valide (format FR ou international)."""
    pattern = r"^(\+?\d[\d\s\-\.]{7,14}\d)$"
    return bool(re.match(pattern, telephone.strip())) if telephone else False


def est_montant_valide(valeur: str) -> bool:
    """Vérifie qu'une chaîne représente un montant numérique positif."""
    try:
        return float(valeur.replace(",", ".")) >= 0
    except (ValueError, AttributeError):
        return False


def est_date_valide(valeur: str, fmt: str = "%d/%m/%Y") -> bool:
    """Vérifie qu'une chaîne correspond au format de date attendu."""
    if not valeur or not valeur.strip():
        return False
    try:
        datetime.strptime(valeur.strip(), fmt)
        return True
    except ValueError:
        return False


def valider_champs(champs: dict[str, str]) -> list[str]:
    """Valide un dictionnaire de champs obligatoires (non vides).

    Args:
        champs: Dictionnaire ``{label: valeur}`` à vérifier.

    Returns:
        Liste des labels dont la valeur est vide ou absente.
    """
    return [label for label, valeur in champs.items() if not est_non_vide(valeur)]
