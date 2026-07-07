"""CRUD pour la table unites (unités de mesure)."""

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_unites() -> list[dict]:
    """Retourne toutes les unités de mesure.

    Returns:
        Liste de dictionnaires ``{id, nom}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nom FROM unites ORDER BY nom ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_unite(nom: str) -> int:
    """Ajoute une nouvelle unité et retourne son identifiant.

    Args:
        nom: Nom de l'unité.

    Returns:
        Identifiant de l'unité créée.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO unites (nom) VALUES (?)",
            (nom,),
        )
        conn.commit()
        logger.info("Unité ajoutée : %s (id=%s)", nom, cursor.lastrowid)
        return cursor.lastrowid
    finally:
        conn.close()


def update_unite(unite_id: int, nom: str) -> bool:
    """Modifie le nom d'une unité.

    Args:
        unite_id: Identifiant de l'unité.
        nom: Nouveau nom.

    Returns:
        ``True`` si la mise à jour a réussi.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE unites SET nom = ? WHERE id = ?",
            (nom, unite_id),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Unité mise à jour : id=%s", unite_id)
        return success
    finally:
        conn.close()


def delete_unite(unite_id: int) -> bool:
    """Supprime une unité si elle n'est pas utilisée.

    Args:
        unite_id: Identifiant de l'unité.

    Returns:
        ``True`` si la suppression a réussi, ``False`` si elle est utilisée.
    """
    if unite_is_used(unite_id):
        return False
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM unites WHERE id = ?", (unite_id,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Unité supprimée : id=%s", unite_id)
        return success
    finally:
        conn.close()


def unite_is_used(unite_id: int) -> bool:
    """Vérifie si une unité est utilisée dans le stock ou les mouvements.

    Args:
        unite_id: Identifiant de l'unité.

    Returns:
        ``True`` si elle est utilisée.
    """
    conn = get_connection()
    try:
        row_stock = conn.execute(
            "SELECT COUNT(*) AS n FROM stock WHERE unite_id = ?",
            (unite_id,),
        ).fetchone()
        if (row_stock["n"] if row_stock else 0) > 0:
            return True
        row_mvt = conn.execute(
            "SELECT COUNT(*) AS n FROM mouvements_stock WHERE unite_id = ?",
            (unite_id,),
        ).fetchone()
        return (row_mvt["n"] if row_mvt else 0) > 0
    finally:
        conn.close()
