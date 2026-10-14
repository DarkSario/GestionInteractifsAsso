"""Tests PR12 : totaux événement, comptes du Bilan AG, schéma de référence."""

from __future__ import annotations

import pytest


@pytest.fixture
def db_fin(tmp_db):
    import db.connection as db_module
    from db.migrations.runner import run_migrations

    db_module.set_db_file(str(tmp_db))
    run_migrations()
    yield db_module
    db_module.set_db_file("")


def test_bilan_ag_affiche_comptes_bancaires(db_fin):
    from core.bilan_ag import collecter_donnees_bilan

    conn = db_fin.get_connection()
    conn.execute("INSERT INTO comptes_bancaires (nom, solde_initial, actif) VALUES ('Compte Test PR12', 123.5, 1)")
    conn.commit()
    conn.close()
    tableau = collecter_donnees_bilan(1)["tableau_comptes"]
    assert "Compte Test PR12" in tableau
    assert "123,50" in tableau


def test_bilan_ag_erreur_distincte_de_aucune_donnee(db_fin, monkeypatch):
    import db.models.tresorerie as treso
    from core.bilan_ag import collecter_donnees_bilan

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(treso, "get_all_comptes", boom)
    tableau = collecter_donnees_bilan(1)["tableau_comptes"]
    assert "erreur" in tableau
    assert "Aucun compte" not in tableau


def test_bilan_ag_valorise_stock_avec_le_schema_courant(db_fin):
    from core.bilan_ag import collecter_donnees_bilan

    _exec(
        db_fin,
        "INSERT INTO stock (nom, prix_achat, quantite) VALUES ('Article bilan', 2.5, 4)",
    )
    donnees = collecter_donnees_bilan(1)
    assert "10,00" in donnees["valeur_stock"]


def test_totaux_evenement_liste_alignes_sur_fiche(db_fin):
    from core.caisses_evenement import calculer_bilan_complet_evenement
    from db.models.evenements import get_all_evenements

    conn = db_fin.get_connection()
    conn.execute("INSERT INTO evenements (id, nom, date_debut) VALUES (1, 'Fete', '2026-05-01')")
    conn.execute(
        "INSERT INTO evenement_stands (evenement_id, nom_stand, type_stand, montant_location, statut)"
        " VALUES (1, 'S1', 'location', 40, 'confirme')"
    )
    conn.commit()
    conn.close()
    bilan = calculer_bilan_complet_evenement(1)
    ev = [e for e in get_all_evenements() if e["id"] == 1][0]
    assert ev["total_recettes"] == bilan["total_recettes"] == 40.0
    assert ev["total_depenses"] == bilan["total_depenses"]


def test_dashboard_explicite_son_perimetre(db_fin):
    from db.models.dashboard import PERIMETRE_RECETTES_MENSUELLES, get_recettes_depenses_mois

    assert get_recettes_depenses_mois(2026, 5)["perimetre_recettes"] == PERIMETRE_RECETTES_MENSUELLES


def test_schema_reference_aligne_sur_migration(db_fin):
    from db.schema import TABLES

    conn = db_fin.get_connection()
    try:
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'tresorerie_operations'"
        ).fetchone()["sql"]
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert "rapproche" in sql
    assert any("rapproche" in c for c in TABLES["tresorerie_operations"])
    assert "comptes_bancaires" in TABLES and "comptes_bancaires" in tables
    assert "tresorerie_comptes" not in tables


# ── PR15 : Bilan AG cohérent sur la période ──────────────────────────────────


def _exec(db_fin, sql, params=()):
    conn = db_fin.get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _textes_section(elements):
    from reportlab.platypus import KeepTogether, Paragraph, Table

    out = []

    def visit(el):
        if isinstance(el, KeepTogether):
            for sub in el._content:
                visit(sub)
        elif isinstance(el, Table):
            for row in el._cellvalues:
                out.extend(str(c) for c in row)
        elif isinstance(el, Paragraph):
            out.append(el.text)

    for el in elements:
        visit(el)
    return "\n".join(out)


def test_soldes_comptes_a_la_fin_de_periode(db_fin):
    from db.models.tresorerie import get_all_comptes, get_solde_compte

    cid = _exec(db_fin, "INSERT INTO comptes_bancaires (nom, solde_initial, actif) VALUES ('C', 100, 1)")
    for date, montant in (("2025-10-01", 50), ("2026-12-01", 500)):
        _exec(
            db_fin,
            "INSERT INTO tresorerie_operations (compte_id, date_operation, type_operation, montant, statut, libelle) "
            "VALUES (?, ?, 'recette', ?, 'valide', 'x')",
            (cid, date, montant),
        )
    assert get_solde_compte(cid, date_fin="2026-08-31") == 150.0
    assert get_solde_compte(cid) == 650.0
    assert get_all_comptes(date_fin="2026-08-31")[0]["solde_actuel"] == 150.0


def test_pdf_ag_resume_utilise_solde_fin_periode(db_fin):
    from core.pdf_bilan_ag import PdfBilanAG

    cid = _exec(db_fin, "INSERT INTO comptes_bancaires (nom, solde_initial, actif) VALUES ('C', 100, 1)")
    _exec(
        db_fin,
        "INSERT INTO tresorerie_operations (compte_id, date_operation, type_operation, montant, statut, libelle) "
        "VALUES (?, '2026-12-01', 'recette', 500, 'valide', 'x')",
        (cid,),
    )
    texte = _textes_section(PdfBilanAG("2025-2026")._section_resume_financier())
    assert "100,00" in texte and "600,00" not in texte


