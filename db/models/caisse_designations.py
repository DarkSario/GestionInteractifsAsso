"""CRUD des désignations réutilisables pour les caisses."""

from __future__ import annotations

from db.connection import get_connection

DESIGNATIONS_CAISSE_PAR_DEFAUT = (
    {
        "nom": "Pièces 1€",
        "montant_unitaire": 1.0,
        "description": "",
        "ordre": 10,
        "actif": 1,
    },
    {
        "nom": "Pièces 2€",
        "montant_unitaire": 2.0,
        "description": "",
        "ordre": 20,
        "actif": 1,
    },
    {
        "nom": "Billets 5€",
        "montant_unitaire": 5.0,
        "description": "",
        "ordre": 30,
        "actif": 1,
    },
    {
        "nom": "Billets 10€",
        "montant_unitaire": 10.0,
        "description": "",
        "ordre": 40,
        "actif": 1,
    },
    {
        "nom": "Billets 20€",
        "montant_unitaire": 20.0,
        "description": "",
        "ordre": 50,
        "actif": 1,
    },
    {
        "nom": "Billets 50€",
        "montant_unitaire": 50.0,
        "description": "",
        "ordre": 60,
        "actif": 1,
    },
    {
        "nom": "Billets 100€",
        "montant_unitaire": 100.0,
        "description": "",
        "ordre": 70,
        "actif": 1,
    },
    {
        "nom": "Chèques",
        "montant_unitaire": 0.0,
        "description": "À remplir",
        "ordre": 80,
        "actif": 1,
    },
    {
        "nom": "SumUp/CB",
        "montant_unitaire": 0.0,
        "description": "À remplir",
        "ordre": 90,
        "actif": 1,
    },
    {
        "nom": "Tickets resto",
        "montant_unitaire": 0.0,
        "description": "À remplir",
        "ordre": 100,
        "actif": 1,
    },
    {
        "nom": "Bons d'achat",
        "montant_unitaire": 0.0,
        "description": "À remplir",
        "ordre": 110,
        "actif": 1,
    },
    {
        "nom": "Autre",
        "montant_unitaire": 0.0,
        "description": "À remplir",
        "ordre": 120,
        "actif": 1,
    },
)


def _nettoyer_nom(nom: str) -> str:
    valeur = str(nom or "").strip()
    if not valeur:
        raise ValueError("Le nom de la désignation est obligatoire.")
    return valeur


def lister_designations_caisse(actif_only: bool = False) -> list[dict]:
    """Liste les désignations triées par ordre puis nom."""
    conn = get_connection()
    try:
        where = "WHERE actif = 1" if actif_only else ""
        rows = conn.execute(f"""
            SELECT id, nom, montant_unitaire, description, ordre, actif, created_at, updated_at
            FROM caisse_designations
            {where}
            ORDER BY ordre ASC, nom COLLATE NOCASE ASC, id ASC
            """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_designation_caisse(designation_id: int) -> dict | None:
    """Retourne une désignation par identifiant."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nom, montant_unitaire, description, ordre, actif, created_at, updated_at
            FROM caisse_designations
            WHERE id = ?
            """,
            (int(designation_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def creer_designation_caisse(
    nom: str,
    montant_unitaire: float,
    description: str | None = None,
    ordre: int = 0,
    actif: bool = True,
) -> int:
    """Crée une désignation réutilisable."""
    nom_val = _nettoyer_nom(nom)
    montant_val = round(float(montant_unitaire or 0), 2)
    if montant_val < 0:
        raise ValueError("Le montant unitaire doit être positif ou nul.")
    ordre_val = int(ordre or 0)
    actif_val = 1 if actif else 0

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO caisse_designations (
                nom, montant_unitaire, description, ordre, actif, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (nom_val, montant_val, (description or "").strip(), ordre_val, actif_val),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def mettre_a_jour_designation_caisse(
    designation_id: int,
    nom: str,
    montant_unitaire: float,
    description: str | None = None,
    ordre: int = 0,
    actif: bool = True,
) -> bool:
    """Met à jour une désignation."""
    nom_val = _nettoyer_nom(nom)
    montant_val = round(float(montant_unitaire or 0), 2)
    if montant_val < 0:
        raise ValueError("Le montant unitaire doit être positif ou nul.")
    ordre_val = int(ordre or 0)
    actif_val = 1 if actif else 0

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE caisse_designations
            SET nom = ?, montant_unitaire = ?, description = ?, ordre = ?, actif = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                nom_val,
                montant_val,
                (description or "").strip(),
                ordre_val,
                actif_val,
                int(designation_id),
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def supprimer_designation_caisse(designation_id: int) -> bool:
    """Supprime une désignation tout en conservant la traçabilité des lignes."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE evenement_caisse_lignes SET designation_id = NULL WHERE designation_id = ?",
            (int(designation_id),),
        )
        cur = conn.execute(
            "DELETE FROM caisse_designations WHERE id = ?", (int(designation_id),)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def definir_activation_designation_caisse(designation_id: int, actif: bool) -> bool:
    """Active ou désactive une désignation."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            UPDATE caisse_designations
            SET actif = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (1 if actif else 0, int(designation_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def reinitialiser_designations_caisses() -> int:
    """Réinitialise les désignations standards."""
    conn = get_connection()
    try:
        for designation in DESIGNATIONS_CAISSE_PAR_DEFAUT:
            conn.execute(
                """
                INSERT INTO caisse_designations (
                    nom, montant_unitaire, description, ordre, actif, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(nom) DO UPDATE SET
                    montant_unitaire = excluded.montant_unitaire,
                    description = excluded.description,
                    ordre = excluded.ordre,
                    actif = excluded.actif,
                    updated_at = datetime('now')
                """,
                (
                    designation["nom"],
                    designation["montant_unitaire"],
                    designation["description"],
                    designation["ordre"],
                    designation["actif"],
                ),
            )
        conn.commit()
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM caisse_designations"
        ).fetchone()
        return int(row["total"] if row else 0)
    finally:
        conn.close()
