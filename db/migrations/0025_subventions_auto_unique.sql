-- PR11 : étend l'unicité des écritures automatiques aux subventions.
-- Les doublons existants sont neutralisés (annulés, jamais supprimés).
UPDATE tresorerie_operations
SET statut = 'annule'
WHERE source_module = 'subvention'
  AND source_id IS NOT NULL
  AND statut != 'annule'
  AND id > (
      SELECT MIN(o2.id) FROM tresorerie_operations o2
      WHERE o2.source_module = tresorerie_operations.source_module
        AND o2.source_id = tresorerie_operations.source_id
        AND o2.statut != 'annule'
  );

DROP INDEX IF EXISTS idx_tresorerie_operations_source_unique;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tresorerie_operations_source_unique
ON tresorerie_operations (source_module, source_id)
WHERE source_id IS NOT NULL
  AND statut != 'annule'
  AND source_module IN ('cotisation', 'don', 'tombola_remboursement', 'subvention');
