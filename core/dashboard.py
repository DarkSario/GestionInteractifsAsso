"""Couche métier du tableau de bord (Phase 8).

Aucun import tkinter/customtkinter dans ce module.
"""

from __future__ import annotations

from datetime import date

from db.models.dashboard import (
    get_alertes_stock,
    get_benevoles_prochains_evenements,
    get_bilan_dernier_evenement,
    get_cheques_en_attente,
    get_comparatif_mois,
    get_evenement_en_cours,
    get_evolution_tresorerie,
    get_info_derniere_sauvegarde,
    get_prochains_evenements,
    get_recettes_depenses_mois,
    get_solde_global,
    get_stats_adherents_dashboard,
    get_stats_subventions_dashboard,
)
from utils.logger import get_logger

logger = get_logger(__name__)

_MOIS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def get_donnees_dashboard() -> dict:
    """Agrège toutes les données nécessaires pour le tableau de bord en un seul appel.

    Returns:
        Dictionnaire complet contenant toutes les sections du dashboard.
    """
    today = date.today()
    annee = today.year
    mois = today.month

    try:
        solde_global = get_solde_global()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_solde_global: %s", exc)
        solde_global = {"solde_total": 0.0, "solde_bancaire": 0.0, "solde_caisse": 0.0, "par_compte": []}

    try:
        recettes_depenses = get_recettes_depenses_mois(annee, mois)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_recettes_depenses_mois: %s", exc)
        recettes_depenses = {"total_recettes": 0.0, "total_depenses": 0.0, "solde_net": 0.0}

    try:
        comparatif = get_comparatif_mois(annee, mois)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_comparatif_mois: %s", exc)
        comparatif = {
            "mois_actuel": {"recettes": 0.0, "depenses": 0.0},
            "mois_precedent": {"recettes": 0.0, "depenses": 0.0},
            "variation_recettes_pct": 0.0,
            "variation_depenses_pct": 0.0,
        }

    try:
        evolution = get_evolution_tresorerie(12)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_evolution_tresorerie: %s", exc)
        evolution = []

    try:
        cheques = get_cheques_en_attente()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_cheques_en_attente: %s", exc)
        cheques = {"nb_remises": 0, "montant_total": 0.0, "details": []}

    try:
        subventions = get_stats_subventions_dashboard()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_stats_subventions_dashboard: %s", exc)
        subventions = {"montant_demande": 0.0, "montant_obtenu": 0.0, "nb_en_attente": 0, "progression_pct": 0.0}

    try:
        prochains_evenements = get_prochains_evenements(3)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_prochains_evenements: %s", exc)
        prochains_evenements = []

    try:
        evenement_en_cours = get_evenement_en_cours()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_evenement_en_cours: %s", exc)
        evenement_en_cours = None

    try:
        bilan_dernier_evenement = get_bilan_dernier_evenement()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_bilan_dernier_evenement: %s", exc)
        bilan_dernier_evenement = None

    try:
        nb_benevoles = get_benevoles_prochains_evenements()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_benevoles_prochains_evenements: %s", exc)
        nb_benevoles = 0

    try:
        stats_adherents = get_stats_adherents_dashboard()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_stats_adherents_dashboard: %s", exc)
        stats_adherents = {
            "nb_total": 0, "nb_actifs": 0, "nb_cotisation_non_reglee": 0,
            "montant_cotisations_dues": 0.0, "nb_nouveaux_ce_mois": 0,
        }

    try:
        alertes_stock = get_alertes_stock()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_alertes_stock: %s", exc)
        alertes_stock = {"critique": [], "faible": []}

    try:
        from core.alertes import get_alertes

        toutes_alertes = get_alertes()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_alertes: %s", exc)
        toutes_alertes = []

    try:
        derniere_sauvegarde = get_info_derniere_sauvegarde()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_info_derniere_sauvegarde: %s", exc)
        derniere_sauvegarde = {"date": "", "nb_jours_depuis": None, "chemin": ""}

    return {
        "periode": get_resume_mois_courant(),
        "solde_global": solde_global,
        "recettes_depenses": recettes_depenses,
        "comparatif": comparatif,
        "evolution": evolution,
        "cheques": cheques,
        "subventions": subventions,
        "prochains_evenements": prochains_evenements,
        "evenement_en_cours": evenement_en_cours,
        "bilan_dernier_evenement": bilan_dernier_evenement,
        "nb_benevoles": nb_benevoles,
        "adherents": stats_adherents,
        "stock": alertes_stock,
        "alertes": toutes_alertes,
        "derniere_sauvegarde": derniere_sauvegarde,
    }


def formater_variation(valeur_actuelle: float, valeur_precedente: float) -> dict:
    """Formate la variation entre deux valeurs.

    Returns:
        {variation_pct, sens: 'hausse'|'baisse'|'stable', couleur}
    """
    if valeur_precedente == 0:
        return {"variation_pct": 0.0, "sens": "stable", "couleur": "gray"}
    variation_pct = round((valeur_actuelle - valeur_precedente) / abs(valeur_precedente) * 100, 1)
    if variation_pct > 0:
        return {"variation_pct": variation_pct, "sens": "hausse", "couleur": "green"}
    if variation_pct < 0:
        return {"variation_pct": abs(variation_pct), "sens": "baisse", "couleur": "red"}
    return {"variation_pct": 0.0, "sens": "stable", "couleur": "gray"}


def calculer_progression_subventions(demande: float, obtenu: float) -> float:
    """Calcule le pourcentage de progression des subventions (0-100).

    Args:
        demande: Montant total demandé.
        obtenu: Montant total obtenu.

    Returns:
        Pourcentage entre 0.0 et 100.0.
    """
    if demande <= 0:
        return 0.0
    return min(100.0, round(obtenu / demande * 100, 1))


def get_resume_mois_courant() -> str:
    """Retourne le mois et l'année courants formatés, ex. « Juillet 2026 ».

    Returns:
        Chaîne formatée.
    """
    today = date.today()
    return f"{_MOIS_FR[today.month - 1]} {today.year}"
