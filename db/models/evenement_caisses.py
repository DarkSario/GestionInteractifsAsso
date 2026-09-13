"""CRUD des caisses détaillées par événement."""

from __future__ import annotations

from db.connection import get_connection
from utils.logger import get_logger

_TYPES_OUVERTURE = {"debut", "fin"}
logger = get_logger(__name__)


def _open_connection(operation: str):
    try:
        return get_connection()
    except Exception:
        logger.exception("Impossible d'ouvrir la connexion DB (%s)", operation)
        raise


def _normaliser_type_ouverture(type_ouverture: str) -> str:
    value = str(type_ouverture or "").strip().lower()
    if value not in _TYPES_OUVERTURE:
        raise ValueError("type_ouverture invalide (attendu: debut ou fin)")
    return value


def _calculer_total(montant_unitaire: float, quantite: int) -> float:
    return round(float(montant_unitaire or 0) * int(quantite or 0), 2)


def creer_caisse(evenement_id: int, nom: str, statut: str = "ouvert") -> int:
    """Crée une caisse pour un événement."""
    nom_val = str(nom or "").strip()
    if not nom_val:
        raise ValueError("Le nom de la caisse est obligatoire.")

    conn = _open_connection("creer_caisse")
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_caisses (evenement_id, nom, nom_caisse, statut, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (int(evenement_id), nom_val, nom_val, statut or "ouvert"),
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception:
        logger.exception(
            "Erreur DB lors de la création d'une caisse (evenement_id=%s, nom=%s)",
            evenement_id,
            nom_val,
        )
        raise
    finally:
        conn.close()


def lister_caisses_evenement(evenement_id: int) -> list[dict]:
    """Retourne les caisses d'un événement avec leurs totaux."""
    conn = _open_connection("lister_caisses_evenement")
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.evenement_id, COALESCE(NULLIF(c.nom, ''), c.nom_caisse) AS nom,
                   COALESCE(c.statut, 'ouvert') AS statut, c.created_at, c.updated_at,
                   COALESCE(SUM(CASE WHEN l.type_ouverture = 'debut' THEN l.total END), 0) AS total_debut,
                   COALESCE(SUM(CASE WHEN l.type_ouverture = 'fin' THEN l.total END), 0) AS total_fin
            FROM evenement_caisses c
            LEFT JOIN evenement_caisse_lignes l ON l.caisse_id = c.id
            WHERE c.evenement_id = ?
            GROUP BY c.id
            ORDER BY c.id ASC
            """,
            (int(evenement_id),),
        ).fetchall()
        caisses: list[dict] = []
        for row in rows:
            data = dict(row)
            data["total_debut"] = round(float(data.get("total_debut") or 0), 2)
            data["total_fin"] = round(float(data.get("total_fin") or 0), 2)
            data["recette"] = round(data["total_fin"] - data["total_debut"], 2)
            caisses.append(data)
        return caisses
    except Exception:
        logger.exception(
            "Erreur DB lors du chargement des caisses (evenement_id=%s)", evenement_id
        )
        raise
    finally:
        conn.close()


def get_caisse(caisse_id: int) -> dict | None:
    """Retourne une caisse avec ses lignes début/fin."""
    conn = _open_connection("get_caisse")
    try:
        row = conn.execute(
            """
            SELECT id, evenement_id, COALESCE(NULLIF(nom, ''), nom_caisse) AS nom,
                   COALESCE(statut, 'ouvert') AS statut, created_at, updated_at
            FROM evenement_caisses
            WHERE id = ?
            """,
            (int(caisse_id),),
        ).fetchone()
        if not row:
            return None
        caisse = dict(row)
        debut = get_lignes_caisse(caisse_id, "debut")
        fin = get_lignes_caisse(caisse_id, "fin")
        total_debut = round(sum(float(l.get("total") or 0) for l in debut), 2)
        total_fin = round(sum(float(l.get("total") or 0) for l in fin), 2)
        caisse["lignes_debut"] = debut
        caisse["lignes_fin"] = fin
        caisse["total_debut"] = total_debut
        caisse["total_fin"] = total_fin
        caisse["recette"] = round(total_fin - total_debut, 2)
        return caisse
    except Exception:
        logger.exception("Erreur DB lors du chargement de la caisse (caisse_id=%s)", caisse_id)
        raise
    finally:
        conn.close()


def mettre_a_jour_caisse(
    caisse_id: int, nom: str | None = None, statut: str | None = None
) -> bool:
    """Met à jour le nom et/ou le statut d'une caisse."""
    updates: list[str] = []
    params: list[object] = []
    if nom is not None:
        nom_val = str(nom).strip()
        if not nom_val:
            raise ValueError("Le nom de la caisse est obligatoire.")
        updates.append("nom = ?")
        updates.append("nom_caisse = ?")
        params.extend([nom_val, nom_val])
    if statut is not None:
        updates.append("statut = ?")
        params.append(str(statut))
    if not updates:
        return False
    updates.append("updated_at = datetime('now')")
    params.append(int(caisse_id))

    conn = _open_connection("mettre_a_jour_caisse")
    try:
        cur = conn.execute(
            f"UPDATE evenement_caisses SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception(
            "Erreur DB lors de la mise à jour de la caisse (caisse_id=%s)", caisse_id
        )
        raise
    finally:
        conn.close()


def supprimer_caisse(caisse_id: int) -> bool:
    """Supprime une caisse et ses lignes."""
    conn = _open_connection("supprimer_caisse")
    try:
        conn.execute(
            "DELETE FROM evenement_caisse_lignes WHERE caisse_id = ?",
            (int(caisse_id),),
        )
        cur = conn.execute(
            "DELETE FROM evenement_caisses WHERE id = ?", (int(caisse_id),)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("Erreur DB lors de la suppression de la caisse (caisse_id=%s)", caisse_id)
        raise
    finally:
        conn.close()


def get_lignes_caisse(caisse_id: int, type_ouverture: str) -> list[dict]:
    """Retourne les lignes d'une caisse pour un type d'ouverture."""
    type_val = _normaliser_type_ouverture(type_ouverture)
    conn = _open_connection("get_lignes_caisse")
    try:
        rows = conn.execute(
            """
            SELECT id, caisse_id, type_ouverture, designation_id,
                   COALESCE(NULLIF(designation_text, ''), designation) AS designation,
                   designation_text, montant_unitaire, quantite, total, created_at, updated_at
            FROM evenement_caisse_lignes
            WHERE caisse_id = ? AND type_ouverture = ?
            ORDER BY id ASC
            """,
            (int(caisse_id), type_val),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception(
            "Erreur DB lors du chargement des lignes de caisse (caisse_id=%s, type=%s)",
            caisse_id,
            type_val,
        )
        raise
    finally:
        conn.close()


def ajouter_ligne_caisse(
    caisse_id: int,
    type_ouverture: str,
    designation: str,
    montant_unitaire: float,
    quantite: int,
    designation_id: int | None = None,
) -> int:
    """Ajoute une ligne de détail à une caisse."""
    type_val = _normaliser_type_ouverture(type_ouverture)
    designation_val = str(designation or "").strip()
    if not designation_val:
        raise ValueError("La désignation est obligatoire.")
    quantite_val = int(quantite or 0)
    if quantite_val < 0:
        raise ValueError("La quantité doit être positive ou nulle.")
    montant_val = float(montant_unitaire or 0)
    if montant_val < 0:
        raise ValueError("Le montant unitaire doit être positif ou nul.")
    total = _calculer_total(montant_val, quantite_val)

    conn = _open_connection("ajouter_ligne_caisse")
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_caisse_lignes (
                caisse_id, type_ouverture, designation_id, designation_text, designation,
                montant_unitaire, quantite, total, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                int(caisse_id),
                type_val,
                int(designation_id) if designation_id else None,
                designation_val,
                designation_val,
                montant_val,
                quantite_val,
                total,
            ),
        )
        conn.execute(
            "UPDATE evenement_caisses SET updated_at = datetime('now') WHERE id = ?",
            (int(caisse_id),),
        )
        conn.commit()
        return int(cur.lastrowid)
    except Exception:
        logger.exception(
            "Erreur DB lors de l'ajout d'une ligne de caisse (caisse_id=%s, type=%s)",
            caisse_id,
            type_val,
        )
        raise
    finally:
        conn.close()


def modifier_ligne_caisse(
    ligne_id: int,
    designation: str,
    montant_unitaire: float,
    quantite: int,
    designation_id: int | None = None,
) -> bool:
    """Modifie une ligne de caisse."""
    designation_val = str(designation or "").strip()
    if not designation_val:
        raise ValueError("La désignation est obligatoire.")
    quantite_val = int(quantite or 0)
    if quantite_val < 0:
        raise ValueError("La quantité doit être positive ou nulle.")
    montant_val = float(montant_unitaire or 0)
    if montant_val < 0:
        raise ValueError("Le montant unitaire doit être positif ou nul.")
    total = _calculer_total(montant_val, quantite_val)

    conn = _open_connection("modifier_ligne_caisse")
    try:
        caisse = conn.execute(
            "SELECT caisse_id FROM evenement_caisse_lignes WHERE id = ?",
            (int(ligne_id),),
        ).fetchone()
        if not caisse:
            return False
        cur = conn.execute(
            """
            UPDATE evenement_caisse_lignes
            SET designation_id = ?, designation_text = ?, designation = ?, montant_unitaire = ?,
                quantite = ?, total = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                int(designation_id) if designation_id else None,
                designation_val,
                designation_val,
                montant_val,
                quantite_val,
                total,
                int(ligne_id),
            ),
        )
        conn.execute(
            "UPDATE evenement_caisses SET updated_at = datetime('now') WHERE id = ?",
            (int(caisse["caisse_id"]),),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("Erreur DB lors de la modification de ligne (ligne_id=%s)", ligne_id)
        raise
    finally:
        conn.close()


def supprimer_ligne_caisse(ligne_id: int) -> bool:
    """Supprime une ligne de caisse."""
    conn = _open_connection("supprimer_ligne_caisse")
    try:
        caisse = conn.execute(
            "SELECT caisse_id FROM evenement_caisse_lignes WHERE id = ?",
            (int(ligne_id),),
        ).fetchone()
        cur = conn.execute(
            "DELETE FROM evenement_caisse_lignes WHERE id = ?", (int(ligne_id),)
        )
        if caisse:
            conn.execute(
                "UPDATE evenement_caisses SET updated_at = datetime('now') WHERE id = ?",
                (int(caisse["caisse_id"]),),
            )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        logger.exception("Erreur DB lors de la suppression de ligne (ligne_id=%s)", ligne_id)
        raise
    finally:
        conn.close()


def get_total_caisse(caisse_id: int, type_ouverture: str) -> float:
    """Retourne le total d'une caisse pour 'debut' ou 'fin'."""
    type_val = _normaliser_type_ouverture(type_ouverture)
    conn = _open_connection("get_total_caisse")
    try:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total), 0) AS total
            FROM evenement_caisse_lignes
            WHERE caisse_id = ? AND type_ouverture = ?
            """,
            (int(caisse_id), type_val),
        ).fetchone()
        return round(float(row["total"] if row else 0), 2)
    except Exception:
        logger.exception(
            "Erreur DB lors du calcul du total caisse (caisse_id=%s, type=%s)",
            caisse_id,
            type_val,
        )
        raise
    finally:
        conn.close()


def get_recette_caisse(caisse_id: int) -> float:
    """Retourne la recette d'une caisse (fin - début)."""
    total_debut = get_total_caisse(caisse_id, "debut")
    total_fin = get_total_caisse(caisse_id, "fin")
    return round(total_fin - total_debut, 2)


def get_total_recettes_caisses_evenement(evenement_id: int) -> float:
    """Retourne la somme des recettes de toutes les caisses d'un événement."""
    conn = _open_connection("get_total_recettes_caisses_evenement")
    try:
        row = conn.execute(
            """
            SELECT COALESCE(
                SUM(CASE WHEN l.type_ouverture = 'fin' THEN l.total
                         WHEN l.type_ouverture = 'debut' THEN -l.total
                         ELSE 0 END), 0
            ) AS recette
            FROM evenement_caisses c
            LEFT JOIN evenement_caisse_lignes l ON l.caisse_id = c.id
            WHERE c.evenement_id = ?
            """,
            (int(evenement_id),),
        ).fetchone()
        return round(float(row["recette"] if row else 0), 2)
    except Exception:
        logger.exception(
            "Erreur DB lors du calcul des recettes des caisses (evenement_id=%s)",
            evenement_id,
        )
        raise
    finally:
        conn.close()
