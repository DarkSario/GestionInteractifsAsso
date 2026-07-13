-- Phase 20 : enrichissement de la table evenement_tombola_lots
-- Migration idempotente : chaque ALTER TABLE est géré par le runner avec try/except

ALTER TABLE tombola_lots ADD COLUMN type_provenance TEXT DEFAULT 'association';
ALTER TABLE tombola_lots ADD COLUMN acheteur_membre_id INTEGER REFERENCES membres(id) ON DELETE SET NULL;
ALTER TABLE tombola_lots ADD COLUMN montant_avance REAL;
ALTER TABLE tombola_lots ADD COLUMN remboursement_statut TEXT DEFAULT 'non_applicable';
ALTER TABLE tombola_lots ADD COLUMN remboursement_date TEXT;
ALTER TABLE tombola_lots ADD COLUMN remboursement_mode TEXT;
ALTER TABLE tombola_lots ADD COLUMN remboursement_reference TEXT;
ALTER TABLE tombola_lots ADD COLUMN donateur_externe TEXT;
ALTER TABLE tombola_lots ADD COLUMN remarque TEXT;
