"""Couche modèles de la base de données."""


def _build_nom_complet(prenom: str | None, nom: str | None, defaut: str = "Inconnu") -> str:
    """Formate un nom complet à partir du prénom et du nom (chaînes ou None)."""
    return f"{prenom or ''} {nom or ''}".strip() or defaut
