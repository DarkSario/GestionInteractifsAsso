"""Logique métier pour le module Événements."""

from __future__ import annotations


def valider_evenement(nom: str, date_debut: str, date_fin: str | None) -> list[str]:
    """Valide les champs obligatoires d'un événement.

    Returns:
        Liste des messages d'erreur (vide si tout est valide).
    """
    erreurs: list[str] = []

    if not nom or not str(nom).strip():
        erreurs.append("Le nom de l'événement est obligatoire.")

    if not date_debut or not str(date_debut).strip():
        erreurs.append("La date de début est obligatoire.")
    else:
        try:
            from datetime import datetime

            d_debut = datetime.strptime(date_debut, "%Y-%m-%d")
            if date_fin and str(date_fin).strip():
                d_fin = datetime.strptime(date_fin, "%Y-%m-%d")
                if d_fin < d_debut:
                    erreurs.append("La date de fin doit être postérieure à la date de début.")
        except ValueError:
            erreurs.append("Le format de date est invalide (attendu : AAAA-MM-JJ).")

    return erreurs


def valider_tarif(nom: str, prix: float | str) -> list[str]:
    """Valide les champs d'un tarif.

    Returns:
        Liste des messages d'erreur (vide si tout est valide).
    """
    erreurs: list[str] = []

    if not nom or not str(nom).strip():
        erreurs.append("Le nom du tarif est obligatoire.")

    try:
        p = float(str(prix).replace(",", "."))
        if p < 0:
            erreurs.append("Le prix doit être supérieur ou égal à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le prix doit être un nombre valide.")

    return erreurs


def calculer_frais_sumup(montant: float, taux: float) -> float:
    """Calcule les frais SumUp pour un montant donné.

    Args:
        montant: Montant brut de la transaction.
        taux: Taux en pourcentage (ex : 1.75).

    Returns:
        Frais arrondis à 2 décimales.
    """
    return round(montant * taux / 100, 2)


def calculer_montant_net(
    montant: float,
    mode_paiement: str,
    taux_sumup: float,
) -> float:
    """Calcule le montant net après éventuels frais SumUp.

    Args:
        montant: Montant brut.
        mode_paiement: Mode de paiement ('sumup', 'carte', 'especes', 'cheque').
        taux_sumup: Taux SumUp en pourcentage.

    Returns:
        Montant net arrondi à 2 décimales.
    """
    if mode_paiement in {"sumup", "carte"}:
        frais = calculer_frais_sumup(montant, taux_sumup)
        return round(montant - frais, 2)
    return round(montant, 2)


def valider_vente(lignes: list[dict], mode_paiement: str) -> list[str]:
    """Valide les données d'une vente.

    Args:
        lignes: Liste de dicts avec les clés 'tarif_id', 'quantite', 'prix_unitaire'.
        mode_paiement: Mode de paiement choisi.

    Returns:
        Liste des messages d'erreur (vide si tout est valide).
    """
    erreurs: list[str] = []

    modes_valides = {"especes", "cheque", "carte", "sumup"}
    if mode_paiement not in modes_valides:
        erreurs.append(f"Mode de paiement invalide : {mode_paiement}.")

    lignes_valides = [l for l in lignes if int(l.get("quantite", 0)) > 0]
    if not lignes_valides:
        erreurs.append("La vente doit contenir au moins un billet (quantité > 0).")

    for i, ligne in enumerate(lignes_valides, start=1):
        try:
            qte = int(ligne.get("quantite", 0))
            if qte <= 0:
                erreurs.append(f"Ligne {i} : la quantité doit être supérieure à 0.")
        except (TypeError, ValueError):
            erreurs.append(f"Ligne {i} : la quantité doit être un entier.")

        try:
            prix = float(str(ligne.get("prix_unitaire", 0)).replace(",", "."))
            if prix < 0:
                erreurs.append(f"Ligne {i} : le prix unitaire doit être ≥ 0.")
        except (TypeError, ValueError):
            erreurs.append(f"Ligne {i} : le prix unitaire doit être un nombre valide.")

    return erreurs


def generer_numero_billet(evenement_id: int, tarif_nom: str, index: int) -> str:
    """Génère un numéro de billet formaté.

    Le numéro est composé de la première lettre du tarif (en majuscule) suivie
    d'un index sur 3 chiffres.  Ex : "A001", "E003".

    Args:
        evenement_id: Identifiant de l'événement (non utilisé mais conservé
                      pour extensibilité future).
        tarif_nom: Nom du tarif (ex : "Adulte", "Enfant").
        index: Index du billet (à partir de 1).

    Returns:
        Numéro de billet formaté (ex : "A001").
    """
    prefix = (tarif_nom[0].upper() if tarif_nom else "X")
    return f"{prefix}{index:03d}"


def calculer_bilan_evenement(evenement_id: int) -> dict:
    """Calcule le bilan financier complet d'un événement.

    Requiert un accès DB ; importe les modèles en interne pour rester
    compatible avec la contrainte « pas de tkinter dans core/ ».

    Returns:
        Dict avec recettes_total, depenses_total, benefice et detail.
    """
    from core.caisses_evenement import calculer_bilan_complet_evenement
    from db.models.evenements import get_depenses_evenement, get_stats_billetterie
    from db.models.stands import get_stands_evenement

    bilan = calculer_bilan_complet_evenement(evenement_id)
    stats = get_stats_billetterie(evenement_id)
    depenses = get_depenses_evenement(evenement_id)
    stands = get_stands_evenement(evenement_id)

    return {
        "recettes_total": round(float(bilan.get("total_recettes") or 0), 2),
        "depenses_total": round(float(bilan.get("total_depenses") or 0), 2),
        "benefice": round(float(bilan.get("benefice_global") or 0), 2),
        "detail": {
            "billetterie": stats,
            "depenses": depenses,
            "stands": stands,
            "recettes_tableaux": round(float(bilan.get("recettes_tableaux") or 0), 2),
            "recettes_tombola": round(float(bilan.get("recettes_tombola") or 0), 2),
            "recettes_buvette": round(float(bilan.get("recettes_buvette") or 0), 2),
            "recettes_caisses": round(float(bilan.get("recettes_caisses") or 0), 2),
            "cout_buvette": round(float(bilan.get("cout_buvette") or 0), 2),
        },
    }
