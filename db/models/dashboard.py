"""Requêtes agrégées pour le tableau de bord (Phase 8).

Aucun import tkinter/customtkinter dans ce module.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Utilitaires internes ──────────────────────────────────────────────────────


def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        logger.warning("_fetch_all: %s", exc)
        return []
    finally:
        conn.close()


def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("_fetch_one: %s", exc)
        return None
    finally:
        conn.close()


def _fetch_scalar(query: str, params: tuple = (), default: Any = 0) -> Any:
    conn = get_connection()
    try:
        row = conn.execute(query, params).fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception as exc:  # noqa: BLE001
        logger.warning("_fetch_scalar: %s", exc)
        return default
    finally:
        conn.close()


def _sum_evenement_ventes_net(
    *,
    evenement_id: int | None = None,
    debut: str | None = None,
    fin: str | None = None,
) -> float:
    query = """
        SELECT COALESCE(SUM(montant_net), 0)
        FROM evenement_ventes
        WHERE statut = 'valide'
    """
    params: list[Any] = []
    if evenement_id is not None:
        query += " AND evenement_id = ?"
        params.append(evenement_id)
    if debut is not None:
        query += " AND date >= ?"
        params.append(debut)
    if fin is not None:
        query += " AND date < ?"
        params.append(fin)
    return float(_fetch_scalar(query, tuple(params), 0))


# ── Trésorerie ────────────────────────────────────────────────────────────────


def get_solde_global() -> dict:
    """Retourne le solde global de tous les comptes actifs.

    Returns:
        Dictionnaire avec solde_total, solde_bancaire, solde_caisse,
        par_compte (liste [{nom, solde}]).
    """
    comptes = _fetch_all(
        """
        SELECT id, nom, solde_initial, est_caisse
        FROM comptes_bancaires
        WHERE actif = 1
        ORDER BY ordre ASC, id ASC
        """
    )
    par_compte = []
    solde_total = 0.0
    solde_bancaire = 0.0
    solde_caisse = 0.0

    for compte in comptes:
        compte_id = compte["id"]
        solde_initial = float(compte.get("solde_initial") or 0)
        # Calculer le solde en appliquant les opérations valides
        ops = _fetch_all(
            """
            SELECT type_operation, montant, statut, source_module
            FROM tresorerie_operations
            WHERE compte_id = ?
            """,
            (compte_id,),
        )
        solde = solde_initial
        for op in ops:
            statut = op.get("statut", "")
            if statut == "annule":
                continue
            montant = float(op.get("montant") or 0)
            type_op = op.get("type_operation", "")
            source = op.get("source_module", "")
            if type_op == "recette":
                solde += montant
            elif type_op == "depense":
                solde -= montant
            elif type_op == "virement_sortant":
                solde -= montant
            elif type_op == "virement_entrant":
                solde += montant
            elif type_op == "remise_cheque" or source == "remise_cheque":
                solde += montant
        solde = round(solde, 2)
        par_compte.append({"nom": compte["nom"], "solde": solde})
        solde_total += solde
        if int(compte.get("est_caisse") or 0):
            solde_caisse += solde
        else:
            solde_bancaire += solde

    return {
        "solde_total": round(solde_total, 2),
        "solde_bancaire": round(solde_bancaire, 2),
        "solde_caisse": round(solde_caisse, 2),
        "par_compte": par_compte,
    }


def get_recettes_depenses_mois(annee: int, mois: int) -> dict:
    """Retourne recettes et dépenses pour un mois donné.

    Args:
        annee: Année (ex. 2026).
        mois: Mois 1-12.

    Returns:
        {total_recettes, total_depenses, solde_net}
    """
    debut = f"{annee}-{mois:02d}-01"
    # Dernier jour du mois
    if mois == 12:
        fin = f"{annee + 1}-01-01"
    else:
        fin = f"{annee}-{mois + 1:02d}-01"

    total_recettes_treso = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant), 0)
            FROM tresorerie_operations
            WHERE type_operation IN ('recette')
              AND statut = 'valide'
              AND date_operation >= ?
              AND date_operation < ?
            """,
            (debut, fin),
            0,
        )
    )
    total_depenses_treso = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant), 0)
            FROM tresorerie_operations
            WHERE type_operation IN ('depense')
              AND statut = 'valide'
              AND date_operation >= ?
              AND date_operation < ?
            """,
            (debut, fin),
            0,
        )
    )
    total_recettes_billetterie = _sum_evenement_ventes_net(debut=debut, fin=fin)
    total_depenses_evenement = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant), 0)
            FROM evenement_depenses
            WHERE date >= ?
              AND date < ?
            """,
            (debut, fin),
            0,
        )
    )
    total_recettes = total_recettes_treso + total_recettes_billetterie
    total_depenses = total_depenses_treso + total_depenses_evenement
    return {
        "total_recettes": round(total_recettes, 2),
        "total_depenses": round(total_depenses, 2),
        "solde_net": round(total_recettes - total_depenses, 2),
    }


