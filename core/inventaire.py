"""Gestion métier des inventaires stock et du coût buvette par événement."""

from __future__ import annotations

import json

from db.connection import get_connection


def _sync_stock_quantites(conn, article_ids: set[int]) -> None:
    for article_id in article_ids:
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


def creer_inventaire(evenement_id: int, type_inventaire: str) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO stock_inventaires (evenement_id, type_inventaire, statut)
            VALUES (?, ?, 'en_cours')
            """,
            (evenement_id if evenement_id else None, type_inventaire),
        )
        inventaire_id = cur.lastrowid

        lots = conn.execute(
            """
            SELECT l.article_id, l.id AS lot_id, l.quantite_restante, l.prix_unitaire_ttc
            FROM stock_lots l
            WHERE l.statut = 'actif'
              AND l.quantite_restante > 0
            ORDER BY l.article_id, date(l.date_achat) ASC, l.id ASC
            """
        ).fetchall()

        for lot in lots:
            qte = int(lot["quantite_restante"] or 0)
            conn.execute(
                """
                INSERT INTO stock_inventaire_lignes (
                    inventaire_id, article_id, lot_id,
                    quantite_theorique, quantite_reelle,
                    prix_unitaire_fifo, valeur_ecart
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    inventaire_id,
                    lot["article_id"],
                    lot["lot_id"],
                    qte,
                    qte,
                    float(lot["prix_unitaire_ttc"] or 0),
                ),
            )

        conn.commit()
        return inventaire_id
    finally:
        conn.close()


def get_lignes_inventaire(inventaire_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id,
                   l.inventaire_id,
                   l.article_id,
                   s.nom AS article,
                   l.lot_id,
                   sl.numero_lot AS lot,
                   l.quantite_theorique AS qte_theorique,
                   l.quantite_reelle AS qte_reelle,
                   (COALESCE(l.quantite_reelle, 0) - COALESCE(l.quantite_theorique, 0)) AS ecart,
                   l.prix_unitaire_fifo AS prix_fifo,
                   l.valeur_ecart
            FROM stock_inventaire_lignes l
            JOIN stock s ON s.id = l.article_id
            LEFT JOIN stock_lots sl ON sl.id = l.lot_id
            WHERE l.inventaire_id = ?
            ORDER BY s.nom ASC, sl.date_achat ASC, l.id ASC
            """,
            (inventaire_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def saisir_ligne_inventaire(
    inventaire_id: int, article_id: int, lot_id: int | None, qte_reelle: int
):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE stock_inventaire_lignes
            SET quantite_reelle = ?
            WHERE inventaire_id = ?
              AND article_id = ?
              AND (
                    (lot_id IS NULL AND ? IS NULL)
                    OR lot_id = ?
              )
            """,
            (int(qte_reelle or 0), inventaire_id, article_id, lot_id, lot_id),
        )
        conn.commit()
    finally:
        conn.close()


