"""Constantes partagées de la fiche événement."""

STATUTS_EVENEMENT = ["planifie", "en_cours", "termine", "annule"]
LABELS_STATUT = {
    "planifie": "Planifié",
    "en_cours": "En cours",
    "termine": "Terminé",
    "annule": "Annulé",
}
STATUTS_LABELS = {v: k for k, v in LABELS_STATUT.items()}
CANAUX = {"sur_place": "Sur place", "prevente": "Prévente"}
CANAUX_INV = {v: k for k, v in CANAUX.items()}
MODES_PAIEMENT = {
    "especes": "Espèces",
    "cheque": "Chèque",
    "carte": "Carte",
    "sumup": "SumUp",
}
MODES_INV = {v: k for k, v in MODES_PAIEMENT.items()}
ONGLETS_MODULES = {
    "🎫 Billetterie": {"billetterie"},
    "💸 Dépenses": {"depenses"},
    "💰 Budget": {"budget_previsionnel"},
    "👥 Bénévoles": {"benevoles"},
    "🎰 Tombola": {"tombola_classique", "tombola_solidaire"},
    "🏪 Stands": {"stands"},
    "📊 Tableaux": {"tableaux"},
    "🧾 Caisses": {"caisses"},
}
LIBELLES_MODULES = {
    "billetterie": "Billetterie",
    "depenses": "Dépenses",
    "benevoles": "Bénévoles",
    "tombola_classique": "Tombola",
    "tombola_solidaire": "Tombola solidaire",
    "stands": "Stands",
    "tableaux": "Tableaux",
    "caisses": "Caisses",
    "budget_previsionnel": "Budget",
}
# Valeurs initiales choisies pour coller au flux de création le plus fréquent.
MODULES_CREATION_INITIAUX = ("billetterie", "depenses", "caisses")
STATUTS_BENEVOLE = {
    "confirme": "Confirmé",
    "desiste": "Désisté",
    "remplace": "Remplacé",
}
STATUTS_BEN_INV = {v: k for k, v in STATUTS_BENEVOLE.items()}
