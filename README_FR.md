# NRIS - Logiciel d'Interprétation des Résultats NIPT

**Version 2.4 Édition Améliorée**
*Tableau de Bord Avancé de Génétique Clinique avec Support Bilingue, Sécurité et Fiabilité Améliorées*

---

## Aperçu

NRIS (NIPT Result Interpretation Software) est un tableau de bord web complet de génétique clinique conçu pour la gestion et l'interprétation des résultats de tests prénatals non invasifs (NIPT). Cette édition améliorée fournit aux professionnels de la santé des outils puissants pour la gestion des patients, l'analyse du contrôle qualité, l'interprétation clinique et la génération automatique de rapports.

### Fonctionnalités Principales

- **Authentification des Utilisateurs et Contrôle d'Accès Basé sur les Rôles**
  - Permissions basées sur les rôles (Administrateur, Généticien, Technicien)

- **Gestion des Patients**
  - Données démographiques complètes et historique clinique
  - Suivi du numéro de dossier médical (MRN) avec application d'unicité
  - Calculs d'IMC et suivi de l'âge gestationnel

- **Analyse des Résultats NIPT**
  - Plusieurs types de panels (Basic, Standard, Plus, Pro)
  - Validation des métriques de contrôle qualité
  - Évaluation automatique du risque de trisomie (T13, T18, T21)
  - Détection de l'aneuploïdie des chromosomes sexuels (SCA)
  - Analyse des trisomies autosomales rares (RAT)
  - Détermination du sexe fœtal
  - **Statut Rapportable** : Indicateur clair Oui/Non indiquant si les résultats doivent être rapportés
    - Oui : Résultats Dépistage Positif ou Dépistage Négatif prêts à être rapportés
    - Non : Re-bibliothèque, Ré-échantillonnage, Échec QC, ou résultats Ambigus nécessitant un traitement supplémentaire

- **Import PDF (Amélioré)**
  - Extraction complète de données à partir de rapports PDF
  - Validation de fichiers (taille, type, vérification de format)
  - Notation de confiance d'extraction (HAUTE/MOYENNE/BASSE)
  - Gestion détaillée des erreurs et journalisation
  - Support de différents formats de rapports
  - Traitement par lot avec suivi de progression

- **Analyses et Visualisations Avancées**
  - Tableaux de bord interactifs avec Plotly
  - Tendances et statistiques des métriques QC
  - Analyse de distribution des résultats
  - Rapports d'utilisation des panels
  - Analyses en cache pour de meilleures performances

- **Rapports PDF Bilingues (NOUVEAU en v2.2)**
  - Rapports cliniques professionnels en **Français** et **Anglais**
  - Sélection de langue par rapport ou préférence par défaut
  - Traduction complète de tout le contenu clinique
  - Recommandations et avertissements localisés

- **Génération Automatique de Rapports PDF**
  - Rapports cliniques professionnels avec en-têtes personnalisables
  - Résumé et interprétation des métriques QC
  - Recommandations cliniques basées sur les seuils
  - Signatures numériques et horodatages

- **Piste d'Audit et Conformité**
  - Journalisation complète des activités des utilisateurs
  - Suivi des modifications de résultats
  - Suivi de connexion/déconnexion
  - Journalisation des tentatives de connexion échouées
  - Capacités d'exportation pour les revues de conformité

- **Protection des Données et Lancement Facile**
  - Sauvegardes automatiques de la base de données au démarrage (conserve les 10 dernières)
  - Mode WAL SQLite pour la résilience aux pannes
  - Vérification de l'intégrité de la base de données
  - Créateur de raccourci de bureau pour un accès en un clic
  - Ouverture automatique du navigateur - pas besoin de copier manuellement le lien

---

## Nouveautés en v2.4

