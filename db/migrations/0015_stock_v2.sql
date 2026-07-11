-- Phase 12 — Refonte Stock & Buvette (FIFO, tags, inventaires, budgets)

-- Tags disponibles (prédéfinis + libres)
CREATE TABLE IF NOT EXISTS stock_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    couleur TEXT DEFAULT '#3B82F6',
    systeme INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO stock_tags (nom, couleur, systeme) VALUES
    ('Buvette',     '#F97316', 1),
    ('Événement',   '#8B5CF6', 1),
    ('Fournitures', '#6B7280', 1),
    ('Matériel',    '#0EA5E9', 1);

-- Liaison articles ↔ tags (multi-tags)
CREATE TABLE IF NOT EXISTS stock_article_tags (
    article_id INTEGER NOT NULL REFERENCES stock(id) ON DELETE CASCADE,
    tag_id     INTEGER NOT NULL REFERENCES stock_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, tag_id)
);

-- Lots d'achat (FIFO)
CREATE TABLE IF NOT EXISTS stock_lots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id      INTEGER NOT NULL REFERENCES stock(id) ON DELETE CASCADE,
    numero_lot      TEXT,
    numero_facture  TEXT,
    fournisseur_id  INTEGER REFERENCES fournisseurs(id),
    date_achat      TEXT NOT NULL DEFAULT (date('now')),
    date_peremption TEXT,
    quantite_initiale  INTEGER NOT NULL DEFAULT 0,
    quantite_restante  INTEGER NOT NULL DEFAULT 0,
    prix_unitaire_ht   REAL NOT NULL DEFAULT 0,
    prix_unitaire_ttc  REAL NOT NULL DEFAULT 0,
    tva_taux           REAL DEFAULT 0,
    statut          TEXT DEFAULT 'actif'
        CHECK(statut IN ('actif','epuise','expire','archive')),
    commentaire     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Liaison lots ↔ tags
CREATE TABLE IF NOT EXISTS stock_lot_tags (
    lot_id  INTEGER NOT NULL REFERENCES stock_lots(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES stock_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (lot_id, tag_id)
);

-- Inventaires (avant/après événement ou ponctuel)
CREATE TABLE IF NOT EXISTS stock_inventaires (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id    INTEGER REFERENCES evenements(id),
    type_inventaire TEXT NOT NULL DEFAULT 'ponctuel'
        CHECK(type_inventaire IN ('avant_evenement','apres_evenement','ponctuel')),
    date_inventaire TEXT NOT NULL DEFAULT (datetime('now')),
    statut          TEXT DEFAULT 'en_cours'
        CHECK(statut IN ('en_cours','valide','annule')),
    commentaire     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Lignes d'inventaire
CREATE TABLE IF NOT EXISTS stock_inventaire_lignes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    inventaire_id      INTEGER NOT NULL REFERENCES stock_inventaires(id) ON DELETE CASCADE,
    article_id         INTEGER NOT NULL REFERENCES stock(id),
    lot_id             INTEGER REFERENCES stock_lots(id),
    quantite_theorique INTEGER DEFAULT 0,
    quantite_reelle    INTEGER DEFAULT 0,
    prix_unitaire_fifo REAL DEFAULT 0,
    valeur_ecart       REAL DEFAULT 0,
    commentaire        TEXT
);

-- Coûts buvette par événement
CREATE TABLE IF NOT EXISTS buvette_couts_evenement (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id        INTEGER NOT NULL REFERENCES evenements(id),
    inventaire_avant_id INTEGER REFERENCES stock_inventaires(id),
    inventaire_apres_id INTEGER REFERENCES stock_inventaires(id),
    cout_total_ht       REAL DEFAULT 0,
    cout_total_ttc      REAL DEFAULT 0,
    statut              TEXT DEFAULT 'calcule'
        CHECK(statut IN ('calcule','valide')),
    detail_json         TEXT DEFAULT '[]',
    created_at          TEXT DEFAULT (datetime('now'))
);

-- Budget prévisionnel par événement
CREATE TABLE IF NOT EXISTS evenement_budget (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    evenement_id            INTEGER NOT NULL REFERENCES evenements(id) UNIQUE,
    recettes_prevues        REAL DEFAULT 0,
    depenses_prevues        REAL DEFAULT 0,
    cout_buvette_prevu      REAL DEFAULT 0,
    nb_personnes_attendues  INTEGER DEFAULT 0,
    prix_moyen_entree       REAL DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

-- Paramètres supplémentaires
INSERT OR IGNORE INTO parametres (cle, valeur, description) VALUES
    ('stock_alerte_peremption_jours', '30', 'Alerter X jours avant péremption'),
    ('stock_fifo_actif', '1', 'Utiliser FIFO pour calcul des coûts (1=oui)');