def get_comparatif_mois(annee: int, mois: int) -> dict:
    """Comparatif mois actuel vs mois précédent.

    Returns:
        {mois_actuel: {recettes, depenses}, mois_precedent: {recettes, depenses},
         variation_recettes_pct, variation_depenses_pct}
    """
    actuel = get_recettes_depenses_mois(annee, mois)
    if mois == 1:
        precedent = get_recettes_depenses_mois(annee - 1, 12)
    else:
        precedent = get_recettes_depenses_mois(annee, mois - 1)

    def _variation(actuelle: float, precedente: float) -> float:
        if precedente == 0:
            return 0.0
        return round((actuelle - precedente) / precedente * 100, 1)

    return {
        "mois_actuel": {
            "recettes": actuel["total_recettes"],
            "depenses": actuel["total_depenses"],
        },
        "mois_precedent": {
            "recettes": precedent["total_recettes"],
            "depenses": precedent["total_depenses"],
        },
        "variation_recettes_pct": _variation(
            actuel["total_recettes"], precedent["total_recettes"]
        ),
        "variation_depenses_pct": _variation(
            actuel["total_depenses"], precedent["total_depenses"]
        ),
    }


def get_evolution_tresorerie(nb_mois: int = 12) -> list[dict]:
    """Évolution du solde global sur les *nb_mois* derniers mois.

    Returns:
        [{mois_label, solde_fin_mois}] du plus ancien au plus récent.
    """
    nb_mois = max(1, int(nb_mois or 1))
    today = date.today().replace(day=1)
    mois_noms = [
        "Jan", "Fév", "Mar", "Avr", "Mai", "Juin",
        "Juil", "Août", "Sep", "Oct", "Nov", "Déc",
    ]
    # Solde initial de tous les comptes actifs (somme)
    row = _fetch_one(
        "SELECT COALESCE(SUM(solde_initial), 0) AS total FROM comptes_bancaires WHERE actif = 1"
    )
    base_initial = float(row["total"] if row else 0)

    # Toutes les opérations valides classées chronologiquement
    ops = _fetch_all(
        """
        SELECT date_operation, type_operation, montant, statut
        FROM tresorerie_operations
        WHERE statut = 'valide'
          AND type_operation NOT IN ('virement_sortant', 'virement_entrant')
        ORDER BY date_operation ASC
        """
    )

    result = []
    for i in range(nb_mois - 1, -1, -1):
        # Mois cible = today - i mois
        annee = today.year
        mois = today.month - i
        while mois <= 0:
            mois += 12
            annee -= 1

        # Dernier jour du mois cible
        if mois == 12:
            fin_mois = date(annee + 1, 1, 1) - timedelta(days=1)
        else:
            fin_mois = date(annee, mois + 1, 1) - timedelta(days=1)

        fin_str = str(fin_mois)

        # Somme de toutes les opérations jusqu'à la fin de ce mois
        cumul = base_initial
        for op in ops:
            if (op.get("date_operation") or "") <= fin_str:
                montant = float(op.get("montant") or 0)
                type_op = op.get("type_operation", "")
                if type_op == "recette":
                    cumul += montant
                elif type_op == "depense":
                    cumul -= montant

        label = f"{mois_noms[mois - 1]} {annee}"
        result.append({"mois_label": label, "solde_fin_mois": round(cumul, 2)})

    return result


