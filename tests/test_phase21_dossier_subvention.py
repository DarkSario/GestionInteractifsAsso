"""Tests Phase 21 — Logo, Thème exports, Graphiques, Dossier Subvention PDF/Excel."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


# ── Logo ──────────────────────────────────────────────────────────────────────


def test_get_logo_path_absent():
    """get_logo_path() retourne None si le fichier logo n'existe pas."""
    from core.logo import get_logo_path, _LOGO_PATH

    # Sauvegarde et supprime le logo s'il existe
    backup = None
    if _LOGO_PATH.exists():
        backup = _LOGO_PATH.with_suffix(".bak")
        shutil.copy2(_LOGO_PATH, backup)
        _LOGO_PATH.unlink()

    try:
        assert get_logo_path() is None
    finally:
        if backup and backup.exists():
            shutil.copy2(backup, _LOGO_PATH)
            backup.unlink()


def test_set_logo_fichier_inexistant():
    """set_logo() retourne False si le fichier source n'existe pas."""
    from core.logo import set_logo

    assert set_logo("/chemin/inexistant/logo.png") is False


def test_set_logo_source_vide():
    """set_logo() retourne False si le chemin est vide."""
    from core.logo import set_logo

    assert set_logo("") is False


def test_set_logo_et_get_logo_path(db_conn, tmp_path):
    """set_logo() copie le fichier et get_logo_path() le retrouve."""
    from core.logo import set_logo, get_logo_path, _LOGO_PATH, supprimer_logo

    # Crée un PNG minimal (1×1 pixel)
    png_minimal = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    source = tmp_path / "logo_test.png"
    source.write_bytes(png_minimal)

    result = set_logo(str(source))
    assert result is True
    assert get_logo_path() is not None
    assert Path(get_logo_path()).exists()

    # Nettoyage
    supprimer_logo()


def test_supprimer_logo_sans_logo(db_conn):
    """supprimer_logo() retourne True même si aucun logo n'est présent."""
    from core.logo import supprimer_logo, _LOGO_PATH

    backup = None
    if _LOGO_PATH.exists():
        backup = _LOGO_PATH.with_suffix(".bak")
        shutil.copy2(_LOGO_PATH, backup)
        _LOGO_PATH.unlink()

    try:
        assert supprimer_logo() is True
    finally:
        if backup and backup.exists():
            shutil.copy2(backup, _LOGO_PATH)
            backup.unlink()


def test_get_logo_config_defaults(db_conn):
    """get_logo_config() retourne les valeurs par défaut sans configuration."""
    from core.logo import get_logo_config

    config = get_logo_config()
    assert "position" in config
    assert "taille" in config
    assert config["position"] in ("gauche", "centre", "droite")
    assert config["taille"] in ("petite", "moyenne", "grande")


def test_set_logo_config(db_conn):
    """set_logo_config() met à jour position et taille."""
    from core.logo import set_logo_config, get_logo_config

    result = set_logo_config(position="centre", taille="grande")
    assert result is True
    config = get_logo_config()
    assert config["position"] == "centre"
    assert config["taille"] == "grande"


# ── Thème exports ──────────────────────────────────────────────────────────────


def test_get_theme_export_defaults(db_conn):
    """get_theme_export() retourne des valeurs par défaut valides."""
    from core.theme_export import get_theme_export

    theme = get_theme_export()
    assert "couleur_principale" in theme
    assert "couleur_secondaire" in theme
    assert "police_titres" in theme
    assert "style_tableaux" in theme
    assert theme["couleur_principale"].startswith("#")


def test_set_theme_export_valide(db_conn):
    """set_theme_export() accepte les valeurs valides."""
    from core.theme_export import set_theme_export, get_theme_export

    set_theme_export(couleur_principale="#FF5500", style_tableaux="classique")
    theme = get_theme_export()
    assert theme["couleur_principale"] == "#FF5500"
    assert theme["style_tableaux"] == "classique"


def test_set_theme_export_couleur_invalide(db_conn):
    """set_theme_export() ignore les couleurs au mauvais format."""
    from core.theme_export import set_theme_export, get_couleur_principale

    couleur_avant = get_couleur_principale()
    set_theme_export(couleur_principale="rouge")  # invalide
    assert get_couleur_principale() == couleur_avant


def test_set_theme_export_style_invalide(db_conn):
    """set_theme_export() ignore les styles inconnus."""
    from core.theme_export import set_theme_export, get_theme_export

    set_theme_export(style_tableaux="futuriste")  # invalide
    theme = get_theme_export()
    assert theme["style_tableaux"] in ("moderne", "classique", "minimaliste")


def test_get_couleur_principale_et_secondaire(db_conn):
    """get_couleur_principale/secondaire retournent des hex valides."""
    import re
    from core.theme_export import get_couleur_principale, get_couleur_secondaire

    regex = re.compile(r"^#[0-9A-Fa-f]{6}$")
    assert regex.match(get_couleur_principale())
    assert regex.match(get_couleur_secondaire())


# ── Graphiques ─────────────────────────────────────────────────────────────────


def test_graphique_camembert(db_conn):
    """graphique_camembert_rl() retourne un objet reportlab non nul."""
    from core.graphiques import graphique_camembert_rl

    donnees = [("Recettes événements", 3000.0), ("Cotisations", 500.0), ("Dons", 200.0)]
    result = graphique_camembert_rl(donnees, titre="Répartition des recettes")
    assert result is not None


