"""CRUD et logique data pour le module Buvette."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Articles ─────────────────────────────────────────────────────────────────


def get_all_articles_buvette(include_archives: bool = False) -> list[dict]:
    """Retourne la liste des articles buvette."""
    conn = get_connection()
    try:
        where_clause = "" if include_archives else "WHERE a.statut_archive = 0"
        rows = conn.execute(
            f"""
            SELECT a.id, a.nom, a.categorie_id, c.nom AS categorie_nom,
                   a.unite_id, u.nom AS unite_nom,
                   a.contenance, a.prix_vente, a.prix_achat,
                   a.stock_actuel, a.stock_id, s.nom AS stock_nom,
                   a.statut_archive, a.commentaire
            FROM articles_buvette a
            LEFT JOIN categories c ON c.id = a.categorie_id
            LEFT JOIN unites u ON u.id = a.unite_id
            LEFT JOIN stock s ON s.id = a.stock_id
            {where_clause}
            ORDER BY a.statut_archive ASC, a.nom ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_article_buvette_by_id(article_id: int) -> dict | None:
    """Retourne un article buvette par identifiant."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT a.id, a.nom, a.categorie_id, c.nom AS categorie_nom,
                   a.unite_id, u.nom AS unite_nom,
                   a.contenance, a.prix_vente, a.prix_achat,
                   a.stock_actuel, a.stock_id, s.nom AS stock_nom,
                   a.statut_archive, a.commentaire
            FROM articles_buvette a
            LEFT JOIN categories c ON c.id = a.categorie_id
            LEFT JOIN unites u ON u.id = a.unite_id
            LEFT JOIN stock s ON s.id = a.stock_id
            WHERE a.id = ?
            """,
            (article_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_article_buvette(
    nom,
    categorie_id,
    unite_id,
    contenance,
    prix_vente,
    prix_achat,
    stock_id,
    commentaire,
) -> int:
    """Ajoute un article buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO articles_buvette
                (nom, categorie_id, unite_id, contenance, prix_vente,
                 prix_achat, stock_id, commentaire, stock_actuel, statut_archive)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (
                nom,
                categorie_id,
                unite_id,
                contenance or None,
                float(prix_vente or 0),
                float(prix_achat or 0),
                stock_id,
                commentaire or None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_article_buvette(
    article_id,
    nom,
    categorie_id,
    unite_id,
    contenance,
    prix_vente,
    prix_achat,
    stock_id,
    commentaire,
) -> bool:
    """Met à jour un article buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE articles_buvette
            SET nom = ?, categorie_id = ?, unite_id = ?, contenance = ?,
                prix_vente = ?, prix_achat = ?, stock_id = ?, commentaire = ?
            WHERE id = ?
            """,
            (
                nom,
                categorie_id,
                unite_id,
                contenance or None,
                float(prix_vente or 0),
                float(prix_achat or 0),
                stock_id,
                commentaire or None,
                article_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def archiver_article_buvette(article_id: int) -> bool:
    """Archive un article buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE articles_buvette SET statut_archive = 1 WHERE id = ?",
            (article_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_articles_buvette_for_select() -> list[dict]:
    """Retourne les articles actifs pour les listes déroulantes."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, nom, stock_actuel
            FROM articles_buvette
            WHERE statut_archive = 0
            ORDER BY nom ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_stock_article_buvette(article_id: int, nouvelle_quantite: int) -> bool:
    """Met à jour le stock d'un article buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE articles_buvette SET stock_actuel = ? WHERE id = ?",
            (int(nouvelle_quantite), article_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ── Inventaires ──────────────────────────────────────────────────────────────


def create_inventaire(date, type_inventaire, evenement_id, commentaire) -> int:
    """Crée un inventaire buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO inventaires_buvette (date, type, evenement_id, commentaire)
            VALUES (?, ?, ?, ?)
            """,
            (date, type_inventaire, evenement_id, commentaire or None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_ligne_inventaire(inventaire_id, article_id, quantite_theorique, quantite_comptee) -> int:
    """Ajoute une ligne à un inventaire buvette."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO inventaire_buvette_lignes
                (inventaire_id, article_id, quantite_theorique, quantite_comptee)
            VALUES (?, ?, ?, ?)
            """,
            (
                inventaire_id,
                article_id,
                int(quantite_theorique or 0),
                int(quantite_comptee),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_inventaire_by_id(inventaire_id: int) -> dict:
    """Retourne un inventaire buvette."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT i.id, i.date, i.type, i.evenement_id, e.nom AS evenement_nom,
                   i.commentaire, i.created_at
            FROM inventaires_buvette i
            LEFT JOIN evenements e ON e.id = i.evenement_id
            WHERE i.id = ?
            """,
            (inventaire_id,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_lignes_inventaire(inventaire_id: int) -> list[dict]:
    """Retourne les lignes d'un inventaire avec calcul de l'écart en Python."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.inventaire_id, l.article_id, a.nom AS article_nom,
                   l.quantite_theorique, l.quantite_comptee
            FROM inventaire_buvette_lignes l
            JOIN articles_buvette a ON a.id = l.article_id
            WHERE l.inventaire_id = ?
            ORDER BY a.nom ASC
            """,
            (inventaire_id,),
        ).fetchall()

        lignes = [dict(r) for r in rows]
        for ligne in lignes:
            ligne["ecart"] = (ligne.get("quantite_comptee") or 0) - (
                ligne.get("quantite_theorique") or 0
            )
        return lignes
    finally:
        conn.close()


def get_last_inventaire_apres_evenement(evenement_id: int) -> dict | None:
    """Retourne le dernier inventaire de type après événement pour l'événement donné."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, date, type, evenement_id, commentaire, created_at
            FROM inventaires_buvette
            WHERE evenement_id = ? AND type = 'apres_evenement'
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (evenement_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_inventaires(limit=50) -> list[dict]:
    """Retourne les derniers inventaires buvette."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT i.id, i.date, i.type, i.evenement_id, e.nom AS evenement_nom,
                   i.commentaire, i.created_at
            FROM inventaires_buvette i
            LEFT JOIN evenements e ON e.id = i.evenement_id
            ORDER BY i.date DESC, i.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Approvisionnements ───────────────────────────────────────────────────────


def create_approvisionnement(date, evenement_id, fournisseur_id, commentaire) -> int:
    """Crée un brouillon d'approvisionnement."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO approvisionnements_buvette
                (date, evenement_id, fournisseur_id, commentaire, montant_total, finalise)
            VALUES (?, ?, ?, ?, 0, 0)
            """,
            (date, evenement_id, fournisseur_id, commentaire or None),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_ligne_approvisionnement(appro_id, article_id, quantite, prix_unitaire) -> int:
    """Ajoute une ligne d'approvisionnement et recalcule le total."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT finalise FROM approvisionnements_buvette WHERE id = ?",
            (appro_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Approvisionnement introuvable : id={appro_id}")
        if row["finalise"]:
            raise ValueError("Cet approvisionnement est déjà finalisé.")

        cursor = conn.execute(
            """
            INSERT INTO approvisionnement_buvette_lignes
                (approvisionnement_id, article_id, quantite, prix_unitaire)
            VALUES (?, ?, ?, ?)
            """,
            (appro_id, article_id, int(quantite), float(prix_unitaire or 0)),
        )

        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(quantite * prix_unitaire), 0) AS total
            FROM approvisionnement_buvette_lignes
            WHERE approvisionnement_id = ?
            """,
            (appro_id,),
        ).fetchone()

        conn.execute(
            "UPDATE approvisionnements_buvette SET montant_total = ? WHERE id = ?",
            (float(total_row["total"] if total_row else 0.0), appro_id),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_approvisionnement_by_id(appro_id: int) -> dict:
    """Retourne l'en-tête d'un approvisionnement."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT a.id, a.date, a.evenement_id, e.nom AS evenement_nom,
                   a.fournisseur_id, f.nom AS fournisseur_nom,
                   a.montant_total, a.commentaire,
                   a.finalise, a.finalise_le, a.created_at
            FROM approvisionnements_buvette a
            LEFT JOIN evenements e ON e.id = a.evenement_id
            LEFT JOIN fournisseurs f ON f.id = a.fournisseur_id
            WHERE a.id = ?
            """,
            (appro_id,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_lignes_approvisionnement(appro_id: int) -> list[dict]:
    """Retourne les lignes d'un approvisionnement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.approvisionnement_id, l.article_id, a.nom AS article_nom,
                   l.quantite, l.prix_unitaire,
                   (l.quantite * l.prix_unitaire) AS total_ligne
            FROM approvisionnement_buvette_lignes l
            JOIN articles_buvette a ON a.id = l.article_id
            WHERE l.approvisionnement_id = ?
            ORDER BY l.id ASC
            """,
            (appro_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def finaliser_approvisionnement(appro_id: int) -> bool:
    """Finalise un approvisionnement: stock buvette + stock général + dépense trésorerie."""
    conn = get_connection()
    try:
        appro = conn.execute(
            """
            SELECT id, date, evenement_id, fournisseur_id, montant_total, commentaire, finalise
            FROM approvisionnements_buvette
            WHERE id = ?
            """,
            (appro_id,),
        ).fetchone()
        if not appro:
            return False
        if appro["finalise"]:
            return False

        lignes = conn.execute(
            """
            SELECT article_id, quantite, prix_unitaire
            FROM approvisionnement_buvette_lignes
            WHERE approvisionnement_id = ?
            """,
            (appro_id,),
        ).fetchall()
        if not lignes:
            return False

        for ligne in lignes:
            article = conn.execute(
                "SELECT id, stock_actuel, stock_id FROM articles_buvette WHERE id = ?",
                (ligne["article_id"],),
            ).fetchone()
            if not article:
                continue

            nouveau_stock_buvette = int(article["stock_actuel"] or 0) + int(ligne["quantite"])
            conn.execute(
                "UPDATE articles_buvette SET stock_actuel = ? WHERE id = ?",
                (nouveau_stock_buvette, article["id"]),
            )

            stock_general_id = article["stock_id"]
            if stock_general_id:
                stock_general = conn.execute(
                    "SELECT quantite FROM stock WHERE id = ?",
                    (stock_general_id,),
                ).fetchone()
                if stock_general:
                    nouveau_stock_general = int(stock_general["quantite"] or 0) - int(
                        ligne["quantite"]
                    )
                    conn.execute(
                        "UPDATE stock SET quantite = ? WHERE id = ?",
                        (nouveau_stock_general, stock_general_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO mouvements_stock
                            (stock_id, date, type, quantite, prix_unitaire,
                             fournisseur_id, evenement_id, numero_facture, commentaire)
                        VALUES (?, ?, 'Sortie — Utilisation', ?, ?, ?, ?, NULL, ?)
                        """,
                        (
                            stock_general_id,
                            appro["date"],
                            -int(ligne["quantite"]),
                            float(ligne["prix_unitaire"] or 0),
                            appro["fournisseur_id"],
                            appro["evenement_id"],
                            f"Approvisionnement buvette #{appro_id}",
                        ),
                    )

        fournisseur_nom = None
        if appro["fournisseur_id"]:
            fournisseur = conn.execute(
                "SELECT nom FROM fournisseurs WHERE id = ?",
                (appro["fournisseur_id"],),
            ).fetchone()
            fournisseur_nom = fournisseur["nom"] if fournisseur else None

        commentaire = appro["commentaire"] or ""
        libelle = f"Approvisionnement buvette — {appro['date']}"
        if commentaire:
            commentaire = f"{libelle}\n{commentaire}"
        else:
            commentaire = libelle

        conn.execute(
            """
            INSERT INTO depenses_diverses
                (date_depense, categorie, montant, fournisseur,
                 statut_reglement, commentaire, statut_remboursement)
            VALUES (?, ?, ?, ?, 'réglé', ?, 'non concerné')
            """,
            (
                appro["date"],
                "Approvisionnement buvette",
                float(appro["montant_total"] or 0),
                fournisseur_nom,
                commentaire,
            ),
        )

        conn.execute(
            """
            UPDATE approvisionnements_buvette
            SET finalise = 1,
                finalise_le = datetime('now')
            WHERE id = ?
            """,
            (appro_id,),
        )

        conn.commit()
        logger.info("Approvisionnement finalisé : id=%s", appro_id)
        return True
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de la finalisation de l'approvisionnement id=%s", appro_id)
        raise
    finally:
        conn.close()


# ── Caisses ──────────────────────────────────────────────────────────────────


def add_caisse(evenement_id, nom, fond_de_caisse, total_brut, date, commentaire) -> int:
    """Ajoute une caisse pour un événement."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO caisses_buvette
                (evenement_id, nom, fond_de_caisse, total_brut, date, commentaire)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                nom,
                float(fond_de_caisse or 0),
                float(total_brut or 0),
                date,
                commentaire or None,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_caisse(caisse_id, nom, fond_de_caisse, total_brut, date, commentaire) -> bool:
    """Met à jour une caisse."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE caisses_buvette
            SET nom = ?, fond_de_caisse = ?, total_brut = ?, date = ?, commentaire = ?
            WHERE id = ?
            """,
            (
                nom,
                float(fond_de_caisse or 0),
                float(total_brut or 0),
                date,
                commentaire or None,
                caisse_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_caisse(caisse_id: int) -> bool:
    """Supprime une caisse."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM caisses_buvette WHERE id = ?", (caisse_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_caisses_by_evenement(evenement_id: int) -> list[dict]:
    """Retourne les caisses d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, evenement_id, nom, fond_de_caisse, total_brut, date, commentaire
            FROM caisses_buvette
            WHERE evenement_id = ?
            ORDER BY id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── Recettes ─────────────────────────────────────────────────────────────────


def calculer_recette_evenement(evenement_id: int) -> dict:
    """Calcule la recette nette d'un événement à partir de ses caisses."""
    detail_caisses = get_caisses_by_evenement(evenement_id)
    total_brut = sum(float(c.get("total_brut") or 0) for c in detail_caisses)
    total_fond_caisse = sum(float(c.get("fond_de_caisse") or 0) for c in detail_caisses)
    recette_nette = total_brut - total_fond_caisse
    return {
        "total_brut": total_brut,
        "total_fond_caisse": total_fond_caisse,
        "recette_nette": recette_nette,
        "detail_caisses": detail_caisses,
    }


def enregistrer_recette_evenement(evenement_id: int) -> int:
    """Calcule et enregistre la recette buvette et la recette de trésorerie associée."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM recettes_buvette WHERE evenement_id = ?",
            (evenement_id,),
        ).fetchone()
        if existing:
            return int(existing["id"])

        calcul = calculer_recette_evenement(evenement_id)
        date_du_jour = datetime.now().strftime("%Y-%m-%d")

        evenement = conn.execute(
            "SELECT nom FROM evenements WHERE id = ?",
            (evenement_id,),
        ).fetchone()
        nom_evenement = evenement["nom"] if evenement else f"Événement #{evenement_id}"

        commentaire_treso = f"Buvette — {nom_evenement} — {date_du_jour}"
        cursor_treso = conn.execute(
            """
            INSERT INTO dons_subventions (date, source, montant, type, commentaire)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                date_du_jour,
                "Buvette",
                float(calcul["recette_nette"]),
                "Recette buvette",
                commentaire_treso,
            ),
        )

        cursor = conn.execute(
            """
            INSERT INTO recettes_buvette
                (evenement_id, date, total_brut, total_fond_caisse, recette_nette, commentaire, tresorerie_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                date_du_jour,
                float(calcul["total_brut"]),
                float(calcul["total_fond_caisse"]),
                float(calcul["recette_nette"]),
                commentaire_treso,
                cursor_treso.lastrowid,
            ),
        )

        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_recettes_buvette(limit=50) -> list[dict]:
    """Retourne l'historique des recettes buvette."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT r.id, r.evenement_id, e.nom AS evenement_nom,
                   r.date, r.total_brut, r.total_fond_caisse, r.recette_nette,
                   r.commentaire, r.tresorerie_id
            FROM recettes_buvette r
            LEFT JOIN evenements e ON e.id = r.evenement_id
            ORDER BY r.date DESC, r.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