def get_top_categories_depenses(annee: int, mois: int, top_n: int = 3) -> list[dict]:
    """Top N catégories de dépenses pour un mois donné.

    Returns:
        [{categorie, montant, pourcentage}] triés par montant décroissant.
    """
    debut = f"{annee}-{mois:02d}-01"
    if mois == 12:
        fin = f"{annee + 1}-01-01"
    else:
        fin = f"{annee}-{mois + 1:02d}-01"

    rows = _fetch_all(
        """
        SELECT COALESCE(c.nom, 'Sans catégorie') AS categorie,
               SUM(o.montant) AS montant
        FROM tresorerie_operations o
        LEFT JOIN tresorerie_categories c ON c.id = o.categorie_id
        WHERE o.type_operation = 'depense'
          AND o.statut = 'valide'
          AND o.date_operation >= ?
          AND o.date_operation < ?
        GROUP BY COALESCE(c.nom, 'Sans catégorie')
        ORDER BY montant DESC
        LIMIT ?
        """,
        (debut, fin, int(top_n)),
    )
    total = sum(float(r.get("montant") or 0) for r in rows)
    result = []
    for r in rows:
        montant = round(float(r.get("montant") or 0), 2)
        pct = round(montant / total * 100, 1) if total > 0 else 0.0
        result.append(
            {"categorie": r["categorie"], "montant": montant, "pourcentage": pct}
        )
    return result


def get_cheques_en_attente() -> dict:
    """Retourne les remises de chèques en attente.

    Returns:
        {nb_remises, montant_total, details: [{remise_id, date, montant}]}
    """
    remises = _fetch_all(
        """
        SELECT id, date_remise, COALESCE(montant_total, 0) AS montant_total
        FROM remises_cheques
        WHERE statut = 'en_attente'
        ORDER BY date_remise DESC
        """
    )
    nb = len(remises)
    montant_total = round(sum(float(r.get("montant_total") or 0) for r in remises), 2)
    details = [
        {
            "remise_id": r["id"],
            "date": r.get("date_remise", ""),
            "montant": round(float(r.get("montant_total") or 0), 2),
        }
        for r in remises
    ]
    return {"nb_remises": nb, "montant_total": montant_total, "details": details}


def get_stats_subventions_dashboard() -> dict:
    """Statistiques subventions pour le dashboard.

    Returns:
        {montant_demande, montant_obtenu, nb_en_attente, progression_pct}
    """
    row = _fetch_one(
        """
        SELECT
            COALESCE(SUM(montant_demande), 0) AS montant_demande,
            COALESCE(SUM(montant_obtenu), 0) AS montant_obtenu,
            SUM(CASE WHEN statut = 'en_attente' THEN 1 ELSE 0 END) AS nb_en_attente
        FROM subventions
        """
    )
    if not row:
        return {
            "montant_demande": 0.0,
            "montant_obtenu": 0.0,
            "nb_en_attente": 0,
            "progression_pct": 0.0,
        }
    montant_demande = round(float(row.get("montant_demande") or 0), 2)
    montant_obtenu = round(float(row.get("montant_obtenu") or 0), 2)
    nb_en_attente = int(row.get("nb_en_attente") or 0)
    progression_pct = (
        round(montant_obtenu / montant_demande * 100, 1) if montant_demande > 0 else 0.0
    )
    return {
        "montant_demande": montant_demande,
        "montant_obtenu": montant_obtenu,
        "nb_en_attente": nb_en_attente,
        "progression_pct": progression_pct,
    }


# ── Événements ────────────────────────────────────────────────────────────────


def get_prochains_evenements(nb: int = 3) -> list[dict]:
    """Retourne les *nb* prochains événements à venir.

    Returns:
        [{id, nom, date_debut, type, statut, nb_benevoles_inscrits}]
    """
    today_str = str(date.today())
    rows = _fetch_all(
        """
        SELECT e.id, e.nom, e.date_debut, e.type, e.statut,
               COUNT(b.id) AS nb_benevoles_inscrits
        FROM evenements e
        LEFT JOIN evenement_benevoles b ON b.evenement_id = e.id
        WHERE e.date_debut > ?
          AND e.statut NOT IN ('annule', 'termine')
        GROUP BY e.id
        ORDER BY e.date_debut ASC
        LIMIT ?
        """,
        (today_str, int(nb)),
    )
    return [dict(r) for r in rows]


def get_evenement_en_cours() -> dict | None:
    """Retourne l'événement en cours aujourd'hui, si existant."""
    today_str = str(date.today())
    return _fetch_one(
        """
        SELECT id, nom, date_debut, date_fin, type, statut
        FROM evenements
        WHERE date_debut <= ?
          AND (date_fin IS NULL OR date_fin >= ?)
          AND statut NOT IN ('annule', 'termine')
        ORDER BY date_debut DESC
        LIMIT 1
        """,
        (today_str, today_str),
    )


