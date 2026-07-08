"""Logique métier pour la tombola."""

from __future__ import annotations

from datetime import datetime


def valider_lot(numero, description) -> list[str]:
    """Valide un lot de tombola."""
    erreurs: list[str] = []

    try:
        n = int(numero)
        if n <= 0:
            erreurs.append("Le numéro du lot doit être supérieur à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le numéro du lot doit être un entier valide.")

    if not description or not str(description).strip():
        erreurs.append("La description du lot est obligatoire.")

    return erreurs


def valider_carnet(numero_debut, numero_fin, prix_carnet) -> list[str]:
    """Valide un carnet de tombola."""
    erreurs: list[str] = []

    try:
        debut = int(numero_debut)
    except (TypeError, ValueError):
        erreurs.append("Le numéro de début doit être un entier.")
        debut = None

    try:
        fin = int(numero_fin)
    except (TypeError, ValueError):
        erreurs.append("Le numéro de fin doit être un entier.")
        fin = None

    if debut is not None and fin is not None and fin < debut:
        erreurs.append("Le numéro de fin doit être supérieur ou égal au numéro de début.")

    try:
        prix = float(str(prix_carnet).replace(",", "."))
        if prix < 0:
            erreurs.append("Le prix du carnet doit être supérieur ou égal à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le prix du carnet doit être un nombre valide.")

    return erreurs


def calculer_stats_tombola(carnets: list[dict], lots: list[dict]) -> dict:
    """Calcule des statistiques de tombola à partir des données déjà chargées."""

    def quantite(c: dict) -> int:
        debut = int(c.get("numero_debut") or 0)
        fin = int(c.get("numero_fin") or 0)
        return max(0, fin - debut + 1)

    total_carnets = sum(quantite(c) for c in carnets)
    vendus = sum(quantite(c) for c in carnets if c.get("statut") == "vendu")
    retournes = sum(quantite(c) for c in carnets if c.get("statut") == "retourne")
    perdus = sum(quantite(c) for c in carnets if c.get("statut") == "perdu")
    montant_total = round(sum(float(c.get("montant_encaisse") or 0) for c in carnets), 2)
    lots_attribues = sum(1 for l in lots if l.get("statut") == "attribue")

    return {
        "total_carnets": total_carnets,
        "vendus": vendus,
        "retournes": retournes,
        "perdus": perdus,
        "montant_total": montant_total,
        "lots_attribues": lots_attribues,
    }


def generer_contenu_pv(evenement: dict, lots: list[dict]) -> str:
    """Génère le contenu texte d'un procès-verbal de tirage."""
    nom_evenement = evenement.get("nom") or f"Événement #{evenement.get('id', '?')}"
    date_evt = evenement.get("date_debut") or "Date non renseignée"
    maintenant = datetime.now().strftime("%d/%m/%Y %H:%M")

    lignes = [
        "PROCÈS-VERBAL DE TIRAGE — TOMBOLA",
        "=" * 42,
        f"Événement : {nom_evenement}",
        f"Date événement : {date_evt}",
        f"Date tirage : {maintenant}",
        "",
        "Lots attribués :",
    ]

    if not lots:
        lignes.append("- Aucun lot enregistré.")
    else:
        for lot in sorted(lots, key=lambda x: int(x.get("numero") or 0)):
            numero = lot.get("numero")
            description = lot.get("description") or "Sans description"
            gagnant = lot.get("numero_gagnant") or "—"
            statut = lot.get("statut") or "en_attente"
            lignes.append(f"- Lot n°{numero} : {description} | Gagnant: {gagnant} | Statut: {statut}")

    lignes.extend(["", "Fin du procès-verbal."])
    return "\n".join(lignes)
