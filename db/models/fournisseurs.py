"""CRUD pour la table fournisseurs."""

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_fournisseurs() -> list[dict]:
    """Retourne tous les fournisseurs.

    Returns:
        Liste de dictionnaires ``{id, nom, telephone, email, commentaire}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom, telephone, email, commentaire
            FROM fournisseurs
            ORDER BY nom ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_fournisseur_by_id(fournisseur_id: int) -> dict | None:
    """Retourne un fournisseur par son identifiant.

    Args:
        fournisseur_id: Identifiant du fournisseur.

    Returns:
        Dictionnaire du fournisseur ou ``None``.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nom, telephone, email, commentaire
            FROM fournisseurs
            WHERE id = ?
            """,
            (fournisseur_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_fournisseur(
    nom: str,
    telephone: str | None = None,
    email: str | None = None,
    commentaire: str | None = None,
) -> int:
    """Ajoute un nouveau fournisseur et retourne son identifiant.

    Args:
        nom: Nom du fournisseur.
        telephone: Numéro de téléphone (optionnel).
        email: Adresse e-mail (optionnelle).
        commentaire: Commentaire libre (optionnel).

    Returns:
        Identifiant du fournisseur créé.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO fournisseurs (nom, telephone, email, commentaire)
            VALUES (?, ?, ?, ?)
            """,
            (nom, telephone or None, email or None, commentaire or None),
        )
        conn.commit()
        logger.info("Fournisseur ajouté : %s (id=%s)", nom, cursor.lastrowid)
        return cursor.lastrowid
    finally:
        conn.close()


def update_fournisseur(
    fournisseur_id: int,
    nom: str,
    telephone: str | None,
    email: str | None,
    commentaire: str | None,
) -> bool:
    """Met à jour un fournisseur.

    Args:
        fournisseur_id: Identifiant du fournisseur.
        nom: Nouveau nom.
        telephone: Nouveau téléphone.
        email: Nouvel e-mail.
        commentaire: Nouveau commentaire.

    Returns:
        ``True`` si la mise à jour a réussi.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE fournisseurs
            SET nom = ?, telephone = ?, email = ?, commentaire = ?
            WHERE id = ?
            """,
            (nom, telephone or None, email or None, commentaire or None, fournisseur_id),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Fournisseur mis à jour : id=%s", fournisseur_id)
        return success
    finally:
        conn.close()


def delete_fournisseur(fournisseur_id: int) -> bool:
    """Supprime un fournisseur s'il n'est pas utilisé.

    Args:
        fournisseur_id: Identifiant du fournisseur.

    Returns:
        ``True`` si la suppression a réussi, ``False`` s'il est utilisé.
    """
    if fournisseur_is_used(fournisseur_id):
        return False
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM fournisseurs WHERE id = ?",
            (fournisseur_id,),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Fournisseur supprimé : id=%s", fournisseur_id)
        return success
    finally:
        conn.close()


def fournisseur_is_used(fournisseur_id: int) -> bool:
    """Vérifie si un fournisseur est utilisé dans les mouvements ou le stock.

    Args:
        fournisseur_id: Identifiant du fournisseur.

    Returns:
        ``True`` s'il est utilisé.
    """
    conn = get_connection()
    try:
        row_mvt = conn.execute(
            "SELECT COUNT(*) AS n FROM mouvements_stock WHERE fournisseur_id = ?",
            (fournisseur_id,),
        ).fetchone()
        if (row_mvt["n"] if row_mvt else 0) > 0:
            return True
        row_stock = conn.execute(
            "SELECT COUNT(*) AS n FROM stock WHERE fournisseur_habituel_id = ?",
            (fournisseur_id,),
        ).fetchone()
        return (row_stock["n"] if row_stock else 0) > 0
    finally:
        conn.close()


def get_fournisseurs_for_select() -> list[dict]:
    """Retourne les fournisseurs pour les listes déroulantes.

    Returns:
        Liste de dictionnaires ``{id, nom}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nom FROM fournisseurs ORDER BY nom ASC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def search_or_create_fournisseur(nom: str) -> int:
    """Retourne l'identifiant du fournisseur ou le crée s'il n'existe pas.

    Args:
        nom: Nom du fournisseur.

    Returns:
        Identifiant du fournisseur (existant ou nouvellement créé).
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM fournisseurs WHERE nom = ?",
            (nom,),
        ).fetchone()
        if row:
            return row["id"]
    finally:
        conn.close()
    return add_fournisseur(nom)
