"""Logique métier du module Trésorerie (Phase 6a)."""

from __future__ import annotations

from datetime import datetime

from db.models.tresorerie import get_all_categories

MIN_VALID_YEAR = 2000
MAX_VALID_YEAR_OFFSET = 50


def to_float(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _date_valide(value: str | None) -> bool:
    if not value or not str(value).strip():
        return False
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def valider_operation(libelle, montant, date_operation, type_operation) -> list[str]:
    erreurs: list[str] = []

    if not libelle or not str(libelle).strip():
        erreurs.append("Le libellé est obligatoire.")

    montant_float = to_float(montant)
    if montant_float is None:
        erreurs.append("Le montant doit être un nombre valide.")
    elif montant_float <= 0:
        erreurs.append("Le montant doit être supérieur à 0.")

    if not _date_valide(str(date_operation)):
        erreurs.append("La date d'opération est invalide (format attendu : YYYY-MM-DD).")

    if type_operation not in {"recette", "depense", "virement_interne"}:
        erreurs.append("Le type d'opération est invalide.")

    return erreurs


def valider_compte(nom, solde_initial) -> list[str]:
    erreurs: list[str] = []

    if not nom or not str(nom).strip():
        erreurs.append("Le nom du compte est obligatoire.")

    if to_float(solde_initial) is None:
        erreurs.append("Le solde initial doit être un nombre valide.")

    return erreurs


def valider_subvention(organisme, annee, montant_demande) -> list[str]:
    erreurs: list[str] = []

    if not organisme or not str(organisme).strip():
        erreurs.append("L'organisme est obligatoire.")

    try:
        annee_int = int(annee)
        max_valid_year = datetime.now().year + MAX_VALID_YEAR_OFFSET
        if annee_int < MIN_VALID_YEAR or annee_int > max_valid_year:
            erreurs.append("L'année est invalide.")
    except (TypeError, ValueError):
        erreurs.append("L'année est invalide.")

    montant = to_float(montant_demande)
    if montant is None:
        erreurs.append("Le montant demandé doit être un nombre valide.")
    elif montant < 0:
        erreurs.append("Le montant demandé ne peut pas être négatif.")

    return erreurs


def valider_remise_cheque(cheques: list[dict]) -> list[str]:
    erreurs: list[str] = []

    if not cheques:
        return ["La remise doit contenir au moins un chèque."]

    for idx, cheque in enumerate(cheques, start=1):
        nom_tireur = cheque.get("nom_tireur")
        montant = to_float(cheque.get("montant"))
        if not nom_tireur or not str(nom_tireur).strip():
            erreurs.append(f"Chèque {idx} : le nom du tireur est obligatoire.")
        if montant is None or montant <= 0:
            erreurs.append(f"Chèque {idx} : le montant doit être supérieur à 0.")

    return erreurs


def calculer_solde_compte(solde_initial: float, operations: list[dict]) -> float:
    solde = float(solde_initial or 0)

    for operation in operations:
        if operation.get("statut") != "valide":
            continue

        montant = float(operation.get("montant") or 0)
        type_operation = operation.get("type_operation")
        if type_operation == "recette":
            solde += montant
        elif type_operation == "depense":
            solde -= montant
        elif type_operation == "virement_interne":
            if operation.get("source_module") == "virement_entrant":
                solde += montant
            else:
                solde -= montant

    return round(solde, 2)


def get_categories_for_type(type_operation: str) -> list[dict]:
    if type_operation == "recette":
        return get_all_categories("recette")
    if type_operation == "depense":
        return get_all_categories("depense")
    return get_all_categories()


def formater_montant(montant: float) -> str:
    value = float(montant or 0)
    return f"{value:,.2f} €".replace(",", " ").replace(".", ",")


def slug_reference_remise(date: str, compte_nom: str) -> str:
    nom = "".join(ch for ch in str(compte_nom or "") if ch.isalnum())
    nom = nom[:8] if nom else "Compte"
    return f"Remise_{nom}_{date}"
