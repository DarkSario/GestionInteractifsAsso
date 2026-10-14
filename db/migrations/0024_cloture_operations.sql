-- PR10 : mémorise les opérations dont le statut a été modifié par une clôture,
-- afin que la réouverture n'annule que ces changements. Les lignes sont
-- conservées après réouverture (date_restauration renseignée) pour la traçabilité.
CREATE TABLE IF NOT EXISTS exercices_operations_cloturees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercice_id INTEGER NOT NULL REFERENCES exercices(id),
    operation_id INTEGER NOT NULL REFERENCES tresorerie_operations(id),
    statut_origine TEXT NOT NULL,
    date_cloture TEXT DEFAULT (datetime('now')),
    date_restauration TEXT
);

CREATE INDEX IF NOT EXISTS idx_exercices_operations_cloturees_ex
ON exercices_operations_cloturees (exercice_id, date_restauration);
CREATE INDEX IF NOT EXISTS idx_exercices_operations_cloturees_op
ON exercices_operations_cloturees (operation_id);