def test_pdf_ag_reconcilie_soldes_et_flux_de_periode(db_fin):
    from core.pdf_bilan_ag import PdfBilanAG

    cid = _exec(db_fin, "INSERT INTO comptes_bancaires (nom, solde_initial, actif) VALUES ('C', 100, 1)")
    for date, type_operation, montant in (
        ("2025-08-31", "recette", 20),
        ("2025-10-01", "recette", 50),
        ("2026-01-01", "depense", 15),
        ("2026-12-01", "recette", 500),
    ):
        _exec(
            db_fin,
            "INSERT INTO tresorerie_operations (compte_id, date_operation, type_operation, montant, statut, libelle) "
            "VALUES (?, ?, ?, ?, 'valide', 'x')",
            (cid, date, type_operation, montant),
        )
    texte = _textes_section(PdfBilanAG("2025-2026")._section_resume_financier())
    assert "120,00" in texte
    assert "50,00" in texte
    assert "15,00" in texte
    assert "35,00" in texte
    assert "155,00" in texte
    assert "600,00" not in texte


def test_pdf_ag_evenements_annee_scolaire_complete(db_fin):
    from core.pdf_bilan_ag import PdfBilanAG

    _exec(db_fin, "INSERT INTO evenements (nom, date_debut, date_fin) VALUES ('Fête automne', '2025-10-10', '2025-10-10')")
    _exec(db_fin, "INSERT INTO evenements (nom, date_debut, date_fin) VALUES ('Kermesse juin', '2026-06-20', '2026-06-20')")
    _exec(db_fin, "INSERT INTO evenements (nom, date_debut, date_fin) VALUES ('Hors période', '2026-09-15', '2026-09-15')")
    _exec(db_fin, "INSERT INTO evenements (nom, date_debut, date_fin) VALUES ('Événement long', '2025-01-01', '2026-12-31')")
    texte = _textes_section(PdfBilanAG("2025-2026")._section_evenements())
    assert "Fête automne" in texte and "Kermesse juin" in texte and "Événement long" in texte
    assert "Hors période" not in texte
    assert "ne s'ajoutent pas aux" in texte


def test_pdf_ag_dons_filtres_sur_toute_la_periode(db_fin):
    from core.pdf_bilan_ag import PdfBilanAG

    conn = db_fin.get_connection()
    try:
        for nom, date_don in (
            ("Don automne", "2025-09-01"),
            ("Don été", "2026-08-31"),
            ("Don avant", "2025-08-31"),
            ("Don après", "2026-09-01"),
        ):
            conn.execute(
                "INSERT INTO dons (date_don, type_donateur, donateur_nom, nature_don, montant) "
                "VALUES (?, 'particulier', ?, 'argent', 10)",
                (date_don, nom),
            )
        conn.commit()
    finally:
        conn.close()
    texte = _textes_section(PdfBilanAG("2025-2026")._section_dons())
    assert "Don automne" in texte and "Don été" in texte
    assert "Don avant" not in texte and "Don après" not in texte
    assert "20,00" in texte


def test_pdf_ag_buvette_sans_troncature_et_periode_complete(db_fin):
    from core.pdf_bilan_ag import PdfBilanAG

    conn = db_fin.get_connection()
    try:
        for i in range(1100):
            conn.execute(
                "INSERT INTO evenements (nom, date_debut) VALUES (?, '2026-03-01')", (f"E{i}",)
            )
            conn.execute(
                "INSERT INTO recettes_buvette (evenement_id, date, total_brut, total_fond_caisse, recette_nette) "
                "VALUES (?, '2026-03-01', 2, 0, 1)",
                (i + 1,),
            )
        eid = conn.execute("INSERT INTO evenements (nom, date_debut) VALUES ('Hors', '2025-03-01')").lastrowid
        conn.execute(
            "INSERT INTO recettes_buvette (evenement_id, date, total_brut, total_fond_caisse, recette_nette) "
            "VALUES (?, '2025-03-01', 999, 0, 999)",
            (eid,),
        )
        conn.commit()
    finally:
        conn.close()
    texte = _textes_section(PdfBilanAG("2025-2026")._section_buvette())
    assert "1100" in texte
    assert "1 100,00" in texte.replace("\u202f", " ").replace("\xa0", " ") or "1100,00" in texte


def test_generer_bilan_ag_delegue_au_generateur_pdf_unique(db_fin, monkeypatch, tmp_path):
    import core.exports as exports
    from core.bilan_ag import generer_bilan_ag

    appels = []
    monkeypatch.setattr(exports, "export_bilan_ag_pdf", lambda *a, **k: appels.append((a, k)) or True)
    ex_id = _exec(
        db_fin,
        "INSERT INTO exercices (nom, date_debut, date_fin) VALUES ('2025-2026', '2025-09-01', '2026-08-31')",
    )
    res = generer_bilan_ag(ex_id, str(tmp_path / "x.pdf"))
    assert res["succes"] is True
    assert appels and appels[0][1]["date_debut"] == "2025-09-01"
    assert appels[0][1]["date_fin"] == "2026-08-31"


def test_schema_reference_exercices_et_evenements(db_fin):
    from db.schema import TABLES

    conn = db_fin.get_connection()
    try:
        for table in (
            "exercices",
            "evenements",
            "comptes_bancaires",
            "tresorerie_operations",
            "evenement_caisses",
            "evenement_caisse_lignes",
        ):
            reel = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            doc = {c.split()[0] for c in TABLES[table]}
            assert reel == doc, (table, reel ^ doc)
    finally:
        conn.close()
