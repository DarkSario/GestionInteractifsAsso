"""Budget prévisionnel/réel des événements (Phase 12)."""

from __future__ import annotations

import math
import sqlite3
from datetime import date

from db.connection import get_connection


def _annee_scolaire_par_defaut() -> str:
    today = date.today()
    start = today.year if today.month >= 9 else today.year - 1
    return f"{start}/{start + 1}"


def _plage_annee_scolaire(annee_scolaire: str | None) -> tuple[str, str]:
    ref = annee_scolaire or _annee_scolaire_par_defaut()
    try:
        parts = str(ref).split("/")
        if len(parts) != 2:
            raise ValueError
        debut_annee = int(parts[0])
        _ = int(parts[1])
    except (TypeError, ValueError) as exc:
        raise ValueError("Format d'année scolaire invalide (attendu : YYYY/YYYY).") from exc
    return f"{debut_annee}-09-01", f"{debut_annee + 1}-09-01"


def get_or_create_budget(evenement_id: int) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, evenement_id, recettes_prevues, depenses_prevues,
                   cout_buvette_prevu, nb_personnes_attendues, prix_moyen_entree,
                   created_at, updated_at
            FROM evenement_budget
            WHERE evenement_id = ?
            """,
            (evenement_id,),
        ).fetchone()
        if row:
            return dict(row)

        conn.execute(
            "INSERT INTO evenement_budget (evenement_id) VALUES (?)",
            (evenement_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM evenement_budget WHERE evenement_id = ?",
            (evenement_id,),
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def sauvegarder_budget(
    evenement_id: int,
    recettes: float,
    depenses: float,
    cout_buvette: float,
    nb_personnes: int,
    prix_moyen_entree: float,
) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO evenement_budget (
                evenement_id,
                recettes_prevues,
                depenses_prevues,
                cout_buvette_prevu,
                nb_personnes_attendues,
                prix_moyen_entree,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(evenement_id) DO UPDATE SET
                recettes_prevues = excluded.recettes_prevues,
                depenses_prevues = excluded.depenses_prevues,
                cout_buvette_prevu = excluded.cout_buvette_prevu,
                nb_personnes_attendues = excluded.nb_personnes_attendues,
                prix_moyen_entree = excluded.prix_moyen_entree,
                updated_at = datetime('now')
            """,
            (
                evenement_id,
                float(recettes or 0),
                float(depenses or 0),
                float(cout_buvette or 0),
                int(nb_personnes or 0),
                float(prix_moyen_entree or 0),
            ),
        )
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _recettes_reelles(conn, evenement_id: int) -> float:
    row = conn.execute(
        """
        SELECT
            COALESCE((
                SELECT SUM(montant_net)
                FROM evenement_ventes
                WHERE evenement_id = ? AND statut = 'valide'
            ), 0)
            +
            COALESCE((
                SELECT SUM(montant_location)
                FROM evenement_stands
                WHERE evenement_id = ?
                  AND type_stand = 'location'
                  AND COALESCE(type_location, 'recette') = 'recette'
                  AND statut != 'annule'
            ), 0)
            AS total
        """,
        (evenement_id, evenement_id),
    ).fetchone()
    return float(row["total"] if row else 0)


def _depenses_reelles(conn, evenement_id: int) -> float:
    row = conn.execute(
        """
        SELECT
            COALESCE((SELECT SUM(montant) FROM evenement_depenses WHERE evenement_id = ?), 0)
            +
            COALESCE((
                SELECT SUM(montant_location)
                FROM evenement_stands
                WHERE evenement_id = ?
                  AND type_stand = 'location'
                  AND COALESCE(type_location, 'recette') = 'depense'
                  AND statut != 'annule'
            ), 0)
            AS total
        """,
        (evenement_id, evenement_id),
    ).fetchone()
    return float(row["total"] if row else 0)


