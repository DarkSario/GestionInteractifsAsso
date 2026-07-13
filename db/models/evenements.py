"""CRUD pour le module Événements."""

from __future__ import annotations

import json
from datetime import datetime

from db.connection import get_connection
from utils.logger import get_logger

logger = get_logger(__name__)

MODULES_EVENEMENT_DISPONIBLES = (
    "billetterie",
    "depenses",
    "benevoles",
    "tombola_classique",
    "tombola_solidaire",
    "stands",
    "tableaux",
    "budget_previsionnel",
)
MODULES_EVENEMENT_PAR_DEFAUT = (
    "billetterie",
    "depenses",
    "benevoles",
)


def _normaliser_module_evenement(module: str | None) -> str:
    return str(module or "").strip().lower()


# ── Événements ───────────────────────────────────────────────────────────────


def get_all_evenements(statut: str | None = None) -> list[dict]:
    """Retourne tous les événements, optionnellement filtrés par statut."""
    conn = get_connection()
    try:
        where = "WHERE e.statut = ?" if statut else ""
        params = (statut,) if statut else ()
        rows = conn.execute(
            f"""
            SELECT e.id, e.nom, e.type, e.description, e.date_debut, e.date_fin,
                   e.statut, e.budget_previsionnel, e.bilan_fin, e.created_at,
                   e.modules_actifs_json,
                   (
                       COALESCE((SELECT SUM(v.montant_net) FROM evenement_ventes v
                                 WHERE v.evenement_id = e.id AND v.statut = 'valide'), 0)
                     + COALESCE((SELECT SUM(s.montant_location) FROM evenement_stands s
                                 WHERE s.evenement_id = e.id
                                   AND s.type_stand = 'location'
                                   AND COALESCE(s.type_location, 'recette') = 'recette'
                                   AND s.statut != 'annule'), 0)
                   ) AS total_recettes,
                   (
                       COALESCE((SELECT SUM(d.montant) FROM evenement_depenses d
                                 WHERE d.evenement_id = e.id), 0)
                     + COALESCE((SELECT SUM(s.montant_location) FROM evenement_stands s
                                 WHERE s.evenement_id = e.id
                                   AND s.type_stand = 'location'
                                   AND COALESCE(s.type_location, 'recette') = 'depense'
                                   AND s.statut != 'annule'), 0)
                   ) AS total_depenses
            FROM evenements e
            {where}
            ORDER BY e.date_debut DESC
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_evenement_by_id(evenement_id: int) -> dict | None:
    """Retourne un événement par identifiant."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, nom, type, description, date_debut, date_fin,
                   statut, budget_previsionnel, bilan_fin, created_at,
                   modules_actifs_json
            FROM evenements
            WHERE id = ?
            """,
            (evenement_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_evenement(
    nom: str,
    type_: str | None,
    description: str | None,
    date_debut: str,
    date_fin: str | None,
    statut: str,
    budget_previsionnel: float | None,
    modules_actifs_json: str | None = None,
) -> int:
    """Crée un événement et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenements
                (nom, type, description, date_debut, date_fin, statut, budget_previsionnel, modules_actifs_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, '["billetterie","depenses","benevoles"]'))
            """,
            (
                nom,
                type_,
                description,
                date_debut,
                date_fin,
                statut,
                budget_previsionnel,
                modules_actifs_json,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_EVENEMENT = frozenset({
    "nom", "type", "description", "date_debut", "date_fin",
    "statut", "budget_previsionnel", "bilan_fin", "modules_actifs_json",
})


def update_evenement(evenement_id: int, **kwargs) -> bool:
    """Met à jour les champs d'un événement."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_EVENEMENT
    if champs_invalides:
        logger.error("update_evenement: colonnes non autorisées : %s", champs_invalides)
        return False
    colonnes = ", ".join(f"{k} = ?" for k in kwargs)
    valeurs = list(kwargs.values()) + [evenement_id]
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE evenements SET {colonnes} WHERE id = ?",
            valeurs,
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("update_evenement: %s", exc)
        return False
    finally:
        conn.close()


def update_bilan_fin(evenement_id: int, bilan: str) -> bool:
    """Met à jour le bilan de fin d'un événement."""
    return update_evenement(evenement_id, bilan_fin=bilan)


