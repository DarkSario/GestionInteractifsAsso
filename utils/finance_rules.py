"""Règles financières partagées (source unique de vérité).

Une opération de trésorerie est soit :
- **comptable** : elle compte dans les recettes/dépenses/soldes ;
- **informative** (traçabilité uniquement) : remise de chèques et dépôt d'espèces,
  déjà comptabilisés dans les recettes d'événements ; elle est conservée dans
  l'historique mais exclue de tous les totaux (dashboard, trésorerie, Bilan AG,
  exports).

Ce module ne dépend d'aucun accès base de données.
"""

from __future__ import annotations

from typing import Iterable

# Règle canonique : une opération « rapprochée » (verrouillée par la clôture d'un
# exercice) compte comme une opération validée dans tous les totaux.
STATUTS_COMPTABLES = frozenset({"valide", "rapproche"})

SOURCES_NON_COMPTABLES = frozenset({"remise_cheque", "depot_especes"})

# Sources qui créent automatiquement une écriture comptable (recette/dépense).
SOURCES_ECRITURE_AUTO = frozenset({"cotisation", "don", "tombola_remboursement"})


# Base de trésorerie : CAISSE. Une subvention n'est une recette que lorsqu'elle est
# réellement versée (date de versement renseignée) ; « partielle » ne compte que
# pour le montant effectivement reçu. Les virements internes ne sont ni recette
# ni dépense brute : ils n'affectent que les soldes de comptes.
STATUTS_SUBVENTION_ENCAISSABLES = frozenset({"accordee", "partielle"})


def subvention_est_encaissee(subvention: dict) -> bool:
    """Vrai si la subvention doit figurer en trésorerie (base caisse)."""
    return (
        subvention.get("statut") in STATUTS_SUBVENTION_ENCAISSABLES
        and float(subvention.get("montant_obtenu") or 0) > 0
        and bool(str(subvention.get("date_versement") or "").strip())
    )


def est_virement_interne(operation: dict) -> bool:
    """Opération de virement interne (jambe sortante ou entrante)."""
    return operation.get("type_operation") == "virement_interne"


def est_source_comptable(source_module: str | None) -> bool:
    """Indique si une source alimente la comptabilité (False = traçabilité seule)."""
    return (source_module or "") not in SOURCES_NON_COMPTABLES


def est_operation_comptable(operation: dict) -> bool:
    """Opération validée ou rapprochée et issue d'une source comptable."""
    return operation.get("statut") in STATUTS_COMPTABLES and est_source_comptable(operation.get("source_module"))


def sql_filtre_comptable(alias: str = "") -> str:
    """Fragment SQL (sans AND initial) excluant les sources non comptables."""
    col = f"{alias}.source_module" if alias else "source_module"
    sources = ", ".join(f"'{s}'" for s in sorted(SOURCES_NON_COMPTABLES))
    return f"({col} IS NULL OR {col} NOT IN ({sources}))"


def montant_signe(operation: dict) -> float:
    """Montant signé d'une opération : recettes +, dépenses/virements sortants -.

    Retourne 0 pour une opération non validée ou non comptable.
    """
    if not est_operation_comptable(operation):
        return 0.0
    montant = float(operation.get("montant") or 0)
    type_operation = operation.get("type_operation")
    if type_operation == "recette":
        return montant
    if type_operation == "depense":
        return -montant
    if type_operation == "virement_interne":
        return montant if operation.get("source_module") == "virement_entrant" else -montant
    return 0.0


def totaux_operations(operations: Iterable[dict]) -> dict[str, float]:
    """Agrège recettes, dépenses et solde (hors non-comptable / non validé)."""
    recettes = 0.0
    depenses = 0.0
    net = 0.0
    for operation in operations:
        signed = montant_signe(operation)
        net += signed
        if est_virement_interne(operation):
            continue
        if signed >= 0:
            recettes += signed
        else:
            depenses += -signed
    recettes = round(recettes, 2)
    depenses = round(depenses, 2)
    return {"total_recettes": recettes, "total_depenses": depenses, "solde": round(net, 2)}


def formater_montant_eur(valeur, defaut: str = "—") -> str:
    """Formate un montant en euros, ASCII uniquement (compatible Helvetica)."""
    try:
        val = round(float(valeur or 0), 2)
    except (TypeError, ValueError):
        return defaut
    centimes = int(round(abs(val) * 100))
    entier, decimales = divmod(centimes, 100)
    signe = "-" if val < 0 and centimes else ""
    return f"{signe}{entier:,}".replace(",", " ") + f",{decimales:02d} EUR"
