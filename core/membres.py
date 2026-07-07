"""Logique métier pour le module Adhérents."""

import re

STATUTS_DISPONIBLES: list[str] = [
    "Président(e)",
    "Vice-Président(e)",
    "Secrétaire",
    "Secrétaire Adjoint(e)",
    "Trésorier(ère)",
    "Trésorier(ère) Adjoint(e)",
    "Membre",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_statuts_disponibles() -> list[str]:
    """Retourne la liste des statuts possibles pour un membre.

    Returns:
        Liste ordonnée des statuts disponibles.
    """
    return list(STATUTS_DISPONIBLES)


def valider_membre(
    nom: str,
    prenom: str,
    email: str,
    telephone: str,  # noqa: ARG001  (non utilisé dans la validation actuelle)
    statut: str,
    date_adhesion: str,  # noqa: ARG001
) -> list[tuple[str, str]]:
    """Valide les données d'un membre et retourne la liste des erreurs.

    Args:
        nom: Nom de famille.
        prenom: Prénom.
        email: Adresse e-mail (optionnelle).
        telephone: Numéro de téléphone (optionnel, non validé).
        statut: Statut dans l'association.
        date_adhesion: Date d'adhésion (optionnelle, non validée au format ici).

    Returns:
        Liste de tuples ``(champ, message)``. Vide si les données sont valides.
        Le champ correspond à la clé du formulaire (ex. ``"nom"``, ``"email"``).
    """
    erreurs: list[tuple[str, str]] = []

    if not nom or not nom.strip():
        erreurs.append(("nom", "Le nom est obligatoire."))

    if not prenom or not prenom.strip():
        erreurs.append(("prenom", "Le prénom est obligatoire."))

    if email and email.strip() and not _EMAIL_RE.match(email.strip()):
        erreurs.append(("email", "L'adresse e-mail n'est pas valide."))

    if not statut or statut not in STATUTS_DISPONIBLES:
        erreurs.append(("statut", "Le statut est obligatoire."))

    return erreurs
