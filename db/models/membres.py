"""CRUD pour la table membres (adhérents)."""

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def get_all_membres(include_archives: bool = False) -> list[dict]:
    """Retourne tous les membres, triés par statut puis nom.

    Args:
        include_archives: Si ``True``, inclut les membres archivés.

    Returns:
        Liste de dictionnaires représentant chaque membre.
    """
    conn = get_connection()
    try:
        if include_archives:
            rows = conn.execute(
                """
                SELECT id, nom, prenom, email, telephone, statut,
                       date_adhesion, commentaire, statut_archive
                FROM membres
                ORDER BY statut_archive ASC, statut ASC, nom ASC, prenom ASC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, nom, prenom, email, telephone, statut,
                       date_adhesion, commentaire, statut_archive
                FROM membres
                WHERE statut_archive = 0
                ORDER BY statut ASC, nom ASC, prenom ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_membre_by_id(membre_id: int) -> dict | None:
    """Retourne un membre par son identifiant.

    Args:
        membre_id: Identifiant du membre.

    Returns:
        Dictionnaire du membre ou ``None`` s'il n'existe pas.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nom, prenom, email, telephone, statut,
                   date_adhesion, commentaire, statut_archive
            FROM membres
            WHERE id = ?
            """,
            (membre_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_membre(
    nom: str,
    prenom: str,
    email: str,
    telephone: str,
    statut: str,
    date_adhesion: str,
    commentaire: str,
) -> int:
    """Ajoute un nouveau membre et retourne son identifiant.

    Args:
        nom: Nom de famille.
        prenom: Prénom.
        email: Adresse e-mail (optionnel).
        telephone: Numéro de téléphone (optionnel).
        statut: Statut dans l'association.
        date_adhesion: Date d'adhésion au format ``YYYY-MM-DD``.
        commentaire: Commentaire libre (optionnel).

    Returns:
        Identifiant (entier) du membre créé.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO membres
                (nom, prenom, email, telephone, statut, date_adhesion, commentaire, statut_archive)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (nom, prenom, email or None, telephone or None, statut, date_adhesion or None, commentaire or None),
        )
        conn.commit()
        logger.info("Membre ajouté : %s %s (id=%s)", prenom, nom, cursor.lastrowid)
        return cursor.lastrowid
    finally:
        conn.close()


def update_membre(
    membre_id: int,
    nom: str,
    prenom: str,
    email: str,
    telephone: str,
    statut: str,
    date_adhesion: str,
    commentaire: str,
) -> bool:
    """Met à jour les informations d'un membre.

    Args:
        membre_id: Identifiant du membre à modifier.
        nom: Nouveau nom.
        prenom: Nouveau prénom.
        email: Nouvelle adresse e-mail.
        telephone: Nouveau numéro de téléphone.
        statut: Nouveau statut.
        date_adhesion: Nouvelle date d'adhésion au format ``YYYY-MM-DD``.
        commentaire: Nouveau commentaire.

    Returns:
        ``True`` si la mise à jour a réussi, ``False`` sinon.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE membres
            SET nom = ?, prenom = ?, email = ?, telephone = ?,
                statut = ?, date_adhesion = ?, commentaire = ?
            WHERE id = ?
            """,
            (nom, prenom, email or None, telephone or None, statut, date_adhesion or None, commentaire or None, membre_id),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Membre mis à jour : id=%s", membre_id)
        else:
            logger.warning("Membre introuvable pour mise à jour : id=%s", membre_id)
        return success
    finally:
        conn.close()


def archiver_membre(membre_id: int) -> bool:
    """Archive un membre (statut_archive = 1) sans le supprimer.

    Args:
        membre_id: Identifiant du membre à archiver.

    Returns:
        ``True`` si l'archivage a réussi, ``False`` sinon.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE membres SET statut_archive = 1 WHERE id = ?",
            (membre_id,),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Membre archivé : id=%s", membre_id)
        else:
            logger.warning("Membre introuvable pour archivage : id=%s", membre_id)
        return success
    finally:
        conn.close()


def get_membres_for_select() -> list[dict]:
    """Retourne les membres actifs pour les listes déroulantes.

    Returns:
        Liste de dictionnaires ``{id, nom, prenom}`` triés par nom.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom, prenom
            FROM membres
            WHERE statut_archive = 0
            ORDER BY nom ASC, prenom ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
