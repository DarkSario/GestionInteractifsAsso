-- Migration initiale : création de toutes les tables
-- Utilisation de CREATE TABLE IF NOT EXISTS pour l'idempotence

CREATE TABLE IF NOT EXISTS config (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    exercice            TEXT,
    date_debut          TEXT,
    date_fin            TEXT,
    disponible_banque   REAL    DEFAULT 0,
    cloture             INTEGER DEFAULT 0,
    solde_report        REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS membres (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nom             TEXT NOT NULL,
    prenom          TEXT,
    email           TEXT,
    telephone       TEXT,
    cotisation      REAL    DEFAULT 0,
    statut          TEXT    DEFAULT 'actif',
    date_adhesion   TEXT,
    commentaire     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    date        TEXT,
    lieu        TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS stock (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nom             TEXT NOT NULL,
    categorie_id    INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    quantite        REAL    DEFAULT 0,
    seuil_alerte    REAL    DEFAULT 0,
    date_peremption TEXT,
    commentaire     TEXT
);

CREATE TABLE IF NOT EXISTS dons_subventions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    source      TEXT,
    montant     REAL    DEFAULT 0,
    type        TEXT,
    justificatif TEXT
);

CREATE TABLE IF NOT EXISTS depenses_regulieres (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    categorie       TEXT,
    montant         REAL    DEFAULT 0,
    fournisseur     TEXT,
    date_depense    TEXT,
    moyen_paiement  TEXT,
    commentaire     TEXT
);

CREATE TABLE IF NOT EXISTS depenses_diverses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    categorie       TEXT,
    montant         REAL    DEFAULT 0,
    fournisseur     TEXT,
    date_depense    TEXT,
    moyen_paiement  TEXT,
    commentaire     TEXT
);

CREATE TABLE IF NOT EXISTS depots_retraits_banque (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    type        TEXT,
    montant     REAL    DEFAULT 0,
    reference   TEXT,
    banque      TEXT,
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS fournisseurs (
    id  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historique_clotures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date_cloture    TEXT,
    exercice        TEXT,
    solde_final     REAL    DEFAULT 0
);

-- ── Buvette ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS buvette_articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL,
    categorie   TEXT,
    prix_vente  REAL    DEFAULT 0,
    prix_achat  REAL    DEFAULT 0,
    stock_actuel REAL   DEFAULT 0,
    actif       INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS buvette_achats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT,
    article_id      INTEGER REFERENCES buvette_articles(id) ON DELETE SET NULL,
    quantite        REAL    DEFAULT 0,
    prix_unitaire   REAL    DEFAULT 0,
    fournisseur     TEXT,
    commentaire     TEXT
);

CREATE TABLE IF NOT EXISTS buvette_inventaires (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    event_id    INTEGER REFERENCES events(id) ON DELETE SET NULL,
    type        TEXT,
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS buvette_inventaire_lignes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    inventaire_id   INTEGER REFERENCES buvette_inventaires(id) ON DELETE CASCADE,
    article_id      INTEGER REFERENCES buvette_articles(id) ON DELETE SET NULL,
    quantite        REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS buvette_recettes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT,
    event_id    INTEGER REFERENCES events(id) ON DELETE SET NULL,
    montant     REAL    DEFAULT 0,
    commentaire TEXT
);

-- ── Événements (modules de vente configurables) ──────────────────────────────

CREATE TABLE IF NOT EXISTS event_modules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER REFERENCES events(id) ON DELETE CASCADE,
    nom         TEXT NOT NULL,
    ordre       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_module_fields (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER REFERENCES event_modules(id) ON DELETE CASCADE,
    nom         TEXT NOT NULL,
    type        TEXT    DEFAULT 'text',
    obligatoire INTEGER DEFAULT 0,
    ordre       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_module_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER REFERENCES event_modules(id) ON DELETE CASCADE,
    field_id    INTEGER REFERENCES event_module_fields(id) ON DELETE CASCADE,
    valeur      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS event_payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER REFERENCES events(id) ON DELETE CASCADE,
    montant     REAL    DEFAULT 0,
    moyen       TEXT,
    date        TEXT,
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS event_caisses (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id            INTEGER REFERENCES events(id) ON DELETE CASCADE,
    nom                 TEXT NOT NULL,
    solde_ouverture     REAL    DEFAULT 0,
    solde_fermeture     REAL    DEFAULT 0
);

CREATE TABLE IF NOT EXISTS event_recettes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER REFERENCES events(id) ON DELETE CASCADE,
    categorie   TEXT,
    montant     REAL    DEFAULT 0,
    date        TEXT,
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS event_depenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER REFERENCES events(id) ON DELETE CASCADE,
    categorie   TEXT,
    montant     REAL    DEFAULT 0,
    date        TEXT,
    commentaire TEXT
);
