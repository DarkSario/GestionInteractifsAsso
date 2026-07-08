"""Logique métier pour les tableaux personnalisés."""

from __future__ import annotations

import json

from db.models.tableaux import (
    get_liste_classes,
    get_liste_fournisseurs,
    get_liste_membres,
    get_liste_paiements,
    get_liste_statuts_perso,
)

_TYPES_COLONNES = {
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


def valider_colonne(nom, type_colonne) -> list[str]:
    """Valide les champs de définition d'une colonne."""
    erreurs: list[str] = []
    if not nom or not str(nom).strip():
        erreurs.append("Le nom de la colonne est obligatoire.")
    if type_colonne not in _TYPES_COLONNES:
        erreurs.append("Le type de colonne est invalide.")
    return erreurs


def get_valeurs_liste(type_colonne: str, liste_perso_valeurs: str) -> list[str]:
    """Retourne les valeurs possibles pour un type de colonne liste."""
    if type_colonne == "liste_paiement":
        return get_liste_paiements()
    if type_colonne == "liste_classes":
        return get_liste_classes()
    if type_colonne == "liste_membres":
        return [v for v in get_liste_membres() if v]
    if type_colonne == "liste_fournisseurs":
        return [v for v in get_liste_fournisseurs() if v]
    if type_colonne == "liste_statut":
        return get_liste_statuts_perso()
    if type_colonne == "liste_perso":
        brut = (liste_perso_valeurs or "").strip()
        if not brut:
            return []
        try:
            data = json.loads(brut)
            if isinstance(data, list):
                return [str(v).strip() for v in data if str(v).strip()]
        except json.JSONDecodeError:
            pass
        return [v.strip() for v in brut.split(";") if v.strip()]
    return []


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    txt = str(value).strip()
    if not txt:
        return None
    txt = txt.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def calculer_total_colonne(
    lignes: list[dict],
    colonne_id: int,
    type_colonne: str,
) -> float | None:
    """Calcule le total d'une colonne nombre/montant."""
    if type_colonne not in {"nombre", "montant"}:
        return None

    total = 0.0
    has_value = False
    key = str(colonne_id)

    for ligne in lignes:
        cellules = ligne.get("cellules") or {}
        raw = cellules.get(key)
        valeur = _to_float(raw)
        if valeur is None:
            continue
        total += valeur
        has_value = True

    if not has_value:
        return 0.0
    return round(total, 2)


def colonnes_to_json(colonnes: list[dict]) -> str:
    """Sérialise une liste de colonnes pour stockage de template."""
    payload = []
    for col in colonnes:
        payload.append(
            {
                "nom": col.get("nom"),
                "type_colonne": col.get("type_colonne", "texte"),
                "liste_perso_valeurs": col.get("liste_perso_valeurs"),
                "afficher_total": 1 if col.get("afficher_total") else 0,
                "ordre": int(col.get("ordre") or 0),
                "largeur": int(col.get("largeur") or 150),
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def json_to_colonnes(json_str: str) -> list[dict]:
    """Désérialise des colonnes depuis un JSON de template."""
    try:
        data = json.loads(json_str or "[]")
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    colonnes: list[dict] = []
    for idx, col in enumerate(data):
        if not isinstance(col, dict):
            continue
        colonnes.append(
            {
                "nom": str(col.get("nom") or "").strip(),
                "type_colonne": col.get("type_colonne") or "texte",
                "liste_perso_valeurs": col.get("liste_perso_valeurs"),
                "afficher_total": 1 if col.get("afficher_total") else 0,
                "ordre": int(col.get("ordre", idx) or idx),
                "largeur": int(col.get("largeur", 150) or 150),
            }
        )
    return colonnes
