"""Diagnostic non intrusif (lecture seule) des points critiques du dépôt.

Usage : ``python -m utils.diagnostic``

Ne modifie ni la base ni les fichiers ; analyse statique du code source.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

POINTS_ENTREE = {
    "Clôture (logique)": "core/cloture.py",
    "Clôture (modèle)": "db/models/cloture.py",
    "Clôture (UI)": "ui/modules/tresorerie/cloture.py",
    "Écritures de trésorerie": "db/models/tresorerie.py",
    "Bilan AG (données)": "core/bilan_ag.py",
    "Bilan AG (PDF)": "core/pdf_bilan_ag.py",
    "Bilan AG (UI export)": "ui/modules/exports/bilan_ag.py",
    "Exports": "core/exports.py",
    "Règles financières (source de vérité)": "utils/finance_rules.py",
}

# Modules de rapport/total qui doivent s'appuyer sur utils.finance_rules.
MODULES_RAPPORTS = (
    "core/bilan_ag.py",
    "core/exports.py",
    "core/cloture.py",
    "db/models/tresorerie.py",
)

FONCTIONS_ATTENDUES = {
    "utils.finance_rules": ("sql_filtre_comptable", "totaux_operations", "est_operation_comptable"),
    "core.cloture": ("valider_cloture", "calculer_solde_cloture"),
    "core.bilan_ag": ("collecter_donnees_bilan", "generer_bilan_ag"),
}


def verifier_points_entree(racine: Path = RACINE) -> list[tuple[str, str, bool]]:
    """Retourne (libellé, chemin, présent) pour chaque point d'entrée."""
    return [(nom, chemin, (racine / chemin).is_file()) for nom, chemin in POINTS_ENTREE.items()]


def verifier_source_verite(racine: Path = RACINE) -> list[tuple[str, bool]]:
    """Indique quels modules de rapport référencent utils.finance_rules."""
    resultats = []
    for chemin in MODULES_RAPPORTS:
        fichier = racine / chemin
        texte = fichier.read_text(encoding="utf-8") if fichier.is_file() else ""
        resultats.append((chemin, "finance_rules" in texte))
    return resultats


def verifier_fonctions() -> list[tuple[str, str, bool]]:
    """Vérifie que les fonctions critiques sont importables."""
    resultats = []
    for module, noms in FONCTIONS_ATTENDUES.items():
        try:
            mod = importlib.import_module(module)
        except Exception:  # diagnostic : ne jamais bloquer
            mod = None
        for nom in noms:
            resultats.append((module, nom, mod is not None and callable(getattr(mod, nom, None))))
    return resultats


def verifier_coherence_regles() -> list[tuple[str, bool]]:
    """Contrôle de cohérence des totaux sur un jeu d'opérations fictif."""
    from utils import finance_rules as fr

    ops = [
        {"statut": "valide", "type_operation": "recette", "montant": 100.0, "source_module": None},
        {"statut": "rapproche", "type_operation": "depense", "montant": 40.0, "source_module": None},
        {"statut": "valide", "type_operation": "recette", "montant": 50.0, "source_module": "remise_cheque"},
    ]
    comptables = [o for o in ops if fr.est_operation_comptable(o)]
    return [
        ("Les sources non comptables sont exclues", len(comptables) == 2),
        ("Les statuts valide et rapproche sont comptés", {o["statut"] for o in comptables} == {"valide", "rapproche"}),
    ]


def generer_rapport() -> tuple[str, int]:
    """Construit le rapport texte et le nombre d'anomalies détectées."""
    lignes: list[str] = []
    anomalies = 0

    def section(titre: str, items) -> None:
        nonlocal anomalies
        lignes.append(f"\n== {titre} ==")
        for libelle, ok in items:
            lignes.append(f"  [{'OK' if ok else 'KO'}] {libelle}")
            anomalies += 0 if ok else 1

    section("Points d'entrée (clôture, écritures, Bilan AG, exports)",
            [(f"{n} : {c}", ok) for n, c, ok in verifier_points_entree()])
    section("Source de vérité des rapports (utils.finance_rules)",
            [(f"{c} référence finance_rules", ok) for c, ok in verifier_source_verite()])
    section("Fonctions critiques importables",
            [(f"{m}.{n}", ok) for m, n, ok in verifier_fonctions()])
    section("Cohérence des règles de totaux", verifier_coherence_regles())
    lignes.append(f"\nAnomalies détectées : {anomalies}")
    return "\n".join(lignes), anomalies


def main() -> int:
    rapport, anomalies = generer_rapport()
    print(rapport)
    return 1 if anomalies else 0


if __name__ == "__main__":
    sys.exit(main())
