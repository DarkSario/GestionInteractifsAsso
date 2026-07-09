"""Gestion des polices PDF personnalisées."""

from __future__ import annotations

from pathlib import Path

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

_POLICES_SYSTEME = [
    {"id": 0, "nom": "Helvetica", "fichier": "Système", "chemin": "", "actif": 1, "est_systeme": 1},
    {"id": -1, "nom": "Times-Roman", "fichier": "Système", "chemin": "", "actif": 1, "est_systeme": 1},
    {"id": -2, "nom": "Courier", "fichier": "Système", "chemin": "", "actif": 1, "est_systeme": 1},
]


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS polices_pdf (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL UNIQUE,
                fichier_ttf TEXT NOT NULL,
                fichier_ttf_bold TEXT,
                fichier_ttf_italic TEXT,
                est_systeme INTEGER DEFAULT 0,
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _normaliser(row: dict) -> dict:
    chemin = row.get("fichier_ttf") or ""
    return {
        "id": row.get("id"),
        "nom": row.get("nom") or "",
        "fichier": Path(chemin).name if chemin else "",
        "chemin": chemin,
        "fichier_ttf": chemin,
        "fichier_ttf_bold": row.get("fichier_ttf_bold") or "",
        "fichier_ttf_italic": row.get("fichier_ttf_italic") or "",
        "actif": row.get("actif", 1),
        "est_systeme": row.get("est_systeme", 0),
    }


def get_all_polices(actif_only: bool = True) -> list[dict]:
    """Retourne les polices système et personnalisées."""
    _ensure_table()
    conn = get_connection()
    try:
        query = "SELECT id, nom, fichier_ttf, fichier_ttf_bold, fichier_ttf_italic, est_systeme, actif FROM polices_pdf"
        if actif_only:
            query += " WHERE actif = 1"
        query += " ORDER BY lower(nom) ASC"
        rows = [_normaliser(dict(row)) for row in conn.execute(query).fetchall()]
        return list(_POLICES_SYSTEME) + rows
    finally:
        conn.close()


def add_police(nom: str, fichier: str, chemin: str) -> int:
    """Ajoute une police personnalisée."""
    _ensure_table()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO polices_pdf (nom, fichier_ttf, est_systeme, actif)
            VALUES (?, ?, 0, 1)
            """,
            (nom.strip(), chemin.strip() or fichier.strip()),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)
    except Exception as exc:
        logger.error("add_police: %s", exc)
        return 0
    finally:
        conn.close()


def delete_police(police_id: int) -> bool:
    """Supprime une police personnalisée."""
    _ensure_table()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM polices_pdf WHERE id = ? AND est_systeme = 0",
            (police_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as exc:
        logger.error("delete_police: %s", exc)
        return False
    finally:
        conn.close()


def get_police_by_id(police_id: int) -> dict | None:
    """Retourne une police personnalisée par identifiant."""
    _ensure_table()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, nom, fichier_ttf, fichier_ttf_bold, fichier_ttf_italic, est_systeme, actif FROM polices_pdf WHERE id = ?",
            (police_id,),
        ).fetchone()
        return _normaliser(dict(row)) if row else None
    finally:
        conn.close()


def get_police_by_nom(nom: str) -> dict | None:
    """Retourne une police par son nom d'affichage."""
    _ensure_table()
    if not nom:
        return None
    for police in _POLICES_SYSTEME:
        if police["nom"] == nom:
            return dict(police)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, nom, fichier_ttf, fichier_ttf_bold, fichier_ttf_italic, est_systeme, actif FROM polices_pdf WHERE nom = ?",
            (nom,),
        ).fetchone()
        return _normaliser(dict(row)) if row else None
    finally:
        conn.close()