def get_bilan_dernier_evenement() -> dict | None:
    """Retourne le bilan du dernier événement terminé.

    Returns:
        {nom, date, recettes_nettes, depenses, benefice_net} ou None.
    """
    ev = _fetch_one(
        """
        SELECT id, nom, date_debut AS date
        FROM evenements
        WHERE statut = 'termine'
        ORDER BY date_debut DESC
        LIMIT 1
        """
    )
    if not ev:
        return None

    ev_id = ev["id"]
    recettes = _sum_evenement_ventes_net(evenement_id=ev_id)
    recettes_stands = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant_location), 0)
            FROM evenement_stands
            WHERE evenement_id = ?
              AND type_stand = 'location'
              AND COALESCE(type_location, 'recette') = 'recette'
              AND statut != 'annule'
            """,
            (ev_id,),
            0,
        )
    )
    depenses = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant), 0)
            FROM evenement_depenses
            WHERE evenement_id = ?
            """,
            (ev_id,),
            0,
        )
    )
    depenses_stands = float(
        _fetch_scalar(
            """
            SELECT COALESCE(SUM(montant_location), 0)
            FROM evenement_stands
            WHERE evenement_id = ?
              AND type_stand = 'location'
              AND COALESCE(type_location, 'recette') = 'depense'
              AND statut != 'annule'
            """,
            (ev_id,),
            0,
        )
    )
    recettes += recettes_stands
    depenses += depenses_stands
    return {
        "nom": ev["nom"],
        "date": ev.get("date", ""),
        "recettes_nettes": round(recettes, 2),
        "depenses": round(depenses, 2),
        "benefice_net": round(recettes - depenses, 2),
    }


def get_benevoles_prochains_evenements() -> int:
    """Nombre total de bénévoles inscrits sur les événements à venir."""
    today_str = str(date.today())
    val = _fetch_scalar(
        """
        SELECT COUNT(b.id)
        FROM evenement_benevoles b
        JOIN evenements e ON e.id = b.evenement_id
        WHERE e.date_debut > ?
          AND e.statut NOT IN ('annule', 'termine')
        """,
        (today_str,),
        0,
    )
    return int(val)


# ── Adhérents ─────────────────────────────────────────────────────────────────


def get_stats_adherents_dashboard() -> dict:
    """Statistiques des adhérents pour le dashboard.

    Returns:
        {nb_total, nb_actifs, nb_cotisation_non_reglee, montant_cotisations_dues,
         nb_nouveaux_ce_mois}
    """
    nb_total = int(_fetch_scalar("SELECT COUNT(*) FROM membres", default=0))
    nb_actifs = int(
        _fetch_scalar(
            "SELECT COUNT(*) FROM membres WHERE statut_archive = 0", default=0
        )
    )

    # Cotisations non réglées : membres actifs dont la cotisation est NULL ou vide
    nb_cotisation_non_reglee = int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM membres
            WHERE statut_archive = 0
              AND (cotisation IS NULL OR TRIM(cotisation) = '')
            """,
            default=0,
        )
    )

    # Nouveaux adhérents ce mois
    today = date.today()
    debut_mois = f"{today.year}-{today.month:02d}-01"
    nb_nouveaux_ce_mois = int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM membres
            WHERE statut_archive = 0
              AND date_adhesion >= ?
            """,
            (debut_mois,),
            0,
        )
    )

    return {
        "nb_total": nb_total,
        "nb_actifs": nb_actifs,
        "nb_cotisation_non_reglee": nb_cotisation_non_reglee,
        "montant_cotisations_dues": 0.0,  # Non suivi dans le schéma actuel
        "nb_nouveaux_ce_mois": nb_nouveaux_ce_mois,
    }


# ── Stock ─────────────────────────────────────────────────────────────────────


