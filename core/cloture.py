"""Logique métier du module Clôture d'exercice (Phase 6b)."""

from __future__ import annotations

from datetime import date, datetime

from db.models.cloture import (
    add_exercice,
    get_all_exercices,
    get_exercice_by_id,
    get_stats_exercice,
)
from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def valider_cloture(exercice_id: int) -> list[str]:
    """Vérifie les prérequis avant de clôturer un exercice.

    Retourne la liste d'erreurs (vide si tout est OK).
    """
    erreurs: list[str] = []

    exercice = get_exercice_by_id(exercice_id)
    if not exercice:
        erreurs.append("Exercice introuvable.")
        return erreurs

    if exercice["statut"] != "ouvert":
        erreurs.append("L'exercice est déjà clôturé.")
        return erreurs

    # Vérifier les opérations en attente dans la période
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) as nb
                FROM tresorerie_operations
                WHERE statut = 'en_attente'
                  AND date_operation BETWEEN ? AND ?
                """,
                (exercice["date_debut"], exercice["date_fin"]),
            ).fetchone()
        finally:
            conn.close()
        nb_attente = row["nb"] if row else 0
        if nb_attente > 0:
            erreurs.append(
                f"{nb_attente} opération(s) en attente sur la période. "
                "Validez ou annulez-les avant la clôture."
            )
    except Exception:
        logger.exception("Erreur lors de la validation de clôture")
        erreurs.append("Impossible de vérifier les opérations en attente.")

    return erreurs


def calculer_solde_cloture(exercice_id: int) -> float:
    """Calcule le solde de clôture (ouverture + recettes - dépenses)."""
    stats = get_stats_exercice(exercice_id)
    return stats["solde_final"]


def calculer_solde_report(exercice_id: int) -> float:
    """Retourne le solde de clôture qui sera reporté en ouverture du prochain exercice."""
    return calculer_solde_cloture(exercice_id)


def generer_nom_exercice(type_exercice: str, date_debut: str) -> str:
    """Génère automatiquement un nom d'exercice.

    'scolaire' + '2025-09-01' → '2025-2026'
    'civile'   + '2025-01-01' → '2025'
    """
    try:
        dt = datetime.strptime(date_debut, "%Y-%m-%d")
    except ValueError:
        return date_debut

    if type_exercice == "civile":
        return str(dt.year)
    # Scolaire : sept → août de l'année suivante
    return f"{dt.year}-{dt.year + 1}"


def verifier_chevauchement(
    date_debut: str,
    date_fin: str,
    type_exercice: str,
    exclude_id: int | None = None,
) -> bool:
    """Vérifie si la période chevauche un exercice existant du même type.

    Retourne True si chevauchement détecté.
    """
    exercices = get_all_exercices(type_exercice)
    for ex in exercices:
        if exclude_id and int(ex["id"]) == exclude_id:
            continue
        # Chevauchement si les périodes se recoupent
        if ex["date_debut"] <= date_fin and ex["date_fin"] >= date_debut:
            return True
    return False


def get_operations_periode(date_debut: str, date_fin: str) -> list[dict]:
    """Retourne les opérations sur une période (pour vérification avant clôture)."""
    try:
        conn = get_connection()
        try:
            rows = conn.execute(
                """
                SELECT o.*, c.nom as compte_nom, cat.nom as categorie_nom
                FROM tresorerie_operations o
                LEFT JOIN comptes_bancaires c ON o.compte_id = c.id
                LEFT JOIN tresorerie_categories cat ON o.categorie_id = cat.id
                WHERE o.date_operation BETWEEN ? AND ?
                  AND o.statut != 'annule'
                ORDER BY o.date_operation ASC
                """,
                (date_debut, date_fin),
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]
    except Exception:
        logger.exception("Erreur lors de la récupération des opérations de la période")
        return []
