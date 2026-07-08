"""Orchestrateur central des exports (PDF et Excel) pour les événements."""

from __future__ import annotations

from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


# ── Configuration association ─────────────────────────────────────────────────


@dataclass
class ConfigAsso:
    nom: str
    adresse: str
    telephone: str
    email: str
    logo_path: str  # chemin fichier ou ""


def get_config_asso() -> ConfigAsso:
    """Lit les paramètres association depuis la DB."""
    from db.models.evenements import get_parametre

    return ConfigAsso(
        nom=get_parametre("asso_nom") or "",
        adresse=get_parametre("asso_adresse") or "",
        telephone=get_parametre("asso_telephone") or "",
        email=get_parametre("asso_email") or "",
        logo_path=get_parametre("asso_logo_path") or "",
    )


# ── Exports PDF ───────────────────────────────────────────────────────────────


def export_bilan_evenement_pdf(evenement_id: int, chemin_sortie: str) -> bool:
    """Génère le PDF complet du bilan d'un événement.

    Returns:
        True si succès, False sinon.
    """
    try:
        from core.pdf_generator import PdfEvenement

        config = get_config_asso()
        gen = PdfEvenement(evenement_id, config)
        return gen.generer(chemin_sortie)
    except Exception as exc:
        logger.error("export_bilan_evenement_pdf: %s", exc)
        return False


def export_pv_tirage_pdf(evenement_id: int, chemin_sortie: str) -> bool:
    """Génère le PV de tirage tombola en PDF.

    Returns:
        True si succès, False sinon.
    """
    try:
        from core.pdf_generator import PvTirage

        config = get_config_asso()
        gen = PvTirage(evenement_id, config)
        return gen.generer(chemin_sortie)
    except Exception as exc:
        logger.error("export_pv_tirage_pdf: %s", exc)
        return False


def export_liste_benevoles_pdf(evenement_id: int, chemin_sortie: str) -> bool:
    """Génère la liste des bénévoles en PDF.

    Returns:
        True si succès, False sinon.
    """
    try:
        from core.pdf_generator import ListeBenevolesPdf

        config = get_config_asso()
        gen = ListeBenevolesPdf(evenement_id, config)
        return gen.generer(chemin_sortie)
    except Exception as exc:
        logger.error("export_liste_benevoles_pdf: %s", exc)
        return False


# ── Exports Excel ─────────────────────────────────────────────────────────────


def export_bilan_evenement_excel(evenement_id: int, chemin_sortie: str) -> bool:
    """Génère le classeur Excel complet d'un événement.

    Returns:
        True si succès, False sinon.
    """
    try:
        from core.excel_generator import ExcelEvenement

        config = get_config_asso()
        gen = ExcelEvenement(evenement_id, config)
        return gen.generer(chemin_sortie)
    except Exception as exc:
        logger.error("export_bilan_evenement_excel: %s", exc)
        return False


def export_liste_benevoles_excel(evenement_id: int, chemin_sortie: str) -> bool:
    """Génère la liste des bénévoles en Excel.

    Returns:
        True si succès, False sinon.
    """
    try:
        from core.excel_generator import ExcelBenevoles

        config = get_config_asso()
        gen = ExcelBenevoles(evenement_id, config)
        return gen.generer(chemin_sortie)
    except Exception as exc:
        logger.error("export_liste_benevoles_excel: %s", exc)
        return False


# ── Utilitaires ───────────────────────────────────────────────────────────────


def slugifier_nom(nom: str) -> str:
    """Convertit un nom en slug sûr pour les noms de fichiers.

    Minuscules, espaces → underscores, suppression des accents et caractères spéciaux.
    """
    import re
    import unicodedata

    # Normalisation unicode → suppression accents
    nfd = unicodedata.normalize("NFD", nom)
    sans_accents = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Minuscules
    slug = sans_accents.lower()
    # Espaces → underscores
    slug = slug.replace(" ", "_")
    # Suppression des caractères non alphanumériques (sauf underscore)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    # Suppression des underscores multiples
    slug = re.sub(r"_+", "_", slug)
    slug = slug.strip("_")
    return slug or "evenement"


def generer_nom_fichier(nom_evenement: str, date: str, extension: str) -> str:
    """Génère un nom de fichier normalisé pour l'export.

    Format : bilan_{slug}_{date}.{extension}
    """
    slug = slugifier_nom(nom_evenement)
    return f"bilan_{slug}_{date}.{extension}"
