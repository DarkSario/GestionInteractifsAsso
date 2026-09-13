"""Couche métier des caisses événement et du bilan global."""

from __future__ import annotations

from db.connection import get_connection
from db.models.evenement_caisses import (
    get_lignes_caisse,
    get_total_caisse,
    get_total_recettes_caisses_evenement,
)


def calculer_total_lignes(lignes: list[dict]) -> float:
    """Calcule la somme des totaux d'un ensemble de lignes."""
    return round(sum(float(ligne.get("total") or 0) for ligne in lignes), 2)


def calculer_totaux_caisse(caisse_id: int) -> dict:
    """Retourne les totaux début/fin et la recette d'une caisse."""
    lignes_debut = get_lignes_caisse(caisse_id, "debut")
    lignes_fin = get_lignes_caisse(caisse_id, "fin")
    total_debut = get_total_caisse(caisse_id, "debut")
    total_fin = get_total_caisse(caisse_id, "fin")
    return {
        "lignes_debut": lignes_debut,
        "lignes_fin": lignes_fin,
        "total_debut": round(total_debut, 2),
        "total_fin": round(total_fin, 2),
        "recette": round(total_fin - total_debut, 2),
    }


def calculer_recettes_caisses_evenement(evenement_id: int) -> float:
    """Retourne la recette totale de toutes les caisses d'un événement."""
    return get_total_recettes_caisses_evenement(evenement_id)


def calculer_bilan_complet_evenement(evenement_id: int) -> dict:
    """Calcule le bénéfice global complet d'un événement.

    Formule:
      (Billetterie + Stands + Tombola + Buvette + Caisses + Tableaux)
      - (Dépenses + Stands dépenses + Coûts buvette)
    """
    from db.models.buvette import calculer_recette_evenement
    from db.models.evenements import get_depenses_evenement, get_stats_billetterie
    from db.models.stands import get_stands_evenement
    from db.models.tableaux import calculer_totaux, get_colonnes_tableau, get_tableaux_evenement
    from db.models.tombola import get_stats_tombola, get_total_dons_tombola_solidaire

    stats_billetterie = get_stats_billetterie(evenement_id)
    recettes_billetterie = float(stats_billetterie.get("total_net") or 0)

    stands = get_stands_evenement(evenement_id)
    recettes_stands = sum(
        float(s.get("montant_location") or 0)
        for s in stands
        if s.get("type_stand") == "location"
        and (s.get("type_location") or "recette") == "recette"
        and s.get("statut") != "annule"
    )
    depenses_stands = sum(
        float(s.get("montant_location") or 0)
        for s in stands
        if s.get("type_stand") == "location"
        and (s.get("type_location") or "recette") == "depense"
        and s.get("statut") != "annule"
    )

    recettes_tableaux = 0.0
    tableaux = get_tableaux_evenement(evenement_id)
    for tableau in tableaux:
        t_id = int(tableau["id"])
        totaux = calculer_totaux(t_id)
        if not totaux:
            continue
        colonnes_by_id = {int(c["id"]): c for c in get_colonnes_tableau(t_id)}
        for col_id, total in totaux.items():
            col = colonnes_by_id.get(col_id, {})
            if col.get("type_colonne") == "montant":
                recettes_tableaux += float(total or 0)

    stats_tombola = get_stats_tombola(evenement_id)
    recettes_tombola = float(stats_tombola.get("montant_total") or 0) + float(
        get_total_dons_tombola_solidaire(evenement_id) or 0
    )

    recettes_buvette = float(calculer_recette_evenement(evenement_id).get("recette_nette") or 0)
    recettes_caisses = float(get_total_recettes_caisses_evenement(evenement_id) or 0)

    depenses = get_depenses_evenement(evenement_id)
    depenses_evenement = sum(float(d.get("montant") or 0) for d in depenses)

    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COALESCE(cout_total_ttc, 0) AS cout_buvette
            FROM buvette_couts_evenement
            WHERE evenement_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (evenement_id,),
        ).fetchone()
        cout_buvette = float(row["cout_buvette"] if row else 0)
    finally:
        conn.close()

    total_recettes = (
        recettes_billetterie
        + recettes_stands
        + recettes_tableaux
        + recettes_tombola
        + recettes_buvette
        + recettes_caisses
    )
    total_depenses = depenses_evenement + depenses_stands + cout_buvette
    benefice_global = total_recettes - total_depenses

    return {
        "recettes_billetterie": round(recettes_billetterie, 2),
        "recettes_stands": round(recettes_stands, 2),
        "recettes_tableaux": round(recettes_tableaux, 2),
        "recettes_tombola": round(recettes_tombola, 2),
        "recettes_buvette": round(recettes_buvette, 2),
        "recettes_caisses": round(recettes_caisses, 2),
        "depenses_evenement": round(depenses_evenement, 2),
        "depenses_stands": round(depenses_stands, 2),
        "cout_buvette": round(cout_buvette, 2),
        "total_recettes": round(total_recettes, 2),
        "total_depenses": round(total_depenses, 2),
        "benefice_global": round(benefice_global, 2),
    }
