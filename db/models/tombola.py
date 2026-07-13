"""CRUD pour la tombola d'un événement."""

from __future__ import annotations

import random
from datetime import datetime

from db.connection import get_connection
from db.models.evenements import get_evenement_by_id
from utils.logger import get_logger

logger = get_logger(__name__)
_LOT_AWARDED_STATUSES = {"attribue", "gagne", "remis"}


def get_lots_evenement(evenement_id: int) -> list[dict]:
    """Retourne les lots de tombola d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.evenement_id, l.numero, l.description, l.valeur_estimee, l.valeur_lot,
                   l.type_lot, l.fournisseur_id, f.nom AS fournisseur_nom, l.donateur,
                   l.sponsor_nom, l.numero_gagnant, l.statut, l.date_tirage, l.commentaire,
                   l.type_provenance, l.acheteur_membre_id,
                   m.nom AS acheteur_nom, m.prenom AS acheteur_prenom,
                   l.montant_avance, l.remboursement_statut, l.remboursement_date,
                   l.remboursement_mode, l.remboursement_reference,
                   l.donateur_externe, l.remarque
            FROM tombola_lots l
            LEFT JOIN fournisseurs f ON f.id = l.fournisseur_id
            LEFT JOIN membres m ON m.id = l.acheteur_membre_id
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
    valeur_lot,
    type_lot,
    fournisseur_id,
    sponsor_nom,
    commentaire,
    donateur=None,
    type_provenance=None,
    acheteur_membre_id=None,
    montant_avance=None,
    remboursement_statut=None,
    donateur_externe=None,
    remarque=None,
) -> int:
    """Ajoute un lot de tombola et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tombola_lots
                (evenement_id, numero, description, valeur_estimee, type_lot,
                 valeur_lot, fournisseur_id, sponsor_nom, commentaire, donateur,
                 type_provenance, acheteur_membre_id, montant_avance,
                 remboursement_statut, donateur_externe, remarque)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                numero,
                description,
                valeur_estimee or 0,
                type_lot,
                valeur_lot if valeur_lot is not None else valeur_estimee or 0,
                fournisseur_id,
                sponsor_nom,
                commentaire,
                donateur,
                type_provenance or "association",
                acheteur_membre_id or None,
                montant_avance or None,
                remboursement_statut or "non_applicable",
                donateur_externe or None,
                remarque or None,
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
        "valeur_lot",
        "type_lot",
        "fournisseur_id",
        "sponsor_nom",
        "donateur",
        "numero_gagnant",
        "statut",
        "date_tirage",
        "commentaire",
        "type_provenance",
        "acheteur_membre_id",
        "montant_avance",
        "remboursement_statut",
        "remboursement_date",
        "remboursement_mode",
        "remboursement_reference",
        "donateur_externe",
        "remarque",
    }
)
_UPDATE_LOT_SQL = {
    col: f"UPDATE tombola_lots SET {col} = ? WHERE id = ?" for col in _COLONNES_LOT
}


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


def marquer_rembourse_lot(
    lot_id: int,
    mode: str,
    reference: str | None,
    date: str,
) -> bool:
    """Marque un lot comme remboursé."""
    return update_lot(
        lot_id,
        remboursement_statut="rembourse",
        remboursement_mode=mode or None,
        remboursement_reference=reference or None,
        remboursement_date=date,
    )


def get_lots_remboursement_en_attente() -> list[dict]:
    """Retourne les lots de tombola dont le remboursement est en attente."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                tl.id,
                'tombola' AS source,
                'tombola:' || tl.id AS remboursement_id,
                e.nom AS evenement_nom,
                m.nom AS membre_nom,
                m.prenom AS membre_prenom,
                tl.description AS description,
                tl.montant_avance AS montant,
                tl.remboursement_statut,
                tl.remboursement_date,
                tl.remboursement_mode,
                tl.remboursement_reference,
                tl.acheteur_membre_id AS membre_id,
                e.date_debut AS date_evenement
            FROM tombola_lots tl
            LEFT JOIN evenements e ON e.id = tl.evenement_id
            LEFT JOIN membres m ON m.id = tl.acheteur_membre_id
            WHERE tl.remboursement_statut = 'en_attente'
              AND tl.acheteur_membre_id IS NOT NULL
            ORDER BY tl.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def enregistrer_gagnant(lot_id: int, numero_gagnant: str) -> bool:
    """Enregistre le numéro gagnant d'un lot et le marque attribué."""
    return update_lot(
        lot_id,
        numero_gagnant=numero_gagnant,
        statut="gagne",
        date_tirage=datetime.now().strftime("%Y-%m-%d"),
    )