def get_alertes_stock() -> dict:
    """Articles en rupture ou en stock faible.

    Returns:
        {critique: [{id, nom, quantite}], faible: [{id, nom, quantite, seuil}]}
    """
    articles = _fetch_all(
        """
        SELECT id, nom, quantite, seuil_alerte
        FROM stock
        WHERE statut_archive = 0
        ORDER BY nom ASC
        """
    )
    critique = []
    faible = []
    for a in articles:
        qte = float(a.get("quantite") or 0)
        seuil = a.get("seuil_alerte")
        if qte <= 0:
            critique.append({"id": a["id"], "nom": a["nom"], "quantite": qte})
        elif seuil is not None and float(seuil) > 0 and qte <= float(seuil):
            faible.append(
                {
                    "id": a["id"],
                    "nom": a["nom"],
                    "quantite": qte,
                    "seuil": float(seuil),
                }
            )
    return {"critique": critique, "faible": faible}


def get_lots_expires_a_archiver() -> int:
    """Retourne le nombre de lots expirés encore actifs."""
    return int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM stock_lots
            WHERE statut = 'actif'
              AND quantite_restante > 0
              AND date_peremption IS NOT NULL
              AND date(date_peremption) < date('now')
            """,
            default=0,
        )
    )


def get_articles_peremption_proche_dashboard(jours: int) -> int:
    """Retourne le nombre de lots qui périment prochainement."""
    return int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM stock_lots
            WHERE statut = 'actif'
              AND quantite_restante > 0
              AND date_peremption IS NOT NULL
              AND date(date_peremption) >= date('now')
              AND date(date_peremption) <= date('now', '+' || ? || ' days')
            """,
            (int(jours),),
            0,
        )
    )


def get_evenements_sans_inventaire_apres() -> int:
    """Événements terminés sans inventaire 'apres_evenement' validé."""
    return int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM evenements e
            WHERE COALESCE(e.statut, '') IN ('termine', 'en_cours')
              AND NOT EXISTS (
                SELECT 1
                FROM stock_inventaires i
                WHERE i.evenement_id = e.id
                  AND i.type_inventaire = 'apres_evenement'
                  AND i.statut = 'valide'
              )
            """,
            default=0,
        )
    )


def get_couts_buvette_non_calcules() -> int:
    """Événements avec inventaires avant/après validés mais sans coût calculé."""
    return int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM evenements e
            WHERE EXISTS (
                SELECT 1 FROM stock_inventaires i1
                WHERE i1.evenement_id = e.id
                  AND i1.type_inventaire = 'avant_evenement'
                  AND i1.statut = 'valide'
            )
              AND EXISTS (
                SELECT 1 FROM stock_inventaires i2
                WHERE i2.evenement_id = e.id
                  AND i2.type_inventaire = 'apres_evenement'
                  AND i2.statut = 'valide'
            )
              AND NOT EXISTS (
                SELECT 1 FROM buvette_couts_evenement c
                WHERE c.evenement_id = e.id
              )
            """,
            default=0,
        )
    )


# ── Alertes globales ──────────────────────────────────────────────────────────


