# Frontière entre stock historique et stock par lots

Le stock repose sur deux chemins complémentaires. Les nouveaux développements
qui ont besoin de traçabilité d'achat ou de consommation par lot doivent utiliser
`core.stock_v2`; les API historiques restent disponibles pour les écrans et
rapports qui manipulent le catalogue et les mouvements.

## Stock historique

- `db.models.stock` gère les articles du catalogue et les mouvements
  (`add_article`, `add_mouvement`, lectures et archivage).
- `core.stock` fournit les types de mouvements et la validation des formulaires
  historiques.
- Les quantités affichées par les écrans historiques sont calculées depuis les
  mouvements lorsqu'il en existe, avec `stock.quantite` comme valeur de repli
  pour les articles sans mouvement.

Ces API sont maintenues pour compatibilité. Les nouveaux comportements ne
doivent pas être ajoutés à ce chemin lorsqu'ils nécessitent des lots, du FIFO,
des tags ou des dates de péremption.

## Stock par lots (`stock_v2`)

`core.stock_v2` gère les lots, leur coût et leurs métadonnées, le stock
théorique, la consommation FIFO, les tags et les péremptions. Les tables
`stock_lots`, `stock_tags` et leurs associations portent le détail de ce flux.
Le total des lots est synchronisé dans `stock.quantite` afin de rester visible
dans les écrans historiques.

Pour les fonctionnalités de lots et de FIFO, les données détaillées de
`stock_v2` font foi. La quantité agrégée est une compatibilité de lecture, pas
un substitut à ce détail. Le formulaire d'entrée actuel ajoute également un
mouvement historique pour conserver l'historique existant; il faut préserver
cette synchronisation lors d'évolutions de ce parcours, sans créer de second
calcul divergent de la quantité.

## Règle d'évolution

Conserver les API historiques sans rupture tant qu'elles sont utilisées.
Orienter les nouvelles fonctionnalités par lot vers `core.stock_v2` et maintenir
explicitement leur compatibilité avec les agrégats lus par les écrans existants.
Ne pas déplacer ni supprimer les anciennes API dans le cadre d'un simple
refactoring structurel.
