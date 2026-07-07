-- Unités de mesure
CREATE TABLE IF NOT EXISTS unites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);

-- Enrichissement de la table fournisseurs existante
ALTER TABLE fournisseurs ADD COLUMN telephone TEXT;
ALTER TABLE fournisseurs ADD COLUMN email TEXT;
ALTER TABLE fournisseurs ADD COLUMN commentaire TEXT;

-- Insertion des catégories par défaut
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Fournitures scolaires', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Matériel événementiel', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Hygiène & Entretien', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Alimentation & Buvette', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Vaisselle & Jetables', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Informatique & Bureautique', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Sécurité & Santé', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Communication & Impression', NULL);
INSERT OR IGNORE INTO categories (nom, parent_id) VALUES ('Divers', NULL);

-- Sous-catégories Fournitures scolaires
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Papeterie', id FROM categories WHERE nom='Fournitures scolaires';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Arts plastiques', id FROM categories WHERE nom='Fournitures scolaires';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Reprographie', id FROM categories WHERE nom='Fournitures scolaires';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Matériel pédagogique', id FROM categories WHERE nom='Fournitures scolaires';

-- Sous-catégories Matériel événementiel
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Décoration', id FROM categories WHERE nom='Matériel événementiel';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Sono & Lumières', id FROM categories WHERE nom='Matériel événementiel';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Mobilier & Tentes', id FROM categories WHERE nom='Matériel événementiel';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Signalétique', id FROM categories WHERE nom='Matériel événementiel';

-- Sous-catégories Hygiène & Entretien
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Produits ménagers', id FROM categories WHERE nom='Hygiène & Entretien';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Hygiène', id FROM categories WHERE nom='Hygiène & Entretien';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Sacs & consommables entretien', id FROM categories WHERE nom='Hygiène & Entretien';

-- Sous-catégories Alimentation & Buvette
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Boissons', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Épicerie', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Frais & périssables', id FROM categories WHERE nom='Alimentation & Buvette';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Confiseries & friandises', id FROM categories WHERE nom='Alimentation & Buvette';

-- Sous-catégories Vaisselle & Jetables
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Assiettes & bols', id FROM categories WHERE nom='Vaisselle & Jetables';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Gobelets & verres', id FROM categories WHERE nom='Vaisselle & Jetables';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Couverts jetables', id FROM categories WHERE nom='Vaisselle & Jetables';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Serviettes & nappes jetables', id FROM categories WHERE nom='Vaisselle & Jetables';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Films & emballages', id FROM categories WHERE nom='Vaisselle & Jetables';

-- Sous-catégories Informatique & Bureautique
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Consommables informatiques', id FROM categories WHERE nom='Informatique & Bureautique';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Matériel informatique', id FROM categories WHERE nom='Informatique & Bureautique';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Fournitures bureau', id FROM categories WHERE nom='Informatique & Bureautique';

-- Sous-catégories Sécurité & Santé
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Premiers secours', id FROM categories WHERE nom='Sécurité & Santé';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Sécurité incendie', id FROM categories WHERE nom='Sécurité & Santé';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'EPI', id FROM categories WHERE nom='Sécurité & Santé';

-- Sous-catégories Communication & Impression
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Affiches & flyers', id FROM categories WHERE nom='Communication & Impression';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Badges & étiquettes', id FROM categories WHERE nom='Communication & Impression';
INSERT OR IGNORE INTO categories (nom, parent_id) SELECT 'Enveloppes & courrier', id FROM categories WHERE nom='Communication & Impression';

-- Insertion des unités par défaut
INSERT OR IGNORE INTO unites (nom) VALUES ('Pièce');
INSERT OR IGNORE INTO unites (nom) VALUES ('Unité');
INSERT OR IGNORE INTO unites (nom) VALUES ('Paire');
INSERT OR IGNORE INTO unites (nom) VALUES ('Lot');
INSERT OR IGNORE INTO unites (nom) VALUES ('Pack / Multipack');
INSERT OR IGNORE INTO unites (nom) VALUES ('Boîte');
INSERT OR IGNORE INTO unites (nom) VALUES ('Carton');
INSERT OR IGNORE INTO unites (nom) VALUES ('Palette');
INSERT OR IGNORE INTO unites (nom) VALUES ('Litre (L)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Centilitre (cL)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Millilitre (mL)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Kilogramme (kg)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Gramme (g)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Mètre (m)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Centimètre (cm)');
INSERT OR IGNORE INTO unites (nom) VALUES ('Rouleau');
INSERT OR IGNORE INTO unites (nom) VALUES ('Feuille');
INSERT OR IGNORE INTO unites (nom) VALUES ('Sachet');
INSERT OR IGNORE INTO unites (nom) VALUES ('Tube');
INSERT OR IGNORE INTO unites (nom) VALUES ('Flacon');
INSERT OR IGNORE INTO unites (nom) VALUES ('Bidon');
INSERT OR IGNORE INTO unites (nom) VALUES ('Brique');
INSERT OR IGNORE INTO unites (nom) VALUES ('Canette');
INSERT OR IGNORE INTO unites (nom) VALUES ('Bouteille');

-- Ajout colonnes manquantes dans stock
ALTER TABLE stock ADD COLUMN unite_id INTEGER REFERENCES unites(id);
ALTER TABLE stock ADD COLUMN fournisseur_habituel_id INTEGER REFERENCES fournisseurs(id);
ALTER TABLE stock ADD COLUMN prix_achat REAL DEFAULT 0;
ALTER TABLE stock ADD COLUMN statut_archive INTEGER DEFAULT 0;

-- Ajout colonnes dans mouvements_stock
ALTER TABLE mouvements_stock ADD COLUMN fournisseur_id INTEGER REFERENCES fournisseurs(id);
ALTER TABLE mouvements_stock ADD COLUMN evenement_id INTEGER REFERENCES evenements(id);
ALTER TABLE mouvements_stock ADD COLUMN numero_facture TEXT;
ALTER TABLE mouvements_stock ADD COLUMN unite_id INTEGER REFERENCES unites(id);
