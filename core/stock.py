"""Logique métier pour le module Stock."""

TYPES_MOUVEMENTS: list[str] = [
    "Entrée — Achat",
    "Entrée — Don/Retour",
    "Sortie — Utilisation",
    "Sortie — Casse/Perte",
    "Inventaire",
]

TYPES_ENTREE: list[str] = [t for t in TYPES_MOUVEMENTS if t.startswith("Entrée")]
TYPES_SORTIE: list[str] = [t for t in TYPES_MOUVEMENTS if t.startswith("Sortie")]


def get_types_mouvements() -> list[str]:
    """Retourne la liste des types de mouvements disponibles."""
    return list(TYPES_MOUVEMENTS)


def is_type_achat(type_mouvement: str) -> bool:
    """Indique si le type de mouvement nécessite les informations achat."""
    return type_mouvement == "Entrée — Achat"


def is_type_sortie_utilisation(type_mouvement: str) -> bool:
    """Indique si le type de mouvement peut être lié à un événement."""
    return type_mouvement == "Sortie — Utilisation"


def valider_article(
    nom: str,
    categorie_id: int | None,
    unite_id: int | None,
    quantite_str: str,
    seuil_alerte_str: str,
    prix_achat_str: str,
) -> list[tuple[str, str]]:
    """Valide les données d'un article et retourne la liste des erreurs.

    Args:
        nom: Nom de l'article.
        categorie_id: Identifiant de la catégorie sélectionnée.
        unite_id: Identifiant de l'unité sélectionnée.
        quantite_str: Quantité initiale sous forme de chaîne.
        seuil_alerte_str: Seuil d'alerte sous forme de chaîne.
        prix_achat_str: Prix d'achat sous forme de chaîne.

    Returns:
        Liste de tuples ``(champ, message)``. Vide si les données sont valides.
    """
    erreurs: list[tuple[str, str]] = []

    if not nom or not nom.strip():
        erreurs.append(("nom", "Le nom est obligatoire."))

    if categorie_id is None:
        erreurs.append(("categorie_id", "La catégorie est obligatoire."))

    if unite_id is None:
        erreurs.append(("unite_id", "L'unité est obligatoire."))

    if quantite_str.strip():
        try:
            q = int(quantite_str.strip())
            if q < 0:
                erreurs.append(("quantite", "La quantité ne peut pas être négative."))
        except ValueError:
            erreurs.append(("quantite", "La quantité doit être un nombre entier."))

    if seuil_alerte_str.strip():
        try:
            s = int(seuil_alerte_str.strip())
            if s < 0:
                erreurs.append(("seuil_alerte", "Le seuil ne peut pas être négatif."))
        except ValueError:
            erreurs.append(("seuil_alerte", "Le seuil doit être un nombre entier."))

    if prix_achat_str.strip():
        try:
            p = float(prix_achat_str.strip().replace(",", "."))
            if p < 0:
                erreurs.append(("prix_achat", "Le prix ne peut pas être négatif."))
        except ValueError:
            erreurs.append(("prix_achat", "Le prix doit être un nombre décimal."))

    return erreurs


def valider_mouvement(
    type_mouvement: str,
    date_str: str,
    quantite_str: str,
    prix_unitaire_str: str,
) -> list[tuple[str, str]]:
    """Valide les données d'un mouvement et retourne la liste des erreurs.

    Args:
        type_mouvement: Type du mouvement.
        date_str: Date du mouvement.
        quantite_str: Quantité du mouvement.
        prix_unitaire_str: Prix unitaire (pour les achats).

    Returns:
        Liste de tuples ``(champ, message)``. Vide si les données sont valides.
    """
    erreurs: list[tuple[str, str]] = []

    if not type_mouvement or type_mouvement not in TYPES_MOUVEMENTS:
        erreurs.append(("type_mouvement", "Le type de mouvement est obligatoire."))

    if not date_str or not date_str.strip():
        erreurs.append(("date", "La date est obligatoire."))

    if not quantite_str.strip():
        erreurs.append(("quantite", "La quantité est obligatoire."))
    else:
        try:
            q = int(quantite_str.strip())
            if q <= 0:
                erreurs.append(("quantite", "La quantité doit être supérieure à 0."))
        except ValueError:
            erreurs.append(("quantite", "La quantité doit être un nombre entier."))

    if prix_unitaire_str.strip():
        try:
            p = float(prix_unitaire_str.strip().replace(",", "."))
            if p < 0:
                erreurs.append(("prix_unitaire", "Le prix ne peut pas être négatif."))
        except ValueError:
            erreurs.append(("prix_unitaire", "Le prix doit être un nombre décimal."))

    return erreurs


def valider_categorie(nom: str) -> list[tuple[str, str]]:
    """Valide les données d'une catégorie.

    Args:
        nom: Nom de la catégorie.

    Returns:
        Liste de tuples ``(champ, message)``. Vide si valide.
    """
    erreurs: list[tuple[str, str]] = []
    if not nom or not nom.strip():
        erreurs.append(("nom", "Le nom est obligatoire."))
    elif len(nom.strip()) > 100:
        erreurs.append(("nom", "Le nom ne peut pas dépasser 100 caractères."))
    return erreurs


def valider_unite(nom: str) -> list[tuple[str, str]]:
    """Valide les données d'une unité.

    Args:
        nom: Nom de l'unité.

    Returns:
        Liste de tuples ``(champ, message)``. Vide si valide.
    """
    erreurs: list[tuple[str, str]] = []
    if not nom or not nom.strip():
        erreurs.append(("nom", "Le nom est obligatoire."))
    elif len(nom.strip()) > 50:
        erreurs.append(("nom", "Le nom ne peut pas dépasser 50 caractères."))
    return erreurs


def valider_fournisseur(nom: str, email: str = "") -> list[tuple[str, str]]:
    """Valide les données d'un fournisseur.

    Args:
        nom: Nom du fournisseur.
        email: Adresse e-mail (optionnelle).

    Returns:
        Liste de tuples ``(champ, message)``. Vide si valide.
    """
    import re

    _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    erreurs: list[tuple[str, str]] = []

    if not nom or not nom.strip():
        erreurs.append(("nom", "Le nom est obligatoire."))

    if email and email.strip() and not _EMAIL_RE.match(email.strip()):
        erreurs.append(("email", "L'adresse e-mail n'est pas valide."))

    return erreurs