### Affichage Amélioré des Rapports d'Analyse
- **Vue Complète Post-Analyse** : Après l'enregistrement et l'analyse d'un échantillon, les résultats sont maintenant affichés dans un format visuel bien structuré
- Informations complètes du patient (nom, MRN, âge, semaines de gestation)
- Affichage des métriques QC avec tous les paramètres de séquençage (Reads, Cff, GC, QS, Unique %, Error %)
- Résultats de trisomie avec Z-scores dans des cartes métriques montrant le statut en un coup d'œil
- Analyse des chromosomes sexuels avec valeurs Z-XX et Z-XY
- Résultats CNV et RAT clairement organisés
- Bannière de résultat final avec code couleur et indicateur de statut rapportable

### Améliorations du Registre
- **Accès Rapide aux PDF Français** : Les actions rapides dans Parcourir et Rechercher incluent maintenant un sélecteur de langue (EN/FR) pour la génération instantanée de PDF

### Amélioration de l'Expérience Utilisateur
- Meilleur retour visuel pour toutes les actions des utilisateurs
- Mise en page plus claire pour plusieurs résultats de test par patient

---

## Nouveautés en v2.3

### Cartes d'Information Patient
- Le registre affiche maintenant des cartes d'information patient individuelles au lieu de tableaux pour une meilleure visualisation des données
- Indicateurs de statut avec code couleur pour une identification rapide des résultats

### Analyses Multi-Anomalies
- Le tableau de bord des statistiques gère correctement les échantillons avec plusieurs anomalies (T21+T18, etc.)
- Graphiques de répartition dédiés pour les cas complexes

### Fonctionnalités d'Analyse Améliorées
- Analyse SCA : Suivi et visualisation détaillés des anomalies des chromosomes sexuels
- Suivi CNV/RAT : Statistiques complètes des variants de nombre de copies et des trisomies autosomales rares
- Cartes de résultats de test avec indicateurs de statut avec code couleur
- Pagination améliorée pour les grands ensembles de données

---

## Nouveautés en v2.2

### Système de Protection et Sauvegarde des Données
- **Sauvegardes Automatiques** : La base de données est automatiquement sauvegardée à chaque démarrage de l'application
  - Sauvegardes stockées dans le dossier `backups/` avec horodatages
  - Le système conserve automatiquement les 10 dernières sauvegardes (les plus anciennes sont supprimées)
  - Utilise l'API de sauvegarde sécurisée de SQLite pour l'intégrité des données
- **Résilience aux Pannes** : Mode WAL SQLite (Write-Ahead Logging) activé
  - Empêche la corruption de la base de données si l'application se ferme de manière inattendue
  - Meilleures performances pour les opérations de lecture/écriture fréquentes
- **Vérifications d'Intégrité de la Base de Données** : Vérification automatique au démarrage
  - Alerte si des problèmes d'intégrité sont détectés
  - Vérification manuelle d'intégrité disponible dans les Paramètres
