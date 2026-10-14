"""CRUD du module Clôture d'exercice (Phase 6b)."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from utils.finance_rules import sql_filtre_comptable
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


def update_exercice(
    exercice_id: int,
    nom: str,
    date_debut: str,
    date_fin: str,
    solde_ouverture: float,
    commentaire: str | None = None,
) -> bool:
    """Met à jour un exercice ouvert (dates, nom, solde d'ouverture)."""
    exercice = get_exercice_by_id(exercice_id)
    if not exercice or exercice.get("statut") != "ouvert":
        return False
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE exercices
            SET nom = ?, date_debut = ?, date_fin = ?,
                solde_ouverture = ?, commentaire = ?
            WHERE id = ?
            """,
            (nom, date_debut, date_fin, float(solde_ouverture or 0), commentaire, exercice_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


class PeriodeClotureeError(ValueError):
    """Écriture refusée : la date appartient à un exercice clôturé."""


def periode_cloturee_conn(conn, *dates: str | None) -> bool:
    """True si l'une des dates tombe dans un exercice clôturé (connexion fournie)."""
    for d in dates:
        if not d:
            continue
        row = conn.execute(
            "SELECT 1 FROM exercices WHERE statut = 'cloture' "
            "AND substr(?, 1, 10) BETWEEN date_debut AND date_fin LIMIT 1",
            (str(d),),
        ).fetchone()
        if row:
            return True
    return False


def verifier_periode_ouverte(conn, *dates: str | None) -> None:
    """Lève PeriodeClotureeError si une date est dans un exercice clôturé."""
    if periode_cloturee_conn(conn, *dates):
        raise PeriodeClotureeError("La période est clôturée : écriture refusée.")


def cloturer_exercice(
    exercice_id: int, solde_cloture: float, commentaire: str | None = None
) -> bool:
    """Clôture un exercice.

    1. Met statut='cloture', date_cloture=now(), solde_cloture.
    2. Verrouille les opérations valides de la période (statut → 'rapproche')
       en mémorisant celles modifiées dans exercices_operations_cloturees.
    3. Insère un log 'cloture' avec le commentaire saisi.
    Tout se déroule dans une seule transaction.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        exercice = conn.execute(
            "SELECT * FROM exercices WHERE id = ?", (exercice_id,)
        ).fetchone()
        if not exercice or exercice["statut"] != "ouvert":
            conn.rollback()
            return False
        exercice = dict(exercice)
        commentaire = (commentaire or "").strip() or exercice.get("commentaire")

        nb_attente = conn.execute(
            "SELECT COUNT(*) FROM tresorerie_operations "
            "WHERE statut = 'en_attente' AND date_operation BETWEEN ? AND ?",
            (exercice["date_debut"], exercice["date_fin"]),
        ).fetchone()[0]
        if nb_attente:
            conn.rollback()
            return False

        conn.execute(
            """
            UPDATE exercices
            SET statut = 'cloture', date_cloture = ?, solde_cloture = ?,
                commentaire = ?
            WHERE id = ?
            """,
            (now, float(solde_cloture), commentaire, exercice_id),
        )
        conn.execute(
            """
            INSERT INTO exercices_operations_cloturees (exercice_id, operation_id, statut_origine)
            SELECT ?, id, statut FROM tresorerie_operations
            WHERE statut = 'valide' AND date_operation BETWEEN ? AND ?
            """,
            (exercice_id, exercice["date_debut"], exercice["date_fin"]),
        )
        conn.execute(
            """
            UPDATE tresorerie_operations
            SET statut = 'rapproche'
            WHERE id IN (SELECT operation_id FROM exercices_operations_cloturees
                         WHERE exercice_id = ? AND date_restauration IS NULL)
            """,
            (exercice_id,),
        )
        conn.execute(
            "INSERT INTO exercices_log (exercice_id, action, commentaire) VALUES (?, 'cloture', ?)",
            (exercice_id, commentaire),
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
    2. Restaure uniquement les opérations modifiées par cette clôture, et
       seulement si elles sont toujours 'rapproche' et non couvertes par un
       autre exercice clôturé (dans ce cas, la mémorisation lui est transférée).
    3. Insère un log 'decloture'. Les traces de clôture sont conservées.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        exercice = conn.execute(
            "SELECT * FROM exercices WHERE id = ?", (exercice_id,)
        ).fetchone()
        if not exercice or exercice["statut"] != "cloture":
            conn.rollback()
            return False

        conn.execute(
            "UPDATE exercices SET statut = 'ouvert', date_decloture = ? WHERE id = ?",
            (now, exercice_id),
        )
        suivis = conn.execute(
            """
            SELECT c.operation_id, c.statut_origine, o.statut, o.date_operation
            FROM exercices_operations_cloturees c
            JOIN tresorerie_operations o ON o.id = c.operation_id
            WHERE c.exercice_id = ? AND c.date_restauration IS NULL
            """,
            (exercice_id,),
        ).fetchall()
        for row in suivis:
            autre = conn.execute(
                "SELECT id FROM exercices WHERE statut = 'cloture' AND id != ? "
                "AND substr(?, 1, 10) BETWEEN date_debut AND date_fin ORDER BY id LIMIT 1",
                (exercice_id, row["date_operation"]),
            ).fetchone()
            if autre:
                # Toujours verrouillée par un autre exercice : transfert du suivi.
                conn.execute(
                    "INSERT INTO exercices_operations_cloturees "
                    "(exercice_id, operation_id, statut_origine) VALUES (?, ?, ?)",
                    (autre["id"], row["operation_id"], row["statut_origine"]),
                )
            elif row["statut"] == "rapproche":
                conn.execute(
                    "UPDATE tresorerie_operations SET statut = ? WHERE id = ?",
                    (row["statut_origine"], row["operation_id"]),
                )
        conn.execute(
            "UPDATE exercices_operations_cloturees SET date_restauration = ? "
            "WHERE exercice_id = ? AND date_restauration IS NULL",
            (now, exercice_id),
        )
        conn.execute(
            "INSERT INTO exercices_log (exercice_id, action) VALUES (?, 'decloture')",
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
        f"""
        SELECT type_operation, montant, statut
        FROM tresorerie_operations
        WHERE date_operation BETWEEN ? AND ?
          AND statut IN ('valide', 'rapproche')
          AND {sql_filtre_comptable()}
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
