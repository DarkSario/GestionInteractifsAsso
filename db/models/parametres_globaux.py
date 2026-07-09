"""CRUD pour les paramètres globaux (Phase 7).

Gère :
- Paramètres clé/valeur génériques (table ``parametres``)
- Classes scolaires (table ``classes_scolaires``)
- Types d'événements (table ``types_evenements``)
- Modes de paiement (table ``modes_paiement``)
"""

from __future__ import annotations

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Utilitaires internes ──────────────────────────────────────────────────────


def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _execute(query: str, params: tuple = ()) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


# ── Paramètres génériques ─────────────────────────────────────────────────────


def get_parametre(cle: str, defaut: str = "") -> str:
    """Retourne la valeur d'un paramètre ou *defaut* si absent."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT valeur FROM parametres WHERE cle = ?", (cle,)
        ).fetchone()
        if row is None:
            return defaut
        return row["valeur"] if row["valeur"] is not None else defaut
    finally:
        conn.close()


def set_parametre(cle: str, valeur: str) -> bool:
    """Insère ou met à jour un paramètre. Retourne True si succès."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO parametres (cle, valeur) VALUES (?, ?)",
            (cle, valeur),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("set_parametre(%s): %s", cle, exc)
        return False
    finally:
        conn.close()


def get_all_parametres() -> dict[str, str]:
    """Retourne tous les paramètres sous forme {cle: valeur}."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT cle, valeur FROM parametres").fetchall()
        return {row["cle"]: (row["valeur"] or "") for row in rows}
    finally:
        conn.close()


# ── Classes scolaires ─────────────────────────────────────────────────────────


def get_all_classes(actif_only: bool = False) -> list[dict]:
    """Retourne toutes les classes scolaires, triées par ordre."""
    query = "SELECT id, nom, ordre, actif FROM classes_scolaires"
    if actif_only:
        query += " WHERE actif = 1"
    query += " ORDER BY ordre ASC, nom ASC"
    return _fetch_all(query)


def add_classe(nom: str, ordre: int = 0) -> int:
    """Ajoute une classe scolaire. Retourne l'id créé, ou 0 en cas d'erreur."""
    try:
        return _execute(
            "INSERT INTO classes_scolaires (nom, ordre) VALUES (?, ?)",
            (nom.strip(), ordre),
        )
    except Exception as exc:
        logger.error("add_classe: %s", exc)
        return 0


def update_classe(classe_id: int, nom: str, ordre: int) -> bool:
    """Met à jour le nom et l'ordre d'une classe scolaire."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE classes_scolaires SET nom = ?, ordre = ? WHERE id = ?",
                (nom.strip(), ordre, classe_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("update_classe: %s", exc)
        return False


def toggle_classe(classe_id: int) -> bool:
    """Bascule l'état actif/inactif d'une classe. Retourne True si succès."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE classes_scolaires SET actif = CASE WHEN actif = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (classe_id,),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("toggle_classe: %s", exc)
        return False


def delete_classe(classe_id: int) -> bool:
    """Supprime une classe scolaire.

    Bloqué si la classe est référencée dans ``evenement_paiements.classe``.
    Retourne True si suppression OK, False sinon.
    """
    conn = get_connection()
    try:
        # Récupérer le nom de la classe
        row_nom = conn.execute(
            "SELECT nom FROM classes_scolaires WHERE id = ?", (classe_id,)
        ).fetchone()
        if not row_nom:
            return False

        nom = row_nom["nom"]

        # Vérification des références dans evenement_paiements
        ref = conn.execute(
            "SELECT COUNT(*) FROM evenement_paiements WHERE classe = ?",
            (nom,),
        ).fetchone()
        if ref and ref[0] > 0:
            logger.warning(
                "delete_classe: classe '%s' (%d) utilisée dans evenement_paiements",
                nom, classe_id,
            )
            return False

        conn.execute("DELETE FROM classes_scolaires WHERE id = ?", (classe_id,))
        conn.commit()
        return True
    except Exception as exc:
        logger.error("delete_classe: %s", exc)
        return False
    finally:
        conn.close()


# ── Types d'événements ────────────────────────────────────────────────────────


def get_all_types_evenements(actif_only: bool = False) -> list[dict]:
    """Retourne tous les types d'événements, triés par ordre."""
    query = "SELECT id, nom, ordre, actif FROM types_evenements"
    if actif_only:
        query += " WHERE actif = 1"
    query += " ORDER BY ordre ASC, nom ASC"
    return _fetch_all(query)


def add_type_evenement(nom: str, ordre: int = 0) -> int:
    """Ajoute un type d'événement. Retourne l'id créé, ou 0 en cas d'erreur."""
    try:
        return _execute(
            "INSERT INTO types_evenements (nom, ordre) VALUES (?, ?)",
            (nom.strip(), ordre),
        )
    except Exception as exc:
        logger.error("add_type_evenement: %s", exc)
        return 0


def update_type_evenement(type_id: int, nom: str, ordre: int = 0) -> bool:
    """Met à jour le nom (et l'ordre optionnel) d'un type d'événement."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE types_evenements SET nom = ?, ordre = ? WHERE id = ?",
                (nom.strip(), ordre, type_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("update_type_evenement: %s", exc)
        return False


def toggle_type_evenement(type_id: int) -> bool:
    """Bascule l'état actif/inactif d'un type d'événement."""
    try:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE types_evenements SET actif = CASE WHEN actif = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (type_id,),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("toggle_type_evenement: %s", exc)
        return False


def delete_type_evenement(type_id: int) -> bool:
    """Supprime un type d'événement.

    Retourne True si suppression OK, False sinon.
    """
    try:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM types_evenements WHERE id = ?", (type_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception as exc:
        logger.error("delete_type_evenement: %s", exc)
        return False


# ── Modes de paiement ─────────────────────────────────────────────────────────


def get_all_modes_paiement(actif_only: bool = False) -> list[dict]:
    """Retourne tous les modes de paiement, triés par ordre."""
    query = "SELECT id, code, libelle, actif, est_systeme, ordre FROM modes_paiement"
    if actif_only:
        query += " WHERE actif = 1"
    query += " ORDER BY ordre ASC, libelle ASC"
    return _fetch_all(query)


def toggle_mode_paiement(mode_id: int) -> bool:
    """Bascule l'état actif/inactif d'un mode de paiement.

    Un mode système (``est_systeme = 1``) peut être désactivé uniquement
    s'il en reste au moins un autre actif.
    Retourne True si succès, False si bloqué ou en cas d'erreur.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT actif, est_systeme FROM modes_paiement WHERE id = ?",
            (mode_id,),
        ).fetchone()
        if not row:
            return False

        # Si on tente de désactiver le dernier mode actif, bloquer
        if row["actif"] == 1:
            nb_actifs = conn.execute(
                "SELECT COUNT(*) FROM modes_paiement WHERE actif = 1"
            ).fetchone()[0]
            if nb_actifs <= 1:
                logger.warning(
                    "toggle_mode_paiement: impossible de désactiver le dernier mode actif (%d)",
                    mode_id,
                )
                return False

        conn.execute(
            "UPDATE modes_paiement SET actif = CASE WHEN actif = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (mode_id,),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("toggle_mode_paiement: %s", exc)
        return False
    finally:
        conn.close()