- **Interface de Gestion des Sauvegardes** (dans l'onglet Paramètres) :
  - Voir toutes les sauvegardes disponibles avec taille et date
  - Créer des sauvegardes manuelles à tout moment
  - Restaurer à partir de n'importe quelle sauvegarde (admin uniquement)
  - Vérifier l'intégrité de la base de données sur demande

### Options de Lancement Facile
- **Créateur de Raccourci de Bureau** : Exécutez `create_desktop_shortcut.bat` une fois
  - Crée un raccourci "NRIS - Patient Registry" sur le bureau
  - Plus besoin de naviguer vers les dossiers ou de copier les liens
  - Choisissez entre le mode normal ou silencieux (console minimisée)
- **Ouverture Automatique du Navigateur** : Le navigateur s'ouvre automatiquement lorsque le serveur est prêt
- **Mode Silencieux** : Exécutez avec une fenêtre de console minimisée pour un bureau plus propre
  - Utilisez `start_NRIS_silent.vbs` directement, ou choisissez l'option 2 dans le créateur de raccourci

### Rapports PDF Bilingues
- **Support Complet de la Langue Française** : Générez des rapports PDF en anglais et en français
  - Tout le contenu clinique entièrement traduit incluant :
    - En-têtes et étiquettes de section
    - Terminologie d'évaluation QC
    - Descriptions des résultats de trisomie et SCA
    - Recommandations cliniques
    - Limitations et avertissements
    - Section d'autorisation
- **Options de Sélection de Langue** :
  - Définir la langue par défaut dans l'onglet Paramètres
  - Choisir la langue par rapport dans les onglets Analyse et Registre
  - Les rapports incluent un suffixe de langue dans le nom de fichier (par exemple, `Report_123_FR.pdf`)

### Interface Utilisateur Améliorée pour les Techniciens
- **Info-bulles Utiles** : Info-bulles explicatives ajoutées dans l'onglet Analyse
  - Champs d'information patient avec conseils
  - Métriques de séquençage avec plages de référence
  - Seuils de Z-score et aide à l'interprétation
  - Explications des types SCA
- **Guidage Visuel** : Légendes ajoutées montrant les seuils de risque en un coup d'œil
- **Flux de Travail Rationalisé** : Mise en page et étiquetage de formulaire améliorés

### Paramètres de Rapport
- Nouvelle section "Paramètres de Rapport" dans l'onglet Paramètres
- Préférence de langue persistante sauvegardée dans la configuration
- Journalisation d'audit pour les changements de préférence de langue

---

## Nouveautés en v2.1

### Améliorations du Flux de Travail Clinique
- **Statut Rapportable** : Remplacement de "Catégorie de Risque" par un indicateur clair "Rapportable" (Oui/Non)
  - Oui = Résultat prêt à être rapporté (Dépistage Positif ou Dépistage Négatif)
  - Non = Nécessite une action supplémentaire (Re-bibliothèque, Ré-échantillonnage, Échec QC, Ambigu)
  - Affiché dans les résultats d'Analyse, le Registre et les rapports PDF
  - Codé par couleur : Rouge pour les résultats positifs, Jaune pour les non-rapportables
- **Réutilisation du MRN pour les Patients Supprimés** : Lorsque les patients sont supprimés, leur MRN est immédiatement disponible pour de nouveaux patients
- **Gestion des Patients Orphelins** : Les patients avec 0 résultat sont automatiquement détectés et peuvent être remplacés lors de l'importation
- **Détection de Doublons Améliorée** : Distinction claire entre les patients avec résultats (ignorer) vs orphelins (remplacer)

### Améliorations de Sécurité
- **Complexité du Mot de Passe** : Les mots de passe doivent maintenant contenir 8+ caractères avec majuscules, minuscules et chiffres
- **Verrouillage du Compte** : Les comptes se verrouillent pendant 15 minutes après 5 tentatives de connexion échouées
- **Expiration de Session** : Déconnexion automatique après 60 minutes d'inactivité
- **Changement de Mot de Passe Forcé** : Le compte admin par défaut nécessite un changement de mot de passe lors de la première connexion
- **Journalisation d'Audit Améliorée** : Tous les événements de sécurité sont enregistrés

### Améliorations de l'Intégrité des Données
- **Application des Clés Étrangères** : Les contraintes de clés étrangères de la base de données sont maintenant correctement appliquées
- **Suppression Douce** : Les patients supprimés sont marqués plutôt que supprimés, empêchant les enregistrements fantômes
- **Libération du MRN lors de la Suppression** : Les patients supprimés en douceur ont leur MRN modifié pour le libérer pour réutilisation
- **Support de Transaction** : Les opérations d'importation utilisent des transactions de base de données pour éviter les sauvegardes partielles

### Optimisations de Performance
- **Index de Base de Données** : Index ajoutés sur les colonnes fréquemment interrogées
- **Mise en Cache des Requêtes** : Requêtes d'analyse mises en cache pendant 60 secondes
- **Requêtes Optimisées** : Plusieurs requêtes combinées en requêtes efficaces uniques
- **Appels de Base de Données Réduits** : Connexions de base de données redondantes minimisées

### Améliorations de l'Import PDF
- **Validation de Fichier** : Limites de taille, vérification de type et vérification d'en-tête
- **Meilleure Gestion des Erreurs** : Messages d'erreur spécifiques pour différents types d'échec
- **Confiance d'Extraction** : Affiche le niveau de confiance pour les données extraites
- **Détection de Champ Manquant** : Rapporte quels champs n'ont pas pu être extraits
- **Détection de PDF Scanné** : Avertit lorsque le PDF semble être basé sur une image
- **Remplacement Intelligent des Orphelins** : Remplace automatiquement les patients avec 0 résultat au lieu de les ignorer

---

## Démarrage Rapide

### Prérequis

- **Python 3.8 ou supérieur** ([Télécharger Python](https://www.python.org/downloads/))
- Windows, macOS ou Linux
- 4 Go de RAM minimum (8 Go recommandé)
- Navigateur web moderne (Chrome, Firefox, Edge, Safari)

### Installation

#### Utilisateurs Windows (Recommandé)

1. **Télécharger ou cloner ce dépôt**
   ```bash
   git clone https://github.com/AzizElGhezal/NRIS.git
   cd NRIS
   ```

2. **Exécuter le lanceur**
   - Double-cliquez sur `start_NRIS_v2.bat`
   - Le lanceur va automatiquement :
     - Vérifier l'installation de Python
     - Créer un environnement virtuel isolé
     - Installer toutes les dépendances
     - Lancer l'application
     - Ouvrir votre navigateur automatiquement

3. **Accéder à l'application**
   - Votre navigateur web s'ouvrira automatiquement sur `http://localhost:8501`

4. **(Optionnel) Créer un Raccourci de Bureau pour un Accès Facile**
   - Double-cliquez sur `create_desktop_shortcut.bat`
   - Choisissez l'option 2 (Mode silencieux) pour une expérience plus propre
   - Un raccourci "NRIS - Patient Registry" apparaîtra sur votre bureau
   - À partir de maintenant, double-cliquez simplement sur le raccourci de bureau pour lancer NRIS

#### Installation Manuelle (Toutes Plateformes)

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/AzizElGhezal/NRIS.git
   cd NRIS
   ```

2. **Créer un environnement virtuel**
   ```bash
   python -m venv venv_NRIS_v2
   ```

3. **Activer l'environnement virtuel**
   - Windows : `venv_NRIS_v2\Scripts\activate`
   - macOS/Linux : `source venv_NRIS_v2/bin/activate`

4. **Installer les dépendances**
   ```bash
   pip install -r requirements_NRIS_v2.txt
   ```

5. **Lancer l'application**
   ```bash
   streamlit run NRIS_Enhanced.py
   ```

6. **Ouvrir votre navigateur sur** `http://localhost:8501`

---

## Identifiants de Connexion par Défaut

```
Nom d'utilisateur : admin
Mot de passe : admin123
```

**IMPORTANT : Vous serez obligé de changer le mot de passe par défaut lors de la première connexion !**

Exigences du mot de passe :
- Au moins 8 caractères
- Au moins une lettre majuscule (A-Z)
- Au moins une lettre minuscule (a-z)
- Au moins un chiffre (0-9)

---

## Guide d'Utilisation

### Configuration Initiale

1. **Créer un Raccourci de Bureau** (optionnel mais recommandé)
   - Exécutez `create_desktop_shortcut.bat` pour un accès futur facile
2. **Connexion** avec les identifiants par défaut
3. **Changer le Mot de Passe** (requis lors de la première connexion)
4. **Configurer les Seuils QC** dans les Paramètres (optionnel)
5. **Créer des Comptes Utilisateur** pour les membres de votre équipe
6. **Importer les Données Patient** ou ajouter les patients manuellement

### Flux de Travail Quotidien

1. **Ajouter/Sélectionner un Patient** depuis l'onglet Gestion des Patients
2. **Entrer les Résultats NIPT** avec les métriques QC
3. **Réviser l'Interprétation Automatique** et les recommandations cliniques
4. **Générer un Rapport PDF** pour les dossiers cliniques
5. **Exporter les Données** pour l'analyse ou la conformité

### Analyses et Rapports

- **Onglet Tableau de Bord** : Aperçu en temps réel des résultats récents et des statistiques
- **Onglet Analyses** : Tendances QC détaillées, distribution des résultats et utilisation des panels
- **Onglet Journal d'Audit** : Suivi complet des activités et rapports de conformité
- **Fonctionnalités d'Export** : Capacités d'exportation de données Excel, CSV et JSON

### Fonctions Administrateur

- **Gestion des Utilisateurs** : Créer/gérer les comptes utilisateur
- **Maintenance de la Base de Données** :
  - Nettoyer les patients orphelins supprimés en douceur
  - Nettoyer TOUS les patients orphelins (y compris ceux actifs avec 0 résultat)
  - Libérer les identifiants MRN pour réutilisation
- **Protection des Données** :
  - Voir et gérer les sauvegardes automatiques
  - Créer des sauvegardes manuelles
  - Restaurer à partir de sauvegardes précédentes
  - Vérifier l'intégrité de la base de données
- **Revue du Journal d'Audit** : Surveiller toute l'activité du système
- **Configuration** : Ajuster les seuils QC et cliniques

---

## Spécifications Techniques

### Pile Technologique

- **Framework** : Streamlit 1.28+
- **Base de Données** : SQLite3 avec application de clés étrangères
- **Visualisation** : Plotly 5.17+
- **Rapports** : ReportLab 4.0+
- **Traitement de Données** : Pandas 2.0+
- **Gestion de PDF** : PyPDF2 3.0+

### Structure des Fichiers

```
NRIS/
├── NRIS_Enhanced.py           # Application principale
├── start_NRIS_v2.bat          # Lanceur Windows (ouvre le navigateur automatiquement)
├── start_NRIS_silent.vbs      # Lanceur silencieux (console minimisée)
├── create_desktop_shortcut.bat # Crée un raccourci de bureau pour un accès facile
├── requirements_NRIS_v2.txt   # Dépendances Python
├── README.md                  # Fichier anglais
├── README_FR.md               # Ce fichier (version française)
├── GUIDE_PERSONNALISATION.md  # Guide de personnalisation (français)
├── nipt_registry_v2.db        # Base de données (créée automatiquement)
├── nris_config.json           # Configuration (créée automatiquement)
└── backups/                   # Sauvegardes automatiques (créées automatiquement)
    └── nris_backup_*.db       # Sauvegardes de base de données horodatées
```

### Schéma de Base de Données

L'application utilise SQLite avec les tables principales suivantes :
- **users** : Comptes utilisateur et authentification
- **patients** : Données démographiques des patients (avec support de suppression douce)
- **results** : Résultats de test NIPT liés aux patients
- **audit_log** : Journalisation complète des activités

Les index sont automatiquement créés sur :
- `patients(mrn_id)` - Recherche rapide de patient
- `results(patient_id)` - Récupération rapide de résultats
- `results(created_at)` - Requêtes basées sur la date
- `audit_log(timestamp)` - Requêtes de journal d'audit

### Dépendances

```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
reportlab>=4.0.0
openpyxl>=3.1.0
xlsxwriter>=3.1.0
PyPDF2>=3.0.0
```

---

## Configuration

### Seuils QC

Les seuils de contrôle qualité par défaut peuvent être personnalisés dans l'onglet Paramètres :

- **ADN Fœtal Libre de Cellules (CFF)** : Minimum 3,5%
- **Contenu GC** : 37,0-44,0%
- **Taux de Lecture Unique** : Minimum 68,0%
- **Taux d'Erreur** : Maximum 1,0%
- **Limites de Score de Qualité** : Négatif <1,7, Positif >2,0

### Seuils d'Interprétation Clinique

- **Trisomie Risque Faible** : <2,58
- **Trisomie Ambigu** : 2,58-6,0
- **Trisomie Risque Élevé** : >6,0
- **Seuil SCA** : >4,5
- **RAT Positif** : >8,0
- **RAT Ambigu** : 4,5-8,0

### Types de Panel

- **NIPT Basic** : Minimum 5M lectures
- **NIPT Standard** : Minimum 7M lectures
- **NIPT Plus** : Minimum 12M lectures
- **NIPT Pro** : Minimum 20M lectures

### Paramètres de Sécurité (Intégrés)

- **Expiration de Session** : 60 minutes
- **Verrouillage de Compte** : 5 tentatives échouées = verrouillage de 15 minutes
- **Exigences de Mot de Passe** : 8+ caractères, casse mixte, chiffres

---

## Sécurité et Conformité

### Fonctionnalités de Sécurité

- Hachage de mot de passe SHA256 avec sel aléatoire
- Authentification basée sur session avec expiration
- Contrôle d'accès basé sur les rôles (RBAC)
- Protection de verrouillage de compte
- Journalisation d'audit pour toutes les modifications de données
- Stockage sécurisé de base de données avec requêtes paramétrées
- Application de contraintes de clés étrangères

### Confidentialité des Données

- Données patient stockées localement dans la base de données SQLite
- Aucune transmission de données externe
- Considérations de conformité HIPAA intégrées
- Piste d'audit pour la conformité réglementaire
- La suppression douce préserve l'intégrité des données

### Protection des Données et Sauvegardes

**Protection Automatique (Intégrée)**
- La base de données est automatiquement sauvegardée à chaque démarrage de l'application
- Les sauvegardes sont stockées dans le dossier `backups/` avec horodatages
- Le système conserve les 10 dernières sauvegardes automatiquement
- Le mode WAL SQLite empêche la corruption lors d'arrêts inattendus
- L'intégrité de la base de données est vérifiée à chaque démarrage

**Options de Sauvegarde Manuelle**
- Créer des sauvegardes manuelles à tout moment depuis Paramètres → Protection des Données
- Restaurer à partir de n'importe quelle sauvegarde (admin uniquement) si nécessaire
- Vérifier l'intégrité de la base de données sur demande

**Pour une Sécurité Supplémentaire**
Copiez périodiquement ces fichiers vers un emplacement externe :
- Dossier `backups/` - Contient toutes les sauvegardes automatiques
- `nipt_registry_v2.db` - Base de données actuelle
- `nris_config.json` - Paramètres de configuration personnalisés

---

## Dépannage

### Problèmes Courants

**L'application ne démarre pas**
- Assurez-vous que Python 3.8+ est installé et dans PATH
- Essayez d'exécuter `pip install -r requirements_NRIS_v2.txt` manuellement
- Vérifiez les paramètres du pare-feu pour le port 8501

**Erreurs de base de données**
- Supprimez `nipt_registry_v2.db` pour réinitialiser (attention : supprime toutes les données)
- Assurez-vous des permissions d'écriture dans le répertoire de l'application

**Erreurs d'importation**
- Vérifiez que toutes les dépendances sont installées : `pip list`
- Mettez à jour pip : `pip install --upgrade pip`
- Réinstallez les exigences : `pip install -r requirements_NRIS_v2.txt --force-reinstall`

**Problèmes d'extraction PDF**
- Assurez-vous que les PDFs sont basés sur du texte (pas des images scannées)
- Vérifiez le niveau de confiance d'extraction pour les indicateurs de qualité
- Consultez la liste des champs manquants pour les PDFs problématiques

**Compte verrouillé**
- Attendez 15 minutes pour le déverrouillage automatique
- L'administrateur peut réinitialiser via la base de données si nécessaire

**Session expirée**
- Reconnectez-vous après 60 minutes d'inactivité
- Ceci est une fonctionnalité de sécurité

**Le navigateur ne s'ouvre pas**
- Naviguez manuellement vers `http://localhost:8501`
- Essayez un navigateur différent
- Vérifiez si le port 8501 est déjà utilisé

---

## Historique des Versions

### Version 2.4 (Actuelle)
**Rapport d'Analyse**
- Affichage post-analyse complet avec informations patient, métriques QC, résultats
- Résultats de trisomie et SCA codés par couleur avec Z-scores
- Indicateur de statut rapportable

**Registre**
- Sélecteur de langue PDF français/anglais dans les actions rapides
- Boutons PDF multi-résultats par résultat de test
- Navigation claire et bannières de sélection de patient

**Expérience Utilisateur**
- Flux de navigation amélioré entre les onglets
- Meilleur retour visuel pour toutes les actions

### Version 2.3
**Améliorations d'Affichage**
- Cartes d'information patient dans le registre
- Support d'analyses multi-anomalies
- Suivi et visualisation SCA
- Statistiques CNV/RAT dans les analyses

### Version 2.2
**Protection des Données**
- Sauvegarde automatique de la base de données à chaque démarrage
- Mode WAL SQLite pour la résilience aux pannes
- Vérification d'intégrité de la base de données au démarrage
- Interface de gestion des sauvegardes dans les Paramètres (voir, créer, restaurer)
- Rotation automatique des sauvegardes (conserve les 10 dernières)

**Lancement Facile**
- Créateur de raccourci de bureau pour un accès en un clic
- Ouverture automatique du navigateur lorsque le serveur est prêt
- Option de mode silencieux (console minimisée)
- Plus besoin de naviguer vers les dossiers ou de copier les liens

**Support Bilingue**
- Support complet de la langue française pour les rapports PDF
- Sélection de langue dans les onglets Analyse et Registre
- Préférence de langue par défaut dans les Paramètres
- Traduction complète du contenu clinique

**Expérience Technicien**
- Info-bulles utiles sur tous les champs de saisie
- Guidage visuel avec légendes de seuil
- Mise en page et étiquetage de formulaire améliorés
- Flux de travail d'analyse rationalisé

### Version 2.1
**Flux de Travail Clinique**
- Nouveau statut "Rapportable" remplace "Catégorie de Risque" confuse
- Indicateur clair Oui/Non pour savoir si les résultats peuvent être rapportés
- Résultats codés par couleur (Rouge=Positif, Jaune=Nécessite action)

**Gestion des Patients**
- Réutilisation du MRN lorsque les patients sont supprimés
- Détection et remplacement intelligents des patients orphelins
- Gestion améliorée des doublons dans l'importation par lot
- Utilitaires de nettoyage améliorés pour les enregistrements orphelins

**Sécurité**
- Exigences de complexité de mot de passe (8+ caractères, casse mixte, chiffres)
- Verrouillage de compte après 5 tentatives de connexion échouées
- Expiration de session de 60 minutes pour les utilisateurs inactifs
- Changement de mot de passe forcé lors de la première connexion
- Journalisation d'audit améliorée

**Intégrité des Données**
- Application de contraintes de clés étrangères de base de données
- Suppression douce avec libération automatique du MRN
- Support de transaction pour les opérations d'importation
- Index de base de données optimisés

**Performance**
- Mise en cache des requêtes pour les analyses (60 secondes)
- Requêtes de base de données combinées et optimisées
- Connexions de base de données redondantes réduites

**Import PDF**
- Validation de fichier (taille, type, format)
- Notation de confiance d'extraction
- Remplacement intelligent des orphelins lors de l'importation
- Meilleure gestion et rapport d'erreur

### Version 2.0
- Ajout d'authentification utilisateur et contrôle d'accès basé sur les rôles
- Implémentation de journalisation d'audit complète
- Tableau de bord d'analyses amélioré avec visualisations Plotly
- Ajout de génération automatique de rapports PDF
- Amélioration de la validation QC et de l'interprétation clinique
- Ajout d'un système de gestion de configuration
- Capacités d'exportation de données améliorées (Excel, CSV, JSON)

---

## Auteur

**Aziz El Ghezal**

---

## Licence

Ce logiciel est fourni pour un usage clinique et de recherche. Veuillez vous assurer de la conformité avec les réglementations locales concernant les logiciels médicaux et la gestion des données patient.

---

## Support et Contributions

Pour les problèmes, demandes de fonctionnalités ou contributions :
- Ouvrez un problème sur le dépôt GitHub
- Contactez l'équipe de développement
- Consultez les journaux d'audit pour le dépannage

---

## Avertissement

Ce logiciel est conçu pour aider les professionnels de santé à interpréter les résultats NIPT. Les décisions cliniques doivent toujours être prises par des professionnels médicaux qualifiés en tenant compte de toutes les informations cliniques disponibles. Cet outil ne remplace pas le jugement médical professionnel.

---

**NRIS v2.4 Édition Améliorée** - Faire Progresser la Génétique Clinique par la Technologie