def test_graphique_barres(db_conn):
    """graphique_barres_rl() retourne un objet reportlab non nul."""
    from core.graphiques import graphique_barres_rl

    donnees = [("Jan", 100.0, 80.0), ("Fév", 200.0, 150.0), ("Mar", 150.0, 120.0)]
    result = graphique_barres_rl(donnees, titre="Recettes vs Dépenses")
    assert result is not None


def test_graphique_courbe(db_conn):
    """graphique_courbe_rl() retourne un objet reportlab non nul."""
    from core.graphiques import graphique_courbe_rl

    donnees = [("Jan", 1000.0), ("Fév", 1200.0), ("Mar", 900.0), ("Avr", 1500.0)]
    result = graphique_courbe_rl(donnees, titre="Évolution du solde")
    assert result is not None


def test_graphique_camembert_vide(db_conn):
    """graphique_camembert_rl() gère les données vides sans lever d'exception."""
    from core.graphiques import graphique_camembert_rl

    result = graphique_camembert_rl([], titre="Vide")
    # Ne doit pas lever d'exception; le résultat peut être None ou un élément vide
    assert result is not None or result is None  # pas d'exception = succès


# ── Excel Dossier Subvention ──────────────────────────────────────────────────


def test_excel_dossier_subvention_genere_fichier(db_conn, tmp_path):
    """ExcelDossierSubvention.generer() crée un fichier Excel."""
    from core.excel_dossier_subvention import ExcelDossierSubvention

    gen = ExcelDossierSubvention(
        periode="2025-2026",
        type_periode="scolaire",
        organisateur="Association Interactifs",
        objet="Aide au fonctionnement",
        montant_demande=2000.0,
    )
    chemin = str(tmp_path / "dossier_test.xlsx")
    result = gen.generer(chemin)
    assert result is True
    assert os.path.isfile(chemin)
    assert os.path.getsize(chemin) > 0


def test_excel_dossier_subvention_annee_civile(db_conn, tmp_path):
    """ExcelDossierSubvention.generer() fonctionne avec une période civile."""
    from core.excel_dossier_subvention import ExcelDossierSubvention

    gen = ExcelDossierSubvention(
        periode="2025",
        type_periode="civile",
        organisateur="Association Interactifs",
        objet="Projet culturel",
        montant_demande=1500.0,
    )
    chemin = str(tmp_path / "dossier_civil.xlsx")
    result = gen.generer(chemin)
    assert result is True
    assert os.path.isfile(chemin)


def test_excel_dossier_subvention_onglets(db_conn, tmp_path):
    """ExcelDossierSubvention produit un classeur avec plusieurs onglets."""
    import openpyxl
    from core.excel_dossier_subvention import ExcelDossierSubvention

    gen = ExcelDossierSubvention(periode="2025-2026", type_periode="scolaire")
    chemin = str(tmp_path / "dossier_onglets.xlsx")
    gen.generer(chemin)

    wb = openpyxl.load_workbook(chemin)
    assert len(wb.sheetnames) >= 3  # Au moins Résumé, Trésorerie, Adhérents


# ── PDF Dossier Subvention ─────────────────────────────────────────────────────


def test_pdf_dossier_subvention_genere_fichier(db_conn, tmp_path):
    """PdfDossierSubvention.generer() crée un fichier PDF."""
    from core.pdf_dossier_subvention import PdfDossierSubvention

    gen = PdfDossierSubvention(
        periode="2025-2026",
        type_periode="scolaire",
        organisateur="Association Interactifs",
        objet="Aide au fonctionnement",
        montant_demande=2000.0,
    )
    chemin = str(tmp_path / "dossier_test.pdf")
    result = gen.generer(chemin)
    assert result is True
    assert os.path.isfile(chemin)
    assert os.path.getsize(chemin) > 0


def test_pdf_dossier_subvention_sections_selectionnees(db_conn, tmp_path):
    """PdfDossierSubvention respecte les sections activées/désactivées."""
    from core.pdf_dossier_subvention import PdfDossierSubvention

    sections = {
        "garde": True,
        "presentation": True,
        "adherents": False,
        "evenements": False,
        "resume_financier": True,
        "projet": False,
        "signatures": False,
    }
    gen = PdfDossierSubvention(
        periode="2025-2026",
        sections=sections,
    )
    chemin = str(tmp_path / "dossier_minimal.pdf")
    result = gen.generer(chemin)
    assert result is True
    assert os.path.isfile(chemin)


def test_pdf_dossier_subvention_periode_civile(db_conn, tmp_path):
    """PdfDossierSubvention fonctionne avec une période civile."""
    from core.pdf_dossier_subvention import PdfDossierSubvention

    gen = PdfDossierSubvention(
        periode="2025",
        type_periode="civile",
        montant_demande=500.0,
    )
    chemin = str(tmp_path / "dossier_civil.pdf")
    result = gen.generer(chemin)
    assert result is True
    assert os.path.isfile(chemin)


def test_pdf_dossier_subvention_calcul_periode_scolaire(db_conn):
    """_calcul_periode retourne les bonnes dates pour l'année scolaire."""
    from core.pdf_dossier_subvention import PdfDossierSubvention

    gen = PdfDossierSubvention(periode="2025-2026", type_periode="scolaire")
    assert gen._date_debut == "2025-09-01"
    assert gen._date_fin == "2026-08-31"


def test_pdf_dossier_subvention_calcul_periode_civile(db_conn):
    """_calcul_periode retourne les bonnes dates pour l'année civile."""
    from core.pdf_dossier_subvention import PdfDossierSubvention

    gen = PdfDossierSubvention(periode="2025", type_periode="civile")
    assert gen._date_debut == "2025-01-01"
    assert gen._date_fin == "2025-12-31"
