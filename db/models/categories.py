"""CRUD pour la table categories (hiérarchique)."""

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_categories() -> list[dict]:
    """Retourne toutes les catégories avec le nom du parent.

    Returns:
        Liste de dictionnaires ``{id, nom, parent_id, parent_nom}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.nom, c.parent_id, p.nom AS parent_nom
            FROM categories c
            LEFT JOIN categories p ON c.parent_id = p.id
            ORDER BY COALESCE(p.nom, c.nom) ASC, c.parent_id NULLS FIRST, c.nom ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_categories_parent() -> list[dict]:
    """Retourne uniquement les catégories racines (sans parent).

    Returns:
        Liste de dictionnaires ``{id, nom}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom
            FROM categories
            WHERE parent_id IS NULL
            ORDER BY nom ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_sous_categories(parent_id: int) -> list[dict]:
    """Retourne les sous-catégories d'un parent donné.

    Args:
        parent_id: Identifiant de la catégorie parente.

    Returns:
        Liste de dictionnaires ``{id, nom, parent_id}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom, parent_id
            FROM categories
            WHERE parent_id = ?
            ORDER BY nom ASC
            """,
            (parent_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_categorie(nom: str, parent_id: int | None = None) -> int:
    """Ajoute une nouvelle catégorie et retourne son identifiant.

    Args:
        nom: Nom de la catégorie.
        parent_id: Identifiant de la catégorie parente (``None`` pour une racine).

    Returns:
        Identifiant de la catégorie créée.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO categories (nom, parent_id) VALUES (?, ?)",
            (nom, parent_id),
        )
        conn.commit()
        logger.info("Catégorie ajoutée : %s (id=%s)", nom, cursor.lastrowid)
        return cursor.lastrowid
    finally:
        conn.close()


def update_categorie(cat_id: int, nom: str) -> bool:
    """Modifie le nom d'une catégorie.

    Args:
        cat_id: Identifiant de la catégorie.
        nom: Nouveau nom.

    Returns:
        ``True`` si la mise à jour a réussi.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE categories SET nom = ? WHERE id = ?",
            (nom, cat_id),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Catégorie mise à jour : id=%s", cat_id)
        return success
    finally:
        conn.close()


def delete_categorie(cat_id: int) -> bool:
    """Supprime une catégorie si elle n'est pas utilisée et sans enfants.

    Args:
        cat_id: Identifiant de la catégorie à supprimer.

    Returns:
        ``True`` si la suppression a réussi, ``False`` sinon.
    """
    if categorie_is_used(cat_id) or categorie_has_children(cat_id):
        return False
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Catégorie supprimée : id=%s", cat_id)
        return success
    finally:
        conn.close()


def categorie_is_used(cat_id: int) -> bool:
    """Vérifie si une catégorie est utilisée dans le stock.

    Args:
        cat_id: Identifiant de la catégorie.

    Returns:
        ``True`` si elle est utilisée.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM stock WHERE categorie_id = ?",
            (cat_id,),
        ).fetchone()
        return (row["n"] if row else 0) > 0
    finally:
        conn.close()


def categorie_has_children(cat_id: int) -> bool:
    """Vérifie si une catégorie possède des sous-catégories.

    Args:
        cat_id: Identifiant de la catégorie.

    Returns:
        ``True`` si elle a des enfants.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM categories WHERE parent_id = ?",
            (cat_id,),
        ).fetchone()
        return (row["n"] if row else 0) > 0
    finally:
        conn.close()
