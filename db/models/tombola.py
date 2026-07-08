"""CRUD pour la tombola d'un événement."""

from __future__ import annotations

from datetime import datetime

from db.connection import get_connection
from db.models.evenements import get_evenement_by_id
from utils.logger import get_logger

logger = get_logger(__name__)


def get_lots_evenement(evenement_id: int) -> list[dict]:
    """Retourne les lots de tombola d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.evenement_id, l.numero, l.description, l.valeur_estimee,
                   l.type_lot, l.fournisseur_id, f.nom AS fournisseur_nom,
                   l.sponsor_nom, l.numero_gagnant, l.statut, l.date_tirage, l.commentaire
            FROM tombola_lots l
            LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id
            WHERE l.evenement_id = ?
            ORDER BY l.numero ASC, l.id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_lot(
    evenement_id,
    numero,
    description,
    valeur_estimee,
    type_lot,
    fournisseur_id,
    sponsor_nom,
    commentaire,
) -> int:
    """Ajoute un lot de tombola et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tombola_lots
                (evenement_id, numero, description, valeur_estimee, type_lot,
                 fournisseur_id, sponsor_nom, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                numero,
                description,
                valeur_estimee or 0,
                type_lot,
                fournisseur_id,
                sponsor_nom,
                commentaire,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_LOT = frozenset(
    {
        "numero",
        "description",
        "valeur_estimee",
        "type_lot",
        "fournisseur_id",
        "sponsor_nom",
        "numero_gagnant",
        "statut",
        "date_tirage",
        "commentaire",
    }
)
_UPDATE_LOT_SQL = {col: f"UPDATE tombola_lots SET {col} = ? WHERE id = ?" for col in _COLONNES_LOT}


def update_lot(lot_id, **kwargs) -> bool:
    """Met à jour un lot de tombola."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_LOT
    if champs_invalides:
        logger.error("update_lot: colonnes non autorisées : %s", champs_invalides)
        return False
    conn = get_connection()
    try:
        total_changes = 0
        for key, value in kwargs.items():
            cur = conn.execute(_UPDATE_LOT_SQL[key], (value, lot_id))
            total_changes += cur.rowcount
        conn.commit()
        return total_changes > 0
    except Exception as exc:
        logger.error("update_lot: %s", exc)
        return False
    finally:
        conn.close()


def delete_lot(lot_id: int) -> bool:
    """Supprime un lot."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM tombola_lots WHERE id = ?", (lot_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_lot: %s", exc)
        return False
    finally:
        conn.close()


def enregistrer_gagnant(lot_id: int, numero_gagnant: str) -> bool:
    """Enregistre le numéro gagnant d'un lot et le marque attribué."""
    return update_lot(
        lot_id,
        numero_gagnant=numero_gagnant,
        statut="attribue",
        date_tirage=datetime.now().strftime("%Y-%m-%d"),
    )


def marquer_non_reclame(lot_id: int) -> bool:
    """Marque un lot comme non réclamé."""
    return update_lot(lot_id, statut="non_reclame")


def get_carnets_evenement(evenement_id: int) -> list[dict]:
    """Retourne les carnets de tombola d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.evenement_id, c.numero_debut, c.numero_fin, c.prix_carnet,
                   c.vendeur_membre_id, c.vendeur_nom_externe,
                   m.nom AS vendeur_nom, m.prenom AS vendeur_prenom,
                   c.statut, c.date_remise, c.montant_encaisse, c.commentaire
            FROM tombola_carnets c
            LEFT JOIN membres m ON m.id = c.vendeur_membre_id
            WHERE c.evenement_id = ?
            ORDER BY c.numero_debut ASC, c.id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_carnet(
    evenement_id,
    numero_debut,
    numero_fin,
    prix_carnet,
    vendeur_membre_id,
    vendeur_nom_externe,
    date_remise,
) -> int:
    """Ajoute un carnet de tombola et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tombola_carnets
                (evenement_id, numero_debut, numero_fin, prix_carnet,
                 vendeur_membre_id, vendeur_nom_externe, date_remise)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                numero_debut,
                numero_fin,
                prix_carnet,
                vendeur_membre_id,
                vendeur_nom_externe,
                date_remise,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_CARNET = frozenset(
    {
        "numero_debut",
        "numero_fin",
        "prix_carnet",
        "vendeur_membre_id",
        "vendeur_nom_externe",
        "statut",
        "date_remise",
        "montant_encaisse",
        "commentaire",
    }
)
_UPDATE_CARNET_SQL = {
    col: f"UPDATE tombola_carnets SET {col} = ? WHERE id = ?"
    for col in _COLONNES_CARNET
}


def update_carnet(carnet_id, **kwargs) -> bool:
    """Met à jour un carnet de tombola."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_CARNET
    if champs_invalides:
        logger.error("update_carnet: colonnes non autorisées : %s", champs_invalides)
        return False
    conn = get_connection()
    try:
        total_changes = 0
        for key, value in kwargs.items():
            cur = conn.execute(_UPDATE_CARNET_SQL[key], (value, carnet_id))
            total_changes += cur.rowcount
        conn.commit()
        return total_changes > 0
    except Exception as exc:
        logger.error("update_carnet: %s", exc)
        return False
    finally:
        conn.close()


def delete_carnet(carnet_id: int) -> bool:
    """Supprime un carnet de tombola."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM tombola_carnets WHERE id = ?", (carnet_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_carnet: %s", exc)
        return False
    finally:
        conn.close()


def _quantite_carnet(carnet: dict) -> int:
    debut = int(carnet.get("numero_debut") or 0)
    fin = int(carnet.get("numero_fin") or 0)
    return max(0, fin - debut + 1)


def get_stats_tombola(evenement_id: int) -> dict:
    """Retourne des statistiques de tombola pour un événement."""
    carnets = get_carnets_evenement(evenement_id)
    lots = get_lots_evenement(evenement_id)

    total_carnets = sum(_quantite_carnet(c) for c in carnets)
    vendus = sum(_quantite_carnet(c) for c in carnets if c.get("statut") == "vendu")
    retournes = sum(_quantite_carnet(c) for c in carnets if c.get("statut") == "retourne")
    perdus = sum(_quantite_carnet(c) for c in carnets if c.get("statut") == "perdu")
    montant_total = round(sum(float(c.get("montant_encaisse") or 0) for c in carnets), 2)
    lots_attribues = sum(1 for l in lots if l.get("statut") == "attribue")

    return {
        "total_carnets": total_carnets,
        "vendus": vendus,
        "retournes": retournes,
        "perdus": perdus,
        "montant_total": montant_total,
        "lots_attribues": lots_attribues,
    }


def generer_pv_tirage(evenement_id: int) -> dict:
    """Retourne les données d'un PV de tirage."""
    evenement = get_evenement_by_id(evenement_id) or {
        "id": evenement_id,
        "nom": f"Événement #{evenement_id}",
    }
    lots = get_lots_evenement(evenement_id)
    lots_tries = sorted(lots, key=lambda l: (int(l.get("numero") or 0), int(l.get("id") or 0)))
    return {
        "evenement": evenement,
        "date_generation": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lots": lots_tries,
    }