def marquer_non_reclame(lot_id: int) -> bool:
    """Marque un lot comme non réclamé."""
    return update_lot(lot_id, statut="reserve")


def get_config_tombola_evenement(evenement_id: int) -> dict:
    """Retourne la configuration tombola de l'événement."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT tombola_prix_ticket, tombola_prix_carnet, tombola_tickets_par_carnet
            FROM evenements
            WHERE id = ?
            """,
            (evenement_id,),
        ).fetchone()
    finally:
        conn.close()
    evenement = dict(row) if row else {}
    return {
        "prix_ticket": float(evenement.get("tombola_prix_ticket") or 1.0),
        "prix_carnet": float(evenement.get("tombola_prix_carnet") or 5.0),
        "tickets_par_carnet": int(evenement.get("tombola_tickets_par_carnet") or 5),
    }


def update_config_tombola_evenement(
    evenement_id: int,
    prix_ticket: float,
    prix_carnet: float,
    tickets_par_carnet: int | None = None,
) -> bool:
    """Met à jour les prix ticket/carnet tombola de l'événement."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE evenements
            SET tombola_prix_ticket = ?,
                tombola_prix_carnet = ?,
                tombola_tickets_par_carnet = ?
            WHERE id = ?
            """,
            (
                float(prix_ticket or 0),
                float(prix_carnet or 0),
                int(tickets_par_carnet or 5),
                evenement_id,
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


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
    retournes = sum(
        _quantite_carnet(c) for c in carnets if c.get("statut") == "retourne"
    )
    perdus = sum(_quantite_carnet(c) for c in carnets if c.get("statut") == "perdu")
    montant_total = round(
        sum(float(c.get("montant_encaisse") or 0) for c in carnets), 2
    )
    lots_attribues = sum(1 for lot in lots if lot.get("statut") in _LOT_AWARDED_STATUSES)

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
    lots_tries = sorted(
        lots,
        key=lambda lot: (int(lot.get("numero") or 0), int(lot.get("id") or 0)),
    )
    return {
        "evenement": evenement,
        "date_generation": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lots": lots_tries,
    }


def add_participation_solidaire(
    evenement_id: int,
    nom: str,
    prenom: str,
    telephone: str | None,
    montant_don: float,
    commentaire: str | None,
) -> int:
    """Ajoute une participation de tombola solidaire."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tombola_solidaire_participations (
                evenement_id, nom, prenom, telephone, montant_don, commentaire
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                nom,
                prenom,
                telephone or None,
                float(montant_don or 0),
                commentaire or None,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_participations_solidaires(evenement_id: int) -> list[dict]:
    """Retourne les participations de tombola solidaire d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, evenement_id, nom, prenom, telephone, montant_don,
                   date_participation, est_gagnant, commentaire, created_at
            FROM tombola_solidaire_participations
            WHERE evenement_id = ?
            ORDER BY est_gagnant DESC, date_participation ASC, id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_total_dons_tombola_solidaire(evenement_id: int) -> float:
    """Calcule le total des dons collectés pour la tombola solidaire."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(montant_don), 0) AS total
            FROM tombola_solidaire_participations
            WHERE evenement_id = ?
            """,
            (evenement_id,),
        ).fetchone()
        return round(float(row["total"] or 0), 2) if row else 0.0
    finally:
        conn.close()


def effectuer_tirage_tombola_solidaire(
    evenement_id: int, seed: int | None = None
) -> dict | None:
    """Désigne aléatoirement un gagnant pour la tombola solidaire.

    Le paramètre ``seed`` est optionnel et sert uniquement à rendre le tirage
    déterministe dans les tests automatisés.
    """
    participations = get_participations_solidaires(evenement_id)
    if not participations:
        return None
    rng = random.Random(seed)
    gagnant = rng.choice(participations)
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE tombola_solidaire_participations
            SET est_gagnant = CASE WHEN id = ? THEN 1 ELSE 0 END
            WHERE evenement_id = ?
            """,
            (gagnant["id"], evenement_id),
        )
        conn.commit()
    finally:
        conn.close()
    for participation in participations:
        participation["est_gagnant"] = 1 if participation["id"] == gagnant["id"] else 0
    return next((p for p in participations if p["id"] == gagnant["id"]), None)