def get_toutes_alertes() -> list[dict]:
    """Génère toutes les alertes actives pour le tableau de bord.

    Niveaux : 'rouge', 'orange', 'bleu'.
    Returns:
        [{niveau, message, module, lien_action}]
    """
    alertes: list[dict] = []
    today = date.today()

    # Stock critique
    stock = get_alertes_stock()
    for a in stock["critique"]:
        alertes.append(
            {
                "niveau": "rouge",
                "message": f"Rupture de stock : {a['nom']} (quantité : {a['quantite']:.0f})",
                "module": "stock",
                "lien_action": "stock",
            }
        )
    for a in stock["faible"]:
        alertes.append(
            {
                "niveau": "orange",
                "message": (
                    f"Stock faible : {a['nom']} "
                    f"({a['quantite']:.0f} / seuil {a['seuil']:.0f})"
                ),
                "module": "stock",
                "lien_action": "stock",
            }
        )

    # Stock v2 : péremption
    jours_peremption = int(
        _fetch_scalar(
            "SELECT COALESCE(valeur, '30') FROM parametres WHERE cle = 'stock_alerte_peremption_jours'",
            default=30,
        )
    )
    nb_expires = get_lots_expires_a_archiver()
    if nb_expires > 0:
        alertes.append(
            {
                "niveau": "rouge",
                "message": f"{nb_expires} lot(s) expiré(s) à archiver",
                "module": "stock",
                "lien_action": "stock",
            }
        )

    nb_proches = get_articles_peremption_proche_dashboard(jours_peremption)
    if nb_proches > 0:
        alertes.append(
            {
                "niveau": "orange",
                "message": (
                    f"{nb_proches} lot(s) périment dans moins de {jours_peremption} jour(s)"
                ),
                "module": "stock",
                "lien_action": "stock",
            }
        )

    # Opérations en attente depuis plus de 7 jours
    seuil_date = str(today - timedelta(days=7))
    nb_ops_attente = int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM tresorerie_operations
            WHERE statut = 'en_attente'
              AND date_operation <= ?
            """,
            (seuil_date,),
            0,
        )
    )
    if nb_ops_attente > 0:
        alertes.append(
            {
                "niveau": "orange",
                "message": (
                    f"{nb_ops_attente} opération(s) en attente depuis plus de 7 jours"
                ),
                "module": "tresorerie",
                "lien_action": "tresorerie",
            }
        )

    # Exercice se terminant dans moins de 30 jours
    exercice_proche = _fetch_one(
        """
        SELECT nom, date_fin
        FROM exercices
        WHERE statut = 'ouvert'
          AND date_fin IS NOT NULL
        ORDER BY date_fin ASC
        LIMIT 1
        """
    )
    if exercice_proche:
        try:
            date_fin = date.fromisoformat(str(exercice_proche["date_fin"]))
            jours_restants = (date_fin - today).days
            if 0 <= jours_restants <= 30:
                alertes.append(
                    {
                        "niveau": "bleu",
                        "message": (
                            f"L'exercice « {exercice_proche['nom']} » se termine "
                            f"dans {jours_restants} jour(s)"
                        ),
                        "module": "tresorerie",
                        "lien_action": "exercices",
                    }
                )
        except (ValueError, TypeError):
            pass

    # Chèques en attente
    cheques = get_cheques_en_attente()
    if cheques["nb_remises"] > 0:
        alertes.append(
            {
                "niveau": "orange",
                "message": (
                    f"{cheques['nb_remises']} remise(s) de chèques en attente "
                    f"— {cheques['montant_total']:.2f} €"
                ),
                "module": "tresorerie",
                "lien_action": "tresorerie",
            }
        )

    # Cotisations non réglées
    stats_adh = get_stats_adherents_dashboard()
    if stats_adh["nb_cotisation_non_reglee"] > 0:
        alertes.append(
            {
                "niveau": "bleu",
                "message": (
                    f"{stats_adh['nb_cotisation_non_reglee']} cotisation(s) "
                    "non renseignée(s)"
                ),
                "module": "adherents",
                "lien_action": "membres",
            }
        )

    nb_sans_apres = get_evenements_sans_inventaire_apres()
    if nb_sans_apres > 0:
        alertes.append(
            {
                "niveau": "orange",
                "message": f"{nb_sans_apres} événement(s) sans inventaire après",
                "module": "buvette",
                "lien_action": "buvette",
            }
        )

    nb_couts_non_calcules = get_couts_buvette_non_calcules()
    if nb_couts_non_calcules > 0:
        alertes.append(
            {
                "niveau": "bleu",
                "message": f"{nb_couts_non_calcules} coût(s) buvette non calculé(s)",
                "module": "buvette",
                "lien_action": "buvette",
            }
        )

    return alertes


# ── Système ───────────────────────────────────────────────────────────────────


def get_info_derniere_sauvegarde() -> dict:
    """Retourne les informations sur la dernière sauvegarde.

    Returns:
        {date, nb_jours_depuis, chemin}
    """
    chemin = ""
    derniere_date_str = ""
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                """
                SELECT chemin_complet, created_at
                FROM sauvegardes
                WHERE statut = 'ok'
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """
            ).fetchone()
        finally:
            conn.close()
        if row:
            chemin = row["chemin_complet"] or ""
            derniere_date_str = row["created_at"] or ""
    except Exception:  # noqa: BLE001
        try:
            from db.models.parametres_globaux import get_parametre  # noqa: PLC0415

            derniere_date_str = get_parametre("derniere_sauvegarde", "")
        except Exception:  # noqa: BLE001
            chemin = ""
            derniere_date_str = ""

    nb_jours: int | None = None
    if derniere_date_str:
        try:
            derniere_date = date.fromisoformat(derniere_date_str[:10])
            nb_jours = (date.today() - derniere_date).days
        except (ValueError, TypeError):
            nb_jours = None

    return {
        "date": derniere_date_str,
        "nb_jours_depuis": nb_jours,
        "chemin": chemin,
    }