def valider_inventaire(inventaire_id: int) -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, article_id, lot_id,
                   COALESCE(quantite_theorique, 0) AS quantite_theorique,
                   COALESCE(quantite_reelle, 0) AS quantite_reelle,
                   COALESCE(prix_unitaire_fifo, 0) AS prix_unitaire_fifo
            FROM stock_inventaire_lignes
            WHERE inventaire_id = ?
            ORDER BY id ASC
            """,
            (inventaire_id,),
        ).fetchall()

        ecart_total_valeur = 0.0
        article_ids: set[int] = set()
        alertes: list[str] = []

        for row in rows:
            qte_theo = int(row["quantite_theorique"])
            qte_reel = int(row["quantite_reelle"])
            if qte_reel < 0:
                qte_reel = 0
                alertes.append(f"Quantité réelle corrigée à 0 sur ligne {row['id']}")

            ecart = qte_reel - qte_theo
            valeur_ecart = round(ecart * float(row["prix_unitaire_fifo"] or 0), 2)
            ecart_total_valeur += valeur_ecart

            conn.execute(
                "UPDATE stock_inventaire_lignes SET quantite_reelle = ?, valeur_ecart = ? WHERE id = ?",
                (qte_reel, valeur_ecart, row["id"]),
            )

            lot_id = row["lot_id"]
            if lot_id:
                conn.execute(
                    """
                    UPDATE stock_lots
                    SET quantite_restante = ?,
                        statut = CASE WHEN ? <= 0 THEN 'epuise' ELSE 'actif' END
                    WHERE id = ?
                    """,
                    (qte_reel, qte_reel, lot_id),
                )
                article_ids.add(int(row["article_id"]))

        _sync_stock_quantites(conn, article_ids)
        conn.execute(
            "UPDATE stock_inventaires SET statut = 'valide' WHERE id = ?",
            (inventaire_id,),
        )
        conn.commit()

        return {
            "nb_lignes": len(rows),
            "ecart_total_valeur": round(ecart_total_valeur, 2),
            "alertes": alertes,
        }
    finally:
        conn.close()


def calculer_cout_buvette_evenement(evenement_id: int) -> dict:
    conn = get_connection()
    try:
        inv_avant = conn.execute(
            """
            SELECT id
            FROM stock_inventaires
            WHERE evenement_id = ?
              AND type_inventaire = 'avant_evenement'
              AND statut = 'valide'
            ORDER BY datetime(date_inventaire) DESC, id DESC
            LIMIT 1
            """,
            (evenement_id,),
        ).fetchone()
        inv_apres = conn.execute(
            """
            SELECT id
            FROM stock_inventaires
            WHERE evenement_id = ?
              AND type_inventaire = 'apres_evenement'
              AND statut = 'valide'
            ORDER BY datetime(date_inventaire) DESC, id DESC
            LIMIT 1
            """,
            (evenement_id,),
        ).fetchone()

        if not inv_avant or not inv_apres:
            return {"cout_ht": 0.0, "cout_ttc": 0.0, "detail": []}

        avant = conn.execute(
            """
            SELECT l.article_id,
                   s.nom AS article,
                   COALESCE(l.lot_id, 0) AS lot_id,
                   COALESCE(sl.numero_lot, '—') AS numero_lot,
                   COALESCE(l.quantite_reelle, l.quantite_theorique, 0) AS qte,
                   COALESCE(sl.prix_unitaire_ht, 0) AS prix_ht,
                   COALESCE(sl.prix_unitaire_ttc, l.prix_unitaire_fifo, 0) AS prix_ttc
            FROM stock_inventaire_lignes l
            JOIN stock s ON s.id = l.article_id
            LEFT JOIN stock_lots sl ON sl.id = l.lot_id
            WHERE l.inventaire_id = ?
            """,
            (inv_avant["id"],),
        ).fetchall()
        apres_rows = conn.execute(
            """
            SELECT COALESCE(lot_id, 0) AS lot_id,
                   COALESCE(quantite_reelle, quantite_theorique, 0) AS qte
            FROM stock_inventaire_lignes
            WHERE inventaire_id = ?
            """,
            (inv_apres["id"],),
        ).fetchall()
        apres = {int(r["lot_id"]): int(r["qte"] or 0) for r in apres_rows}

        detail: list[dict] = []
        total_ht = 0.0
        total_ttc = 0.0

        for row in avant:
            lot_id = int(row["lot_id"] or 0)
            qte_avant = int(row["qte"] or 0)
            qte_apres = int(apres.get(lot_id, 0))
            qte_consommee = max(0, qte_avant - qte_apres)
            if qte_consommee <= 0:
                continue

            prix_ht = float(row["prix_ht"] or 0)
            prix_ttc = float(row["prix_ttc"] or 0)
            cout_ht = round(qte_consommee * prix_ht, 2)
            cout_ttc = round(qte_consommee * prix_ttc, 2)
            total_ht += cout_ht
            total_ttc += cout_ttc
            detail.append(
                {
                    "article_id": row["article_id"],
                    "article": row["article"],
                    "lot_id": lot_id,
                    "lot": row["numero_lot"],
                    "qte_consommee": qte_consommee,
                    "prix_ht": prix_ht,
                    "prix_ttc": prix_ttc,
                    "cout_ht": cout_ht,
                    "cout_ttc": cout_ttc,
                }
            )

        conn.execute(
            """
            INSERT INTO buvette_couts_evenement (
                evenement_id, inventaire_avant_id, inventaire_apres_id,
                cout_total_ht, cout_total_ttc, statut, detail_json
            ) VALUES (?, ?, ?, ?, ?, 'calcule', ?)
            """,
            (
                evenement_id,
                inv_avant["id"],
                inv_apres["id"],
                round(total_ht, 2),
                round(total_ttc, 2),
                json.dumps(detail, ensure_ascii=False),
            ),
        )
        conn.commit()

        return {"cout_ht": round(total_ht, 2), "cout_ttc": round(total_ttc, 2), "detail": detail}
    finally:
        conn.close()


def get_inventaires(evenement_id: int = None) -> list[dict]:
    conn = get_connection()
    try:
        if evenement_id is not None:
            rows = conn.execute(
                """
                SELECT i.id, i.evenement_id, e.nom AS evenement_nom,
                       i.type_inventaire, i.date_inventaire, i.statut, i.commentaire, i.created_at
                FROM stock_inventaires i
                LEFT JOIN evenements e ON e.id = i.evenement_id
                WHERE i.evenement_id = ?
                ORDER BY datetime(i.date_inventaire) DESC, i.id DESC
                """,
                (evenement_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT i.id, i.evenement_id, e.nom AS evenement_nom,
                       i.type_inventaire, i.date_inventaire, i.statut, i.commentaire, i.created_at
                FROM stock_inventaires i
                LEFT JOIN evenements e ON e.id = i.evenement_id
                ORDER BY datetime(i.date_inventaire) DESC, i.id DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
