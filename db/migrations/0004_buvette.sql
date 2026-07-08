-- Nouvelles sous-catégories buvette dans Alimentation & Buvette
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Alcools & spiritueux', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Bières & vins', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Snacks & apéritifs', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Sans alcool & softs', id FROM categories WHERE nom='Alimentation & Buvette';

-- Articles buvette
CREATE TABLE IF NOT EXISTS articles_buvette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    categorie_id INTEGER REFERENCES categories(id),
    unite_id INTEGER REFERENCES unites(id),
    contenance TEXT,
    prix_vente REAL NOT NULL DEFAULT 0,
    prix_achat REAL DEFAULT 0,
    stock_actuel INTEGER DEFAULT 0,
    stock_id INTEGER REFERENCES stock(id),
    statut_archive INTEGER DEFAULT 0,
    commentaire TEXT
);

-- Inventaires buvette
CREATE TABLE IF NOT EXISTS inventaires_buvette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('avant_evenement', 'apres_evenement', 'hors_evenement')),
    evenement_id INTEGER REFERENCES evenements(id),
    commentaire TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Lignes d'inventaire (écart calculé côté Python pour compatibilité SQLite)
CREATE TABLE IF NOT EXISTS inventaire_buvette_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inventaire_id INTEGER NOT NULL REFERENCES inventaires_buvette(id),
    article_id INTEGER NOT NULL REFERENCES articles_buvette(id),
    quantite_theorique INTEGER DEFAULT 0,
    quantite_comptee INTEGER NOT NULL
);

-- Approvisionnements buvette
CREATE TABLE IF NOT EXISTS approvisionnements_buvette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    evenement_id INTEGER REFERENCES evenements(id),
    fournisseur_id INTEGER REFERENCES fournisseurs(id),
    montant_total REAL DEFAULT 0,
    commentaire TEXT,
    finalise INTEGER DEFAULT 0,
    finalise_le TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Lignes d'approvisionnement
CREATE TABLE IF NOT EXISTS approvisionnement_buvette_lignes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    approvisionnement_id INTEGER NOT NULL REFERENCES approvisionnements_buvette(id),
    article_id INTEGER NOT NULL REFERENCES articles_buvette(id),
    quantite INTEGER NOT NULL,
    prix_unitaire REAL DEFAULT 0
);

-- Caisses par événement
CREATE TABLE IF NOT EXISTS caisses_buvette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    nom TEXT NOT NULL,
    fond_de_caisse REAL DEFAULT 0,
    total_brut REAL DEFAULT 0,
    commentaire TEXT,
    date TEXT NOT NULL
);

-- Recettes buvette (calculées depuis caisses)
CREATE TABLE IF NOT EXISTS recettes_buvette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id INTEGER NOT NULL REFERENCES evenements(id),
    date TEXT NOT NULL,
    total_brut REAL DEFAULT 0,
    total_fond_caisse REAL DEFAULT 0,
    recette_nette REAL DEFAULT 0,
    commentaire TEXT,
    tresorerie_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recettes_buvette_evenement_unique ON recettes_buvette(evenement_id);
