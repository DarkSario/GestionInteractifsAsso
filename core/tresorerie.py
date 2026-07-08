"""Logique métier pour le module Trésorerie."""

from __future__ import annotations

from db.models.tresorerie import (
    get_all_depenses_diverses,
    get_all_depenses_regulieres,
    get_all_depots_retraits,
    get_all_dons,
    get_all_retrocessions,
    get_config,
)

CATEGORIES_DEPENSE = [
    "Achats matériel",
    "Alimentation / boissons",
    "Assurance",
    "Communication / impression",
    "Déplacements",
    "Divers",
    "Frais bancaires",
    "Fournitures bureau",
    "Locations",
    "Prestataires",
    "Remboursements",
    "Salaires / honoraires",
    "Taxes / impôts",
]

TYPES_DON = [
    "don",
    "subvention",
    "autre",
]

MOYENS_PAIEMENT = [
    "espèces",
    "chèque",
    "carte",
    "virement",
    "autre",
]

STATUTS_REGLEMENT = [
    "non réglé",
    "réglé",
    "en attente",
]

TYPES_MOUVEMENT_BANQUE = [
    "dépôt",
    "retrait",
]


def valider_depense(
    date_depense: str,
    categorie: str,
    montant: str | float,
) -> list[str]:
    """Valide les champs d'une dépense. Retourne une liste d'erreurs."""
    erreurs: list[str] = []
    if not date_depense or not str(date_depense).strip():
        erreurs.append("La date est obligatoire.")
    if not categorie or not str(categorie).strip():
        erreurs.append("La catégorie est obligatoire.")
    try:
        val = float(str(montant).replace(",", "."))
        if val <= 0:
            erreurs.append("Le montant doit être supérieur à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le montant doit être un nombre valide.")
    return erreurs


def valider_don(
    date: str,
    source: str,
    montant: str | float,
) -> list[str]:
    """Valide les champs d'un don/subvention. Retourne une liste d'erreurs."""
    erreurs: list[str] = []
    if not date or not str(date).strip():
        erreurs.append("La date est obligatoire.")
    if not source or not str(source).strip():
        erreurs.append("La source est obligatoire.")
    try:
        val = float(str(montant).replace(",", "."))
        if val <= 0:
            erreurs.append("Le montant doit être supérieur à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le montant doit être un nombre valide.")
    return erreurs


def valider_mouvement_banque(
    date: str,
    type_mouvement: str,
    montant: str | float,
) -> list[str]:
    """Valide un mouvement bancaire. Retourne une liste d'erreurs."""
    erreurs: list[str] = []
    if not date or not str(date).strip():
        erreurs.append("La date est obligatoire.")
    if type_mouvement not in TYPES_MOUVEMENT_BANQUE:
        erreurs.append("Le type de mouvement est invalide (dépôt ou retrait).")
    try:
        val = float(str(montant).replace(",", "."))
        if val <= 0:
            erreurs.append("Le montant doit être supérieur à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le montant doit être un nombre valide.")
    return erreurs


def valider_retrocession(
    date: str,
    ecole: str,
    montant: str | float,
) -> list[str]:
    """Valide une rétrocession. Retourne une liste d'erreurs."""
    erreurs: list[str] = []
    if not date or not str(date).strip():
        erreurs.append("La date est obligatoire.")
    if not ecole or not str(ecole).strip():
        erreurs.append("Le nom de l'école est obligatoire.")
    try:
        val = float(str(montant).replace(",", "."))
        if val <= 0:
            erreurs.append("Le montant doit être supérieur à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le montant doit être un nombre valide.")
    return erreurs


def _to_float(value) -> float:
    """Convertit une valeur en float, retourne 0.0 en cas d'erreur."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def calculer_bilan(exercice: str | None = None) -> dict:
    """Calcule le bilan complet de trésorerie pour l'exercice donné.

    Retourne un dictionnaire avec :
    - solde_ouverture, total_recettes, total_depenses,
      total_depots, total_retraits, total_retrocessions,
      solde_theorique, solde_banque.
    """
    config = get_config()
    solde_ouverture = _to_float(config.get("solde_ouverture"))
    disponible_banque = _to_float(config.get("disponible_banque"))

    dons = get_all_dons(exercice)
    total_dons = round(sum(_to_float(d.get("montant")) for d in dons), 2)

    dep_reg = get_all_depenses_regulieres(exercice)
    total_dep_reg = round(sum(_to_float(d.get("montant")) for d in dep_reg), 2)

    dep_div = get_all_depenses_diverses(exercice)
    total_dep_div = round(sum(_to_float(d.get("montant")) for d in dep_div), 2)

    depots_retraits = get_all_depots_retraits(exercice)
    total_depots = round(
        sum(
            _to_float(m.get("montant"))
            for m in depots_retraits
            if m.get("type") == "dépôt"
        ),
        2,
    )
    total_retraits = round(
        sum(
            _to_float(m.get("montant"))
            for m in depots_retraits
            if m.get("type") == "retrait"
        ),
        2,
    )

    retrocessions = get_all_retrocessions(exercice)
    total_retrocessions = round(
        sum(_to_float(r.get("montant")) for r in retrocessions), 2
    )

    total_recettes = round(total_dons, 2)
    total_depenses = round(total_dep_reg + total_dep_div + total_retrocessions, 2)

    solde_theorique = round(
        solde_ouverture + total_recettes - total_depenses, 2
    )
    solde_banque = round(
        disponible_banque + total_depots - total_retraits, 2
    )

    return {
        "solde_ouverture": solde_ouverture,
        "total_dons": total_dons,
        "total_depenses_regulieres": total_dep_reg,
        "total_depenses_diverses": total_dep_div,
        "total_retrocessions": total_retrocessions,
        "total_recettes": total_recettes,
        "total_depenses": total_depenses,
        "total_depots": total_depots,
        "total_retraits": total_retraits,
        "solde_theorique": solde_theorique,
        "solde_banque": solde_banque,
    }