def _cout_buvette_reel(conn, evenement_id: int) -> float:
    row = conn.execute(
        """
        SELECT COALESCE(cout_total_ttc, 0) AS total
        FROM buvette_couts_evenement
        WHERE evenement_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (evenement_id,),
    ).fetchone()
    return float(row["total"] if row else 0)


def get_bilan_reel(evenement_id: int) -> dict:
    conn = get_connection()
    try:
        budget = get_or_create_budget(evenement_id)
        recettes_reelles = _recettes_reelles(conn, evenement_id)
        depenses_reelles = _depenses_reelles(conn, evenement_id)
        cout_buvette_reel = _cout_buvette_reel(conn, evenement_id)

        benefice_reel = recettes_reelles - depenses_reelles - cout_buvette_reel
        recettes_prevues = float(budget.get("recettes_prevues") or 0)
        depenses_prevues = float(budget.get("depenses_prevues") or 0)
        cout_buvette_prevu = float(budget.get("cout_buvette_prevu") or 0)
        benefice_prevu = recettes_prevues - depenses_prevues - cout_buvette_prevu

        return {
            "recettes_reelles": round(recettes_reelles, 2),
            "depenses_reelles": round(depenses_reelles, 2),
            "cout_buvette_reel": round(cout_buvette_reel, 2),
            "benefice_reel": round(benefice_reel, 2),
            "ecart_recettes": round(recettes_reelles - recettes_prevues, 2),
            "ecart_depenses": round(depenses_prevues - depenses_reelles, 2),
            "ecart_benefice": round(benefice_reel - benefice_prevu, 2),
        }
    finally:
        conn.close()


def get_seuil_rentabilite(evenement_id: int) -> dict:
    conn = get_connection()
    try:
        budget = get_or_create_budget(evenement_id)
        prix_moyen = float(budget.get("prix_moyen_entree") or 0)
        cout_total = float(budget.get("depenses_prevues") or 0) + float(
            budget.get("cout_buvette_prevu") or 0
        )
        seuil_prevu = int(math.ceil(cout_total / prix_moyen)) if prix_moyen > 0 else 0

        row = conn.execute(
            """
            SELECT COALESCE(SUM(l.quantite), 0) AS total
            FROM evenement_vente_lignes l
            JOIN evenement_ventes v ON v.id = l.vente_id
            WHERE v.evenement_id = ?
              AND v.statut = 'valide'
            """,
            (evenement_id,),
        ).fetchone()
        personnes_reelles = int(row["total"] if row else 0)
        manque = max(0, seuil_prevu - personnes_reelles)

        return {
            "seuil_prevu": seuil_prevu,
            "cout_total": round(cout_total, 2),
            "prix_moyen": round(prix_moyen, 2),
            "personnes_reelles": personnes_reelles,
            "atteint": personnes_reelles >= seuil_prevu if seuil_prevu > 0 else True,
            "manque": manque,
        }
    finally:
        conn.close()


def get_bilan_annuel_buvette(annee_scolaire: str = None) -> dict:
    debut, fin = _plage_annee_scolaire(annee_scolaire)
    conn = get_connection()
    try:
        tag_buvette = conn.execute(
            "SELECT id FROM stock_tags WHERE nom = 'Buvette' LIMIT 1"
        ).fetchone()
        tag_id = int(tag_buvette["id"]) if tag_buvette else 0

        params = (tag_id, tag_id)
        achats_row = conn.execute(
            """
            SELECT COALESCE(SUM(l.quantite_initiale * l.prix_unitaire_ttc), 0) AS total
            FROM stock_lots l
            WHERE EXISTS (SELECT 1 FROM stock_lot_tags lt WHERE lt.lot_id = l.id AND lt.tag_id = ?)
               OR EXISTS (SELECT 1 FROM stock_article_tags at WHERE at.article_id = l.article_id AND at.tag_id = ?)
            """,
            params,
        ).fetchone()

        restant_row = conn.execute(
            """
            SELECT COALESCE(SUM(l.quantite_restante * l.prix_unitaire_ttc), 0) AS total
            FROM stock_lots l
            WHERE l.statut IN ('actif', 'epuise')
              AND (EXISTS (SELECT 1 FROM stock_lot_tags lt WHERE lt.lot_id = l.id AND lt.tag_id = ?)
                OR EXISTS (SELECT 1 FROM stock_article_tags at WHERE at.article_id = l.article_id AND at.tag_id = ?))
            """,
            params,
        ).fetchone()

        couts_row = conn.execute(
            """
            SELECT COALESCE(SUM(c.cout_total_ttc), 0) AS total
            FROM buvette_couts_evenement c
            JOIN (
                SELECT evenement_id, MAX(id) AS max_id
                FROM buvette_couts_evenement
                GROUP BY evenement_id
            ) x ON x.max_id = c.id
            JOIN evenements e ON e.id = c.evenement_id
            WHERE date(e.date_debut) >= date(?)
              AND date(e.date_debut) < date(?)
            """,
            (debut, fin),
        ).fetchone()

        events = conn.execute(
            """
            SELECT e.id, e.nom,
                   COALESCE((SELECT SUM(v.montant_net)
                             FROM evenement_ventes v
                             WHERE v.evenement_id = e.id AND v.statut = 'valide'), 0) AS recettes,
                   COALESCE((SELECT c.cout_total_ttc
                             FROM buvette_couts_evenement c
                             WHERE c.evenement_id = e.id
                             ORDER BY c.id DESC
                             LIMIT 1), 0) AS cout_buvette
            FROM evenements e
            WHERE date(e.date_debut) >= date(?)
              AND date(e.date_debut) < date(?)
            ORDER BY date(e.date_debut) ASC, e.id ASC
            """,
            (debut, fin),
        ).fetchall()

        par_evenement = []
        for ev in events:
            recettes = float(ev["recettes"] or 0)
            cout = float(ev["cout_buvette"] or 0)
            par_evenement.append(
                {
                    "nom": ev["nom"],
                    "recettes": round(recettes, 2),
                    "cout_buvette": round(cout, 2),
                    "marge": round(recettes - cout, 2),
                }
            )

        return {
            "total_achats": round(float(achats_row["total"] if achats_row else 0), 2),
            "total_couts_consommes": round(float(couts_row["total"] if couts_row else 0), 2),
            "stock_restant": round(float(restant_row["total"] if restant_row else 0), 2),
            "par_evenement": par_evenement,
        }
    finally:
        conn.close()
