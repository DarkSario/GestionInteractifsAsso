"""Couche métier pour les cotisations adhérents (Phase 16).

Ne doit pas importer tkinter ni customtkinter.
"""

from __future__ import annotations

from datetime import date

from db.models.cotisations import (
    add_cotisation,
    get_cotisations_adherent,
    get_nb_cotisations_en_attente,
    get_stats_cotisations,
    renouveler_cotisations_masse,
    update_cotisation,
)
from db.models.parametres_globaux import get_parametre, set_parametre
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Paramètre montant par défaut ──────────────────────────────────────────────


def get_montant_cotisation_defaut() -> float:
    """Retourne le montant de cotisation par défaut (0.0 = offerte)."""
    try:
        return float(get_parametre("cotisation_montant_defaut", "0.0"))
    except (ValueError, TypeError):
        return 0.0


def set_montant_cotisation_defaut(montant: float) -> bool:
    """Sauvegarde le montant de cotisation par défaut dans les paramètres."""
    return set_parametre("cotisation_montant_defaut", str(montant))


# ── Logique métier ────────────────────────────────────────────────────────────


def cotisation_est_a_jour(adherent_id: int, annee: int) -> bool:
    """Retourne True si l'adhérent a une cotisation 'payee' ou 'offerte' pour l'année.

    Une cotisation 'en_attente' signifie qu'elle n'est PAS à jour.
    L'absence de cotisation est considérée comme à jour (comportement par défaut :
    cotisation offerte à 0€).
    """
    cotisations = get_cotisations_adherent(adherent_id)
    cotisation_annee = next((c for c in cotisations if c["annee"] == annee), None)
    if cotisation_annee is None:
        return True
    return cotisation_annee["statut"] in ("payee", "offerte")


def get_annee_courante() -> int:
    """Retourne l'année courante (ex. 2026)."""
    return date.today().year


def renouveler_annee_courante(
    annee: int | None = None,
    montant: float | None = None,
    statut: str | None = None,
    exercice_id: int | None = None,
) -> int:
    """Renouvelle les cotisations pour l'année (ou l'année courante).

    Utilise le montant par défaut si non précisé.
    """
    if annee is None:
        annee = get_annee_courante()
    if montant is None:
        montant = get_montant_cotisation_defaut()
    if statut is None:
        statut = "offerte" if montant == 0.0 else "en_attente"

    return renouveler_cotisations_masse(annee, montant, statut, exercice_id)


def get_alertes_cotisations() -> list[dict]:
    """Retourne les alertes de cotisations pour le tableau de bord.

    Returns:
        [{niveau, message, module, lien_action}]
    """
    alertes = []
    annee = get_annee_courante()
    nb_en_attente = get_nb_cotisations_en_attente(annee)
    if nb_en_attente > 0:
        alertes.append(
            {
                "niveau": "orange",
                "message": (
                    f"{nb_en_attente} cotisation(s) en attente pour {annee}"
                ),
                "module": "membres",
                "lien_action": "membres",
            }
        )
    return alertes


__all__ = [
    "get_montant_cotisation_defaut",
    "set_montant_cotisation_defaut",
    "cotisation_est_a_jour",
    "get_annee_courante",
    "renouveler_annee_courante",
    "get_alertes_cotisations",
    "add_cotisation",
    "get_cotisations_adherent",
    "get_stats_cotisations",
    "update_cotisation",
]
