"""Helpers pour la manipulation des dates."""

from datetime import date, datetime


def aujourd_hui() -> str:
    """Retourne la date du jour au format ``JJ/MM/AAAA``."""
    return date.today().strftime("%d/%m/%Y")


def date_vers_str(d: date | datetime | None, fmt: str = "%d/%m/%Y") -> str:
    """Convertit une date en chaîne formatée.

    Args:
        d: Objet :class:`date` ou :class:`datetime`, ou ``None``.
        fmt: Format strftime souhaité.

    Returns:
        Chaîne formatée, ou chaîne vide si ``d`` est ``None``.
    """
    if d is None:
        return ""
    return d.strftime(fmt)


def str_vers_date(s: str, fmt: str = "%d/%m/%Y") -> date | None:
    """Convertit une chaîne en objet :class:`date`.

    Args:
        s: Chaîne à analyser.
        fmt: Format strftime attendu.

    Returns:
        Objet :class:`date`, ou ``None`` si la chaîne est vide ou invalide.
    """
    if not s or not s.strip():
        return None
    try:
        return datetime.strptime(s.strip(), fmt).date()
    except ValueError:
        return None


def annee_courante() -> int:
    """Retourne l'année civile en cours."""
    return date.today().year


def exercice_courant() -> str:
    """Retourne l'exercice en cours au format ``AAAA``."""
    return str(annee_courante())
