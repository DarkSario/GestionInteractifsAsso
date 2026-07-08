"""CRUD pour la gestion des stands d'un événement."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


def get_stands_evenement(evenement_id: int) -> list[dict]:
    """Retourne les stands d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.evenement_id, s.numero_emplacement, s.nom_stand, s.type_stand,
                   s.responsable_membre_id, s.responsable_nom_externe,
                   m.nom AS responsable_nom, m.prenom AS responsable_prenom,
                   s.montant_location, s.paiement_avant, s.statut, s.commentaire, s.tresorerie_id
            FROM evenement_stands s
            LEFT JOIN membres m ON m.id = s.responsable_membre_id
            WHERE s.evenement_id = ?
            ORDER BY s.numero_emplacement ASC, s.id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_stand(
    evenement_id,
    numero_emplacement,
    nom_stand,
    type_stand,
    responsable_membre_id,
    responsable_nom_externe,
    montant_location,
    paiement_avant,
    commentaire,
) -> int:
    """Ajoute un stand et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_stands
                (evenement_id, numero_emplacement, nom_stand, type_stand,
                 responsable_membre_id, responsable_nom_externe,
                 montant_location, paiement_avant, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                numero_emplacement,
                nom_stand,
                type_stand,
                responsable_membre_id,
                responsable_nom_externe,
                montant_location or 0,
                1 if paiement_avant else 0,
                commentaire,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_STAND = frozenset(
    {
        "numero_emplacement",
        "nom_stand",
        "type_stand",
        "responsable_membre_id",
        "responsable_nom_externe",
        "montant_location",
        "paiement_avant",
        "statut",
        "commentaire",
        "tresorerie_id",
    }
)
_UPDATE_STAND_SQL = {
    col: f"UPDATE evenement_stands SET {col} = ? WHERE id = ?"
    for col in _COLONNES_STAND
}


def update_stand(stand_id, **kwargs) -> bool:
    """Met à jour un stand."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_STAND
    if champs_invalides:
        logger.error("update_stand: colonnes non autorisées : %s", champs_invalides)
        return False
    conn = get_connection()
    try:
        total_changes = 0
        for key, value in kwargs.items():
            cur = conn.execute(_UPDATE_STAND_SQL[key], (value, stand_id))
            total_changes += cur.rowcount
        conn.commit()
        return total_changes > 0
    except Exception as exc:
        logger.error("update_stand: %s", exc)
        return False
    finally:
        conn.close()


def delete_stand(stand_id: int) -> bool:
    """Supprime un stand."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM evenement_stands WHERE id = ?", (stand_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_stand: %s", exc)
        return False
    finally:
        conn.close()


def finaliser_location_stand(stand_id: int) -> bool:
    """Crée la recette de trésorerie d'un stand en location."""
    conn = get_connection()
    try:
        stand = conn.execute(
            """
            SELECT s.id, s.evenement_id, s.nom_stand, s.type_stand, s.montant_location, s.tresorerie_id,
                   e.nom AS evenement_nom
            FROM evenement_stands s
            LEFT JOIN evenements e ON e.id = s.evenement_id
            WHERE s.id = ?
            """,
            (stand_id,),
        ).fetchone()
        if not stand:
            return False

        data = dict(stand)
        if data.get("type_stand") != "location":
            return False

        if data.get("tresorerie_id"):
            return True

        montant = float(data.get("montant_location") or 0)
        if montant <= 0:
            return False

        date_du_jour = datetime.now().strftime("%Y-%m-%d")
        evenement_nom = data.get("evenement_nom") or f"Événement #{data.get('evenement_id')}"
        commentaire = f"Location stand — {evenement_nom} — {data.get('nom_stand') or 'Stand'}"
        cur_treso = conn.execute(
            """
            INSERT INTO dons_subventions (date, source, montant, type, commentaire)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date_du_jour, "Stand", montant, "Location stand", commentaire),
        )
        conn.execute(
            "UPDATE evenement_stands SET tresorerie_id = ? WHERE id = ?",
            (cur_treso.lastrowid, stand_id),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("finaliser_location_stand: %s", exc)
        return False
    finally:
        conn.close()


def get_attente_evenement(evenement_id: int) -> list[dict]:
    """Retourne la liste d'attente des stands d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, evenement_id, nom, prenom, contact, date_inscription, commentaire
            FROM evenement_stands_attente
            WHERE evenement_id = ?
            ORDER BY date_inscription ASC, id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_attente(evenement_id, nom, prenom, contact, commentaire) -> int:
    """Ajoute une entrée en liste d'attente et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_stands_attente (evenement_id, nom, prenom, contact, commentaire)
            VALUES (?, ?, ?, ?, ?)
            """,
            (evenement_id, nom, prenom, contact, commentaire),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def delete_attente(attente_id: int) -> bool:
    """Supprime une entrée de liste d'attente."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM evenement_stands_attente WHERE id = ?", (attente_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_attente: %s", exc)
        return False
    finally:
        conn.close()


def promouvoir_attente(attente_id: int) -> bool:
    """Promeut une entrée de liste d'attente en stand confirmé."""
    conn = get_connection()
    try:
        attente = conn.execute(
            """
            SELECT id, evenement_id, nom, prenom, contact, commentaire
            FROM evenement_stands_attente
            WHERE id = ?
            """,
            (attente_id,),
        ).fetchone()
        if not attente:
            return False

        data = dict(attente)
        prenom = (data.get("prenom") or "").strip()
        nom = (data.get("nom") or "").strip()
        identite = " ".join([p for p in [prenom, nom] if p]).strip() or "Inscrit"

        conn.execute(
            """
            INSERT INTO evenement_stands
                (evenement_id, numero_emplacement, nom_stand, type_stand,
                 responsable_nom_externe, montant_location, paiement_avant, statut, commentaire)
            VALUES (?, NULL, ?, 'benevole', ?, 0, 0, 'confirme', ?)
            """,
            (
                data["evenement_id"],
                f"Stand {identite}",
                identite,
                data.get("commentaire"),
            ),
        )
        conn.execute("DELETE FROM evenement_stands_attente WHERE id = ?", (attente_id,))
        conn.commit()
        return True
    except Exception as exc:
        logger.error("promouvoir_attente: %s", exc)
        return False
    finally:
        conn.close()


def get_stats_stands(evenement_id: int) -> dict:
    """Retourne des statistiques globales sur les stands."""
    stands = get_stands_evenement(evenement_id)
    actifs = [s for s in stands if s.get("statut") != "annule"]
    total = len(actifs)
    benevoles = sum(1 for s in actifs if s.get("type_stand") == "benevole")
    locations = sum(1 for s in actifs if s.get("type_stand") == "location")
    montant_locations = round(
        sum(float(s.get("montant_location") or 0) for s in actifs if s.get("type_stand") == "location"),
        2,
    )
    return {
        "total": total,
        "benevoles": benevoles,
        "locations": locations,
        "montant_locations": montant_locations,
    }
