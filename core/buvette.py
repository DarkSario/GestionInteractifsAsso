"""Logique métier pour le module Buvette."""

from __future__ import annotations


def valider_article_buvette(nom, prix_vente, categorie_id, unite_id) -> list[str]:
    """Valide les champs de base d'un article buvette."""
    erreurs: list[str] = []

    if not nom or not str(nom).strip():
        erreurs.append("Le nom de l'article est obligatoire.")

    if categorie_id is None:
        erreurs.append("La catégorie est obligatoire.")

    if unite_id is None:
        erreurs.append("L'unité est obligatoire.")

    try:
        prix = float(str(prix_vente).replace(",", "."))
        if prix < 0:
            erreurs.append("Le prix de vente doit être supérieur ou égal à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le prix de vente doit être un nombre valide.")

    return erreurs


def valider_caisse(nom, fond_de_caisse, total_brut) -> list[str]:
    """Valide les informations de caisse."""
    erreurs: list[str] = []

    if not nom or not str(nom).strip():
        erreurs.append("Le nom de la caisse est obligatoire.")

    try:
        fond = float(str(fond_de_caisse).replace(",", "."))
        if fond < 0:
            erreurs.append("Le fond de caisse doit être supérieur ou égal à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le fond de caisse doit être un nombre valide.")

    try:
        brut = float(str(total_brut).replace(",", "."))
        if brut < 0:
            erreurs.append("Le total brut doit être supérieur ou égal à 0.")
    except (TypeError, ValueError):
        erreurs.append("Le total brut doit être un nombre valide.")

    return erreurs


def calculer_net_caisses(caisses: list[dict]) -> dict:
    """Calcule les totaux de recette nette sur un ensemble de caisses."""
    total_brut = sum(float(c.get("total_brut") or 0) for c in caisses)
    total_fond_caisse = sum(float(c.get("fond_de_caisse") or 0) for c in caisses)
    recette_nette = total_brut - total_fond_caisse

    return {
        "recette_nette": recette_nette,
        "total_brut": total_brut,
        "total_fond_caisse": total_fond_caisse,
    }


def valider_inventaire_lignes(lignes: list[dict]) -> list[str]:
    """Valide les lignes d'inventaire saisies."""
    erreurs: list[str] = []

    if not lignes:
        erreurs.append("Au moins une ligne d'inventaire est requise.")
        return erreurs

    for i, ligne in enumerate(lignes, start=1):
        if ligne.get("article_id") is None:
            erreurs.append(f"Ligne {i} : article manquant.")
            continue

        try:
            qte = int(ligne.get("quantite_comptee"))
            if qte < 0:
                erreurs.append(f"Ligne {i} : la quantité comptée ne peut pas être négative.")
        except (TypeError, ValueError):
            erreurs.append(f"Ligne {i} : la quantité comptée doit être un entier.")

    return erreurs