def get_evenements_for_select() -> list[dict]:
    """Retourne les événements (id, nom, date_debut) pour les listes déroulantes."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, nom, date_debut FROM evenements ORDER BY date_debut DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def serialiser_modules_actifs(modules: list[str] | tuple[str, ...] | None) -> str:
    """Sérialise une liste de modules activés."""
    modules_valides = []
    for module in modules or MODULES_EVENEMENT_PAR_DEFAUT:
        module_normalise = _normaliser_module_evenement(module)
        if (
            module_normalise in MODULES_EVENEMENT_DISPONIBLES
            and module_normalise not in modules_valides
        ):
            modules_valides.append(module_normalise)
    if not modules_valides:
        modules_valides = list(MODULES_EVENEMENT_PAR_DEFAUT)
    return json.dumps(modules_valides, ensure_ascii=False)


def modules_actifs_depuis_json(modules_actifs_json: str | None) -> list[str]:
    """Retourne les modules actifs normalisés.

    Les événements historiques sans configuration explicite gardent tous les
    onglets visibles par défaut.
    """
    if not modules_actifs_json:
        return list(MODULES_EVENEMENT_DISPONIBLES)
    try:
        raw = json.loads(modules_actifs_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return list(MODULES_EVENEMENT_DISPONIBLES)
    if not isinstance(raw, list):
        return list(MODULES_EVENEMENT_DISPONIBLES)

    modules_valides: list[str] = []
    for module in raw:
        module_normalise = _normaliser_module_evenement(module)
        if (
            module_normalise in MODULES_EVENEMENT_DISPONIBLES
            and module_normalise not in modules_valides
        ):
            modules_valides.append(module_normalise)
    return modules_valides or list(MODULES_EVENEMENT_PAR_DEFAUT)


def get_modules_actifs_evenement(evenement_id: int) -> list[str]:
    """Retourne les modules actifs d'un événement."""
    evenement = get_evenement_by_id(evenement_id)
    if not evenement:
        return list(MODULES_EVENEMENT_PAR_DEFAUT)
    return modules_actifs_depuis_json(evenement.get("modules_actifs_json"))


# ── Tarifs ───────────────────────────────────────────────────────────────────


def get_tarifs_evenement(evenement_id: int) -> list[dict]:
    """Retourne les tarifs d'un événement, triés par ordre."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, evenement_id, nom, prix, est_gratuit, ordre
            FROM evenement_tarifs
            WHERE evenement_id = ?
            ORDER BY ordre ASC, id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_tarif(
    evenement_id: int,
    nom: str,
    prix: float,
    est_gratuit: int,
    ordre: int,
) -> int:
    """Crée un tarif et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_tarifs (evenement_id, nom, prix, est_gratuit, ordre)
            VALUES (?, ?, ?, ?, ?)
            """,
            (evenement_id, nom, prix, est_gratuit, ordre),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_TARIF = frozenset({"nom", "prix", "est_gratuit", "ordre"})


def update_tarif(tarif_id: int, **kwargs) -> bool:
    """Met à jour les champs d'un tarif."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_TARIF
    if champs_invalides:
        logger.error("update_tarif: colonnes non autorisées : %s", champs_invalides)
        return False
    colonnes = ", ".join(f"{k} = ?" for k in kwargs)
    valeurs = list(kwargs.values()) + [tarif_id]
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE evenement_tarifs SET {colonnes} WHERE id = ?",
            valeurs,
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("update_tarif: %s", exc)
        return False
    finally:
        conn.close()


