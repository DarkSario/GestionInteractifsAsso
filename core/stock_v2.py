"""Logique métier Phase 12 pour le stock (lots FIFO, tags, péremption)."""

from __future__ import annotations

from db.connection import get_connection


def _sync_stock_quantite(conn, article_id: int) -> None:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(quantite_restante), 0) AS total
        FROM stock_lots
        WHERE article_id = ?
          AND statut IN ('actif', 'epuise')
        """,
        (article_id,),
    ).fetchone()
    conn.execute(
        "UPDATE stock SET quantite = ? WHERE id = ?",
        (int(row["total"] if row else 0), article_id),
    )


def get_lots_fifo(article_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, numero_lot, date_achat, quantite_restante, prix_unitaire_ttc
            FROM stock_lots
            WHERE article_id = ?
              AND statut = 'actif'
              AND quantite_restante > 0
            ORDER BY date(date_achat) ASC, id ASC
            """,
            (article_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def consommer_stock_fifo(article_id: int, quantite: int) -> list[dict]:
    quantite = int(quantite or 0)
    if quantite <= 0:
        return []

    conn = get_connection()
    try:
        lots = conn.execute(
            """
            SELECT id, quantite_restante, prix_unitaire_ttc
            FROM stock_lots
            WHERE article_id = ?
              AND statut = 'actif'
              AND quantite_restante > 0
            ORDER BY date(date_achat) ASC, id ASC
            """,
            (article_id,),
        ).fetchall()

        restant = quantite
        detail: list[dict] = []
        for lot in lots:
            if restant <= 0:
                break
            disponible = int(lot["quantite_restante"] or 0)
            if disponible <= 0:
                continue
            qte = min(disponible, restant)
            nouveau = disponible - qte
            conn.execute(
                """
                UPDATE stock_lots
                SET quantite_restante = ?,
                    statut = CASE WHEN ? <= 0 THEN 'epuise' ELSE statut END
                WHERE id = ?
                """,
                (nouveau, nouveau, lot["id"]),
            )
            prix = float(lot["prix_unitaire_ttc"] or 0)
            detail.append(
                {
                    "lot_id": lot["id"],
                    "qte_consommee": qte,
                    "prix_unit": prix,
                    "cout": round(qte * prix, 2),
                }
            )
            restant -= qte

        _sync_stock_quantite(conn, article_id)
        conn.commit()
        return detail
    finally:
        conn.close()


def calculer_cout_fifo(article_id: int, quantite: int) -> float:
    quantite = int(quantite or 0)
    if quantite <= 0:
        return 0.0

    lots = get_lots_fifo(article_id)
    restant = quantite
    total = 0.0
    for lot in lots:
        if restant <= 0:
            break
        disponible = int(lot.get("quantite_restante") or 0)
        qte = min(disponible, restant)
        total += qte * float(lot.get("prix_unitaire_ttc") or 0)
        restant -= qte
    return round(total, 2)


def get_stock_theorique(article_id: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(quantite_restante), 0) AS total
            FROM stock_lots
            WHERE article_id = ?
              AND statut IN ('actif', 'epuise')
            """,
            (article_id,),
        ).fetchone()
        return int(row["total"] if row else 0)
    finally:
        conn.close()


def get_articles_peremption_proche(jours: int = 30) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id AS article_id,
                   s.nom AS article,
                   l.id AS lot_id,
                   l.numero_lot AS lot,
                   l.date_peremption,
                   CAST(julianday(date(l.date_peremption)) - julianday(date('now')) AS INTEGER) AS jours_restants,
                   l.quantite_restante AS quantite
            FROM stock_lots l
            JOIN stock s ON s.id = l.article_id
            WHERE l.statut = 'actif'
              AND l.quantite_restante > 0
              AND l.date_peremption IS NOT NULL
              AND date(l.date_peremption) >= date('now')
              AND date(l.date_peremption) <= date('now', '+' || ? || ' days')
            ORDER BY date(l.date_peremption) ASC, s.nom ASC
            """,
            (int(jours),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_articles_perimes() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id AS article_id,
                   s.nom AS article,
                   l.id AS lot_id,
                   l.numero_lot AS lot,
                   l.date_peremption,
                   l.quantite_restante AS quantite
            FROM stock_lots l
            JOIN stock s ON s.id = l.article_id
            WHERE l.statut = 'actif'
              AND l.quantite_restante > 0
              AND l.date_peremption IS NOT NULL
              AND date(l.date_peremption) < date('now')
            ORDER BY date(l.date_peremption) ASC, s.nom ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def archiver_lots_perimes() -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE stock_lots
            SET statut = 'expire'
            WHERE statut = 'actif'
              AND quantite_restante > 0
              AND date_peremption IS NOT NULL
              AND date(date_peremption) < date('now')
            """
        )
        conn.commit()
        return int(cur.rowcount)
    finally:
        conn.close()


def add_lot(
    article_id,
    quantite,
    prix_ht,
    prix_ttc,
    tva_taux,
    fournisseur_id,
    numero_facture,
    numero_lot,
    date_achat,
    date_peremption,
    commentaire,
    tag_ids,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO stock_lots (
                article_id, numero_lot, numero_facture, fournisseur_id,
                date_achat, date_peremption,
                quantite_initiale, quantite_restante,
                prix_unitaire_ht, prix_unitaire_ttc, tva_taux,
                commentaire
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(article_id),
                (numero_lot or "").strip() or None,
                (numero_facture or "").strip() or None,
                int(fournisseur_id) if fournisseur_id else None,
                (date_achat or "").strip() or None,
                (date_peremption or "").strip() or None,
                int(quantite or 0),
                int(quantite or 0),
                float(prix_ht or 0),
                float(prix_ttc or 0),
                float(tva_taux or 0),
                (commentaire or "").strip() or None,
            ),
        )
        lot_id = cur.lastrowid

        clean_tag_ids = sorted({int(t) for t in (tag_ids or []) if t})
        for tag_id in clean_tag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO stock_lot_tags (lot_id, tag_id) VALUES (?, ?)",
                (lot_id, tag_id),
            )

        _sync_stock_quantite(conn, int(article_id))
        conn.commit()
        return lot_id
    finally:
        conn.close()


def get_lots_par_article(article_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, article_id, numero_lot, numero_facture, fournisseur_id,
                   date_achat, date_peremption,
                   quantite_initiale, quantite_restante,
                   prix_unitaire_ht, prix_unitaire_ttc, tva_taux,
                   statut, commentaire, created_at
            FROM stock_lots
            WHERE article_id = ?
            ORDER BY date(date_achat) ASC, id ASC
            """,
            (article_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_tags() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nom, couleur, systeme, created_at FROM stock_tags ORDER BY systeme DESC, nom ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_tag(nom: str, couleur: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO stock_tags (nom, couleur, systeme) VALUES (?, ?, 0)",
            ((nom or "").strip(), (couleur or "#3B82F6").strip() or "#3B82F6"),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_article_tags(article_id: int, tag_ids: list[int]):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM stock_article_tags WHERE article_id = ?", (article_id,))
        clean_tag_ids = sorted({int(t) for t in (tag_ids or []) if t})
        for tag_id in clean_tag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO stock_article_tags (article_id, tag_id) VALUES (?, ?)",
                (article_id, tag_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_article_tags(article_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.nom, t.couleur, t.systeme
            FROM stock_article_tags at
            JOIN stock_tags t ON t.id = at.tag_id
            WHERE at.article_id = ?
            ORDER BY t.systeme DESC, t.nom ASC
            """,
            (article_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
