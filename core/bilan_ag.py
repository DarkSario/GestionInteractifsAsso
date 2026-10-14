"""Données du Bilan AG (template Markdown, Phase 16) et point d'entrée PDF unifié.

Le template est stocké dans config/bilan_ag_template.md et peut être
modifié librement sans toucher au code Python.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from utils.finance_rules import formater_montant_eur, sql_filtre_comptable
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Chemins des templates ─────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).parent.parent
_TEMPLATE_PATH = _BASE_DIR / "config" / "bilan_ag_template.md"
_TEMPLATE_DEFAULT_PATH = _BASE_DIR / "config" / "bilan_ag_template.default.md"

# ── Variables disponibles dans le template ────────────────────────────────────

VARIABLES_DISPONIBLES = [
    ("nom_asso", "Nom de l'association"),
    ("exercice", "Exercice (ex. 2025-2026)"),
    ("date_export", "Date d'export (format jj/mm/aaaa)"),
    ("nb_adherents", "Nombre d'adhérents actifs"),
    ("nb_benevoles", "Nombre de bénévoles mobilisés"),
    ("total_recettes", "Total des recettes de l'exercice"),
    ("total_depenses", "Total des dépenses de l'exercice"),
    ("solde", "Solde de l'exercice (recettes - dépenses)"),
    ("tableau_evenements", "Tableau récapitulatif des événements"),
    ("tableau_comptes", "Soldes par compte bancaire/caisse"),
    ("valeur_stock", "Valeur totale du stock actuel"),
    ("nb_mouvements_stock", "Nombre de mouvements de stock"),
    ("tableau_dons", "Tableau récapitulatif des dons de l'exercice"),
    ("total_dons", "Montant total des dons de l'exercice"),
    ("introduction", "Texte d'introduction (saisi avant export)"),
    ("conclusion", "Conclusion & perspectives (saisie avant export)"),
]


# ── Gestion du template ───────────────────────────────────────────────────────


def get_template_bilan() -> str:
    """Lit le template depuis config/bilan_ag_template.md.

    Si le fichier n'existe pas, retourne le template par défaut.
    """
    try:
        return _TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Template bilan_ag introuvable, utilisation du défaut.")
        return _TEMPLATE_DEFAULT_PATH.read_text(encoding="utf-8")
    except Exception as exc:
        logger.exception("get_template_bilan: %s", exc)
        return ""


def save_template_bilan(contenu: str) -> None:
    """Sauvegarde le template modifié dans config/bilan_ag_template.md."""
    try:
        _TEMPLATE_PATH.write_text(contenu, encoding="utf-8")
    except Exception as exc:
        logger.exception("save_template_bilan: %s", exc)
        raise


def reset_template_bilan() -> None:
    """Remet le template par défaut (copie bilan_ag_template.default.md)."""
    try:
        contenu_defaut = _TEMPLATE_DEFAULT_PATH.read_text(encoding="utf-8")
        _TEMPLATE_PATH.write_text(contenu_defaut, encoding="utf-8")
    except Exception as exc:
        logger.exception("reset_template_bilan: %s", exc)
        raise


# ── Collecte des données ──────────────────────────────────────────────────────


def _formater_montant(valeur: float) -> str:
    """Formate un montant (ASCII uniquement, compatible Helvetica)."""
    return formater_montant_eur(valeur, defaut="0,00 EUR")


def _construire_tableau_evenements(evenements: list[dict]) -> str:
    """Génère un tableau Markdown des événements."""
    if not evenements:
        return "_Aucun événement pour cet exercice._"

    lignes = [
        "| Événement | Date | Recettes | Dépenses | Solde |",
        "|---|---|---:|---:|---:|",
    ]
    for ev in evenements:
        recettes = float(ev.get("total_recettes") or 0)
        depenses = float(ev.get("total_depenses") or 0)
        solde = recettes - depenses
        lignes.append(
            f"| {ev.get('nom', '')} "
            f"| {ev.get('date_debut', '')[:10]} "
            f"| {_formater_montant(recettes)} "
            f"| {_formater_montant(depenses)} "
            f"| {_formater_montant(solde)} |"
        )
    return "\n".join(lignes)


def _construire_tableau_comptes(comptes: list[dict]) -> str:
    """Génère un tableau Markdown des soldes par compte."""
    if not comptes:
        return "_Aucun compte défini._"

    lignes = [
        "| Compte | Solde |",
        "|---|---:|",
    ]
    for c in comptes:
        lignes.append(
            f"| {c.get('nom', '')} | {_formater_montant(float(c.get('solde') or 0))} |"
        )
    return "\n".join(lignes)


def collecter_donnees_bilan(
    exercice_id: int,
    introduction: str = "",
    conclusion: str = "",
) -> dict:
    """Collecte toutes les données pour remplir le template du bilan AG.

    Returns:
        Dictionnaire de variables prêtes à être substituées dans le template.
    """
    donnees: dict = {
        "introduction": introduction or "_À compléter._",
        "conclusion": conclusion or "_À compléter._",
        "date_export": date.today().strftime("%d/%m/%Y"),
        "exercice": "",
        "nom_asso": "",
        "nb_adherents": "0",
        "nb_benevoles": "0",
        "total_recettes": "0,00 €",
        "total_depenses": "0,00 €",
        "solde": "0,00 €",
        "tableau_evenements": "_Aucun événement._",
        "tableau_comptes": "_Aucun compte._",
        "valeur_stock": "0,00 €",
        "nb_mouvements_stock": "0",
        "tableau_dons": "_Aucun don._",
        "total_dons": "0.00 €",
    }

    # Nom de l'association
    try:
        from db.models.parametres_globaux import get_parametre

        donnees["nom_asso"] = get_parametre("asso_nom", "Association")
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – nom_asso: %s", exc)

    # Exercice (bornes de période : les opérations et événements n'ont pas de colonne exercice_id)
    periode_debut, periode_fin = "", ""
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT nom, date_debut, date_fin FROM exercices WHERE id = ?",
                (exercice_id,),
            ).fetchone()
        finally:
            conn.close()
        if row:
            periode_debut, periode_fin = row["date_debut"] or "", row["date_fin"] or ""
            donnees["exercice"] = row["nom"] or (
                f"{(row['date_debut'] or '')[:4]}–{(row['date_fin'] or '')[:4]}"
            )
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – exercice: %s", exc)

    # Adhérents actifs
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            nb = conn.execute(
                "SELECT COUNT(*) FROM membres WHERE statut_archive = 0"
            ).fetchone()[0]
        finally:
            conn.close()
        donnees["nb_adherents"] = str(nb)
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – nb_adherents: %s", exc)

    # Bénévoles (tous les membres avec statut contenant "bénévole" ou liés à des événements)
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            nb_bev = conn.execute(
                """
                SELECT COUNT(DISTINCT membre_id)
                FROM evenements_benevoles
                """
            ).fetchone()[0]
        finally:
            conn.close()
        donnees["nb_benevoles"] = str(nb_bev)
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – nb_benevoles: %s", exc)

    # Bilan financier de l'exercice
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            row_fin = conn.execute(
                f"""
                SELECT
                    COALESCE(SUM(CASE WHEN type_operation = 'recette' THEN montant ELSE 0 END), 0) AS recettes,
                    COALESCE(SUM(CASE WHEN type_operation = 'depense' THEN montant ELSE 0 END), 0) AS depenses
                FROM tresorerie_operations
                WHERE date_operation BETWEEN ? AND ?
                  AND statut IN ('valide', 'rapproche')
                  AND {sql_filtre_comptable()}
                """,
                (periode_debut, periode_fin),
            ).fetchone()
        finally:
            conn.close()
        if row_fin:
            recettes = float(row_fin["recettes"])
            depenses = float(row_fin["depenses"])
            solde = recettes - depenses
            donnees["total_recettes"] = _formater_montant(recettes)
            donnees["total_depenses"] = _formater_montant(depenses)
            donnees["solde"] = _formater_montant(solde)
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – bilan_financier: %s", exc)

    # Événements de l'exercice
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            evenements = conn.execute(
                f"""
                SELECT e.nom, e.date_debut,
                    COALESCE(SUM(CASE WHEN o.type_operation = 'recette' THEN o.montant ELSE 0 END), 0) AS total_recettes,
                    COALESCE(SUM(CASE WHEN o.type_operation = 'depense' THEN o.montant ELSE 0 END), 0) AS total_depenses
                FROM evenements e
                LEFT JOIN tresorerie_operations o ON o.evenement_id = e.id
                    AND o.statut IN ('valide', 'rapproche')
                    AND {sql_filtre_comptable('o')}
                WHERE e.date_debut BETWEEN ? AND ?
                GROUP BY e.id, e.nom, e.date_debut
                ORDER BY e.date_debut
                """,
                (periode_debut, periode_fin),
            ).fetchall()
        finally:
            conn.close()
        donnees["tableau_evenements"] = _construire_tableau_evenements(
            [dict(e) for e in evenements]
        )
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – tableau_evenements: %s", exc)

    # Comptes (table courante : comptes_bancaires, soldes via le modèle trésorerie)
    try:
        from db.models.tresorerie import get_all_comptes

        comptes = [
            {"nom": c["nom"], "solde": c.get("solde_actuel") or 0}
            for c in get_all_comptes(actif_only=True, date_fin=periode_fin or None)
        ]
        donnees["tableau_comptes"] = _construire_tableau_comptes(comptes)
    except Exception as exc:
        logger.error("collecter_donnees_bilan – tableau_comptes: %s", exc)
        donnees["tableau_comptes"] = "_Soldes des comptes indisponibles (erreur de lecture)._"

    # Dons
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            dons = conn.execute(
                """
                SELECT date_don, donateur_nom, donateur_prenom, nature_don,
                       COALESCE(montant, valeur_estimee, 0) AS montant
                FROM dons
                WHERE exercice_id = ?
                ORDER BY date_don, id
                """,
                (exercice_id,),
            ).fetchall()
        finally:
            conn.close()

        if dons:
            lignes_dons = [
                "| Date | Donateur | Nature | Montant |",
                "|---|---|---|---:|",
            ]
            total_dons = 0.0
            for don in dons:
                montant = float(don["montant"] or 0)
                total_dons += montant
                donateur = f"{don['donateur_nom'] or ''} {don['donateur_prenom'] or ''}".strip()
                lignes_dons.append(
                    f"| {(don['date_don'] or '')[:10]} | {donateur} | {don['nature_don'] or ''} | {_formater_montant(montant)} |"
                )
            donnees["tableau_dons"] = "\n".join(lignes_dons)
            donnees["total_dons"] = _formater_montant(total_dons)
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – dons: %s", exc)

    # Stock
    try:
        from db.connection import get_connection

        conn = get_connection()
        try:
            val = conn.execute(
                "SELECT COALESCE(SUM(quantite_stock * prix_unitaire_ht), 0) FROM articles WHERE actif = 1"
            ).fetchone()[0]
            nb_mouvements = conn.execute(
                "SELECT COUNT(*) FROM mouvements_stock"
            ).fetchone()[0]
        finally:
            conn.close()
        donnees["valeur_stock"] = _formater_montant(float(val))
        donnees["nb_mouvements_stock"] = str(nb_mouvements)
    except Exception as exc:
        logger.warning("collecter_donnees_bilan – stock: %s", exc)

    return donnees


# ── Génération PDF ────────────────────────────────────────────────────────────


def _remplacer_variables(template: str, donnees: dict) -> str:
    """Remplace les {{variable}} dans le template par les données."""

    def remplacer(match: re.Match) -> str:
        cle = match.group(1).strip()
        return str(donnees.get(cle, f"{{{{ {cle} }}}}"))

    return re.sub(r"\{\{([^}]+)\}\}", remplacer, template)


def generer_bilan_ag(
    exercice_id: int,
    chemin_destination: str,
    introduction: str = "",
    conclusion: str = "",
) -> dict:
    """Génère le PDF du bilan AG via le générateur unique ``PdfBilanAG``.

    Chemin unifié avec l'export du menu Exports (``core.exports.export_bilan_ag_pdf``).
    Le rendu Markdown historique est abandonné : le modèle Markdown n'est plus
    utilisé que pour les variables de ``collecter_donnees_bilan``.

    Returns:
        {succes: bool, chemin: str, message: str}
    """
    try:
        from core.exports import export_bilan_ag_pdf
        from db.connection import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT nom, type_exercice, date_debut, date_fin FROM exercices WHERE id = ?",
                (exercice_id,),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return {"succes": False, "chemin": chemin_destination, "message": "Exercice introuvable."}

        debut, fin = row["date_debut"] or "", row["date_fin"] or ""
        nom = row["nom"] or f"{debut[:4]}-{fin[:4]}"
        ok = export_bilan_ag_pdf(
            nom,
            chemin_destination,
            type_periode=row["type_exercice"] or "scolaire",
            introduction=introduction,
            conclusion=conclusion,
            date_debut=debut or None,
            date_fin=fin or None,
        )
        return {
            "succes": bool(ok),
            "chemin": chemin_destination,
            "message": "Bilan AG généré avec succès." if ok else "Le bilan AG n'a pas pu être généré.",
        }
    except Exception as exc:
        logger.exception("generer_bilan_ag: %s", exc)
        return {"succes": False, "chemin": chemin_destination, "message": str(exc)}
