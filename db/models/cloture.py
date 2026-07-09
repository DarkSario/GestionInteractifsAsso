"""CRUD du module Clôture d'exercice (Phase 6b)."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _execute(query: str, params: tuple = ()) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


# ── Exercices ────────────────────────────────────────────────────────────────


def get_all_exercices(type_exercice: str | None = None) -> list[dict]:
    """Retourne tous les exercices, optionnellement filtrés par type."""
    if type_exercice:
        return _fetch_all(
            "SELECT * FROM exercices WHERE type_exercice = ? ORDER BY date_debut DESC",
            (type_exercice,),
        )
    return _fetch_all("SELECT * FROM exercices ORDER BY date_debut DESC")


def get_exercice_by_id(exercice_id: int) -> dict | None:
    """Retourne un exercice par son ID."""
    return _fetch_one("SELECT * FROM exercices WHERE id = ?", (exercice_id,))


def get_exercice_courant(type_exercice: str) -> dict | None:
    """Retourne l'exercice ouvert du type donné."""
    return _fetch_one(
        """
        SELECT * FROM exercices
        WHERE type_exercice = ? AND statut = 'ouvert'
        ORDER BY date_debut DESC
        LIMIT 1
        """,
        (type_exercice,),
    )


def add_exercice(
    nom: str,
    type_exercice: str,
    date_debut: str,
    date_fin: str,
    solde_ouverture: float,
    commentaire: str | None = None,
) -> int:
    """Crée un nouvel exercice et retourne son ID."""
    return _execute(
        """
        INSERT INTO exercices
        (nom, type_exercice, date_debut, date_fin, solde_ouverture, commentaire)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (nom, type_exercice, date_debut, date_fin, float(solde_ouverture or 0), commentaire),
    )


def cloturer_exercice(exercice_id: int, solde_cloture: float) -> bool:
    """Clôture un exercice.

    1. Met statut='cloture', date_cloture=now(), solde_cloture.
    2. Verrouille les opérations de la période (statut → 'rapproche').
    3. Insère un log 'cloture'.
    """
    exercice = get_exercice_by_id(exercice_id)
    if not exercice or exercice["statut"] != "ouvert":
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE exercices
            SET statut = 'cloture',
                date_cloture = ?,
                solde_cloture = ?
            WHERE id = ?
            """,
            (now, float(solde_cloture), exercice_id),
        )
        # Verrouiller les opérations valides de la période
        conn.execute(
            """
            UPDATE tresorerie_operations
            SET statut = 'rapproche'
            WHERE statut = 'valide'
              AND date_operation BETWEEN ? AND ?
            """,
            (exercice["date_debut"], exercice["date_fin"]),
        )
        conn.execute(
            """
            INSERT INTO exercices_log (exercice_id, action, commentaire)
            VALUES (?, 'cloture', ?)
            """,
            (exercice_id, exercice.get("commentaire")),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de la clôture de l'exercice %d", exercice_id)
        return False
    finally:
        conn.close()


def decloturer_exercice(exercice_id: int) -> bool:
    """Déclôture un exercice.

    1. Met statut='ouvert', date_decloture=now().
    2. Déverrouille les opérations (statut 'rapproche' → 'valide').
    3. Insère un log 'decloture'.
    """
    exercice = get_exercice_by_id(exercice_id)
    if not exercice or exercice["statut"] != "cloture":
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE exercices
            SET statut = 'ouvert',
                date_decloture = ?
            WHERE id = ?
            """,
            (now, exercice_id),
        )
        # Déverrouiller les opérations de la période
        conn.execute(
            """
            UPDATE tresorerie_operations
            SET statut = 'valide'
            WHERE statut = 'rapproche'
              AND date_operation BETWEEN ? AND ?
            """,
            (exercice["date_debut"], exercice["date_fin"]),
        )
        conn.execute(
            """
            INSERT INTO exercices_log (exercice_id, action)
            VALUES (?, 'decloture')
            """,
            (exercice_id,),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de la déclôture de l'exercice %d", exercice_id)
        return False
    finally:
        conn.close()


def get_log_exercice(exercice_id: int) -> list[dict]:
    """Retourne le journal d'actions d'un exercice."""
    return _fetch_all(
        "SELECT * FROM exercices_log WHERE exercice_id = ? ORDER BY date_action ASC",
        (exercice_id,),
    )


def is_periode_cloturee(date_operation: str) -> bool:
    """Vérifie si une date tombe dans un exercice clôturé."""
    row = _fetch_one(
        """
        SELECT id FROM exercices
        WHERE statut = 'cloture'
          AND ? BETWEEN date_debut AND date_fin
        LIMIT 1
        """,
        (date_operation,),
    )
    return row is not None


def get_stats_exercice(exercice_id: int) -> dict:
    """Calcule les statistiques financières d'un exercice."""
    exercice = get_exercice_by_id(exercice_id)
    if not exercice:
        return {
            "total_recettes": 0.0,
            "total_depenses": 0.0,
            "solde_final": 0.0,
            "nb_operations": 0,
        }

    rows = _fetch_all(
        """
        SELECT type_operation, montant, statut
        FROM tresorerie_operations
        WHERE date_operation BETWEEN ? AND ?
          AND statut != 'annule'
        """,
        (exercice["date_debut"], exercice["date_fin"]),
    )

    total_recettes = 0.0
    total_depenses = 0.0
    for row in rows:
        montant = float(row.get("montant") or 0)
        if row["type_operation"] == "recette":
            total_recettes += montant
        elif row["type_operation"] == "depense":
            total_depenses += montant

    solde_ouverture = float(exercice.get("solde_ouverture") or 0)
    return {
        "total_recettes": total_recettes,
        "total_depenses": total_depenses,
        "solde_final": solde_ouverture + total_recettes - total_depenses,
        "nb_operations": len(rows),
    }


def get_parametre(cle: str) -> str | None:
    """Retourne la valeur d'un paramètre."""
    row = _fetch_one("SELECT valeur FROM parametres WHERE cle = ?", (cle,))
    return row["valeur"] if row else None


def set_parametre(cle: str, valeur: str) -> None:
    """Met à jour ou insère un paramètre."""
    _execute(
        "INSERT OR REPLACE INTO parametres (cle, valeur) VALUES (?, ?)",
        (cle, valeur),
    )
