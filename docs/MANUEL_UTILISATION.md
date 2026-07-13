# 📖 Manuel d'utilisation — Gestion Interactifs Asso

> Ce manuel est destiné aux bénévoles et membres du bureau.
> Pas besoin de connaissances informatiques particulières !

---

## Sommaire

1. [Premier démarrage](#1-premier-démarrage)
2. [Tableau de bord & alertes](#2-tableau-de-bord--alertes)
3. [Événements](#3-événements)
4. [Trésorerie](#4-trésorerie)
5. [Stock & Buvette](#5-stock--buvette)
6. [Adhérents & Cotisations](#6-adhérents--cotisations)
7. [Paramètres & Sauvegardes](#7-paramètres--sauvegardes)
8. [Exports & Bilan AG](#8-exports--bilan-ag)
9. [Questions fréquentes (FAQ)](#9-questions-fréquentes-faq)

---

## 1. Premier démarrage

**À quoi ça sert ?** Cette étape configure l'application pour votre association et crée la base de données qui va stocker toutes vos informations.

### Lancer l'application

1. Double-cliquez sur le fichier `run_app.py` (ou ouvrez un terminal et tapez `python run_app.py`)
2. Une fenêtre de bienvenue s'ouvre

### Créer une base de données

1. Cliquez sur **"Créer une nouvelle base de données"**
2. Choisissez un dossier où la sauvegarder (ex. : `Documents/InteractifsAsso/`)
3. Donnez-lui un nom (ex. : `gestion_2025_2026.db`)
4. Cliquez sur **"Créer"**

> 💡 **Conseil :** Créez la base dans un dossier sauvegardé automatiquement (OneDrive, Google Drive, etc.)

### Ouvrir une base existante

Si vous avez déjà une base de données, cliquez sur **"Ouvrir une base existante"** et sélectionnez le fichier `.db`.

### Configurer votre association

Dès la première ouverture, allez dans **Administration → ⚙️ Paramètres** :
1. Onglet **🏢 Association** : saisissez le nom, l'adresse, le téléphone et l'email de votre association
2. Ajoutez votre logo si vous en avez un (utilisé dans les exports PDF)
3. Cliquez **"💾 Enregistrer"**

**Erreurs fréquentes :**
- Oublier de renseigner le nom de l'association → obligatoire pour les exports PDF
- Choisir un dossier réseau lent pour la base → peut ralentir l'application

---

## 2. Tableau de bord & alertes

**À quoi ça sert ?** La page d'accueil vous donne un résumé en un coup d'œil de l'état de votre association : finances, événements à venir, alertes.

### Ce que vous voyez sur le tableau de bord

- **Solde global** : total de tous vos comptes bancaires et de caisse
- **Recettes et dépenses** du mois en cours
- **Prochains événements** : les 3 événements les plus proches
- **Adhérents** : nombre de membres actifs
- **Alertes** : signaux importants (voir ci-dessous)

### Les alertes

Des alertes colorées apparaissent en haut du tableau de bord pour vous prévenir :

| Couleur | Signification | Exemple |
|---|---|---|
| 🔴 Rouge | Urgent | Stock Coca épuisé (0 unités) |
| 🟠 Orange | À traiter | 3 cotisations en attente, sauvegarde non faite depuis 8 jours |
| 🔵 Bleu | À surveiller | Fête de la musique dans 5 jours |

**Cliquez sur une alerte** pour aller directement au module concerné.

> ✅ Si aucune alerte n'est présente, vous verrez le message "Tout est en ordre"

### Actualisation

Le tableau de bord se rafraîchit automatiquement toutes les 5 minutes. Vous pouvez aussi fermer et rouvrir la page depuis le menu.

---

## 3. Événements

**À quoi ça sert ?** Gérer chaque événement de l'association : fête scolaire, repas, vide-grenier... avec la billetterie, les dépenses, les bénévoles et la buvette.

### Créer un événement

1. Allez dans **Événements** depuis le menu latéral
2. Cliquez **"+ Créer un événement"**
3. Remplissez :
   - Nom de l'événement (ex. : "Fête de l'école 2026")
   - Date de début et de fin
   - Type (fête, spectacle, repas…)
   - Lieu (optionnel)
4. Cliquez **"💾 Enregistrer"**

### Gérer la billetterie

Depuis la fiche de l'événement, onglet **🎫 Billetterie** :
- Définissez les types de billets (adulte, enfant, famille…) avec leur prix
- Saisissez les ventes au fur et à mesure
- Les recettes sont calculées automatiquement

**Exemple concret :** Pour la fête de l'école, créez : "Adulte 5 €", "Enfant 2 €", "Famille (2A+2E) 12 €"

### Saisir les dépenses

Onglet **💸 Dépenses** :
- Ajoutez chaque dépense liée à l'événement (achat de matériel, location de sono…)
- Choisissez la catégorie (matériel, communication, nourriture…)
- Ajoutez un justificatif si nécessaire

### Gérer les bénévoles

Onglet **👫 Bénévoles** :
- Associez des membres de votre liste d'adhérents à l'événement
- Notez leur rôle (caisse, buvette, installation…)
- Suivez les présences

### La tombola

Onglet **🎰 Tombola** :
- Définissez les lots et leur valeur
- Saisissez les numéros de billets vendus
- Tirez les gagnants au sort

### Export du bilan événement

Depuis la fiche événement, cliquez **"📄 Exporter le bilan"** pour générer un PDF récapitulatif.

**Erreurs fréquentes :**
- Ne pas associer les dépenses à l'événement → elles n'apparaîtront pas dans le bilan
- Oublier de clôturer un événement passé → il continuera d'apparaître dans "en cours"

---

## 4. Trésorerie

**À quoi ça sert ?** Suivre toutes les entrées et sorties d'argent de l'association, gérer vos comptes bancaires et votre caisse.

### Créer un compte

1. Allez dans **Trésorerie → Comptes**
2. Cliquez **"+ Ajouter un compte"**
3. Nommez-le (ex. : "Compte courant BNP", "Caisse espèces")
4. Choisissez le type : bancaire ou caisse

> 💡 Créez au minimum un compte bancaire et une caisse espèces pour un suivi complet.

### Saisir une opération

1. Allez dans **Trésorerie → Opérations**
2. Cliquez **"+ Nouvelle opération"**
3. Remplissez :
   - Date
   - Type : Recette ou Dépense
   - Montant
   - Compte concerné
   - Description (ex. : "Don Mairie Exemple - Subvention 2026")
4. Cliquez **"💾 Enregistrer"**

### Remises de chèques

Quand vous allez déposer des chèques à la banque :
1. Allez dans **Trésorerie → Remises de chèques**
2. Créez une remise et listez les chèques inclus
3. Une fois déposé, marquez-la comme "Effectuée"

### Subventions

Suivez vos demandes de subventions dans **Trésorerie → Subventions** :
- Montant demandé / montant obtenu
- Organisme financeur
- Statut (en attente, accordée, refusée)

**Erreurs fréquentes :**
- Confondre recette et dépense → le solde sera faux
- Oublier de rapprocher les relevés bancaires

---

## 5. Stock & Buvette

**À quoi ça sert ?** Gérer votre stock de boissons et produits, les achats fournisseurs et les ventes lors des événements.

### Gérer les articles

1. Allez dans **Stock → Articles**
2. Cliquez **"+ Ajouter un article"**
3. Remplissez :
   - Nom (ex. : "Coca-Cola 33cl")
   - Catégorie (boissons, confiseries, pizzas…)
   - Prix de vente
   - Seuil d'alerte (ex. : 12 → alerte si moins de 12 unités)
4. Cliquez **"💾 Enregistrer"**

### Entrées en stock (achats fournisseur)

Quand vous achetez de la marchandise :
1. Allez dans **Stock → Entrées**
2. Cliquez **"+ Nouvelle entrée"**
3. Sélectionnez l'article et saisissez la quantité et le prix d'achat
4. Le stock est mis à jour automatiquement

### La Buvette

L'onglet **Buvette** suit les ventes lors des événements :
1. Sélectionnez l'événement concerné
2. Saisissez les ventes par article
3. Le stock est automatiquement décrémenté

### Inventaires

Faites régulièrement un inventaire pour vérifier que le stock réel correspond au stock enregistré :
1. Allez dans **Stock → Inventaires**
2. Cliquez **"+ Nouvel inventaire"**
3. Pour chaque article, saisissez la quantité réelle comptée
4. L'application calcule les écarts

**Erreurs fréquentes :**
- Oublier de faire une entrée en stock après un achat → stock négatif affiché
- Ne pas faire d'inventaire de clôture → solde stock incorrect en fin d'exercice

---

## 6. Adhérents & Cotisations

**À quoi ça sert ?** Gérer la liste de vos membres, leurs informations de contact et le suivi de leurs cotisations.

### Ajouter un adhérent

1. Allez dans **Membres** depuis le menu
2. Cliquez **"+ Ajouter"**
3. Remplissez :
   - Nom et prénom (obligatoires)
   - Email et téléphone
   - Statut (actif, bénévole, famille…)
   - Date d'adhésion
4. Cliquez **"💾 Enregistrer"**

### Modifier un adhérent

Double-cliquez sur un adhérent dans la liste, ou sélectionnez-le et cliquez **"✏️ Modifier"**.

### Archiver un adhérent

Quand un membre quitte l'association, archivez-le (ne supprimez pas !) :
1. Sélectionnez-le dans la liste
2. Cliquez **"🗑️ Archiver"**

> Les adhérents archivés sont masqués mais leurs données sont conservées. Cochez "Archivés" pour les afficher.

### Gérer les cotisations

Cliquez sur **"💳 Cotisations"** dans la fenêtre des membres pour ouvrir le gestionnaire de cotisations.

**Statuts des cotisations :**
- 🟢 **Offerte** : cotisation à 0 € (votre pratique actuelle pour les bénévoles)
- ✅ **Payée** : cotisation réglée
- 🟠 **En attente** : cotisation due mais pas encore payée

### Renouveler les cotisations en masse

En début d'année, créez d'un coup les cotisations pour tous les membres actifs :
1. Ouvrez le gestionnaire de cotisations
2. Choisissez l'année
3. Cliquez **"🔄 Renouveler en masse"**
4. Confirmez

> Si le montant par défaut est 0 €, toutes les cotisations seront créées en statut "offerte" automatiquement.

### Configurer le montant par défaut

Dans **Administration → ⚙️ Paramètres → 💰 Financier** :
- Champ **"Montant cotisation par défaut"** : mettez `0.00` pour tout offrir, ou un montant si vous passez à des cotisations payantes.

**Erreurs fréquentes :**
- Supprimer un membre au lieu de l'archiver → perte de l'historique
- Oublier de renouveler les cotisations en début d'année

---

## 7. Paramètres & Sauvegardes

**À quoi ça sert ?** Configurer l'application selon vos besoins et protéger vos données par des sauvegardes régulières.

### Accéder aux paramètres

Allez dans **Administration → ⚙️ Paramètres** (raccourci : `Ctrl+,`)

### Les 5 onglets de paramètres

| Onglet | Contenu |
|---|---|
| 🏢 Association | Nom, adresse, logo de votre asso |
| 💰 Financier | Taux SumUp, comptes par défaut, montant cotisation |
| 📅 Événements | Classes scolaires et types d'événements |
| 🖥️ Système | Thème, sauvegarde automatique, dossiers |
| 📄 Exports & PDF | Polices, couleurs, modèle Bilan AG |

### Faire une sauvegarde manuelle

1. Allez dans **Administration → ⚙️ Paramètres → 🖥️ Système**
2. Cliquez **"💾 Sauvegarder maintenant"**
3. La sauvegarde est créée dans le dossier configuré

> ✅ Une sauvegarde réussie met à jour la date "Dernière sauvegarde" affichée.

### Activer la sauvegarde automatique

Dans l'onglet **🖥️ Système** :
1. Cochez **"Activer la sauvegarde automatique"**
2. Définissez la fréquence (ex. : 7 jours)
3. Choisissez un dossier de sauvegarde
4. Cliquez **"💾 Enregistrer"**

> ⚠️ **Alerte :** Si la sauvegarde n'a pas été faite depuis plus de 7 jours, une alerte orange apparaît sur le tableau de bord.

### Restaurer une sauvegarde

En cas de problème :
1. Allez dans **Administration → Restauration**
2. Sélectionnez le fichier de sauvegarde `.db`
3. Confirmez la restauration

> ⚠️ La restauration remplace la base actuelle par la sauvegarde. Toutes les modifications depuis la sauvegarde seront perdues.

### Changer le thème

Dans l'onglet **🖥️ Système** : choisissez entre mode **🌙 Sombre** et **☀️ Clair**.

**Erreurs fréquentes :**
- Ne jamais faire de sauvegarde → risque de tout perdre en cas de problème
- Sauvegarder sur le même disque que la base → inutile si le disque tombe en panne

---

## 8. Exports & Bilan AG

**À quoi ça sert ?** Générer des documents officiels pour votre association : bilan pour l'Assemblée Générale, listes des membres, relevés de trésorerie.

### Générer le Bilan AG en PDF

1. Allez dans **Exports → Bilan AG**
2. Sélectionnez l'exercice concerné (ex. : 2025-2026)
3. Rédigez un **mot d'introduction** (facultatif)
4. Rédigez une **conclusion** (facultatif)
5. Cliquez **"📄 Exporter en PDF"**
6. Choisissez où sauvegarder le fichier

Le PDF généré contient automatiquement :
- Vie de l'association (adhérents, bénévoles)
- Bilan des événements (tableau récapitulatif)
- Bilan financier (recettes, dépenses, solde)
- Soldes par compte
- Stock & Buvette

### Personnaliser le modèle du Bilan AG

Vous pouvez modifier la structure du document sans toucher au code :
1. Allez dans **Administration → ⚙️ Paramètres → 📄 Exports & PDF**
2. Cliquez **"✏️ Modifier le modèle Bilan AG"**
3. Modifiez le texte à votre guise (les zones `{{variable}}` sont remplies automatiquement)
4. Cliquez **"💾 Enregistrer"**

**Variables disponibles dans le modèle :**
- `{{nom_asso}}` : nom de votre association
- `{{exercice}}` : année de l'exercice
- `{{nb_adherents}}` : nombre de membres actifs
- `{{total_recettes}}` / `{{total_depenses}}` / `{{solde}}` : données financières
- `{{introduction}}` / `{{conclusion}}` : textes saisis avant export

> Pour revenir au modèle d'origine : **"🔄 Restaurer le modèle par défaut"**

### Autres exports disponibles

- **Liste des membres** → PDF ou Excel
- **Relevé de compte** → PDF avec toutes les opérations
- **Bilan d'un événement** → PDF depuis la fiche événement
- **Stock** → PDF ou Excel

**Erreurs fréquentes :**
- Export impossible si reportlab n'est pas installé → `pip install reportlab`
- Chemin de destination avec des caractères spéciaux → préférez un chemin simple

---

## 9. Questions fréquentes (FAQ)

### L'application ne démarre pas

**Vérifiez que Python 3.10+ est bien installé :**
```
python --version
```
Si Python n'est pas reconnu, téléchargez-le sur [python.org](https://www.python.org).

**Installez les dépendances :**
```
pip install -r requirements.txt
```

**Sur Linux, tkinter doit être installé séparément :**
```
sudo apt install python3-tk
```

---

### J'ai fermé la fenêtre par erreur, mes données sont-elles perdues ?

Oui, si vous aviez des saisies en cours non enregistrées. Cliquez toujours sur **"💾 Enregistrer"** avant de fermer une fenêtre.

---

### Comment retrouver un ancien adhérent archivé ?

Dans la liste des membres, cochez la case **"Archivés"** en haut de la liste.

---

### Le solde de trésorerie semble incorrect

Vérifiez que :
1. Toutes les opérations ont bien le bon type (Recette ou Dépense)
2. Les opérations sont bien liées au bon compte
3. Il n'y a pas d'opération en doublon

---

### Je veux changer l'année de l'exercice

Allez dans **Administration → ⚙️ Paramètres → 🏢 Association** et mettez à jour les dates de l'exercice scolaire courant.

---

### Comment faire si je me trompe de saisie ?

La plupart des éléments peuvent être modifiés : double-cliquez dessus ou sélectionnez et cliquez **"✏️ Modifier"**.

---

### L'alerte "Sauvegarde oubliée" s'affiche

Allez dans **Administration → ⚙️ Paramètres → 🖥️ Système** et cliquez **"💾 Sauvegarder maintenant"**.

---

### Comment transférer la base de données sur un autre ordinateur ?

1. Faites une sauvegarde manuelle
2. Copiez le fichier `.db` sur l'autre ordinateur
3. Sur le nouvel ordinateur, lancez l'application et sélectionnez **"Ouvrir une base existante"**

---

### Je veux que plusieurs personnes utilisent l'application

L'application n'est pas multi-utilisateurs en temps réel. La solution la plus simple est de stocker la base de données sur un dossier partagé (réseau local ou cloud) et de s'assurer qu'une seule personne l'utilise à la fois.

---

*Document généré pour l'Association Interactifs — mise à jour Phase 16*
