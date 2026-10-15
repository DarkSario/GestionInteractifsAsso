"""Tests du module de diagnostic en lecture seule."""

from utils import diagnostic


def test_points_entree_presents():
    assert all(ok for _, _, ok in diagnostic.verifier_points_entree())


def test_coherence_regles():
    assert all(ok for _, ok in diagnostic.verifier_coherence_regles())


def test_rapport_genere():
    rapport, anomalies = diagnostic.generer_rapport()
    assert "Anomalies détectées" in rapport
    assert isinstance(anomalies, int)
