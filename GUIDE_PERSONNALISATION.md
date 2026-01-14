# Guide de Personnalisation NRIS Enhanced

**Version 2.4** | Date: Janvier 2026

---

## Table des Matières

1. [Introduction](#1-introduction)
2. [Adaptation de l'Import PDF aux Templates de Laboratoire](#2-adaptation-de-limport-pdf-aux-templates-de-laboratoire)
3. [Modification des Paramètres Internes (Z-Scores, Rapports, etc.)](#3-modification-des-paramètres-internes-z-scores-rapports-etc)
4. [Ajout de Sécurité : Chiffrement des Données](#4-ajout-de-sécurité--chiffrement-des-données)
5. [Sauvegarde et Restauration](#5-sauvegarde-et-restauration)
6. [Dépannage](#6-dépannage)

---

## 1. Introduction

Ce guide est destiné aux laboratoires qui souhaitent personnaliser le système NRIS Enhanced pour répondre à leurs besoins spécifiques. Il couvre trois aspects principaux :

- **Personnalisation de l'import PDF** pour s'adapter aux différents formats de rapports NIPT
- **Modification des paramètres cliniques** (seuils de Z-scores, paramètres QC, etc.)
- **Implémentation du chiffrement des données** (non inclus dans le système de base)

### Prérequis

- Connaissances de base en Python 3.8+
- Accès aux fichiers source du système NRIS Enhanced
- Droits d'écriture sur le dossier de l'application
- Éditeur de texte ou IDE (VSCode, PyCharm, etc.)

### Fichiers Principaux

| Fichier | Description |
|---------|-------------|
| `NRIS_Enhanced.py` | Fichier principal (5,673 lignes) |
| `nris_config.json` | Configuration personnalisée |
| `nipt_registry_v2.db` | Base de données SQLite |
| `backups/` | Dossier des sauvegardes |

---

## 2. Adaptation de l'Import PDF aux Templates de Laboratoire

### 2.1. Comprendre le Système d'Extraction Actuel

Le système utilise **PyPDF2** pour extraire le texte des PDFs, puis applique des **expressions régulières (regex)** pour identifier et extraire les données.

**Localisation du code :** `NRIS_Enhanced.py`, lignes **1477-2245**

**Fonction principale :** `extract_data_from_pdf(pdf_file)`

#### Flux d'Extraction

```
PDF → PyPDF2.PdfReader → Extraction de texte → Normalisation
  ↓
Regex patterns (multiple variants par champ)
  ↓
Validation des valeurs (plages acceptables)
  ↓
Dictionnaire de données extraites
```

### 2.2. Structure des Patterns Regex

Chaque champ de données possède **plusieurs patterns** pour gérer différents formats de rapports.

#### Exemple : Extraction du Nom du Patient

**Lignes 1579-1593 dans NRIS_Enhanced.py**

```python
name_patterns = [
    r'(?:Patient|Patient\s+Name|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|ID|Age|DOB|...))',
    r'Full\s+Name[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|\n|$))',
    r'Patient\s*:\s*([A-Za-z][A-Za-z\s\-\'\.]+)',
    # ... autres patterns
]
```

**Stratégie :**
- Tente chaque pattern dans l'ordre
- Retient la première correspondance valide
- Applique une validation (longueur, caractères autorisés)

### 2.3. Comment Ajouter un Nouveau Format de PDF

#### Étape 1 : Analyser Votre Template PDF

1. **Ouvrez un exemple de rapport** de votre laboratoire
2. **Notez la structure exacte** des sections
3. **Identifiez les étiquettes** utilisées pour chaque champ

**Exemple de rapport :**
```
Laboratoire GeneDx
-------------------
Nom Patient    : Marie DUPONT
No. Dossier    : MRN-2024-0123
Âge Maternel   : 32 ans
Âge Gestationnel: 12+3 semaines
-------------------
Résultats DPNI
Trisomie 21    : NÉGATIF (Z = 0.45)
Trisomie 18    : NÉGATIF (Z = -0.32)
```

#### Étape 2 : Localiser la Section de Patterns

**Dans NRIS_Enhanced.py**, recherchez la section correspondante :

- **Nom du patient** : lignes ~1579-1593
- **MRN/ID** : lignes ~1596-1611
- **Âge maternel** : lignes ~1614-1630
- **Semaines de grossesse** : lignes ~1633-1649
- **Z-scores** : lignes ~1900-1921

#### Étape 3 : Ajouter Votre Pattern

##### Exemple : Ajouter un pattern pour "No. Dossier"

**Avant (lignes 1596-1611) :**
```python
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'Patient\s+ID[:\s]+([A-Za-z0-9\-]+)',
    r'Accession\s*#?[:\s]+([A-Za-z0-9\-]+)',
    # ...
]
```

**Après (ajouter votre pattern) :**
```python
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'Patient\s+ID[:\s]+([A-Za-z0-9\-]+)',
    r'Accession\s*#?[:\s]+([A-Za-z0-9\-]+)',
    r'No\.\s+Dossier[:\s]+([A-Za-z0-9\-]+)',  # ← NOUVEAU PATTERN
    # ...
]
```

##### Exemple : Z-Score avec Format Français

**Ligne ~1905 (Z21 pattern) :**

**Avant :**
```python
z21_patterns = [
    r'(?:Trisomy)?21[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
    r'T21[:\s]*Z[:\s]*[=:]?\s*(-?\d+\.?\d*)',
    # ...
]
```

**Après :**
```python
z21_patterns = [
    r'(?:Trisomy)?21[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
    r'T21[:\s]*Z[:\s]*[=:]?\s*(-?\d+\.?\d*)',
    r'Trisomie\s+21[:\s]*NÉGATIF[:\s]*\(Z\s*=\s*(-?\d+\.?\d*)\)',  # ← NOUVEAU
    # ...
]
```

#### Étape 4 : Tester Votre Modification

1. **Sauvegardez** NRIS_Enhanced.py
2. **Redémarrez** l'application
3. **Importez un PDF test** de votre laboratoire
4. **Vérifiez** que les données sont correctement extraites

### 2.4. Validation et Plages de Valeurs

Après extraction, le système valide les valeurs. Vous pouvez ajuster ces plages.

**Localisation :** lignes ~1448-1463 (fonctions `safe_float`, `safe_int`)

**Exemple : Plages de validation**

```python
# Ligne ~1618 : Validation de l'âge maternel
if age and (15 <= age <= 60):
    data['age'] = age

# Ligne ~1638 : Validation des semaines de grossesse
if weeks and (9 <= weeks <= 42):
    data['weeks'] = weeks

# Ligne ~1782 : Validation du Cff (%)
if cff and (0.5 <= cff <= 50):
    data['cff'] = cff

# Ligne ~1808 : Validation des Z-scores
if z_val and (-20 <= z_val <= 50):
    # Accepté
```

**Pour modifier :** Changez les valeurs min/max selon vos besoins cliniques.

### 2.5. Gestion des PDFs Scannés

Si vos PDFs sont **scannés** (images), le système ne peut pas extraire le texte directement.

**Solutions :**

#### Option A : Utiliser OCR (Reconnaissance Optique de Caractères)

**Installer pytesseract :**
```bash
pip install pytesseract pillow pdf2image
```

**Modifier NRIS_Enhanced.py (ajouter après ligne 42) :**

```python
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def extract_text_from_scanned_pdf(pdf_path):
    """Extract text from scanned PDF using OCR."""
    images = convert_from_path(pdf_path, dpi=300)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang='fra')  # ou 'eng'
    return text
```

**Dans la fonction `extract_data_from_pdf` (ligne ~1504), ajouter :**

```python
# Essayer extraction normale
page_text = page.extract_text()

# Si le texte est vide ou très court, essayer OCR
if not page_text or len(page_text.strip()) < 50:
    page_text = extract_text_from_scanned_pdf(pdf_file)
```

#### Option B : Demander aux fournisseurs des PDFs textuels

Contactez votre laboratoire pour obtenir des rapports en format **PDF textuel** plutôt que scanné.

### 2.6. Ajouter un Nouveau Champ de Données

Si votre laboratoire inclut des données supplémentaires (ex : ethnicité, jumeau, type de conception), vous pouvez les ajouter.

#### Étape 1 : Modifier la Base de Données

**Ajouter une colonne à la table `patients` :**

```python
# Dans la fonction init_database() (après ligne 554)
try:
    c.execute("ALTER TABLE patients ADD COLUMN ethnicity TEXT")
except sqlite3.OperationalError:
    pass  # Colonne déjà existante
```

#### Étape 2 : Ajouter l'Extraction

**Dans `extract_data_from_pdf` (après ligne 1593) :**

```python
# Extraction de l'ethnicité
ethnicity_patterns = [
    r'Ethnicity[:\s]+([A-Za-z\s]+)',
    r'Ethnie[:\s]+([A-Za-z\s]+)',
]
data['ethnicity'] = extract_with_fallback(text, ethnicity_patterns, default=None)
```

#### Étape 3 : Modifier le Stockage

**Dans la fonction `save_result` (ligne ~1200) :**

**Avant :**
```python
INSERT INTO patients (mrn_id, full_name, age, ...)
VALUES (?, ?, ?, ...)
```

**Après :**
```python
INSERT INTO patients (mrn_id, full_name, age, ethnicity, ...)
VALUES (?, ?, ?, ?, ...)
```

#### Étape 4 : Ajouter dans l'Interface

**Dans l'onglet Analysis (ligne ~3745), ajouter :**

```python
ethnicity = st.text_input("Ethnicity / Ethnie", key="ethnicity")
```

---

## 3. Modification des Paramètres Internes (Z-Scores, Rapports, etc.)

### 3.1. Configuration par Défaut

Tous les paramètres sont définis dans **DEFAULT_CONFIG** (lignes 50-76).

```python
DEFAULT_CONFIG = {
    'QC_THRESHOLDS': {
        'MIN_CFF': 3.5,           # % minimum de fraction fœtale
        'MAX_CFF': 50.0,          # % maximum de fraction fœtale
        'GC_RANGE': [37.0, 44.0], # Plage GC% acceptable
        'MIN_UNIQ_RATE': 68.0,    # % minimum de reads uniques
        'MAX_ERROR_RATE': 1.0,    # % maximum d'erreurs de séquençage
        'QS_LIMIT_NEG': 1.7,      # QS limite pour résultats négatifs
        'QS_LIMIT_POS': 2.0       # QS limite pour résultats positifs
    },
    'PANEL_READ_LIMITS': {
        'NIPT Basic': 5,      # Millions de reads
        'NIPT Standard': 7,
        'NIPT Plus': 12,
        'NIPT Pro': 20
    },
    'CLINICAL_THRESHOLDS': {
        'TRISOMY_LOW': 2.58,      # Z < 2.58 → Risque faible
        'TRISOMY_AMBIGUOUS': 6.0, # Z ≥ 6.0 → POSITIF
        'SCA_THRESHOLD': 4.5,     # Seuil pour aneuploïdie des chromosomes sexuels
        'RAT_POSITIVE': 8.0,      # Z ≥ 8.0 → RAT positif
        'RAT_AMBIGUOUS': 4.5      # Seuil ambiguë pour RAT
    },
    'REPORT_LANGUAGE': 'en',      # 'en' ou 'fr'
    'ALLOW_ALPHANUMERIC_MRN': False,
    'DEFAULT_SORT': 'id'          # 'id' ou 'mrn'
}
```

### 3.2. Méthode 1 : Modification via l'Interface (Recommandée)

L'application dispose d'un **onglet Settings** permettant de modifier les paramètres sans toucher au code.

#### Accéder aux Settings

1. **Connectez-vous** avec un compte admin
2. **Naviguez** vers l'onglet "⚙️ Settings"
3. **Modifiez** les valeurs dans les sections :
   - **QC Thresholds**
   - **Panel Read Limits**
   - **Clinical Thresholds**
   - **Report Settings**

#### Sauvegarder les Modifications

- Les modifications sont **automatiquement sauvegardées** dans `nris_config.json`
- Un **message de confirmation** s'affiche en haut de la page
- Les **nouvelles valeurs** sont utilisées immédiatement

### 3.3. Méthode 2 : Modification Directe du Fichier de Configuration

Si vous préférez modifier directement le fichier de configuration :

#### Localiser le Fichier

```bash
ls nris_config.json
```

Si le fichier n'existe pas, il sera créé au premier lancement de l'application.

#### Éditer le Fichier

**Exemple de `nris_config.json` :**

```json
{
  "QC_THRESHOLDS": {
    "MIN_CFF": 4.0,
    "MAX_CFF": 45.0,
    "GC_RANGE": [38.0, 43.0],
    "MIN_UNIQ_RATE": 70.0,
    "MAX_ERROR_RATE": 0.8,
    "QS_LIMIT_NEG": 1.5,
    "QS_LIMIT_POS": 1.8
  },
  "PANEL_READ_LIMITS": {
    "NIPT Basic": 6,
    "NIPT Standard": 8,
    "NIPT Plus": 15,
    "NIPT Pro": 25
  },
  "CLINICAL_THRESHOLDS": {
    "TRISOMY_LOW": 3.0,
    "TRISOMY_AMBIGUOUS": 7.0,
    "SCA_THRESHOLD": 5.0,
    "RAT_POSITIVE": 9.0,
    "RAT_AMBIGUOUS": 5.0
  },
  "REPORT_LANGUAGE": "fr",
  "ALLOW_ALPHANUMERIC_MRN": true,
  "DEFAULT_SORT": "mrn"
}
```

#### Appliquer les Modifications

**Redémarrez l'application** pour charger la nouvelle configuration.

### 3.4. Modifier la Logique d'Interprétation des Z-Scores

Si vous souhaitez modifier la **logique de classification** (au-delà des seuils), éditez les fonctions d'analyse.

#### Fonction : analyze_trisomy() (lignes 831-840)

**Logique actuelle :**

```python
def analyze_trisomy(z: float, config: dict) -> Tuple[str, str]:
    """Analyze trisomy Z-score."""
    low_thresh = config['CLINICAL_THRESHOLDS']['TRISOMY_LOW']
    ambig_thresh = config['CLINICAL_THRESHOLDS']['TRISOMY_AMBIGUOUS']

    if z < low_thresh:
        return ("Low Risk", "LOW")
    elif z < ambig_thresh:
        return (f"High Risk (Z:{z:.2f}) -> Re-library", "HIGH")
    else:
        return ("POSITIVE", "POSITIVE")
```

**Exemple de modification :** Ajouter une catégorie "MODÉRÉ"

```python
def analyze_trisomy(z: float, config: dict) -> Tuple[str, str]:
    """Analyze trisomy Z-score with MODERATE category."""
    low_thresh = config['CLINICAL_THRESHOLDS']['TRISOMY_LOW']
    moderate_thresh = 4.0  # Nouveau seuil
    ambig_thresh = config['CLINICAL_THRESHOLDS']['TRISOMY_AMBIGUOUS']

    if z < low_thresh:
        return ("Low Risk", "LOW")
    elif z < moderate_thresh:
        return (f"Moderate Risk (Z:{z:.2f}) -> Counsel patient", "MODERATE")
    elif z < ambig_thresh:
        return (f"High Risk (Z:{z:.2f}) -> Re-library", "HIGH")
    else:
        return ("POSITIVE", "POSITIVE")
```

### 3.5. Personnaliser les Rapports PDF

#### Langue du Rapport

**Via Settings :**
- Sélectionnez "English" ou "Français" dans l'onglet Settings

**Via Code (ligne ~2349) :**
```python
def generate_pdf_report(..., language='en'):
    # 'en' ou 'fr'
```

#### Modifier le Nom du Laboratoire

**Ligne ~2430 dans NRIS_Enhanced.py :**

```python
# En-tête du PDF
lab_name = "Votre Laboratoire de Génétique"  # ← Modifiez ici
pdf.setFont("Helvetica-Bold", 16)
pdf.drawCentredString(width / 2, height - 50, lab_name)
```

#### Ajouter un Logo

**Après ligne 2430, ajouter :**

```python
from reportlab.lib.utils import ImageReader

logo_path = "logo_labo.png"  # Chemin vers votre logo
logo = ImageReader(logo_path)
pdf.drawImage(logo, 50, height - 80, width=100, height=50, preserveAspectRatio=True)
```

#### Modifier le Pied de Page

**Ligne ~2820 :**

```python
footer_text = "Confidentiel - Usage médical uniquement"
pdf.drawCentredString(width / 2, 30, footer_text)
```

### 3.6. Tableau de Risque Maternel Basé sur l'Âge

Le système utilise des **tables de risque basées sur l'âge maternel** (Hook EB, 1981).

**Localisation :** lignes 2271-2319

**Pour mettre à jour avec de nouvelles données :**

```python
def get_maternal_age_risk(age: int, condition: str) -> str:
    """Get age-based prior risk."""
    risk_table = {
        20: {'T21': 1441, 'T18': 10000, 'T13': 14300},
        25: {'T21': 1340, 'T18': 8800, 'T13': 12700},
        30: {'T21': 895, 'T18': 6200, 'T13': 9100},
        35: {'T21': 356, 'T18': 2700, 'T13': 4200},
        40: {'T21': 97, 'T18': 860, 'T13': 1300},
        45: {'T21': 23, 'T18': 250, 'T13': 380},
        # Ajoutez ou modifiez les valeurs selon vos données
    }
    # ...
```

---

## 4. Ajout de Sécurité : Chiffrement des Données

**⚠️ IMPORTANT :** Le système de base NRIS Enhanced **ne chiffre PAS** les données dans la base de données SQLite. Les données sont stockées en clair.

Cette section vous guide pour implémenter le chiffrement si vous avez besoin de protéger les données sensibles (noms, MRN, résultats).

### 4.1. Pourquoi Chiffrer ?

- **Conformité réglementaire** (RGPD, HIPAA, etc.)
- **Protection contre les accès non autorisés** (vol de disque dur, backup)
- **Sécurité en transit** (si la DB est stockée sur un réseau)

### 4.2. Approches de Chiffrement

#### Option A : Chiffrement au Niveau des Colonnes (Recommandé)

Chiffrer uniquement les colonnes sensibles (nom, MRN) avant stockage.

**Avantages :**
- Performance acceptable
- Possibilité de recherche sur certains champs non chiffrés

**Inconvénients :**
- Nécessite modification du code
- Pas de recherche sur champs chiffrés

#### Option B : Chiffrement de Toute la Base de Données

Utiliser **SQLCipher** (extension SQLite avec chiffrement).

**Avantages :**
- Chiffrement transparent
- Aucune modification du code applicatif

**Inconvénients :**
- Nécessite installation de SQLCipher
- Légère baisse de performance

#### Option C : Chiffrement du Disque (Niveau OS)

Utiliser **LUKS** (Linux), **BitLocker** (Windows), **FileVault** (macOS).

**Avantages :**
- Pas de modification de l'application
- Protège tous les fichiers

**Inconvénients :**
- Ne protège que si le disque est démonté
- Ne protège pas contre un accès avec session ouverte

### 4.3. Implémentation : Chiffrement au Niveau des Colonnes

#### Étape 1 : Installer la Bibliothèque cryptography

```bash
pip install cryptography
```

#### Étape 2 : Créer un Module de Chiffrement

**Créer un nouveau fichier `encryption.py` :**

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os

class DataEncryptor:
    """Encrypt/decrypt sensitive data in the database."""

    def __init__(self, master_password: str):
        """
        Initialize encryptor with a master password.

        Args:
            master_password: Strong password used to derive encryption key
        """
        # Générer une clé à partir du mot de passe
        salt = b'nris_salt_2026_v1'  # Stockez ce salt de manière sécurisée
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return None
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string.

        Args:
            ciphertext: Encrypted string (base64 encoded)

        Returns:
            Decrypted string
        """
        if not ciphertext:
            return None
        decrypted = self.cipher.decrypt(ciphertext.encode())
        return decrypted.decode()

# Initialiser l'encrypteur global (utiliser un mot de passe fort)
# ⚠️ NE PAS stocker le mot de passe dans le code en production !
# Utilisez des variables d'environnement ou un gestionnaire de secrets
MASTER_PASSWORD = os.getenv('NRIS_MASTER_KEY', 'ChangeThisToAStrongPassword2026!')
encryptor = DataEncryptor(MASTER_PASSWORD)
```

#### Étape 3 : Modifier NRIS_Enhanced.py pour Utiliser le Chiffrement

**Ajouter l'import (après ligne 42) :**

```python
from encryption import encryptor
```

**Modifier la fonction save_result (ligne ~1200) :**

**Avant :**
```python
c.execute("""
    INSERT INTO patients (mrn_id, full_name, ...)
    VALUES (?, ?, ...)
""", (mrn, name, ...))
```

**Après (avec chiffrement) :**
```python
# Chiffrer les données sensibles
encrypted_mrn = encryptor.encrypt(mrn)
encrypted_name = encryptor.encrypt(name)

c.execute("""
    INSERT INTO patients (mrn_id, full_name, ...)
    VALUES (?, ?, ...)
""", (encrypted_mrn, encrypted_name, ...))
```

**Modifier les fonctions de lecture (exemple : Registry tab, ligne ~4568) :**

**Avant :**
```python
df = pd.read_sql("SELECT mrn_id, full_name, ... FROM patients", conn)
```

**Après (avec déchiffrement) :**
```python
df = pd.read_sql("SELECT mrn_id, full_name, ... FROM patients", conn)

# Déchiffrer les colonnes sensibles
df['mrn_id'] = df['mrn_id'].apply(lambda x: encryptor.decrypt(x) if x else None)
df['full_name'] = df['full_name'].apply(lambda x: encryptor.decrypt(x) if x else None)
```

#### Étape 4 : Gestion Sécurisée du Mot de Passe Maître

**⚠️ CRITIQUE :** Ne jamais stocker le mot de passe en clair dans le code !

**Méthode 1 : Variable d'Environnement**

```bash
# Linux/macOS
export NRIS_MASTER_KEY="VotreMotDePasseTrèsSecurisé2026!"

# Windows
set NRIS_MASTER_KEY=VotreMotDePasseTrèsSecurisé2026!
```

**Méthode 2 : Fichier de Configuration Sécurisé**

```python
# Dans encryption.py
import json

def load_master_key():
    """Load master key from secure config file."""
    with open('/secure/path/nris_key.json', 'r') as f:
        config = json.load(f)
    return config['master_key']

MASTER_PASSWORD = load_master_key()
```

**Protéger le fichier :**
```bash
chmod 600 /secure/path/nris_key.json  # Lecture/écriture uniquement pour le propriétaire
```

**Méthode 3 : Gestionnaire de Secrets (Production)**

Pour un environnement de production, utilisez :
- **AWS Secrets Manager**
- **Azure Key Vault**
- **HashiCorp Vault**
- **Google Cloud Secret Manager**

### 4.4. Implémentation : Chiffrement avec SQLCipher

#### Étape 1 : Installer SQLCipher

**Ubuntu/Debian :**
```bash
sudo apt-get install sqlcipher libsqlcipher-dev
pip install pysqlcipher3
```

**macOS :**
```bash
brew install sqlcipher
pip install pysqlcipher3
```

**Windows :**
Téléchargez le binaire depuis https://www.zetetic.net/sqlcipher/

#### Étape 2 : Modifier le Code de Connexion

**Dans NRIS_Enhanced.py, ligne ~418 :**

**Avant :**
```python
import sqlite3

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn
```

**Après (avec SQLCipher) :**
```python
from pysqlcipher3 import dbapi2 as sqlite3

DB_PASSWORD = os.getenv('NRIS_DB_PASSWORD', 'StrongDBPassword2026!')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(f"PRAGMA key = '{DB_PASSWORD}'")
    return conn
```

#### Étape 3 : Migrer la Base Existante

Si vous avez déjà une base non chiffrée, migrez-la :

```python
import sqlite3
from pysqlcipher3 import dbapi2 as sqlcipher

# Connexion à l'ancienne DB (non chiffrée)
old_conn = sqlite3.connect('nipt_registry_v2.db')

# Connexion à la nouvelle DB (chiffrée)
new_conn = sqlcipher.connect('nipt_registry_v2_encrypted.db')
new_conn.execute("PRAGMA key = 'VotreMotDePasse'")

# Copier toutes les données
old_conn.backup(new_conn)

old_conn.close()
new_conn.close()

# Renommer les fichiers
os.rename('nipt_registry_v2.db', 'nipt_registry_v2_OLD.db')
os.rename('nipt_registry_v2_encrypted.db', 'nipt_registry_v2.db')
```

### 4.5. Implémentation : Chiffrement au Niveau du Disque

#### Linux (LUKS)

**Créer une partition chiffrée :**

```bash
# Créer un volume chiffré
sudo cryptsetup luksFormat /dev/sdX

# Ouvrir le volume
sudo cryptsetup luksOpen /dev/sdX nris_encrypted

# Formater et monter
sudo mkfs.ext4 /dev/mapper/nris_encrypted
sudo mount /dev/mapper/nris_encrypted /mnt/nris_data

# Déplacer la base de données
sudo mv nipt_registry_v2.db /mnt/nris_data/
sudo ln -s /mnt/nris_data/nipt_registry_v2.db nipt_registry_v2.db
```

#### Windows (BitLocker)

1. **Ouvrir le Panneau de configuration** → BitLocker
2. **Activer BitLocker** sur le disque contenant l'application
3. **Choisir un mode de déverrouillage** (mot de passe, clé USB, TPM)
4. **Sauvegarder la clé de récupération** (CRITIQUE !)

#### macOS (FileVault)

1. **Préférences Système** → **Sécurité et confidentialité**
2. **Onglet FileVault** → **Activer FileVault**
3. **Choisir la méthode de récupération** (compte iCloud ou clé)

### 4.6. Chiffrement des Sauvegardes

Les sauvegardes du dossier `backups/` doivent également être chiffrées.

**Créer un script de sauvegarde chiffré :**

```bash
#!/bin/bash
# backup_encrypted.sh

BACKUP_DIR="/secure/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="nris_backup_${TIMESTAMP}.tar.gz.gpg"

# Créer l'archive
tar czf - nipt_registry_v2.db nris_config.json | \
gpg --symmetric --cipher-algo AES256 -o "${BACKUP_DIR}/${BACKUP_FILE}"

echo "Backup créé : ${BACKUP_FILE}"

# Supprimer les sauvegardes de plus de 30 jours
find ${BACKUP_DIR} -name "nris_backup_*.tar.gz.gpg" -mtime +30 -delete
```

**Rendre le script exécutable :**
```bash
chmod +x backup_encrypted.sh
```

**Restaurer une sauvegarde :**
```bash
gpg --decrypt nris_backup_20260114_120000.tar.gz.gpg | tar xzf -
```

### 4.7. Chiffrement en Transit (HTTPS)

Si vous déployez NRIS sur un serveur web, utilisez **HTTPS**.

**Avec Streamlit + NGINX :**

```nginx
# /etc/nginx/sites-available/nris
server {
    listen 443 ssl;
    server_name nris.votrelabo.com;

    ssl_certificate /etc/letsencrypt/live/nris.votrelabo.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nris.votrelabo.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Obtenir un certificat SSL gratuit avec Let's Encrypt :**
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d nris.votrelabo.com
```

---

## 5. Sauvegarde et Restauration

### 5.1. Sauvegarde Manuelle

**Fichiers à sauvegarder :**
- `nipt_registry_v2.db` (base de données)
- `nris_config.json` (configuration)
- `backups/` (dossier de sauvegardes automatiques)
- `NRIS_Enhanced.py` (si modifié)

**Commande simple :**
```bash
tar czf nris_backup_$(date +%Y%m%d).tar.gz \
    nipt_registry_v2.db \
    nris_config.json \
    backups/ \
    NRIS_Enhanced.py
```

### 5.2. Sauvegarde Automatique

**Créer un script cron (Linux/macOS) :**

```bash
# Éditer crontab
crontab -e

# Ajouter une ligne pour sauvegarder chaque jour à 2h du matin
0 2 * * * /chemin/vers/backup_encrypted.sh
```

**Créer une tâche planifiée (Windows) :**

1. **Ouvrir le Planificateur de tâches**
2. **Créer une tâche de base**
3. **Configurer pour s'exécuter quotidiennement**
4. **Action** : Exécuter `backup_script.bat`

### 5.3. Restauration

**Restaurer depuis une sauvegarde :**

```bash
# Arrêter l'application

# Extraire la sauvegarde
tar xzf nris_backup_20260114.tar.gz

# OU si chiffrée avec GPG
gpg --decrypt nris_backup_20260114.tar.gz.gpg | tar xzf -

# Redémarrer l'application
streamlit run NRIS_Enhanced.py
```

### 5.4. Migration vers un Nouveau Serveur

**Sur l'ancien serveur :**
```bash
# Créer une sauvegarde complète
tar czf nris_migration.tar.gz NRIS_Enhanced.py nipt_registry_v2.db nris_config.json
```

**Sur le nouveau serveur :**
```bash
# Installer Python et dépendances
pip install streamlit pandas numpy PyPDF2 reportlab

# Extraire la sauvegarde
tar xzf nris_migration.tar.gz

# Tester la base de données
sqlite3 nipt_registry_v2.db "PRAGMA integrity_check;"

# Lancer l'application
streamlit run NRIS_Enhanced.py
```

---

## 6. Dépannage

### 6.1. Problèmes d'Import PDF

#### Problème : Aucune donnée extraite

**Causes possibles :**
1. PDF scanné (image) au lieu de PDF textuel
2. Format de rapport non supporté
3. Encodage de caractères non standard

**Solutions :**
- Vérifier que le PDF contient du texte (essayer de copier-coller du texte)
- Ajouter des patterns regex pour votre format (voir section 2.3)
- Utiliser OCR pour les PDFs scannés (voir section 2.5)

#### Problème : Extraction partielle

**Solution :**
- Activer le mode debug en ajoutant dans `extract_data_from_pdf` (ligne ~1500) :
  ```python
  print(f"Texte extrait : {text[:500]}")  # Afficher les 500 premiers caractères
  ```
- Identifier quels champs manquent
- Ajouter des patterns regex appropriés

### 6.2. Problèmes de Configuration

#### Problème : Modifications non appliquées

**Solutions :**
1. Vérifier que `nris_config.json` est bien dans le même dossier que `NRIS_Enhanced.py`
2. Vérifier la syntaxe JSON (utiliser https://jsonlint.com)
3. Redémarrer complètement l'application (Ctrl+C puis relancer)

#### Problème : Configuration réinitialisée

**Cause :** Le fichier `nris_config.json` a été supprimé ou corrompu.

**Solution :**
- Restaurer depuis `backups/backup_X.json`
- Ou reconfigurer via l'onglet Settings

### 6.3. Problèmes de Chiffrement

#### Problème : "Decryption failed" ou "Invalid token"

**Cause :** Mauvais mot de passe maître.

**Solution :**
- Vérifier la variable d'environnement `NRIS_MASTER_KEY`
- Si le mot de passe a été changé, vous devez déchiffrer avec l'ancien puis rechiffrer avec le nouveau

#### Problème : Base de données corrompue après migration SQLCipher

**Solution :**
1. Restaurer la sauvegarde non chiffrée
2. Refaire la migration avec le bon mot de passe
3. Tester l'intégrité : `PRAGMA integrity_check;`

### 6.4. Problèmes de Performance

#### Problème : Application lente après chiffrement

**Solutions :**
- Utiliser le chiffrement au niveau colonnes uniquement pour les champs sensibles
- Ajouter des index sur les colonnes fréquemment recherchées :
  ```sql
  CREATE INDEX idx_encrypted_mrn ON patients(mrn_id);
  ```
- Augmenter la RAM allouée à SQLite :
  ```python
  conn.execute("PRAGMA cache_size = -64000")  # 64 MB
  ```

### 6.5. Support et Aide

**Ressources :**
- **Documentation SQLite :** https://www.sqlite.org/docs.html
- **Documentation Streamlit :** https://docs.streamlit.io
- **Regex101 (test de regex) :** https://regex101.com
- **Cryptography Library :** https://cryptography.io/en/latest/

**Logs de débogage :**

Ajouter dans `NRIS_Enhanced.py` (au début) :

```python
import logging

logging.basicConfig(
    filename='nris_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

Puis utiliser dans le code :
```python
logger.debug("Extraction PDF démarrée")
logger.info(f"Données extraites : {data}")
logger.error(f"Erreur : {e}")
```

---

## Annexe A : Checklist de Personnalisation

- [ ] Analyser les templates PDF de votre laboratoire
- [ ] Ajouter les patterns regex nécessaires dans `extract_data_from_pdf`
- [ ] Tester l'import avec plusieurs PDFs types
- [ ] Configurer les seuils cliniques selon vos protocoles
- [ ] Configurer les limites QC (Cff, GC, reads, etc.)
- [ ] Personnaliser le nom du laboratoire dans les rapports PDF
- [ ] Ajouter le logo du laboratoire (optionnel)
- [ ] Décider du niveau de chiffrement requis (colonnes, DB complète, disque)
- [ ] Implémenter le chiffrement choisi
- [ ] Tester le chiffrement/déchiffrement
- [ ] Configurer les sauvegardes automatiques
- [ ] Tester la restauration depuis une sauvegarde
- [ ] Documenter les modifications spécifiques à votre laboratoire
- [ ] Former le personnel sur les nouvelles fonctionnalités

---

## Annexe B : Glossaire

| Terme | Définition |
|-------|------------|
| **Cff** | Cell-free fetal DNA fraction (% d'ADN fœtal dans le plasma maternel) |
| **GC%** | Pourcentage de bases guanine-cytosine dans les séquences |
| **MRN** | Medical Record Number (numéro de dossier médical) |
| **NIPT** | Non-Invasive Prenatal Testing (dépistage prénatal non invasif) |
| **OCR** | Optical Character Recognition (reconnaissance optique de caractères) |
| **QC** | Quality Control (contrôle qualité) |
| **QS** | Quality Score (score de qualité du séquençage) |
| **RAT** | Rare Autosomal Trisomy (trisomie autosomale rare) |
| **SCA** | Sex Chromosome Aneuploidy (aneuploïdie des chromosomes sexuels) |
| **Z-score** | Score statistique mesurant l'écart par rapport à la normale |

---

## Annexe C : Exemples de Patterns Regex Courants

```python
# Numéro de dossier
r'MRN[:\s]+(\d{7})'
r'Dossier[:\s]+([A-Z0-9\-]+)'
r'ID[:\s]*#?(\d+)'

# Date (format JJ/MM/AAAA)
r'(\d{2}/\d{2}/\d{4})'

# Date (format AAAA-MM-JJ)
r'(\d{4}-\d{2}-\d{2})'

# Pourcentage
r'(\d+\.?\d*)\s*%'

# Z-score
r'Z[:\s]*=?\s*(-?\d+\.?\d+)'

# Résultat positif/négatif
r'(POSITIF|NÉGATIF|POSITIVE|NEGATIVE)'

# Nom complet (avec accents)
r'([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)'

# Âge
r'(\d{2})\s*ans?'
r'Age[:\s]+(\d+)'
```

---

**Fin du Guide de Personnalisation NRIS Enhanced**

Pour toute question ou assistance supplémentaire, consultez les ressources en ligne ou contactez le développeur du système.

---

**Version :** 2.4
**Dernière mise à jour :** Janvier 2026
**Auteur :** Système NRIS Enhanced
**Licence :** Usage interne de laboratoire uniquement
