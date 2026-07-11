"""CRUD pour les tableaux personnalisés d'événements."""

from __future__ import annotations

import json

from db.connection import get_connection
from db.models.evenements import get_parametre
from db.models.fournisseurs import get_all_fournisseurs
from db.models.membres import get_all_membres
from utils.logger import get_logger

logger = get_logger(__name__)

_VALID_COLUMN_TYPES = {
    "texte",
    "nombre",
    "montant",
    "date",
    "checkbox",
    "liste_paiement",
    "liste_classes",
    "liste_membres",
    "liste_fournisseurs",
    "liste_statut",
    "liste_perso",
}


def _normaliser_type_colonne(type_colonne: str | None) -> str:
    brut = str(type_colonne or "texte").strip().lower()
    return brut if brut in _VALID_COLUMN_TYPES else "texte"


# ── Tableaux ─────────────────────────────────────────────────────────────────


def get_tableaux_evenement(evenement_id: int) -> list[dict]:
    """Retourne les tableaux personnalisés d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT t.id, t.evenement_id, t.nom, t.description, t.ordre, t.created_at,
                   (SELECT COUNT(*) FROM tableaux_lignes l WHERE l.tableau_id = t.id) AS nb_lignes
            FROM tableaux_perso t
            WHERE t.evenement_id = ?
            ORDER BY t.ordre ASC, t.id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_tableau(evenement_id, nom, description, ordre) -> int:
    """Crée un tableau personnalisé et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tableaux_perso (evenement_id, nom, description, ordre)
            VALUES (?, ?, ?, ?)
            """,
            (evenement_id, nom, description, ordre or 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_tableau(tableau_id, nom, description) -> bool:
    """Met à jour le nom/description d'un tableau."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE tableaux_perso SET nom = ?, description = ? WHERE id = ?",
            (nom, description, tableau_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("update_tableau: %s", exc)
        return False
    finally:
        conn.close()


def delete_tableau(tableau_id: int) -> bool:
    """Supprime un tableau et toutes ses données."""
    conn = get_connection()
    try:
        conn.execute(
            """
            DELETE FROM tableaux_cellules
            WHERE ligne_id IN (
                SELECT id FROM tableaux_lignes WHERE tableau_id = ?
            )
            """,
            (tableau_id,),
        )
        conn.execute("DELETE FROM tableaux_lignes WHERE tableau_id = ?", (tableau_id,))
        conn.execute(
            "DELETE FROM tableaux_colonnes WHERE tableau_id = ?", (tableau_id,)
        )
        cur = conn.execute("DELETE FROM tableaux_perso WHERE id = ?", (tableau_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_tableau: %s", exc)
        return False
    finally:
        conn.close()


def dupliquer_tableau(tableau_id: int, nouvel_evenement_id: int) -> int:
    """Duplique la structure d'un tableau (sans lignes/cellules)."""
    conn = get_connection()
    try:
        tableau = conn.execute(
            "SELECT nom, description, ordre FROM tableaux_perso WHERE id = ?",
            (tableau_id,),
        ).fetchone()
        if not tableau:
            return 0

        cur = conn.execute(
            """
            INSERT INTO tableaux_perso (evenement_id, nom, description, ordre)
            VALUES (?, ?, ?, ?)
            """,
            (
                nouvel_evenement_id,
                f"{tableau['nom']} (copie)",
                tableau["description"],
                tableau["ordre"],
            ),
        )
        nouveau_id = cur.lastrowid

        colonnes = conn.execute(
            """
            SELECT nom, type_colonne, liste_perso_valeurs, afficher_total, ordre, largeur
            FROM tableaux_colonnes
            WHERE tableau_id = ?
            ORDER BY ordre ASC, id ASC
            """,
            (tableau_id,),
        ).fetchall()

        for col in colonnes:
            conn.execute(
                """
                INSERT INTO tableaux_colonnes
                    (tableau_id, nom, type_colonne, liste_perso_valeurs, afficher_total, ordre, largeur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nouveau_id,
                    col["nom"],
                    col["type_colonne"],
                    col["liste_perso_valeurs"],
                    col["afficher_total"],
                    col["ordre"],
                    col["largeur"],
                ),
            )

        conn.commit()
        return nouveau_id
    finally:
        conn.close()


# ── Colonnes ─────────────────────────────────────────────────────────────────


def get_colonnes_tableau(tableau_id: int) -> list[dict]:
    """Retourne les colonnes d'un tableau."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, tableau_id, nom, type_colonne, liste_perso_valeurs,
                   afficher_total, ordre, largeur
            FROM tableaux_colonnes
            WHERE tableau_id = ?
            ORDER BY ordre ASC, id ASC
            """,
            (tableau_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_colonne(
    tableau_id,
    nom,
    type_colonne,
    liste_perso_valeurs,
    afficher_total,
    ordre,
    largeur,
) -> int:
    """Ajoute une colonne à un tableau."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tableaux_colonnes
                (tableau_id, nom, type_colonne, liste_perso_valeurs, afficher_total, ordre, largeur)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tableau_id,
                nom,
                _normaliser_type_colonne(type_colonne),
                liste_perso_valeurs,
                1 if afficher_total else 0,
                ordre or 0,
                largeur or 150,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_TABLEAU_COLONNE = frozenset(
    {
        "nom",
        "type_colonne",
        "liste_perso_valeurs",
        "afficher_total",
        "ordre",
        "largeur",
    }
)
_UPDATE_COLONNE_SQL = {
    col: f"UPDATE tableaux_colonnes SET {col} = ? WHERE id = ?"
    for col in _COLONNES_TABLEAU_COLONNE
}


def update_colonne(colonne_id, **kwargs) -> bool:
    """Met à jour une colonne."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_TABLEAU_COLONNE
    if champs_invalides:
        logger.error("update_colonne: colonnes non autorisées : %s", champs_invalides)
        return False
    conn = get_connection()
    try:
        total_changes = 0
        for key, value in kwargs.items():
            if key == "type_colonne":
                value = _normaliser_type_colonne(str(value))
            cur = conn.execute(_UPDATE_COLONNE_SQL[key], (value, colonne_id))
            total_changes += cur.rowcount
        conn.commit()
        return total_changes > 0
    except Exception as exc:
        logger.error("update_colonne: %s", exc)
        return False
    finally:
        conn.close()


def delete_colonne(colonne_id: int) -> bool:
    """Supprime une colonne et ses cellules."""
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM tableaux_cellules WHERE colonne_id = ?", (colonne_id,)
        )
        cur = conn.execute("DELETE FROM tableaux_colonnes WHERE id = ?", (colonne_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_colonne: %s", exc)
        return False
    finally:
        conn.close()


def reordonner_colonnes(tableau_id: int, ordre_ids: list[int]) -> bool:
    """Réordonne les colonnes d'un tableau."""
    if not ordre_ids:
        return False
    conn = get_connection()
    try:
        for idx, col_id in enumerate(ordre_ids):
            conn.execute(
                "UPDATE tableaux_colonnes SET ordre = ? WHERE id = ? AND tableau_id = ?",
                (idx, col_id, tableau_id),
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("reordonner_colonnes: %s", exc)
        return False
    finally:
        conn.close()


# ── Lignes ───────────────────────────────────────────────────────────────────


def get_lignes_tableau(tableau_id: int) -> list[dict]:
    """Retourne les lignes d'un tableau avec toutes leurs cellules."""
    conn = get_connection()
    try:
        lignes = conn.execute(
            """
            SELECT id, tableau_id, membre_id, statut_ligne, ordre, created_at
            FROM tableaux_lignes
            WHERE tableau_id = ?
            ORDER BY ordre ASC, id ASC
            """,
            (tableau_id,),
        ).fetchall()
        resultat: list[dict] = []
        for ligne_row in lignes:
            ligne = dict(ligne_row)
            cellules = conn.execute(
                """
                SELECT colonne_id, valeur
                FROM tableaux_cellules
                WHERE ligne_id = ?
                """,
                (ligne["id"],),
            ).fetchall()
            ligne["cellules"] = {str(c["colonne_id"]): c["valeur"] for c in cellules}
            resultat.append(ligne)
        return resultat
    finally:
        conn.close()


def add_ligne(tableau_id, membre_id, statut_ligne, ordre) -> int:
    """Ajoute une ligne à un tableau."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tableaux_lignes (tableau_id, membre_id, statut_ligne, ordre)
            VALUES (?, ?, ?, ?)
            """,
            (tableau_id, membre_id, statut_ligne or "normal", ordre or 0),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_ligne_statut(ligne_id: int, statut: str) -> bool:
    """Met à jour le statut d'une ligne."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE tableaux_lignes SET statut_ligne = ? WHERE id = ?",
            (statut, ligne_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("update_ligne_statut: %s", exc)
        return False
    finally:
        conn.close()


def update_ligne(
    ligne_id: int,
    valeurs: dict[int, str] | None = None,
    statut_ligne: str | None = None,
) -> bool:
    """Met à jour une ligne complète et ses cellules."""
    conn = get_connection()
    try:
        exists = conn.execute(
            "SELECT id FROM tableaux_lignes WHERE id = ?",
            (ligne_id,),
        ).fetchone()
        if not exists:
            return False
        if statut_ligne is not None:
            conn.execute(
                "UPDATE tableaux_lignes SET statut_ligne = ? WHERE id = ?",
                (statut_ligne, ligne_id),
            )
        for colonne_id, valeur in (valeurs or {}).items():
            existing = conn.execute(
                "SELECT id FROM tableaux_cellules WHERE ligne_id = ? AND colonne_id = ?",
                (ligne_id, colonne_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE tableaux_cellules SET valeur = ? WHERE id = ?",
                    (valeur, existing["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tableaux_cellules (ligne_id, colonne_id, valeur)
                    VALUES (?, ?, ?)
                    """,
                    (ligne_id, colonne_id, valeur),
                )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("update_ligne: %s", exc)
        return False
    finally:
        conn.close()


def delete_ligne(ligne_id: int) -> bool:
    """Supprime une ligne et ses cellules."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM tableaux_cellules WHERE ligne_id = ?", (ligne_id,))
        cur = conn.execute("DELETE FROM tableaux_lignes WHERE id = ?", (ligne_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_ligne: %s", exc)
        return False
    finally:
        conn.close()


# ── Cellules ─────────────────────────────────────────────────────────────────


def set_cellule(ligne_id: int, colonne_id: int, valeur: str) -> bool:
    """Crée ou met à jour une cellule."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM tableaux_cellules WHERE ligne_id = ? AND colonne_id = ?",
            (ligne_id, colonne_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE tableaux_cellules SET valeur = ? WHERE id = ?",
                (valeur, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO tableaux_cellules (ligne_id, colonne_id, valeur) VALUES (?, ?, ?)",
                (ligne_id, colonne_id, valeur),
            )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("set_cellule: %s", exc)
        return False
    finally:
        conn.close()


def get_cellules_ligne(ligne_id: int) -> dict:
    """Retourne les cellules d'une ligne sous forme {colonne_id: valeur}."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT colonne_id, valeur FROM tableaux_cellules WHERE ligne_id = ?",
            (ligne_id,),
        ).fetchall()
        return {int(r["colonne_id"]): r["valeur"] for r in rows}
    finally:
        conn.close()


# ── Totaux ───────────────────────────────────────────────────────────────────


def calculer_totaux(tableau_id: int) -> dict:
    """Retourne les totaux automatiques par colonne de type nombre/montant."""
    from core.tableaux import calculer_total_colonne

    colonnes = [
        c
        for c in get_colonnes_tableau(tableau_id)
        if c.get("afficher_total") and c.get("type_colonne") in {"nombre", "montant"}
    ]
    lignes = get_lignes_tableau(tableau_id)
    totaux: dict[int, float] = {}
    for col in colonnes:
        total = calculer_total_colonne(lignes, int(col["id"]), str(col["type_colonne"]))
        if total is not None:
            totaux[int(col["id"])] = total
    return totaux


# ── Templates ────────────────────────────────────────────────────────────────


def get_all_templates() -> list[dict]:
    """Retourne tous les templates de tableaux."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, nom, description, colonnes_json, created_at
            FROM tableaux_templates
            ORDER BY nom ASC, id DESC
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_template(nom, description, tableau_id) -> int:
    """Sauvegarde la structure d'un tableau comme template."""
    from core.tableaux import colonnes_to_json

    colonnes = get_colonnes_tableau(tableau_id)
    colonnes_json = colonnes_to_json(colonnes)

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO tableaux_templates (nom, description, colonnes_json)
            VALUES (?, ?, ?)
            """,
            (nom, description, colonnes_json),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def apply_template(template_id: int, evenement_id: int) -> int:
    """Crée un nouveau tableau depuis un template."""
    from core.tableaux import json_to_colonnes

    conn = get_connection()
    try:
        template = conn.execute(
            "SELECT nom, description, colonnes_json FROM tableaux_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        if not template:
            return 0

        cur = conn.execute(
            "INSERT INTO tableaux_perso (evenement_id, nom, description, ordre) VALUES (?, ?, ?, 0)",
            (evenement_id, template["nom"], template["description"]),
        )
        tableau_id = cur.lastrowid

        colonnes = json_to_colonnes(template["colonnes_json"])
        for idx, col in enumerate(colonnes):
            conn.execute(
                """
                INSERT INTO tableaux_colonnes
                    (tableau_id, nom, type_colonne, liste_perso_valeurs, afficher_total, ordre, largeur)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tableau_id,
                    col.get("nom"),
                    col.get("type_colonne", "texte"),
                    col.get("liste_perso_valeurs"),
                    1 if col.get("afficher_total") else 0,
                    int(col.get("ordre", idx)),
                    int(col.get("largeur", 150)),
                ),
            )

        conn.commit()
        return tableau_id
    finally:
        conn.close()


def delete_template(template_id: int) -> bool:
    """Supprime un template."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM tableaux_templates WHERE id = ?", (template_id,)
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        logger.error("delete_template: %s", exc)
        return False
    finally:
        conn.close()


# ── Listes configurables ─────────────────────────────────────────────────────


def _json_param_to_list(cle: str, fallback: list[str]) -> list[str]:
    valeur = get_parametre(cle)
    if not valeur:
        return fallback
    try:
        data = json.loads(valeur)
    except json.JSONDecodeError:
        return fallback
    if not isinstance(data, list):
        return fallback
    return [str(v) for v in data if str(v).strip()]


def get_liste_classes() -> list[str]:
    """Retourne la liste des classes scolaires."""
    return _json_param_to_list(
        "classes_scolaires",
        ["PS", "MS", "GS", "CP", "CE1", "CE2", "CM1", "CM2"],
    )


def get_liste_statuts_perso() -> list[str]:
    """Retourne la liste des statuts personnalisés."""
    return _json_param_to_list(
        "statuts_perso",
        ["En attente", "Confirmé", "Payé", "Annulé"],
    )


def get_liste_paiements() -> list[str]:
    """Retourne les modes de paiement disponibles pour les listes."""
    return ["Espèces", "Carte", "Chèque", "SumUp", "Virement"]


def get_liste_membres() -> list[str]:
    """Retourne une liste de membres formatée pour les colonnes liées."""
    membres = get_all_membres()
    return [f"{m.get('prenom', '')} {m.get('nom', '')}".strip() for m in membres]


def get_liste_fournisseurs() -> list[str]:
    """Retourne une liste de fournisseurs formatée."""
    fournisseurs = get_all_fournisseurs()
    return [str(f.get("nom") or "") for f in fournisseurs]
