# NRIS Enhanced Customization Guide

**Version 2.4** | Date: January 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Adapting PDF Import to Laboratory Templates](#2-adapting-pdf-import-to-laboratory-templates)
3. [Modifying Internal Parameters (Z-Scores, Reports, etc.)](#3-modifying-internal-parameters-z-scores-reports-etc)
4. [Adding Security: Data Encryption](#4-adding-security-data-encryption)
5. [Backup and Restore](#5-backup-and-restore)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Introduction

This guide is intended for laboratories wishing to customize the NRIS Enhanced system to meet their specific needs. It covers three main aspects:

- **PDF import customization** to adapt to different NIPT report formats
- **Modification of clinical parameters** (Z-score thresholds, QC parameters, etc.)
- **Data encryption implementation** (not included in the base system)

### Prerequisites

- Basic knowledge of Python 3.8+
- Access to NRIS Enhanced source files
- Write permissions on the application folder
- Text editor or IDE (VSCode, PyCharm, etc.)

### Main Files

| File | Description |
|------|-------------|
| `NRIS_Enhanced.py` | Main file (5,673 lines) |
| `nris_config.json` | Custom configuration |
| `nipt_registry_v2.db` | SQLite database |
| `backups/` | Backup folder |

---

## 2. Adapting PDF Import to Laboratory Templates

### 2.1. Understanding the Current Extraction System

The system uses **PyPDF2** to extract text from PDFs, then applies **regular expressions (regex)** to identify and extract data.

**Code location:** `NRIS_Enhanced.py`, lines **1477-2245**

**Main function:** `extract_data_from_pdf(pdf_file)`

#### Extraction Flow

```
PDF → PyPDF2.PdfReader → Text extraction → Normalization
  ↓
Regex patterns (multiple variants per field)
  ↓
Value validation (acceptable ranges)
  ↓
Dictionary of extracted data
```

### 2.2. Regex Pattern Structure

Each data field has **multiple patterns** to handle different report formats.

#### Example: Patient Name Extraction

**Lines 1579-1593 in NRIS_Enhanced.py**

```python
name_patterns = [
    r'(?:Patient|Patient\s+Name|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|ID|Age|DOB|...))',
    r'Full\s+Name[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|\n|$))',
    r'Patient\s*:\s*([A-Za-z][A-Za-z\s\-\'\.]+)',
    # ... other patterns
]
```

**Strategy:**
- Try each pattern in order
- Keep the first valid match
- Apply validation (length, allowed characters)

### 2.3. How to Add a New PDF Format

#### Step 1: Analyze Your PDF Template

1. **Open a sample report** from your laboratory
2. **Note the exact structure** of sections
3. **Identify the labels** used for each field

**Example report:**
```
GeneDx Laboratory
-------------------
Patient Name       : Marie DUPONT
File No.          : MRN-2024-0123
Maternal Age      : 32 years
Gestational Age   : 12+3 weeks
-------------------
NIPT Results
Trisomy 21        : NEGATIVE (Z = 0.45)
Trisomy 18        : NEGATIVE (Z = -0.32)
```

#### Step 2: Locate the Pattern Section

**In NRIS_Enhanced.py**, search for the corresponding section:

- **Patient name** : lines ~1579-1593
- **MRN/ID** : lines ~1596-1611
- **Maternal age** : lines ~1614-1630
- **Gestational weeks** : lines ~1633-1649
- **Z-scores** : lines ~1900-1921

#### Step 3: Add Your Pattern

##### Example: Adding a pattern for "File No."

**Before (lines 1596-1611):**
```python
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'Patient\s+ID[:\s]+([A-Za-z0-9\-]+)',
    r'Accession\s*#?[:\s]+([A-Za-z0-9\-]+)',
    # ...
]
```

**After (add your pattern):**
```python
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'Patient\s+ID[:\s]+([A-Za-z0-9\-]+)',
    r'Accession\s*#?[:\s]+([A-Za-z0-9\-]+)',
    r'File\s+No\.[:\s]+([A-Za-z0-9\-]+)',  # ← NEW PATTERN
    # ...
]
```

##### Example: Z-Score with French Format

**Line ~1905 (Z21 pattern):**

**Before:**
```python
z21_patterns = [
    r'(?:Trisomy)?21[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
    r'T21[:\s]*Z[:\s]*[=:]?\s*(-?\d+\.?\d*)',
    # ...
]
```

**After:**
```python
z21_patterns = [
    r'(?:Trisomy)?21[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
    r'T21[:\s]*Z[:\s]*[=:]?\s*(-?\d+\.?\d*)',
    r'Trisomie\s+21[:\s]*NÉGATIF[:\s]*\(Z\s*=\s*(-?\d+\.?\d*)\)',  # ← NEW
    # ...
]
```

#### Step 4: Test Your Modification

1. **Save** NRIS_Enhanced.py
2. **Restart** the application
3. **Import a test PDF** from your laboratory
4. **Verify** that data is correctly extracted

### 2.4. Validation and Value Ranges

After extraction, the system validates values. You can adjust these ranges.

**Location:** lines ~1448-1463 (functions `safe_float`, `safe_int`)

**Example: Validation ranges**

```python
# Line ~1618: Maternal age validation
if age and (15 <= age <= 60):
    data['age'] = age

# Line ~1638: Gestational weeks validation
if weeks and (9 <= weeks <= 42):
    data['weeks'] = weeks

# Line ~1782: Cff (%) validation
if cff and (0.5 <= cff <= 50):
    data['cff'] = cff

# Line ~1808: Z-score validation
if z_val and (-20 <= z_val <= 50):
    # Accepted
```

**To modify:** Change min/max values according to your clinical needs.

### 2.5. Handling Scanned PDFs

If your PDFs are **scanned** (images), the system cannot extract text directly.

**Solutions:**

#### Option A: Use OCR (Optical Character Recognition)

**Install pytesseract:**
```bash
pip install pytesseract pillow pdf2image
```

**Modify NRIS_Enhanced.py (add after line 42):**

```python
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

def extract_text_from_scanned_pdf(pdf_path):
    """Extract text from scanned PDF using OCR."""
    images = convert_from_path(pdf_path, dpi=300)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang='eng')  # or 'fra'
    return text
```

**In the `extract_data_from_pdf` function (line ~1504), add:**

```python
# Try normal extraction
page_text = page.extract_text()

# If text is empty or very short, try OCR
if not page_text or len(page_text.strip()) < 50:
    page_text = extract_text_from_scanned_pdf(pdf_file)
```

#### Option B: Request Text PDFs from Providers

Contact your laboratory to obtain reports in **text PDF** format rather than scanned.

### 2.6. Adding a New Data Field

If your laboratory includes additional data (e.g., ethnicity, twin, conception type), you can add them.

#### Step 1: Modify the Database

**Add a column to the `patients` table:**

```python
# In the init_database() function (after line 554)
try:
    c.execute("ALTER TABLE patients ADD COLUMN ethnicity TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists
```

#### Step 2: Add Extraction

**In `extract_data_from_pdf` (after line 1593):**

```python
# Ethnicity extraction
ethnicity_patterns = [
    r'Ethnicity[:\s]+([A-Za-z\s]+)',
    r'Ethnie[:\s]+([A-Za-z\s]+)',
]
data['ethnicity'] = extract_with_fallback(text, ethnicity_patterns, default=None)
```

#### Step 3: Modify Storage

**In the `save_result` function (line ~1200):**

**Before:**
```python
INSERT INTO patients (mrn_id, full_name, age, ...)
VALUES (?, ?, ?, ...)
```

**After:**
```python
INSERT INTO patients (mrn_id, full_name, age, ethnicity, ...)
VALUES (?, ?, ?, ?, ...)
```

#### Step 4: Add to Interface

**In the Analysis tab (line ~3745), add:**

```python
ethnicity = st.text_input("Ethnicity / Ethnie", key="ethnicity")
```

---

## 3. Modifying Internal Parameters (Z-Scores, Reports, etc.)

### 3.1. Default Configuration

All parameters are defined in **DEFAULT_CONFIG** (lines 50-76).

```python
DEFAULT_CONFIG = {
    'QC_THRESHOLDS': {
        'MIN_CFF': 3.5,           # Minimum fetal fraction %
        'MAX_CFF': 50.0,          # Maximum fetal fraction %
        'GC_RANGE': [37.0, 44.0], # Acceptable GC% range
        'MIN_UNIQ_RATE': 68.0,    # Minimum unique reads %
        'MAX_ERROR_RATE': 1.0,    # Maximum sequencing error %
        'QS_LIMIT_NEG': 1.7,      # QS limit for negative results
        'QS_LIMIT_POS': 2.0       # QS limit for positive results
    },
    'PANEL_READ_LIMITS': {
        'NIPT Basic': 5,      # Millions of reads
        'NIPT Standard': 7,
        'NIPT Plus': 12,
        'NIPT Pro': 20
    },
    'CLINICAL_THRESHOLDS': {
        'TRISOMY_LOW': 2.58,      # Z < 2.58 → Low risk
        'TRISOMY_AMBIGUOUS': 6.0, # Z ≥ 6.0 → POSITIVE
        'SCA_THRESHOLD': 4.5,     # Threshold for sex chromosome aneuploidy
        'RAT_POSITIVE': 8.0,      # Z ≥ 8.0 → RAT positive
        'RAT_AMBIGUOUS': 4.5      # Ambiguous threshold for RAT
    },
    'REPORT_LANGUAGE': 'en',      # 'en' or 'fr'
    'ALLOW_ALPHANUMERIC_MRN': False,
    'DEFAULT_SORT': 'id'          # 'id' or 'mrn'
}
```

### 3.2. Method 1: Modification via Interface (Recommended)

The application has a **Settings tab** allowing you to modify parameters without touching the code.

#### Access Settings

1. **Log in** with an admin account
2. **Navigate** to the "⚙️ Settings" tab
3. **Modify** values in the sections:
   - **QC Thresholds**
   - **Panel Read Limits**
   - **Clinical Thresholds**
   - **Report Settings**

#### Save Modifications

- Modifications are **automatically saved** in `nris_config.json`
- A **confirmation message** appears at the top of the page
- **New values** are used immediately

### 3.3. Method 2: Direct Configuration File Modification

If you prefer to modify the configuration file directly:

#### Locate the File

```bash
ls nris_config.json
```

If the file doesn't exist, it will be created at the first application launch.

#### Edit the File

**Example `nris_config.json`:**

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

#### Apply Modifications

**Restart the application** to load the new configuration.

### 3.4. Modify Z-Score Interpretation Logic

If you want to modify the **classification logic** (beyond thresholds), edit the analysis functions.

#### Function: analyze_trisomy() (lines 831-840)

**Current logic:**

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

**Example modification:** Add a "MODERATE" category

```python
def analyze_trisomy(z: float, config: dict) -> Tuple[str, str]:
    """Analyze trisomy Z-score with MODERATE category."""
    low_thresh = config['CLINICAL_THRESHOLDS']['TRISOMY_LOW']
    moderate_thresh = 4.0  # New threshold
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

### 3.5. Customize PDF Reports

#### Report Language

**Via Settings:**
- Select "English" or "Français" in the Settings tab

**Via Code (line ~2349):**
```python
def generate_pdf_report(..., language='en'):
    # 'en' or 'fr'
```

#### Modify Laboratory Name

**Line ~2430 in NRIS_Enhanced.py:**

```python
# PDF header
lab_name = "Your Genetics Laboratory"  # ← Modify here
pdf.setFont("Helvetica-Bold", 16)
pdf.drawCentredString(width / 2, height - 50, lab_name)
```

#### Add a Logo

**After line 2430, add:**

```python
from reportlab.lib.utils import ImageReader

logo_path = "lab_logo.png"  # Path to your logo
logo = ImageReader(logo_path)
pdf.drawImage(logo, 50, height - 80, width=100, height=50, preserveAspectRatio=True)
```

#### Modify Footer

**Line ~2820:**

```python
footer_text = "Confidential - Medical use only"
pdf.drawCentredString(width / 2, 30, footer_text)
```

### 3.6. Maternal Age Risk Table

The system uses **age-based risk tables** (Hook EB, 1981).

**Location:** lines 2271-2319

**To update with new data:**

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
        # Add or modify values according to your data
    }
    # ...
```

---

## 4. Adding Security: Data Encryption

**⚠️ IMPORTANT:** The base NRIS Enhanced system **does NOT encrypt** data in the SQLite database. Data is stored in plain text.

This section guides you to implement encryption if you need to protect sensitive data (names, MRN, results).

### 4.1. Why Encrypt?

- **Regulatory compliance** (GDPR, HIPAA, etc.)
- **Protection against unauthorized access** (disk theft, backup)
- **Security in transit** (if DB is stored on a network)

### 4.2. Encryption Approaches

#### Option A: Column-Level Encryption (Recommended)

Encrypt only sensitive columns (name, MRN) before storage.

**Advantages:**
- Acceptable performance
- Ability to search on some non-encrypted fields

**Disadvantages:**
- Requires code modification
- No search on encrypted fields

#### Option B: Full Database Encryption

Use **SQLCipher** (SQLite extension with encryption).

**Advantages:**
- Transparent encryption
- No application code modification

**Disadvantages:**
- Requires SQLCipher installation
- Slight performance decrease

#### Option C: Disk Encryption (OS Level)

Use **LUKS** (Linux), **BitLocker** (Windows), **FileVault** (macOS).

**Advantages:**
- No application modification
- Protects all files

**Disadvantages:**
- Only protects if disk is unmounted
- Does not protect against access with open session

### 4.3. Implementation: Column-Level Encryption

#### Step 1: Install cryptography Library

```bash
pip install cryptography
```

#### Step 2: Create an Encryption Module

**Create a new file `encryption.py`:**

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
        # Generate a key from the password
        salt = b'nris_salt_2026_v1'  # Store this salt securely
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

# Initialize global encryptor (use a strong password)
# ⚠️ DO NOT store the password in code in production!
# Use environment variables or a secrets manager
MASTER_PASSWORD = os.getenv('NRIS_MASTER_KEY', 'ChangeThisToAStrongPassword2026!')
encryptor = DataEncryptor(MASTER_PASSWORD)
```

#### Step 3: Modify NRIS_Enhanced.py to Use Encryption

**Add import (after line 42):**

```python
from encryption import encryptor
```

**Modify the save_result function (line ~1200):**

**Before:**
```python
c.execute("""
    INSERT INTO patients (mrn_id, full_name, ...)
    VALUES (?, ?, ...)
""", (mrn, name, ...))
```

**After (with encryption):**
```python
# Encrypt sensitive data
encrypted_mrn = encryptor.encrypt(mrn)
encrypted_name = encryptor.encrypt(name)

c.execute("""
    INSERT INTO patients (mrn_id, full_name, ...)
    VALUES (?, ?, ...)
""", (encrypted_mrn, encrypted_name, ...))
```

**Modify read functions (example: Registry tab, line ~4568):**

**Before:**
```python
df = pd.read_sql("SELECT mrn_id, full_name, ... FROM patients", conn)
```

**After (with decryption):**
```python
df = pd.read_sql("SELECT mrn_id, full_name, ... FROM patients", conn)

# Decrypt sensitive columns
df['mrn_id'] = df['mrn_id'].apply(lambda x: encryptor.decrypt(x) if x else None)
df['full_name'] = df['full_name'].apply(lambda x: encryptor.decrypt(x) if x else None)
```

#### Step 4: Secure Master Password Management

**⚠️ CRITICAL:** Never store the password in plain text in code!

**Method 1: Environment Variable**

```bash
# Linux/macOS
export NRIS_MASTER_KEY="YourVerySecurePassword2026!"

# Windows
set NRIS_MASTER_KEY=YourVerySecurePassword2026!
```

**Method 2: Secure Configuration File**

```python
# In encryption.py
import json

def load_master_key():
    """Load master key from secure config file."""
    with open('/secure/path/nris_key.json', 'r') as f:
        config = json.load(f)
    return config['master_key']

MASTER_PASSWORD = load_master_key()
```

**Protect the file:**
```bash
chmod 600 /secure/path/nris_key.json  # Read/write only for owner
```

**Method 3: Secrets Manager (Production)**

For a production environment, use:
- **AWS Secrets Manager**
- **Azure Key Vault**
- **HashiCorp Vault**
- **Google Cloud Secret Manager**

### 4.4. Implementation: Encryption with SQLCipher

#### Step 1: Install SQLCipher

**Ubuntu/Debian:**
```bash
sudo apt-get install sqlcipher libsqlcipher-dev
pip install pysqlcipher3
```

**macOS:**
```bash
brew install sqlcipher
pip install pysqlcipher3
```

**Windows:**
Download the binary from https://www.zetetic.net/sqlcipher/

#### Step 2: Modify Connection Code

**In NRIS_Enhanced.py, line ~418:**

**Before:**
```python
import sqlite3

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn
```

**After (with SQLCipher):**
```python
from pysqlcipher3 import dbapi2 as sqlite3

DB_PASSWORD = os.getenv('NRIS_DB_PASSWORD', 'StrongDBPassword2026!')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(f"PRAGMA key = '{DB_PASSWORD}'")
    return conn
```

#### Step 3: Migrate Existing Database

If you already have an unencrypted database, migrate it:

```python
import sqlite3
from pysqlcipher3 import dbapi2 as sqlcipher

# Connect to old DB (unencrypted)
old_conn = sqlite3.connect('nipt_registry_v2.db')

# Connect to new DB (encrypted)
new_conn = sqlcipher.connect('nipt_registry_v2_encrypted.db')
new_conn.execute("PRAGMA key = 'YourPassword'")

# Copy all data
old_conn.backup(new_conn)

old_conn.close()
new_conn.close()

# Rename files
os.rename('nipt_registry_v2.db', 'nipt_registry_v2_OLD.db')
os.rename('nipt_registry_v2_encrypted.db', 'nipt_registry_v2.db')
```

### 4.5. Implementation: Disk-Level Encryption

#### Linux (LUKS)

**Create an encrypted partition:**

```bash
# Create an encrypted volume
sudo cryptsetup luksFormat /dev/sdX

# Open the volume
sudo cryptsetup luksOpen /dev/sdX nris_encrypted

# Format and mount
sudo mkfs.ext4 /dev/mapper/nris_encrypted
sudo mount /dev/mapper/nris_encrypted /mnt/nris_data

# Move the database
sudo mv nipt_registry_v2.db /mnt/nris_data/
sudo ln -s /mnt/nris_data/nipt_registry_v2.db nipt_registry_v2.db
```

#### Windows (BitLocker)

1. **Open Control Panel** → BitLocker
2. **Enable BitLocker** on the disk containing the application
3. **Choose an unlock mode** (password, USB key, TPM)
4. **Save the recovery key** (CRITICAL!)

#### macOS (FileVault)

1. **System Preferences** → **Security & Privacy**
2. **FileVault tab** → **Enable FileVault**
3. **Choose recovery method** (iCloud account or key)

### 4.6. Backup Encryption

Backups in the `backups/` folder should also be encrypted.

**Create an encrypted backup script:**

```bash
#!/bin/bash
# backup_encrypted.sh

BACKUP_DIR="/secure/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="nris_backup_${TIMESTAMP}.tar.gz.gpg"

# Create the archive
tar czf - nipt_registry_v2.db nris_config.json | \
gpg --symmetric --cipher-algo AES256 -o "${BACKUP_DIR}/${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"

# Remove backups older than 30 days
find ${BACKUP_DIR} -name "nris_backup_*.tar.gz.gpg" -mtime +30 -delete
```

**Make the script executable:**
```bash
chmod +x backup_encrypted.sh
```

**Restore a backup:**
```bash
gpg --decrypt nris_backup_20260114_120000.tar.gz.gpg | tar xzf -
```

### 4.7. Encryption in Transit (HTTPS)

If you deploy NRIS on a web server, use **HTTPS**.

**With Streamlit + NGINX:**

```nginx
# /etc/nginx/sites-available/nris
server {
    listen 443 ssl;
    server_name nris.yourlab.com;

    ssl_certificate /etc/letsencrypt/live/nris.yourlab.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nris.yourlab.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Get a free SSL certificate with Let's Encrypt:**
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d nris.yourlab.com
```

---

## 5. Backup and Restore

### 5.1. Manual Backup

**Files to backup:**
- `nipt_registry_v2.db` (database)
- `nris_config.json` (configuration)
- `backups/` (automatic backups folder)
- `NRIS_Enhanced.py` (if modified)

**Simple command:**
```bash
tar czf nris_backup_$(date +%Y%m%d).tar.gz \
    nipt_registry_v2.db \
    nris_config.json \
    backups/ \
    NRIS_Enhanced.py
```

### 5.2. Automatic Backup

**Create a cron script (Linux/macOS):**

```bash
# Edit crontab
crontab -e

# Add a line to backup daily at 2 AM
0 2 * * * /path/to/backup_encrypted.sh
```

**Create a scheduled task (Windows):**

1. **Open Task Scheduler**
2. **Create a basic task**
3. **Configure to run daily**
4. **Action**: Execute `backup_script.bat`

### 5.3. Restore

**Restore from backup:**

```bash
# Stop the application

# Extract the backup
tar xzf nris_backup_20260114.tar.gz

# OR if encrypted with GPG
gpg --decrypt nris_backup_20260114.tar.gz.gpg | tar xzf -

# Restart the application
streamlit run NRIS_Enhanced.py
```

### 5.4. Migration to a New Server

**On the old server:**
```bash
# Create a complete backup
tar czf nris_migration.tar.gz NRIS_Enhanced.py nipt_registry_v2.db nris_config.json
```

**On the new server:**
```bash
# Install Python and dependencies
pip install streamlit pandas numpy PyPDF2 reportlab

# Extract the backup
tar xzf nris_migration.tar.gz

# Test the database
sqlite3 nipt_registry_v2.db "PRAGMA integrity_check;"

# Launch the application
streamlit run NRIS_Enhanced.py
```

---

## 6. Troubleshooting

### 6.1. PDF Import Issues

#### Problem: No data extracted

**Possible causes:**
1. Scanned PDF (image) instead of text PDF
2. Unsupported report format
3. Non-standard character encoding

**Solutions:**
- Verify that the PDF contains text (try copying and pasting text)
- Add regex patterns for your format (see section 2.3)
- Use OCR for scanned PDFs (see section 2.5)

#### Problem: Partial extraction

**Solution:**
- Enable debug mode by adding in `extract_data_from_pdf` (line ~1500):
  ```python
  print(f"Extracted text: {text[:500]}")  # Display first 500 characters
  ```
- Identify which fields are missing
- Add appropriate regex patterns

### 6.2. Configuration Issues

#### Problem: Modifications not applied

**Solutions:**
1. Verify that `nris_config.json` is in the same folder as `NRIS_Enhanced.py`
2. Verify JSON syntax (use https://jsonlint.com)
3. Completely restart the application (Ctrl+C then relaunch)

#### Problem: Configuration reset

**Cause:** The `nris_config.json` file was deleted or corrupted.

**Solution:**
- Restore from `backups/backup_X.json`
- Or reconfigure via the Settings tab

### 6.3. Encryption Issues

#### Problem: "Decryption failed" or "Invalid token"

**Cause:** Wrong master password.

**Solution:**
- Verify the environment variable `NRIS_MASTER_KEY`
- If the password was changed, you must decrypt with the old one then re-encrypt with the new one

#### Problem: Corrupted database after SQLCipher migration

**Solution:**
1. Restore the unencrypted backup
2. Redo the migration with the correct password
3. Test integrity: `PRAGMA integrity_check;`

### 6.4. Performance Issues

#### Problem: Application slow after encryption

**Solutions:**
- Use column-level encryption only for sensitive fields
- Add indexes on frequently searched columns:
  ```sql
  CREATE INDEX idx_encrypted_mrn ON patients(mrn_id);
  ```
- Increase RAM allocated to SQLite:
  ```python
  conn.execute("PRAGMA cache_size = -64000")  # 64 MB
  ```

### 6.5. Support and Help

**Resources:**
- **SQLite Documentation:** https://www.sqlite.org/docs.html
- **Streamlit Documentation:** https://docs.streamlit.io
- **Regex101 (regex testing):** https://regex101.com
- **Cryptography Library:** https://cryptography.io/en/latest/

**Debug logs:**

Add in `NRIS_Enhanced.py` (at the beginning):

```python
import logging

logging.basicConfig(
    filename='nris_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

Then use in code:
```python
logger.debug("PDF extraction started")
logger.info(f"Extracted data: {data}")
logger.error(f"Error: {e}")
```

---

## Appendix A: Customization Checklist

- [ ] Analyze your laboratory's PDF templates
- [ ] Add necessary regex patterns in `extract_data_from_pdf`
- [ ] Test import with several typical PDFs
- [ ] Configure clinical thresholds according to your protocols
- [ ] Configure QC limits (Cff, GC, reads, etc.)
- [ ] Customize laboratory name in PDF reports
- [ ] Add laboratory logo (optional)
- [ ] Decide on required encryption level (columns, full DB, disk)
- [ ] Implement chosen encryption
- [ ] Test encryption/decryption
- [ ] Configure automatic backups
- [ ] Test restore from backup
- [ ] Document modifications specific to your laboratory
- [ ] Train staff on new features

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Cff** | Cell-free fetal DNA fraction (% of fetal DNA in maternal plasma) |
| **GC%** | Percentage of guanine-cytosine bases in sequences |
| **MRN** | Medical Record Number |
| **NIPT** | Non-Invasive Prenatal Testing |
| **OCR** | Optical Character Recognition |
| **QC** | Quality Control |
| **QS** | Quality Score (sequencing quality score) |
| **RAT** | Rare Autosomal Trisomy |
| **SCA** | Sex Chromosome Aneuploidy |
| **Z-score** | Statistical score measuring deviation from normal |

---

## Appendix C: Common Regex Pattern Examples

```python
# Medical record number
r'MRN[:\s]+(\d{7})'
r'File[:\s]+([A-Z0-9\-]+)'
r'ID[:\s]*#?(\d+)'

# Date (DD/MM/YYYY format)
r'(\d{2}/\d{2}/\d{4})'

# Date (YYYY-MM-DD format)
r'(\d{4}-\d{2}-\d{2})'

# Percentage
r'(\d+\.?\d*)\s*%'

# Z-score
r'Z[:\s]*=?\s*(-?\d+\.?\d+)'

# Positive/negative result
r'(POSITIF|NÉGATIF|POSITIVE|NEGATIVE)'

# Full name (with accents)
r'([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)'

# Age
r'(\d{2})\s*ans?'
r'Age[:\s]+(\d+)'
```

---

**End of NRIS Enhanced Customization Guide**

For any questions or additional assistance, consult online resources or contact the system developer.

---

**Version:** 2.4
**Last Updated:** January 2026
**Author:** NRIS Enhanced System
**License:** Laboratory internal use only