def delete_tarif(tarif_id: int) -> bool:
    """Supprime un tarif."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM evenement_tarifs WHERE id = ?", (tarif_id,))
        conn.commit()
        return True
    except Exception as exc:
        logger.error("delete_tarif: %s", exc)
        return False
    finally:
        conn.close()


# ── Ventes ───────────────────────────────────────────────────────────────────


def add_vente(
    evenement_id: int,
    date: str,
    canal: str,
    mode_paiement: str,
    nom_tireur: str | None,
    montant_total: float,
    frais_sumup: float,
    montant_net: float,
    commentaire: str | None,
) -> int:
    """Crée une vente et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_ventes
                (evenement_id, date, canal, mode_paiement, nom_tireur,
                 montant_total, frais_sumup, montant_net, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                date,
                canal,
                mode_paiement,
                nom_tireur,
                montant_total,
                frais_sumup,
                montant_net,
                commentaire,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_vente_ligne(
    vente_id: int,
    tarif_id: int,
    quantite: int,
    prix_unitaire: float,
) -> int:
    """Crée une ligne de vente et retourne son identifiant."""
    sous_total = quantite * prix_unitaire
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_vente_lignes
                (vente_id, tarif_id, quantite, prix_unitaire, sous_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            (vente_id, tarif_id, quantite, prix_unitaire, sous_total),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def add_billet(vente_ligne_id: int, numero: str, tarif_id: int) -> int:
    """Crée un billet numéroté et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_billets (vente_ligne_id, numero, tarif_id)
            VALUES (?, ?, ?)
            """,
            (vente_ligne_id, numero, tarif_id),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_ventes_evenement(evenement_id: int) -> list[dict]:
    """Retourne les ventes d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, evenement_id, date, canal, mode_paiement, nom_tireur,
                   montant_total, frais_sumup, montant_net, statut,
                   motif_annulation, commentaire, created_at
            FROM evenement_ventes
            WHERE evenement_id = ?
            ORDER BY date DESC, id DESC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lignes_vente(vente_id: int) -> list[dict]:
    """Retourne les lignes d'une vente avec les noms de tarifs."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT l.id, l.vente_id, l.tarif_id, t.nom AS tarif_nom,
                   l.quantite, l.prix_unitaire, l.sous_total
            FROM evenement_vente_lignes l
            JOIN evenement_tarifs t ON t.id = l.tarif_id
            WHERE l.vente_id = ?
            ORDER BY l.id ASC
            """,
            (vente_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def annuler_vente(vente_id: int, motif: str) -> bool:
    """Annule une vente et marque ses billets comme annulés."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE evenement_ventes SET statut = 'annule', motif_annulation = ? WHERE id = ?",
            (motif, vente_id),
        )
        conn.execute(
            """
            UPDATE evenement_billets SET statut = 'annule'
            WHERE vente_ligne_id IN (
                SELECT id FROM evenement_vente_lignes WHERE vente_id = ?
            )
            """,
            (vente_id,),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("annuler_vente: %s", exc)
        return False
    finally:
        conn.close()


def get_stats_billetterie(evenement_id: int) -> dict:
    """Retourne des statistiques de billetterie pour un événement."""
    conn = get_connection()
    try:
        # Totaux globaux (ventes valides seulement)
        totaux = conn.execute(
            """
            SELECT
                COUNT(*) AS nb_ventes,
                COALESCE(SUM(montant_total), 0) AS total_recette,
                COALESCE(SUM(montant_net), 0) AS total_net,
                COALESCE(SUM(frais_sumup), 0) AS total_frais
            FROM evenement_ventes
            WHERE evenement_id = ? AND statut = 'valide'
            """,
            (evenement_id,),
        ).fetchone()

        # Total billets émis
        nb_billets = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM evenement_billets b
            JOIN evenement_vente_lignes l ON l.id = b.vente_ligne_id
            JOIN evenement_ventes v ON v.id = l.vente_id
            WHERE v.evenement_id = ? AND b.statut = 'emis' AND v.statut = 'valide'
            """,
            (evenement_id,),
        ).fetchone()

        # Par tarif
        par_tarif = conn.execute(
            """
            SELECT t.nom AS tarif_nom,
                   COALESCE(SUM(l.quantite), 0) AS quantite,
                   COALESCE(SUM(l.sous_total), 0) AS sous_total
            FROM evenement_vente_lignes l
            JOIN evenement_tarifs t ON t.id = l.tarif_id
            JOIN evenement_ventes v ON v.id = l.vente_id
            WHERE v.evenement_id = ? AND v.statut = 'valide'
            GROUP BY t.id, t.nom
            ORDER BY quantite DESC
            """,
            (evenement_id,),
        ).fetchall()

        # Par canal
        par_canal = conn.execute(
            """
            SELECT canal, COUNT(*) AS nb, COALESCE(SUM(montant_total), 0) AS total
            FROM evenement_ventes
            WHERE evenement_id = ? AND statut = 'valide'
            GROUP BY canal
            """,
            (evenement_id,),
        ).fetchall()

        # Par mode de paiement
        par_mode = conn.execute(
            """
            SELECT mode_paiement, COUNT(*) AS nb,
                   COALESCE(SUM(montant_total), 0) AS total
            FROM evenement_ventes
            WHERE evenement_id = ? AND statut = 'valide'
            GROUP BY mode_paiement
            """,
            (evenement_id,),
        ).fetchall()

        return {
            "total_billets": nb_billets["n"] if nb_billets else 0,
            "nb_ventes": totaux["nb_ventes"] if totaux else 0,
            "total_recette": totaux["total_recette"] if totaux else 0.0,
            "total_net": totaux["total_net"] if totaux else 0.0,
            "total_frais": totaux["total_frais"] if totaux else 0.0,
            "par_tarif": [dict(r) for r in par_tarif],
            "par_canal": [dict(r) for r in par_canal],
            "par_mode_paiement": [dict(r) for r in par_mode],
        }
    finally:
        conn.close()


# ── Dépenses ─────────────────────────────────────────────────────────────────


def add_depense(
    evenement_id: int,
    libelle: str,
    montant: float,
    date: str,
    categorie: str | None,
    fournisseur_id: int | None,
    mode_paiement: str | None,
    commentaire: str | None,
    avance_par_membre_id: int | None = None,
    remboursement_statut: str = 'non_applicable',
    remboursement_date: str | None = None,
    remboursement_mode: str | None = None,
    remboursement_reference: str | None = None,
) -> int:
    """Crée une dépense et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_depenses
                (evenement_id, libelle, montant, date, categorie,
                 fournisseur_id, mode_paiement, commentaire, avance_par_membre_id,
                 remboursement_statut, remboursement_date, remboursement_mode, remboursement_reference)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                libelle,
                montant,
                date,
                categorie,
                fournisseur_id,
                mode_paiement,
                commentaire,
                avance_par_membre_id,
                remboursement_statut or 'non_applicable',
                remboursement_date,
                remboursement_mode,
                remboursement_reference,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_depenses_evenement(evenement_id: int) -> list[dict]:
    """Retourne les dépenses d'un événement avec nom du fournisseur."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.evenement_id, d.libelle, d.montant, d.date,
                   d.categorie, d.fournisseur_id,
                   f.nom AS fournisseur_nom,
                   d.mode_paiement, d.commentaire, d.tresorerie_id, d.created_at,
                   d.avance_par_membre_id, d.remboursement_statut, d.remboursement_date,
                   d.remboursement_mode, d.remboursement_reference,
                   m.nom AS avance_par_nom, m.prenom AS avance_par_prenom
            FROM evenement_depenses d
            LEFT JOIN fournisseurs f ON f.id = d.fournisseur_id
            LEFT JOIN membres m ON m.id = d.avance_par_membre_id
            WHERE d.evenement_id = ?
            ORDER BY d.date DESC, d.id DESC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


_COLONNES_DEPENSE = frozenset({
    "libelle", "montant", "date", "categorie",
    "fournisseur_id", "mode_paiement", "commentaire", "tresorerie_id",
    "avance_par_membre_id", "remboursement_statut", "remboursement_date",
    "remboursement_mode", "remboursement_reference",
})


def update_depense(depense_id: int, **kwargs) -> bool:
    """Met à jour les champs d'une dépense."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_DEPENSE
    if champs_invalides:
        logger.error("update_depense: colonnes non autorisées : %s", champs_invalides)
        return False
    colonnes = ", ".join(f"{k} = ?" for k in kwargs)
    valeurs = list(kwargs.values()) + [depense_id]
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE evenement_depenses SET {colonnes} WHERE id = ?",
            valeurs,
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("update_depense: %s", exc)
        return False
    finally:
        conn.close()


def delete_depense(depense_id: int) -> bool:
    """Supprime une dépense."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM evenement_depenses WHERE id = ?", (depense_id,))
        conn.commit()
        return True
    except Exception as exc:
        logger.error("delete_depense: %s", exc)
        return False
    finally:
        conn.close()


# ── Bénévoles ─────────────────────────────────────────────────────────────────


def add_benevole(
    evenement_id: int,
    membre_id: int | None,
    nom_externe: str | None,
    prenom_externe: str | None,
    role: str | None,
    heure_debut: str | None,
    heure_fin: str | None,
    statut: str,
    commentaire: str | None = None,
) -> int:
    """Crée un bénévole affecté à un événement et retourne son identifiant."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO evenement_benevoles
                (evenement_id, membre_id, nom_externe, prenom_externe,
                 role, heure_debut, heure_fin, statut, commentaire)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evenement_id,
                membre_id,
                nom_externe,
                prenom_externe,
                role,
                heure_debut,
                heure_fin,
                statut,
                commentaire,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


_COLONNES_BENEVOLE = frozenset({
    "membre_id", "nom_externe", "prenom_externe", "role",
    "heure_debut", "heure_fin", "statut", "remplacant_id", "commentaire",
})


def update_benevole(benevole_id: int, **kwargs) -> bool:
    """Met à jour les champs d'un bénévole."""
    if not kwargs:
        return False
    champs_invalides = set(kwargs) - _COLONNES_BENEVOLE
    if champs_invalides:
        logger.error("update_benevole: colonnes non autorisées : %s", champs_invalides)
        return False
    colonnes = ", ".join(f"{k} = ?" for k in kwargs)
    valeurs = list(kwargs.values()) + [benevole_id]
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE evenement_benevoles SET {colonnes} WHERE id = ?",
            valeurs,
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("update_benevole: %s", exc)
        return False
    finally:
        conn.close()


def delete_benevole(benevole_id: int) -> bool:
    """Supprime un bénévole d'un événement."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM evenement_benevoles WHERE id = ?", (benevole_id,))
        conn.commit()
        return True
    except Exception as exc:
        logger.error("delete_benevole: %s", exc)
        return False
    finally:
        conn.close()


def get_benevoles_evenement(evenement_id: int) -> list[dict]:
    """Retourne les bénévoles affectés à un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT b.id, b.evenement_id, b.membre_id,
                   m.nom AS membre_nom, m.prenom AS membre_prenom,
                   b.nom_externe, b.prenom_externe,
                   b.role, b.heure_debut, b.heure_fin,
                   b.statut, b.remplacant_id, b.commentaire
            FROM evenement_benevoles b
            LEFT JOIN membres m ON m.id = b.membre_id
            WHERE b.evenement_id = ?
            ORDER BY b.id ASC
            """,
            (evenement_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_stats_benevoles(evenement_id: int) -> dict:
    """Retourne des statistiques sur les bénévoles d'un événement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT statut, heure_debut, heure_fin
            FROM evenement_benevoles
            WHERE evenement_id = ?
            """,
            (evenement_id,),
        ).fetchall()

        total = len(rows)
        confirmes = sum(1 for r in rows if r["statut"] == "confirme")
        desistes = sum(1 for r in rows if r["statut"] == "desiste")

        total_minutes = 0
        for r in rows:
            if r["statut"] == "confirme" and r["heure_debut"] and r["heure_fin"]:
                try:
                    h1 = datetime.strptime(r["heure_debut"], "%H:%M")
                    h2 = datetime.strptime(r["heure_fin"], "%H:%M")
                    diff = (h2 - h1).seconds // 60
                    if diff > 0:
                        total_minutes += diff
                except ValueError:
                    pass

        return {
            "total": total,
            "confirmes": confirmes,
            "desistes": desistes,
            "total_heures": total_minutes / 60,
        }
    finally:
        conn.close()


# ── Paramètres ───────────────────────────────────────────────────────────────


def get_parametre(cle: str) -> str | None:
    """Retourne la valeur d'un paramètre ou None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT valeur FROM parametres WHERE cle = ?", (cle,)
        ).fetchone()
        return row["valeur"] if row else None
    finally:
        conn.close()


def set_parametre(cle: str, valeur: str) -> bool:
    """Insère ou met à jour un paramètre."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO parametres (cle, valeur) VALUES (?, ?)",
            (cle, valeur),
        )
        conn.commit()
        return True
    except Exception as exc:
        logger.error("set_parametre: %s", exc)
        return False
    finally:
        conn.close()
