"""CRUD pour les tables stock et mouvements_stock."""

from __future__ import annotations

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)
_SQL_QUANTITE_ACTUELLE = """
CASE
    WHEN COUNT(ms.id) > 0 THEN COALESCE(SUM(ms.quantite), 0)
    ELSE COALESCE(s.quantite, 0)
END
"""


def _quantite_stock_calculee(conn, stock_id: int) -> int:
    """Retourne la quantité actuelle calculée depuis les mouvements.

    Si l'article ne possède encore aucun mouvement, on conserve la quantité
    enregistrée sur la fiche article pour rester rétrocompatible.
    """
    row = conn.execute(
        """
        SELECT
            s.quantite AS quantite_article,
            COUNT(m.id) AS nb_mouvements,
            COALESCE(SUM(m.quantite), 0) AS quantite_mouvements
        FROM stock s
        LEFT JOIN mouvements_stock m ON m.stock_id = s.id
        WHERE s.id = ?
        GROUP BY s.id, s.quantite
        """,
        (stock_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Article introuvable : id={stock_id}")
    if row["nb_mouvements"] == 0:
        return int(row["quantite_article"] or 0)
    return int(row["quantite_mouvements"] or 0)


def _recalculer_quantite_stock(conn, stock_id: int) -> int:
    """Recalcule puis persiste la quantité actuelle d'un article."""
    quantite = _quantite_stock_calculee(conn, stock_id)
    conn.execute("UPDATE stock SET quantite = ? WHERE id = ?", (quantite, stock_id))
    return quantite


# ── Articles ─────────────────────────────────────────────────────────────────


def get_all_articles(include_archives: bool = False) -> list[dict]:
    """Retourne tous les articles du stock.

    Args:
        include_archives: Si ``True``, inclut les articles archivés.

    Returns:
        Liste de dictionnaires représentant chaque article.
    """
    conn = get_connection()
    try:
        if include_archives:
            rows = conn.execute(
                f"""
                SELECT s.id, s.nom, s.categorie_id, c.nom AS categorie_nom,
                       s.unite_id, u.nom AS unite_nom,
                       s.fournisseur_habituel_id, f.nom AS fournisseur_nom,
                       {_SQL_QUANTITE_ACTUELLE} AS quantite,
                       s.seuil_alerte, s.prix_achat,
                       s.lot, s.commentaire, s.statut_archive
                FROM stock s
                LEFT JOIN categories c ON s.categorie_id = c.id
                LEFT JOIN unites u ON s.unite_id = u.id
                LEFT JOIN fournisseurs f ON s.fournisseur_habituel_id = f.id
                LEFT JOIN mouvements_stock ms ON ms.stock_id = s.id
                GROUP BY
                    s.id, s.nom, s.categorie_id, c.nom, s.unite_id, u.nom,
                    s.fournisseur_habituel_id, f.nom, s.quantite, s.seuil_alerte,
                    s.prix_achat, s.lot, s.commentaire, s.statut_archive
                ORDER BY s.statut_archive ASC, s.nom ASC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT s.id, s.nom, s.categorie_id, c.nom AS categorie_nom,
                       s.unite_id, u.nom AS unite_nom,
                       s.fournisseur_habituel_id, f.nom AS fournisseur_nom,
                       {_SQL_QUANTITE_ACTUELLE} AS quantite,
                       s.seuil_alerte, s.prix_achat,
                       s.lot, s.commentaire, s.statut_archive
                FROM stock s
                LEFT JOIN categories c ON s.categorie_id = c.id
                LEFT JOIN unites u ON s.unite_id = u.id
                LEFT JOIN fournisseurs f ON s.fournisseur_habituel_id = f.id
                LEFT JOIN mouvements_stock ms ON ms.stock_id = s.id
                WHERE s.statut_archive = 0
                GROUP BY
                    s.id, s.nom, s.categorie_id, c.nom, s.unite_id, u.nom,
                    s.fournisseur_habituel_id, f.nom, s.quantite, s.seuil_alerte,
                    s.prix_achat, s.lot, s.commentaire, s.statut_archive
                ORDER BY s.nom ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_article_by_id(article_id: int) -> dict | None:
    """Retourne un article par son identifiant.

    Args:
        article_id: Identifiant de l'article.

    Returns:
        Dictionnaire de l'article ou ``None``.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            f"""
            SELECT s.id, s.nom, s.categorie_id, c.nom AS categorie_nom,
                   s.unite_id, u.nom AS unite_nom,
                   s.fournisseur_habituel_id, f.nom AS fournisseur_nom,
                   {_SQL_QUANTITE_ACTUELLE} AS quantite,
                   s.seuil_alerte, s.prix_achat,
                   s.lot, s.commentaire, s.statut_archive
            FROM stock s
            LEFT JOIN categories c ON s.categorie_id = c.id
            LEFT JOIN unites u ON s.unite_id = u.id
            LEFT JOIN fournisseurs f ON s.fournisseur_habituel_id = f.id
            LEFT JOIN mouvements_stock ms ON ms.stock_id = s.id
            WHERE s.id = ?
            GROUP BY
                s.id, s.nom, s.categorie_id, c.nom, s.unite_id, u.nom,
                s.fournisseur_habituel_id, f.nom, s.quantite, s.seuil_alerte,
                s.prix_achat, s.lot, s.commentaire, s.statut_archive
            """,
            (article_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_article(
    nom: str,
    categorie_id: int | None,
    unite_id: int | None,
    fournisseur_habituel_id: int | None,
    quantite: int,
    seuil_alerte: int,
    prix_achat: float,
    lot: str | None,
    commentaire: str | None,
) -> int:
    """Ajoute un nouvel article et retourne son identifiant.

    Args:
        nom: Nom de l'article.
        categorie_id: Identifiant de la catégorie.
        unite_id: Identifiant de l'unité.
        fournisseur_habituel_id: Identifiant du fournisseur habituel.
        quantite: Quantité initiale.
        seuil_alerte: Seuil d'alerte.
        prix_achat: Prix d'achat unitaire.
        lot: Numéro de lot (optionnel).
        commentaire: Commentaire libre (optionnel).

    Returns:
        Identifiant de l'article créé.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO stock
                (nom, categorie_id, unite_id, fournisseur_habituel_id,
                 quantite, seuil_alerte, prix_achat, lot, commentaire, statut_archive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                nom,
                categorie_id,
                unite_id,
                fournisseur_habituel_id,
                quantite,
                seuil_alerte,
                prix_achat or 0.0,
                lot or None,
                commentaire or None,
            ),
        )
        conn.commit()
        logger.info("Article ajouté : %s (id=%s)", nom, cursor.lastrowid)
        return cursor.lastrowid
    finally:
        conn.close()


def update_article(
    article_id: int,
    nom: str,
    categorie_id: int | None,
    unite_id: int | None,
    fournisseur_habituel_id: int | None,
    seuil_alerte: int,
    prix_achat: float,
    lot: str | None,
    commentaire: str | None,
) -> bool:
    """Met à jour un article (hors quantité, gérée par mouvements).

    Args:
        article_id: Identifiant de l'article.
        nom: Nouveau nom.
        categorie_id: Nouvelle catégorie.
        unite_id: Nouvelle unité.
        fournisseur_habituel_id: Nouveau fournisseur habituel.
        seuil_alerte: Nouveau seuil d'alerte.
        prix_achat: Nouveau prix d'achat.
        lot: Nouveau numéro de lot.
        commentaire: Nouveau commentaire.

    Returns:
        ``True`` si la mise à jour a réussi.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE stock
            SET nom = ?, categorie_id = ?, unite_id = ?,
                fournisseur_habituel_id = ?, seuil_alerte = ?,
                prix_achat = ?, lot = ?, commentaire = ?
            WHERE id = ?
            """,
            (
                nom,
                categorie_id,
                unite_id,
                fournisseur_habituel_id,
                seuil_alerte,
                prix_achat or 0.0,
                lot or None,
                commentaire or None,
                article_id,
            ),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Article mis à jour : id=%s", article_id)
        return success
    finally:
        conn.close()


def archiver_article(article_id: int) -> bool:
    """Archive un article sans le supprimer.

    Args:
        article_id: Identifiant de l'article.

    Returns:
        ``True`` si l'archivage a réussi.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE stock SET statut_archive = 1 WHERE id = ?",
            (article_id,),
        )
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info("Article archivé : id=%s", article_id)
        return success
    finally:
        conn.close()


def get_articles_for_select() -> list[dict]:
    """Retourne les articles non archivés pour les listes déroulantes.

    Returns:
        Liste de dictionnaires ``{id, nom}``.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom
            FROM stock
            WHERE statut_archive = 0
            ORDER BY nom ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Mouvements ────────────────────────────────────────────────────────────────


def add_mouvement(
    stock_id: int,
    date: str,
    type_mouvement: str,
    quantite: int,
    prix_unitaire: float | None,
    fournisseur_id: int | None,
    evenement_id: int | None,
    numero_facture: str | None,
    commentaire: str | None,
) -> int:
    """Enregistre un mouvement de stock et met à jour la quantité.

    Pour le type ``Inventaire``, la quantité saisie remplace le stock.
    Pour tous les autres types, la quantité est un delta (positif ou négatif).

    Args:
        stock_id: Identifiant de l'article.
        date: Date au format ``YYYY-MM-DD``.
        type_mouvement: Type du mouvement.
        quantite: Quantité du mouvement (valeur absolue).
        prix_unitaire: Prix unitaire (pour les achats).
        fournisseur_id: Identifiant du fournisseur.
        evenement_id: Identifiant de l'événement lié.
        numero_facture: Numéro de facture.
        commentaire: Commentaire libre.

    Returns:
        Identifiant du mouvement créé.
    """
    conn = get_connection()
    try:
        # Récupérer le stock actuel
        stock_actuel = _quantite_stock_calculee(conn, stock_id)

        # Calculer le nouveau stock
        if type_mouvement == "Inventaire":
            quantite_enregistree = quantite - stock_actuel
        elif type_mouvement.startswith("Entrée"):
            quantite_enregistree = quantite
        else:
            # Sortie
            quantite_enregistree = -quantite

        # Insérer le mouvement
        cursor = conn.execute(
            """
            INSERT INTO mouvements_stock
                (stock_id, date, type, quantite, prix_unitaire,
                 fournisseur_id, evenement_id, numero_facture, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stock_id,
                date,
                type_mouvement,
                quantite_enregistree,
                prix_unitaire,
                fournisseur_id,
                evenement_id,
                numero_facture or None,
                commentaire or None,
            ),
        )

        # Mettre à jour la quantité en stock
        _recalculer_quantite_stock(conn, stock_id)
        conn.commit()
        logger.info(
            "Mouvement ajouté : stock_id=%s type=%s qté=%s",
            stock_id, type_mouvement, quantite_enregistree,
        )
        return cursor.lastrowid
    finally:
        conn.close()


def get_mouvements_by_article(stock_id: int) -> list[dict]:
    """Retourne l'historique des mouvements d'un article.

    Args:
        stock_id: Identifiant de l'article.

    Returns:
        Liste de dictionnaires représentant chaque mouvement.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.stock_id, m.date, m.type, m.quantite,
                   m.prix_unitaire, m.commentaire,
                   m.fournisseur_id, f.nom AS fournisseur_nom,
                   m.evenement_id, e.nom AS evenement_nom,
                   m.numero_facture
            FROM mouvements_stock m
            LEFT JOIN fournisseurs f ON m.fournisseur_id = f.id
            LEFT JOIN evenements e ON m.evenement_id = e.id
            WHERE m.stock_id = ?
            ORDER BY m.date DESC, m.id DESC
            """,
            (stock_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_mouvements(limit: int = 100) -> list[dict]:
    """Retourne les derniers mouvements tous articles confondus.

    Args:
        limit: Nombre maximum de mouvements à retourner.

    Returns:
        Liste de dictionnaires représentant chaque mouvement.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT m.id, m.stock_id, s.nom AS article_nom,
                   m.date, m.type, m.quantite,
                   m.prix_unitaire, m.commentaire,
                   m.fournisseur_id, f.nom AS fournisseur_nom,
                   m.evenement_id, e.nom AS evenement_nom,
                   m.numero_facture
            FROM mouvements_stock m
            LEFT JOIN stock s ON m.stock_id = s.id
            LEFT JOIN fournisseurs f ON m.fournisseur_id = f.id
            LEFT JOIN evenements e ON m.evenement_id = e.id
            ORDER BY m.date DESC, m.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def article_has_mouvements(article_id: int) -> bool:
    """Vérifie si un article a des mouvements enregistrés.

    Args:
        article_id: Identifiant de l'article.

    Returns:
        ``True`` s'il a au moins un mouvement.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM mouvements_stock WHERE stock_id = ?",
            (article_id,),
        ).fetchone()
        return (row["n"] if row else 0) > 0
    finally:
        conn.close()


def delete_mouvement(mouvement_id: int) -> bool:
    """Supprime un mouvement et recalcule la quantité en stock.

    Args:
        mouvement_id: Identifiant du mouvement à supprimer.

    Returns:
        ``True`` si la suppression a réussi.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT stock_id, quantite FROM mouvements_stock WHERE id = ?",
            (mouvement_id,),
        ).fetchone()
        if not row:
            return False

        stock_id = row["stock_id"]

        conn.execute("DELETE FROM mouvements_stock WHERE id = ?", (mouvement_id,))
        _recalculer_quantite_stock(conn, stock_id)
        conn.commit()
        logger.info("Mouvement supprimé : id=%s", mouvement_id)
        return True
    finally:
        conn.close()
