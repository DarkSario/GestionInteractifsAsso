-- Configuration et exercice
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_asso TEXT NOT NULL DEFAULT 'Mon Association',
    exercice TEXT,
    date_debut TEXT,
    date_fin TEXT,
    solde_ouverture REAL DEFAULT 0,
    disponible_banque REAL DEFAULT 0,
    cloture INTEGER DEFAULT 0,
    solde_report REAL DEFAULT 0
);

-- Membres / Adhérents
CREATE TABLE IF NOT EXISTS membres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    email TEXT,
    telephone TEXT,
    cotisation TEXT,
    statut TEXT DEFAULT 'actif',
    date_adhesion TEXT,
    commentaire TEXT
);

-- Catégories (stock, dépenses...)
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- Événements
CREATE TABLE IF NOT EXISTS evenements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    date TEXT,
    lieu TEXT,
    description TEXT
);

-- Stock général
CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    categorie_id INTEGER,
    quantite INTEGER DEFAULT 0,
    seuil_alerte INTEGER DEFAULT 0,
    date_peremption TEXT,
    lot TEXT,
    commentaire TEXT,
    FOREIGN KEY (categorie_id) REFERENCES categories(id)
);

-- Mouvements de stock
CREATE TABLE IF NOT EXISTS mouvements_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    prix_unitaire REAL,
    commentaire TEXT,
    FOREIGN KEY (stock_id) REFERENCES stock(id)
);

-- Dons et subventions
CREATE TABLE IF NOT EXISTS dons_subventions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT,
    montant REAL NOT NULL,
    type TEXT,
    justificatif TEXT,
    commentaire TEXT
);

-- Dépenses régulières
CREATE TABLE IF NOT EXISTS depenses_regulieres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_depense TEXT NOT NULL,
    categorie TEXT,
    montant REAL NOT NULL,
    fournisseur TEXT,
    moyen_paiement TEXT,
    numero_cheque TEXT,
    numero_facture TEXT,
    statut_reglement TEXT DEFAULT 'non réglé',
    commentaire TEXT
);

-- Dépenses diverses
CREATE TABLE IF NOT EXISTS depenses_diverses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_depense TEXT NOT NULL,
    categorie TEXT,
    montant REAL NOT NULL,
    fournisseur TEXT,
    moyen_paiement TEXT,
    numero_cheque TEXT,
    numero_facture TEXT,
    statut_reglement TEXT DEFAULT 'non réglé',
    commentaire TEXT
);

-- Dépôts et retraits bancaires
CREATE TABLE IF NOT EXISTS depots_retraits_banque (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL,
    montant REAL NOT NULL,
    reference TEXT,
    banque TEXT,
    pointe INTEGER DEFAULT 0,
    commentaire TEXT
);

-- Fournisseurs
CREATE TABLE IF NOT EXISTS fournisseurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);

-- Historique des clôtures
CREATE TABLE IF NOT EXISTS historique_clotures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_cloture TEXT NOT NULL,
    exercice TEXT,
    solde_final REAL
);

-- Buvette : articles
CREATE TABLE IF NOT EXISTS buvette_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    categorie TEXT,
    unite TEXT,
    contenance TEXT,
    prix_vente REAL DEFAULT 0,
    prix_achat REAL DEFAULT 0,
    stock INTEGER DEFAULT 0,
    commentaire TEXT
);

-- Buvette : achats / approvisionnement
CREATE TABLE IF NOT EXISTS buvette_achats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    date_achat TEXT NOT NULL,
    quantite INTEGER NOT NULL,
    prix_unitaire REAL,
    fournisseur TEXT,
    numero_facture TEXT,
    commentaire TEXT,
    FOREIGN KEY (article_id) REFERENCES buvette_articles(id)
);

-- Buvette : inventaires
CREATE TABLE IF NOT EXISTS buvette_inventaires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_inventaire TEXT NOT NULL,
    evenement_id INTEGER,
    type_inventaire TEXT CHECK(type_inventaire IN ('avant', 'apres', 'hors_evenement')),
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Buvette : lignes d'inventaire
CREATE TABLE IF NOT EXISTS buvette_inventaire_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventaire_id INTEGER NOT NULL,
    article_id INTEGER NOT NULL,
    quantite INTEGER NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (inventaire_id) REFERENCES buvette_inventaires(id),
    FOREIGN KEY (article_id) REFERENCES buvette_articles(id)
);

-- Buvette : recettes
CREATE TABLE IF NOT EXISTS buvette_recettes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER,
    date_recette TEXT NOT NULL,
    montant REAL NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Événements : modules de vente configurables
CREATE TABLE IF NOT EXISTS evenement_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL,
    nom_module TEXT NOT NULL,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Événements : champs des modules
CREATE TABLE IF NOT EXISTS evenement_module_champs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    nom_champ TEXT NOT NULL,
    type_champ TEXT NOT NULL,
    prix_unitaire REAL,
    FOREIGN KEY (module_id) REFERENCES evenement_modules(id)
);

-- Événements : données saisies dans les modules
CREATE TABLE IF NOT EXISTS evenement_module_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    ligne_index INTEGER NOT NULL,
    champ_id INTEGER NOT NULL,
    valeur TEXT,
    FOREIGN KEY (module_id) REFERENCES evenement_modules(id),
    FOREIGN KEY (champ_id) REFERENCES evenement_module_champs(id)
);

-- Événements : paiements reçus
CREATE TABLE IF NOT EXISTS evenement_paiements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL,
    nom_payeur TEXT,
    classe TEXT,
    mode_paiement TEXT,
    banque TEXT,
    numero_cheque TEXT,
    montant REAL NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Événements : caisses
CREATE TABLE IF NOT EXISTS evenement_caisses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL,
    nom_caisse TEXT NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Événements : recettes
CREATE TABLE IF NOT EXISTS evenement_recettes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL,
    source TEXT,
    montant REAL NOT NULL,
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Événements : dépenses
CREATE TABLE IF NOT EXISTS evenement_depenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL,
    categorie TEXT,
    montant REAL NOT NULL,
    fournisseur TEXT,
    date_depense TEXT,
    moyen_paiement TEXT,
    numero_cheque TEXT,
    numero_facture TEXT,
    statut_reglement TEXT DEFAULT 'non réglé',
    commentaire TEXT,
    FOREIGN KEY (evenement_id) REFERENCES evenements(id)
);

-- Rétrocessions aux écoles
CREATE TABLE IF NOT EXISTS retrocessions_ecoles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ecole TEXT NOT NULL,
    montant REAL NOT NULL,
    commentaire TEXT
);
