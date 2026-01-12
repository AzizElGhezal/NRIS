"""
NIPT Result Interpretation Software (NRIS) v2.2 - Enhanced Edition
By AzizElGhezal
---------------------------
Advanced clinical genetics dashboard with authentication, analytics,
PDF reports, visualizations, and comprehensive audit logging.

Version 2.2 Improvements:
- Bilingual PDF reports (English and French)
- Language preference settings
- Improved UI for technicians with helpful tooltips
- Streamlined workflow

Version 2.1 Improvements:
- Enhanced security (password complexity, account lockout, session timeout)
- Database integrity (foreign keys, soft delete, transactions)
- Performance optimizations (indexes, caching, query optimization)
- Improved PDF import (validation, error handling, confidence scoring)
"""

import sqlite3
import json
import io
import hashlib
import secrets
import re
import shutil
import os
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path
import base64

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import PyPDF2

# ==================== CONFIGURATION ====================
DB_FILE = "nipt_registry_v2.db"
CONFIG_FILE = "nris_config.json"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10  # Keep last 10 backups

DEFAULT_CONFIG = {
    'QC_THRESHOLDS': {
        'MIN_CFF': 3.5,
        'MAX_CFF': 50.0,
        'GC_RANGE': [37.0, 44.0],
        'MIN_UNIQ_RATE': 68.0,
        'MAX_ERROR_RATE': 1.0,
        'QS_LIMIT_NEG': 1.7,
        'QS_LIMIT_POS': 2.0
    },
    'PANEL_READ_LIMITS': {
        "NIPT Basic": 5,
        "NIPT Standard": 7,
        "NIPT Plus": 12,
        "NIPT Pro": 20
    },
    'CLINICAL_THRESHOLDS': {
        'TRISOMY_LOW': 2.58,
        'TRISOMY_AMBIGUOUS': 6.0,
        'SCA_THRESHOLD': 4.5,
        'RAT_POSITIVE': 8.0,
        'RAT_AMBIGUOUS': 4.5
    },
    'REPORT_LANGUAGE': 'en'  # Default language for PDF reports: 'en' or 'fr'
}

# ==================== TRANSLATIONS ====================
# Bilingual support for PDF reports (English and French)

TRANSLATIONS = {
    'en': {
        # PDF Header
        'lab_title': 'CLINICAL GENETICS LABORATORY',
        'report_title': 'Non-Invasive Prenatal Testing (NIPT) Report',

        # Report Metadata
        'report_id': 'Report ID:',
        'report_date': 'Report Date:',
        'panel_type': 'Panel Type:',
        'report_time': 'Report Time:',

        # Patient Information
        'patient_info': 'PATIENT INFORMATION',
        'name': 'Name:',
        'mrn': 'MRN:',
        'maternal_age': 'Maternal Age:',
        'gestational_age': 'Gestational Age:',
        'weight': 'Weight:',
        'height': 'Height:',
        'bmi': 'BMI:',
        'years': 'years',
        'weeks': 'weeks',

        # QC Assessment
        'qc_assessment': 'QUALITY CONTROL ASSESSMENT',
        'qc_status': 'QC Status',
        'parameter': 'Parameter',
        'value': 'Value',
        'reference_range': 'Reference Range',
        'status': 'Status',
        'fetal_fraction': 'Fetal Fraction (Cff)',
        'gc_content': 'GC Content',
        'seq_reads': 'Sequencing Reads',
        'unique_rate': 'Unique Read Rate',
        'error_rate': 'Error Rate',
        'quality_score': 'Quality Score',
        'qc_recommendation': 'QC Recommendation:',
        'qc_override_applied': 'QC Override Applied:',
        'original_status': 'Original status was',
        'validated_by': 'Validated by',
        'reason': 'Reason:',
        'override': 'Override',
        'pass': 'PASS',
        'fail': 'FAIL',
        'warning': 'WARNING',

        # Results Section
        'aneuploidy_results': 'ANEUPLOIDY SCREENING RESULTS',
        'condition': 'Condition',
        'result': 'Result',
        'z_score': 'Z-Score',
        'reportable': 'Reportable',
        'ref': 'Ref',
        'trisomy_21': 'Trisomy 21 (Down Syndrome)',
        'trisomy_18': 'Trisomy 18 (Edwards Syndrome)',
        'trisomy_13': 'Trisomy 13 (Patau Syndrome)',
        'sca': 'Sex Chromosome Aneuploidy',
        'fetal_sex': 'Fetal Sex:',
        'male': 'Male',
        'female': 'Female',
        'undetermined': 'Undetermined',

        # CNV & RAT
        'cnv_findings': 'COPY NUMBER VARIATION (CNV) FINDINGS',
        'rat_findings': 'RARE AUTOSOMAL TRISOMY (RAT) FINDINGS',
        'finding': 'Finding',
        'clinical_significance': 'Clinical Significance',

        # Maternal Factors
        'maternal_factors': 'MATERNAL FACTORS & AGE-BASED RISK',
        'bmi_underweight': '(Underweight)',
        'bmi_normal': '(Normal)',
        'bmi_overweight': '(Overweight)',
        'bmi_obese': '(Obese - may affect fetal fraction)',
        'age_risk_text': 'Based on maternal age of {age} years, the a priori risks are: Trisomy 21: 1 in {t21}, Trisomy 18: 1 in {t18}, Trisomy 13: 1 in {t13}',

        # Final Interpretation
        'final_interpretation': 'FINAL INTERPRETATION',

        # Clinical Recommendations
        'clinical_recommendations': 'CLINICAL RECOMMENDATIONS',
        'no_high_risk': 'No high-risk findings detected. Continue standard prenatal care.',
        'nipt_screening': 'NIPT is a screening test. It does not diagnose chromosomal abnormalities.',
        'rec_t21_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Genetic counseling should be offered.',
        'rec_t18_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.',
        'rec_t13_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.',
        'rec_sca_positive': 'Genetic counseling recommended. Confirmatory testing may be considered based on clinical judgment.',
        'rec_cnv_positive': 'Detailed ultrasound recommended. Genetic counseling and possible confirmatory testing advised.',
        'rec_rat_positive': 'Genetic counseling recommended. Clinical correlation and possible confirmatory testing advised.',
        'rec_high_risk': 'Re-analysis recommended. If persistent, consider confirmatory diagnostic testing.',
        'rec_low_risk': 'No additional testing indicated based on NIPT result alone. Standard prenatal care recommended.',

        # Clinical Notes
        'clinical_notes': 'CLINICAL NOTES & OBSERVATIONS',
        'key_markers': 'Key clinical markers:',
        'nt_noted': 'Nuchal Translucency noted',
        'ff_concerns': 'Fetal Fraction concerns noted',
        'ivf_noted': 'ART/IVF conception noted',
        'multiple_noted': 'Multiple gestation noted',

        # Limitations
        'limitations': 'LIMITATIONS AND DISCLAIMER',
        'important_info': 'Important Information:',
        'disclaimer_1': 'NIPT is a screening test, not a diagnostic test. Positive results should be confirmed with diagnostic testing (amniocentesis or CVS).',
        'disclaimer_2': 'False positive and false negative results can occur. A negative result does not eliminate the possibility of chromosomal abnormalities.',
        'disclaimer_3': 'This test screens for specific chromosomal conditions and does not detect all genetic disorders.',
        'disclaimer_4': 'Results should be interpreted in conjunction with other clinical findings, ultrasound, and maternal history.',
        'disclaimer_5': 'Test performance may be affected by factors including: low fetal fraction, maternal chromosomal abnormalities, confined placental mosaicism, vanishing twin, or maternal malignancy.',
        'disclaimer_6': 'Genetic counseling is recommended for all patients, especially those with positive or inconclusive results.',

        # Authorization
        'authorization': 'AUTHORIZATION',
        'performed_by': 'Performed by:',
        'reviewed_by': 'Reviewed by:',
        'approved_by': 'Approved by:',
        'date': 'Date:',
        'clinical_pathologist': 'Clinical Pathologist',
        'lab_director': 'Laboratory Director',
        'lab_staff': 'Laboratory Staff',

        # Footer
        'report_generated': 'Report generated:',
        'version': 'NRIS v2.2 Enhanced Edition',
    },
    'fr': {
        # PDF Header
        'lab_title': 'LABORATOIRE DE GENETIQUE CLINIQUE',
        'report_title': 'Rapport de Depistage Prenatal Non Invasif (DPNI)',

        # Report Metadata
        'report_id': 'ID du rapport:',
        'report_date': 'Date du rapport:',
        'panel_type': 'Type de panel:',
        'report_time': 'Heure du rapport:',

        # Patient Information
        'patient_info': 'INFORMATIONS PATIENTE',
        'name': 'Nom:',
        'mrn': 'NDM:',
        'maternal_age': 'Age maternel:',
        'gestational_age': 'Age gestationnel:',
        'weight': 'Poids:',
        'height': 'Taille:',
        'bmi': 'IMC:',
        'years': 'ans',
        'weeks': 'semaines',

        # QC Assessment
        'qc_assessment': 'EVALUATION DU CONTROLE QUALITE',
        'qc_status': 'Statut CQ',
        'parameter': 'Parametre',
        'value': 'Valeur',
        'reference_range': 'Plage de reference',
        'status': 'Statut',
        'fetal_fraction': 'Fraction foetale (Cff)',
        'gc_content': 'Contenu GC',
        'seq_reads': 'Lectures de sequencage',
        'unique_rate': 'Taux de lectures uniques',
        'error_rate': "Taux d'erreur",
        'quality_score': 'Score de qualite',
        'qc_recommendation': 'Recommandation CQ:',
        'qc_override_applied': 'Derogation CQ appliquee:',
        'original_status': 'Le statut original etait',
        'validated_by': 'Valide par',
        'reason': 'Raison:',
        'override': 'Derogation',
        'pass': 'CONFORME',
        'fail': 'NON CONFORME',
        'warning': 'ATTENTION',

        # Results Section
        'aneuploidy_results': 'RESULTATS DU DEPISTAGE DES ANEUPLOIDIES',
        'condition': 'Condition',
        'result': 'Resultat',
        'z_score': 'Score Z',
        'reportable': 'Rapportable',
        'ref': 'Ref',
        'trisomy_21': 'Trisomie 21 (Syndrome de Down)',
        'trisomy_18': 'Trisomie 18 (Syndrome d\'Edwards)',
        'trisomy_13': 'Trisomie 13 (Syndrome de Patau)',
        'sca': 'Aneuploidie des chromosomes sexuels',
        'fetal_sex': 'Sexe foetal:',
        'male': 'Masculin',
        'female': 'Feminin',
        'undetermined': 'Indetermine',

        # CNV & RAT
        'cnv_findings': 'RESULTATS DES VARIATIONS DU NOMBRE DE COPIES (CNV)',
        'rat_findings': 'RESULTATS DES TRISOMIES AUTOSOMIQUES RARES (TAR)',
        'finding': 'Resultat',
        'clinical_significance': 'Signification clinique',

        # Maternal Factors
        'maternal_factors': 'FACTEURS MATERNELS ET RISQUE LIE A L\'AGE',
        'bmi_underweight': '(Insuffisance ponderale)',
        'bmi_normal': '(Normal)',
        'bmi_overweight': '(Surpoids)',
        'bmi_obese': '(Obesite - peut affecter la fraction foetale)',
        'age_risk_text': 'Selon l\'age maternel de {age} ans, les risques a priori sont: Trisomie 21: 1 sur {t21}, Trisomie 18: 1 sur {t18}, Trisomie 13: 1 sur {t13}',

        # Final Interpretation
        'final_interpretation': 'INTERPRETATION FINALE',

        # Clinical Recommendations
        'clinical_recommendations': 'RECOMMANDATIONS CLINIQUES',
        'no_high_risk': 'Aucun resultat a haut risque detecte. Poursuivre les soins prenataux standards.',
        'nipt_screening': 'Le DPNI est un test de depistage. Il ne diagnostique pas les anomalies chromosomiques.',
        'rec_t21_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Un conseil genetique devrait etre propose.',
        'rec_t18_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Une echographie detaillee et un conseil genetique sont conseilles.',
        'rec_t13_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Une echographie detaillee et un conseil genetique sont conseilles.',
        'rec_sca_positive': 'Conseil genetique recommande. Un test de confirmation peut etre envisage selon le jugement clinique.',
        'rec_cnv_positive': 'Echographie detaillee recommandee. Conseil genetique et eventuel test de confirmation conseilles.',
        'rec_rat_positive': 'Conseil genetique recommande. Correlation clinique et eventuel test de confirmation conseilles.',
        'rec_high_risk': 'Re-analyse recommandee. Si le resultat persiste, envisager un test diagnostique de confirmation.',
        'rec_low_risk': 'Aucun test supplementaire indique sur la seule base du resultat DPNI. Soins prenataux standards recommandes.',

        # Clinical Notes
        'clinical_notes': 'NOTES CLINIQUES ET OBSERVATIONS',
        'key_markers': 'Marqueurs cliniques cles:',
        'nt_noted': 'Clarte nucale notee',
        'ff_concerns': 'Preoccupations concernant la fraction foetale notees',
        'ivf_noted': 'Conception par PMA/FIV notee',
        'multiple_noted': 'Grossesse multiple notee',

        # Limitations
        'limitations': 'LIMITES ET AVERTISSEMENT',
        'important_info': 'Informations importantes:',
        'disclaimer_1': 'Le DPNI est un test de depistage, pas un test diagnostique. Les resultats positifs doivent etre confirmes par un test diagnostique (amniocent&egrave;se ou biopsie de villosites choriales).',
        'disclaimer_2': 'Des faux positifs et faux negatifs peuvent survenir. Un resultat negatif n\'elimine pas la possibilite d\'anomalies chromosomiques.',
        'disclaimer_3': 'Ce test depiste des conditions chromosomiques specifiques et ne detecte pas tous les troubles genetiques.',
        'disclaimer_4': 'Les resultats doivent etre interpretes en conjonction avec d\'autres donnees cliniques, l\'echographie et l\'historique maternel.',
        'disclaimer_5': 'La performance du test peut etre affectee par des facteurs incluant: faible fraction foetale, anomalies chromosomiques maternelles, mosaicisme placentaire confine, jumeau evanescent ou malignite maternelle.',
        'disclaimer_6': 'Un conseil genetique est recommande pour toutes les patientes, en particulier celles avec des resultats positifs ou non concluants.',

        # Authorization
        'authorization': 'AUTORISATION',
        'performed_by': 'Realise par:',
        'reviewed_by': 'Revise par:',
        'approved_by': 'Approuve par:',
        'date': 'Date:',
        'clinical_pathologist': 'Pathologiste clinique',
        'lab_director': 'Directeur du laboratoire',
        'lab_staff': 'Personnel du laboratoire',

        # Footer
        'report_generated': 'Rapport genere:',
        'version': 'NRIS v2.1 Edition Amelioree',
    }
}

def get_translation(key: str, lang: str = 'en') -> str:
    """Get translated text for a given key and language."""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))

# ==================== DATA PROTECTION FUNCTIONS ====================

def ensure_backup_dir() -> Path:
    """Ensure backup directory exists and return its path."""
    backup_path = Path(BACKUP_DIR)
    backup_path.mkdir(exist_ok=True)
    return backup_path

def create_backup(reason: str = "manual") -> Optional[str]:
    """Create a timestamped backup of the database.

    Args:
        reason: Why backup was created (startup, periodic, manual, pre_import)

    Returns:
        Path to backup file or None if backup failed
    """
    if not os.path.exists(DB_FILE):
        return None

    try:
        backup_path = ensure_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nris_backup_{timestamp}_{reason}.db"
        backup_file = backup_path / backup_filename

        # Use SQLite's backup API for safe copying
        source_conn = sqlite3.connect(DB_FILE)
        dest_conn = sqlite3.connect(str(backup_file))
        source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        # Rotate old backups (keep only MAX_BACKUPS)
        rotate_backups()

        return str(backup_file)
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def rotate_backups() -> None:
    """Remove old backups, keeping only the most recent MAX_BACKUPS."""
    try:
        backup_path = ensure_backup_dir()
        backups = sorted(
            [f for f in backup_path.glob("nris_backup_*.db")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # Remove backups beyond the limit
        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink()
            except Exception:
                pass
    except Exception:
        pass

def list_backups() -> List[Dict[str, Any]]:
    """List all available backups with metadata."""
    try:
        backup_path = ensure_backup_dir()
        backups = []
        for backup_file in sorted(backup_path.glob("nris_backup_*.db"),
                                   key=lambda x: x.stat().st_mtime,
                                   reverse=True):
            stat = backup_file.stat()
            backups.append({
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return backups
    except Exception:
        return []

def restore_backup(backup_path: str) -> Tuple[bool, str]:
    """Restore database from a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Tuple of (success, message)
    """
    if not os.path.exists(backup_path):
        return False, "Backup file not found"

    try:
        # First, create a backup of current state
        create_backup("pre_restore")

        # Restore using SQLite backup API
        source_conn = sqlite3.connect(backup_path)
        dest_conn = sqlite3.connect(DB_FILE)
        source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        return True, "Database restored successfully"
    except Exception as e:
        return False, f"Restore failed: {e}"

def verify_database_integrity() -> Tuple[bool, str]:
    """Run SQLite integrity check on the database.

    Returns:
        Tuple of (is_ok, message)
    """
    if not os.path.exists(DB_FILE):
        return True, "Database does not exist yet (will be created)"

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            return True, "Database integrity verified"
        else:
            return False, f"Integrity issues found: {result}"
    except Exception as e:
        return False, f"Integrity check failed: {e}"

def startup_data_protection() -> Dict[str, Any]:
    """Perform startup data protection tasks.

    This should be called once when the application starts.
    Creates a backup and verifies database integrity.

    Returns:
        Dictionary with status information
    """
    status = {
        'backup_created': False,
        'backup_path': None,
        'integrity_ok': False,
        'integrity_message': '',
        'warnings': []
    }

    # Check integrity first
    is_ok, message = verify_database_integrity()
    status['integrity_ok'] = is_ok
    status['integrity_message'] = message

    if not is_ok:
        status['warnings'].append(f"Database integrity issue: {message}")

    # Create startup backup (only if database exists)
    if os.path.exists(DB_FILE):
        backup_path = create_backup("startup")
        if backup_path:
            status['backup_created'] = True
            status['backup_path'] = backup_path
        else:
            status['warnings'].append("Failed to create startup backup")

    return status

# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Get database connection with foreign keys and WAL mode enabled.

    WAL (Write-Ahead Logging) mode provides:
    - Better crash resilience
    - Concurrent read access during writes
    - Improved performance for frequent writes
    """
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL for crash resilience
    conn.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and speed
    return conn

def init_database() -> None:
    """Enhanced database with audit logging and user management."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()

        # Enable foreign key constraints
        c.execute("PRAGMA foreign_keys = ON")

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'technician',
                created_at TEXT,
                last_login TEXT,
                must_change_password INTEGER DEFAULT 0,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mrn_id TEXT UNIQUE,
                full_name TEXT,
                age INTEGER,
                weight_kg REAL,
                height_cm INTEGER,
                bmi REAL,
                weeks INTEGER,
                clinical_notes TEXT,
                created_at TEXT,
                created_by INTEGER,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                panel_type TEXT,
                qc_status TEXT,
                qc_details TEXT,
                qc_advice TEXT,
                qc_metrics_json TEXT,
                t21_res TEXT,
                t18_res TEXT,
                t13_res TEXT,
                sca_res TEXT,
                cnv_json TEXT,
                rat_json TEXT,
                full_z_json TEXT,
                final_summary TEXT,
                created_at TEXT,
                created_by INTEGER,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')

        # Migration: Add qc_metrics_json column if it doesn't exist
        try:
            c.execute("ALTER TABLE results ADD COLUMN qc_metrics_json TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Migration: Add QC override columns for staff validation
        for col_sql in [
            "ALTER TABLE results ADD COLUMN qc_override INTEGER DEFAULT 0",
            "ALTER TABLE results ADD COLUMN qc_override_by INTEGER",
            "ALTER TABLE results ADD COLUMN qc_override_reason TEXT",
            "ALTER TABLE results ADD COLUMN qc_override_at TEXT"
        ]:
            try:
                c.execute(col_sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Migration: Add new user security columns if they don't exist
        for col_sql in [
            "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN locked_until TEXT"
        ]:
            try:
                c.execute(col_sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Migration: Add is_deleted column to patients for soft delete
        try:
            c.execute("ALTER TABLE patients ADD COLUMN is_deleted INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists

        c.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TEXT,
                ip_address TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Create indexes for better query performance
        index_statements = [
            "CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients(mrn_id)",
            "CREATE INDEX IF NOT EXISTS idx_patients_deleted ON patients(is_deleted)",
            "CREATE INDEX IF NOT EXISTS idx_results_patient_id ON results(patient_id)",
            "CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_results_qc_status ON results(qc_status)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
        ]
        for idx_sql in index_statements:
            try:
                c.execute(idx_sql)
            except sqlite3.OperationalError:
                pass  # Index might already exist

        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            admin_hash = hash_password("admin123")
            c.execute("""
                INSERT INTO users (username, password_hash, full_name, role, created_at, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin", admin_hash, "System Administrator", "admin", datetime.now().isoformat(), 1))

def log_audit(action: str, details: str, user_id: Optional[int] = None) -> None:
    """Log user actions for compliance with better error handling."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Truncate details to prevent excessively long entries
            safe_details = str(details)[:1000] if details else ""
            c.execute("""
                INSERT INTO audit_log (user_id, action, details, timestamp, ip_address)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, safe_details, datetime.now().isoformat(), "local"))
            conn.commit()
    except Exception as e:
        # Silently fail audit logging to not interrupt main operations
        pass

def hash_password(password: str) -> str:
    """Hash password with salt using SHA256."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hash_str: str) -> bool:
    """Verify password against hash."""
    try:
        salt, pwd_hash = hash_str.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except Exception:
        return False

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password meets complexity requirements.

    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, ""

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

def authenticate_user(username: str, password: str) -> Optional[Dict]:
    """Authenticate user with account lockout protection."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, username, password_hash, full_name, role,
                       must_change_password, failed_login_attempts, locked_until
                FROM users WHERE username = ?
            """, (username,))
            row = c.fetchone()

            if not row:
                log_audit("LOGIN_FAILED", f"Unknown username: {username}", None)
                return None

            user_id, _, pwd_hash, full_name, role, must_change_pwd, failed_attempts, locked_until = row

            # Check if account is locked
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    remaining = (lock_time - datetime.now()).seconds // 60
                    log_audit("LOGIN_BLOCKED", f"Account locked for user {username}", user_id)
                    return {'error': f'Account locked. Try again in {remaining + 1} minutes.'}
                else:
                    # Lockout expired, reset
                    c.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,))

            if verify_password(password, pwd_hash):
                # Successful login - reset failed attempts
                c.execute("""
                    UPDATE users SET last_login = ?, failed_login_attempts = 0, locked_until = NULL
                    WHERE id = ?
                """, (datetime.now().isoformat(), user_id))
                conn.commit()
                log_audit("LOGIN", f"User {username} logged in", user_id)
                return {
                    'id': user_id,
                    'username': username,
                    'name': full_name,
                    'role': role,
                    'must_change_password': bool(must_change_pwd)
                }
            else:
                # Failed login
                new_attempts = (failed_attempts or 0) + 1
                if new_attempts >= MAX_LOGIN_ATTEMPTS:
                    lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                    c.execute("""
                        UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?
                    """, (new_attempts, lock_until, user_id))
                    log_audit("ACCOUNT_LOCKED", f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts", user_id)
                else:
                    c.execute("UPDATE users SET failed_login_attempts = ? WHERE id = ?", (new_attempts, user_id))
                    log_audit("LOGIN_FAILED", f"Invalid password for {username} (attempt {new_attempts})", user_id)
                conn.commit()
    except Exception as e:
        pass
    return None

def load_config() -> Dict:
    """Load configuration from file or return defaults."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict) -> bool:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except:
        return False

# ==================== ANALYSIS FUNCTIONS ====================

def validate_inputs(reads: float, cff: float, gc: float, age: int) -> List[str]:
    """Validate clinical inputs."""
    errors = []
    if reads < 0 or reads > 100: errors.append("Reads must be 0-100M")
    if cff < 0 or cff > 50: errors.append("Cff must be 0-50%")
    if gc < 0 or gc > 100: errors.append("GC must be 0-100%")
    if age < 15 or age > 60: errors.append("Age must be 15-60")
    return errors

def check_qc_metrics(config: Dict, panel: str, reads: float, cff: float, gc: float, 
                    qs: float, uniq: float, error: float, is_positive: bool) -> Tuple[str, List[str], str]:
    """Enhanced QC with configurable thresholds."""
    thresholds = config['QC_THRESHOLDS']
    issues, advice = [], []
    
    min_reads = config['PANEL_READ_LIMITS'].get(panel, 5)
    if reads < min_reads:
        issues.append(f"HARD: Reads {reads}M < {min_reads}M")
        advice.append("Resequencing")

    if cff < thresholds['MIN_CFF']:
        issues.append(f"HARD: Cff {cff}% < {thresholds['MIN_CFF']}%")
        advice.append("Resample")

    max_cff = thresholds.get('MAX_CFF', 50.0)
    if cff > max_cff:
        issues.append(f"HARD: Cff {cff}% > {max_cff}%")
        advice.append("Resample")

    gc_range = thresholds['GC_RANGE']
    if not (gc_range[0] <= gc <= gc_range[1]):
        issues.append(f"HARD: GC {gc}% out of range")
        advice.append("Re-library")

    qs_limit = thresholds['QS_LIMIT_POS'] if is_positive else thresholds['QS_LIMIT_NEG']
    if qs >= qs_limit:
        issues.append(f"HARD: QS {qs} >= {qs_limit}")
        advice.append("Re-library")

    if uniq < thresholds['MIN_UNIQ_RATE']:
        issues.append(f"SOFT: UniqueRate {uniq}% Low")
    if error > thresholds['MAX_ERROR_RATE']:
        issues.append(f"SOFT: ErrorRate {error}% High")

    status = "FAIL" if any("HARD" in i for i in issues) else ("WARNING" if issues else "PASS")
    advice_str = " / ".join(set(advice)) if advice else "None"
    
    return status, issues, advice_str

def analyze_trisomy(config: Dict, z_score: float, chrom: str) -> Tuple[str, str]:
    """Returns (result, risk_level)."""
    thresholds = config['CLINICAL_THRESHOLDS']
    if pd.isna(z_score): return "Invalid Data", "UNKNOWN"
    
    if z_score < thresholds['TRISOMY_LOW']: 
        return "Low Risk", "LOW"
    if z_score < thresholds['TRISOMY_AMBIGUOUS']: 
        return f"High Risk (Z:{z_score:.2f}) -> Re-library", "HIGH"
    return "POSITIVE -> Report Positive", "POSITIVE"

def analyze_sca(config: Dict, sca_type: str, z_xx: float, z_xy: float, cff: float) -> Tuple[str, str]:
    """Enhanced SCA analysis based on GeneMind NIPT guidelines.

    SCA decision logic per document:
    - XX/XY: Report Negative
    - XYY/XXY/XXX+XY: Report Positive
    - XO: If Z-score(XX) >= 4.5, report XO; else re-library
    - XXX: If Z-score(XX) >= 4.5, report XXX; else re-library
    - XO+XY: If Z-score(XY) >= 6, report XO+XY; else re-library
    """
    if cff < config['QC_THRESHOLDS']['MIN_CFF']:
        return "INVALID (Cff < 3.5%)", "INVALID"

    threshold = config['CLINICAL_THRESHOLDS']['SCA_THRESHOLD']  # 4.5
    xy_threshold = 6.0  # Threshold for XO+XY per document

    if sca_type == "XX": return "Negative (Female)", "LOW"
    if sca_type == "XY": return "Negative (Male)", "LOW"

    if sca_type == "XO":
        return ("POSITIVE (Turner XO)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XO -> Re-library", "HIGH")

    if sca_type == "XXX":
        return ("POSITIVE (Triple X)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XXX -> Re-library", "HIGH")

    # XXX+XY: Always report positive per document
    if sca_type == "XXX+XY":
        return "POSITIVE (XXX+XY)", "POSITIVE"

    # XO+XY: Check Z-score(XY) >= 6 per document
    if sca_type == "XO+XY":
        return ("POSITIVE (XO+XY)", "POSITIVE") if z_xy >= xy_threshold else ("Ambiguous XO+XY -> Re-library", "HIGH")

    if sca_type in ["XXY", "XYY"]:
        return f"POSITIVE ({sca_type})", "POSITIVE"

    return "Ambiguous SCA -> Re-library", "HIGH"

def analyze_rat(config: Dict, chrom: int, z_score: float) -> Tuple[str, str]:
    """RAT analysis."""
    thresholds = config['CLINICAL_THRESHOLDS']
    if z_score >= thresholds['RAT_POSITIVE']: return "POSITIVE", "POSITIVE"
    if z_score > thresholds['RAT_AMBIGUOUS']: return "Ambiguous -> Re-library", "HIGH"
    return "Low Risk", "LOW"

def analyze_cnv(size: float, ratio: float) -> Tuple[str, float, str]:
    """CNV analysis."""
    if size >= 10: threshold = 6.0
    elif size > 7: threshold = 8.0
    elif size > 3.5: threshold = 10.0
    else: threshold = 12.0

    if ratio >= threshold:
        return f"High Risk -> Re-library", threshold, "HIGH"
    return "Low Risk", threshold, "LOW"


def get_reportable_status(result_text: str, qc_status: str = "PASS", qc_override: bool = False) -> Tuple[str, str]:
    """Determine if a result should be reported to the patient.

    Args:
        result_text: The result text (e.g., "Low Risk", "High Risk -> Re-library", "POSITIVE")
        qc_status: QC status (PASS, FAIL, WARNING)
        qc_override: Whether QC has been overridden by staff

    Returns:
        Tuple of (reportable_status, reason)
        - "Yes": Result should be reported (positive or negative/low risk)
        - "No": Result requires re-processing (re-library, resample, QC fail)
    """
    result_upper = str(result_text).upper()

    # QC Fail without override -> Not reportable
    if qc_status == "FAIL" and not qc_override:
        return "No", "QC Fail"

    # Check for conditions requiring re-processing
    if "RE-LIBRARY" in result_upper or "RELIBRARY" in result_upper:
        return "No", "Re-library required"
    if "RESAMPLE" in result_upper:
        return "No", "Resample required"
    if "AMBIGUOUS" in result_upper:
        return "No", "Ambiguous result"
    if "INVALID" in result_upper and not qc_override:
        return "No", "Invalid result"

    # POSITIVE or Low Risk -> Reportable
    if "POSITIVE" in result_upper:
        return "Yes", "Screen Positive"
    if "LOW" in result_upper or "NEGATIVE" in result_upper:
        return "Yes", "Screen Negative"

    # Default: assume reportable if none of the above conditions match
    return "Yes", "Result available"


def override_qc_status(result_id: int, reason: str, user_id: int) -> Tuple[bool, str]:
    """Override QC status to PASS for a result. Staff validation feature.

    Also updates final_summary to reflect the override - removes QC FAIL status
    and recalculates based on the actual test results.
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # First, get the current result data to recalculate final_summary
            c.execute("""
                SELECT t21_res, t18_res, t13_res, sca_res, cnv_json, rat_json, final_summary
                FROM results WHERE id = ?
            """, (result_id,))
            row = c.fetchone()
            if not row:
                return False, "Result not found"

            t21_res, t18_res, t13_res, sca_res, cnv_json, rat_json, old_summary = row

            # Recalculate final_summary based on actual test results (ignoring QC status)
            all_results = [str(t21_res), str(t18_res), str(t13_res), str(sca_res)]
            is_positive = any('POSITIVE' in r.upper() for r in all_results)
            is_high_risk = any('HIGH' in r.upper() or 'RE-LIBRARY' in r.upper() or 'RESAMPLE' in r.upper() for r in all_results)

            # Check CNV and RAT for high risk
            try:
                cnvs = json.loads(cnv_json) if cnv_json else []
                rats = json.loads(rat_json) if rat_json else []
                if cnvs or rats:
                    is_high_risk = True
            except:
                pass

            # Determine new final_summary
            if is_positive:
                new_summary = "POSITIVE DETECTED"
            elif is_high_risk:
                new_summary = "HIGH RISK (SEE ADVICE)"
            else:
                new_summary = "NEGATIVE"

            c.execute("""
                UPDATE results
                SET qc_override = 1,
                    qc_override_by = ?,
                    qc_override_reason = ?,
                    qc_override_at = ?,
                    final_summary = ?
                WHERE id = ?
            """, (user_id, reason, datetime.now().isoformat(), new_summary, result_id))
            if c.rowcount == 0:
                return False, "Result not found"
            conn.commit()
            log_audit("QC_OVERRIDE", f"QC override applied to result {result_id}: {reason}. Summary changed from '{old_summary}' to '{new_summary}'", user_id)
            return True, f"QC status overridden to PASS. Final summary updated to '{new_summary}'"
    except Exception as e:
        return False, f"Override failed: {str(e)}"

def remove_qc_override(result_id: int, user_id: int) -> Tuple[bool, str]:
    """Remove QC override from a result.

    Also restores the final_summary to 'INVALID (QC FAIL)' since the QC failure
    is no longer being overridden.
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # Get current qc_status to determine if we need to restore QC FAIL summary
            c.execute("SELECT qc_status, final_summary FROM results WHERE id = ?", (result_id,))
            row = c.fetchone()
            if not row:
                return False, "Result not found"

            qc_status, current_summary = row

            # If original QC was FAIL, restore the final_summary to INVALID (QC FAIL)
            new_summary = "INVALID (QC FAIL)" if qc_status == "FAIL" else current_summary

            c.execute("""
                UPDATE results
                SET qc_override = 0,
                    qc_override_by = NULL,
                    qc_override_reason = NULL,
                    qc_override_at = NULL,
                    final_summary = ?
                WHERE id = ?
            """, (new_summary, result_id))
            if c.rowcount == 0:
                return False, "Result not found"
            conn.commit()
            log_audit("QC_OVERRIDE_REMOVED", f"QC override removed from result {result_id}. Summary restored to '{new_summary}'", user_id)
            return True, f"QC override removed. Final summary restored to '{new_summary}'"
    except Exception as e:
        return False, f"Remove override failed: {str(e)}"

def get_qc_override_info(result_id: int) -> Optional[Dict]:
    """Get QC override information for a result."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT r.qc_override, r.qc_override_reason, r.qc_override_at, u.full_name
                FROM results r
                LEFT JOIN users u ON r.qc_override_by = u.id
                WHERE r.id = ?
            """, (result_id,))
            row = c.fetchone()
            if row and row[0]:
                return {
                    'is_overridden': bool(row[0]),
                    'reason': row[1],
                    'override_at': row[2],
                    'override_by': row[3]
                }
    except Exception:
        pass
    return None

def check_duplicate_patient(mrn: str) -> Tuple[bool, Optional[Dict]]:
    """Check if a patient with this MRN already exists (excluding deleted). Returns (exists, patient_info)."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.full_name, p.mrn_id, p.age, p.weeks, COUNT(r.id) as result_count
                FROM patients p
                LEFT JOIN results r ON r.patient_id = p.id
                WHERE p.mrn_id = ? AND (p.is_deleted = 0 OR p.is_deleted IS NULL)
                GROUP BY p.id
            """, (mrn,))
            row = c.fetchone()
            if row:
                return True, {
                    'id': row[0],
                    'name': row[1],
                    'mrn': row[2],
                    'age': row[3],
                    'weeks': row[4],
                    'result_count': row[5]
                }
    except Exception:
        pass
    return False, None

def delete_patient(patient_id: int, hard_delete: bool = False) -> Tuple[bool, str]:
    """Delete a patient and all associated results.

    Args:
        patient_id: The database ID of the patient
        hard_delete: If True, permanently delete. If False, soft delete (but auto hard-delete orphans).

    Returns:
        (success, message)
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # Check if patient exists
            c.execute("SELECT mrn_id, full_name FROM patients WHERE id = ?", (patient_id,))
            patient = c.fetchone()
            if not patient:
                return False, "Patient not found"

            mrn, name = patient

            # Check if patient has any results - orphans (no results) are always hard deleted
            c.execute("SELECT COUNT(*) FROM results WHERE patient_id = ?", (patient_id,))
            result_count = c.fetchone()[0]

            # Auto hard-delete if patient has no results (orphan) to free up the ID
            if result_count == 0:
                hard_delete = True

            if hard_delete:
                # First delete all associated results
                c.execute("DELETE FROM results WHERE patient_id = ?", (patient_id,))
                deleted_results = c.rowcount

                # Then delete the patient
                c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))

                conn.commit()
                log_audit("HARD_DELETE_PATIENT",
                         f"Permanently deleted patient {mrn} ({name}) and {deleted_results} results",
                         st.session_state.user['id'] if 'user' in st.session_state else None)
                return True, f"Permanently deleted patient {mrn} and {deleted_results} associated results"
            else:
                # Soft delete - mark as deleted AND modify MRN to free it for reuse
                # Store original MRN in clinical_notes for potential recovery
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                deleted_mrn = f"DELETED_{timestamp}_{mrn}"

                # Get current clinical notes to preserve them
                c.execute("SELECT clinical_notes FROM patients WHERE id = ?", (patient_id,))
                current_notes = c.fetchone()[0] or ''

                # Append original MRN to notes for recovery purposes
                recovery_note = f"[DELETED: Original MRN was '{mrn}']"
                if recovery_note not in current_notes:
                    updated_notes = f"{current_notes}\n{recovery_note}".strip()
                else:
                    updated_notes = current_notes

                c.execute("""
                    UPDATE patients
                    SET is_deleted = 1, mrn_id = ?, clinical_notes = ?
                    WHERE id = ?
                """, (deleted_mrn, updated_notes, patient_id))
                conn.commit()
                log_audit("DELETE_PATIENT",
                         f"Soft deleted patient {mrn} ({name}), MRN changed to {deleted_mrn}",
                         st.session_state.user['id'] if 'user' in st.session_state else None)
                return True, f"Patient {mrn} marked as deleted"

    except Exception as e:
        return False, f"Delete failed: {str(e)}"

def restore_patient(patient_id: int) -> Tuple[bool, str]:
    """Restore a soft-deleted patient. Attempts to recover original MRN from clinical notes."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            # Get current patient data including notes with original MRN
            c.execute("SELECT mrn_id, clinical_notes FROM patients WHERE id = ?", (patient_id,))
            row = c.fetchone()
            if not row:
                return False, "Patient not found"

            current_mrn, notes = row

            # Try to extract original MRN from notes
            original_mrn = None
            if notes:
                import re
                mrn_match = re.search(r'\[DELETED: Original MRN was \'([^\']+)\'\]', notes)
                if mrn_match:
                    original_mrn = mrn_match.group(1)
                    # Check if original MRN is available (not taken by another patient)
                    c.execute("""
                        SELECT id FROM patients
                        WHERE mrn_id = ? AND id != ? AND (is_deleted = 0 OR is_deleted IS NULL)
                    """, (original_mrn, patient_id))
                    if c.fetchone():
                        # Original MRN is taken, can't restore to it
                        original_mrn = None

            if original_mrn:
                # Restore with original MRN and clean up notes
                cleaned_notes = notes.replace(f"[DELETED: Original MRN was '{original_mrn}']", '').strip()
                c.execute("""
                    UPDATE patients
                    SET is_deleted = 0, mrn_id = ?, clinical_notes = ?
                    WHERE id = ?
                """, (original_mrn, cleaned_notes, patient_id))
            else:
                # Just restore without changing MRN (keep the DELETED_ prefix or current MRN)
                c.execute("UPDATE patients SET is_deleted = 0 WHERE id = ?", (patient_id,))

            if c.rowcount == 0:
                return False, "Patient not found"
            conn.commit()
            log_audit("RESTORE_PATIENT", f"Restored patient {patient_id}",
                     st.session_state.user['id'] if 'user' in st.session_state else None)
            return True, "Patient restored successfully"
    except Exception as e:
        return False, f"Restore failed: {str(e)}"

def cleanup_orphaned_patients(include_active: bool = False) -> Tuple[int, str]:
    """Clean up patients with no associated results (ghost patients).

    Args:
        include_active: If True, also delete active patients (is_deleted=0) with no results.
                       If False, only delete soft-deleted patients with no results.
    """
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            # Find and delete patients with no results
            if include_active:
                # Delete ALL patients with no results (including active ones)
                c.execute("""
                    DELETE FROM patients
                    WHERE id NOT IN (SELECT DISTINCT patient_id FROM results WHERE patient_id IS NOT NULL)
                """)
            else:
                # Only delete soft-deleted patients with no results
                c.execute("""
                    DELETE FROM patients
                    WHERE id NOT IN (SELECT DISTINCT patient_id FROM results WHERE patient_id IS NOT NULL)
                    AND (is_deleted = 1 OR is_deleted IS NULL)
                """)
            deleted_count = c.rowcount
            conn.commit()

            if deleted_count > 0:
                log_audit("CLEANUP_ORPHANS", f"Removed {deleted_count} orphaned patient records (include_active={include_active})",
                         st.session_state.user['id'] if 'user' in st.session_state else None)
            return deleted_count, f"Cleaned up {deleted_count} orphaned patient records"
    except Exception as e:
        return 0, f"Cleanup failed: {str(e)}"

def get_next_patient_id(cursor) -> int:
    """Get the next available patient ID, reusing IDs from deleted patients.

    This finds the lowest unused ID by looking for gaps in the sequence
    or returning max_id + 1 if no gaps exist.
    """
    # Get all existing patient IDs (including deleted ones, since we want to reuse truly deleted slots)
    cursor.execute("SELECT id FROM patients ORDER BY id")
    existing_ids = {row[0] for row in cursor.fetchall()}

    if not existing_ids:
        return 1

    # Find the first gap in the sequence starting from 1
    expected_id = 1
    for existing_id in sorted(existing_ids):
        if existing_id > expected_id:
            # Found a gap - return the missing ID
            return expected_id
        expected_id = existing_id + 1

    # No gaps found, return the next ID after the max
    return max(existing_ids) + 1

def save_result(patient: Dict, results: Dict, clinical: Dict, full_z: Optional[Dict] = None,
                qc_metrics: Optional[Dict] = None, allow_duplicate: bool = True) -> Tuple[int, str]:
    """Save with audit logging and transaction support. Returns (result_id, message)."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Start transaction
        c.execute("BEGIN TRANSACTION")

        # Check for existing patient (excluding deleted)
        c.execute("""
            SELECT id, full_name FROM patients
            WHERE mrn_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)
        """, (patient['id'],))
        existing = c.fetchone()

        if existing:
            patient_db_id = existing[0]
            existing_name = existing[1]
            if not allow_duplicate:
                conn.rollback()
                return 0, f"Patient with ID '{patient['id']}' already exists in registry as '{existing_name}'"
        else:
            # Get the next available patient ID (reusing IDs from deleted patients)
            next_id = get_next_patient_id(c)
            c.execute("""
                INSERT INTO patients
                (id, mrn_id, full_name, age, weight_kg, height_cm, bmi, weeks, clinical_notes, created_at, created_by, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                next_id, patient['id'], patient['name'], patient['age'], patient['weight'],
                patient['height'], patient['bmi'], patient['weeks'], patient['notes'],
                datetime.now().isoformat(), st.session_state.user['id']
            ))
            patient_db_id = next_id

        # Prepare QC metrics JSON
        qc_metrics_json = json.dumps(qc_metrics) if qc_metrics else "{}"

        c.execute("""
            INSERT INTO results
            (patient_id, panel_type, qc_status, qc_details, qc_advice, qc_metrics_json,
             t21_res, t18_res, t13_res, sca_res,
             cnv_json, rat_json, full_z_json, final_summary, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_db_id, results['panel'], results['qc_status'],
            str(results['qc_msgs']), results['qc_advice'], qc_metrics_json,
            clinical['t21'], clinical['t18'], clinical['t13'], clinical['sca'],
            json.dumps(clinical['cnv_list']), json.dumps(clinical['rat_list']),
            json.dumps(full_z) if full_z else "{}", clinical['final'],
            datetime.now().isoformat(), st.session_state.user['id']
        ))
        result_id = c.lastrowid

        # Commit transaction
        conn.commit()

        log_audit("SAVE_RESULT", f"Created result {result_id} for patient {patient['id']}", st.session_state.user['id'])
        return result_id, "Success"
    except Exception as e:
        if conn:
            conn.rollback()
        st.error(f"Database error: {e}")
        return 0, str(e)
    finally:
        if conn:
            conn.close()

def update_patient(patient_id: int, data: Dict) -> Tuple[bool, str]:
    """Update patient information."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE patients
                SET full_name = ?, age = ?, weight_kg = ?, height_cm = ?, bmi = ?,
                    weeks = ?, clinical_notes = ?
                WHERE id = ? AND (is_deleted = 0 OR is_deleted IS NULL)
            """, (
                data['name'], data['age'], data['weight'], data['height'],
                data['bmi'], data['weeks'], data['notes'], patient_id
            ))
            conn.commit()
            log_audit("UPDATE_PATIENT", f"Updated patient {patient_id}", st.session_state.user['id'])
            return True, "Patient updated successfully"
    except Exception as e:
        return False, str(e)

def update_result(result_id: int, data: Dict, user_id: int) -> Tuple[bool, str]:
    """Update test result information including z-scores, QC metrics, and clinical results."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE results
                SET panel_type = ?, qc_status = ?, qc_details = ?, qc_advice = ?,
                    qc_metrics_json = ?, t21_res = ?, t18_res = ?, t13_res = ?, sca_res = ?,
                    cnv_json = ?, rat_json = ?, full_z_json = ?, final_summary = ?
                WHERE id = ?
            """, (
                data['panel_type'], data['qc_status'], data['qc_details'], data['qc_advice'],
                json.dumps(data['qc_metrics']), data['t21_res'], data['t18_res'], data['t13_res'],
                data['sca_res'], json.dumps(data['cnv_list']), json.dumps(data['rat_list']),
                json.dumps(data['full_z']), data['final_summary'], result_id
            ))
            conn.commit()
            log_audit("UPDATE_RESULT", f"Updated result {result_id}", user_id)
            return True, "Result updated successfully"
    except Exception as e:
        return False, str(e)

def get_result_details(result_id: int) -> Optional[Dict]:
    """Get full result details for editing."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, patient_id, panel_type, qc_status, qc_details, qc_advice,
                       qc_metrics_json, t21_res, t18_res, t13_res, sca_res,
                       cnv_json, rat_json, full_z_json, final_summary, created_at
                FROM results
                WHERE id = ?
            """, (result_id,))
            row = c.fetchone()
            if row:
                return {
                    'id': row[0],
                    'patient_id': row[1],
                    'panel_type': row[2],
                    'qc_status': row[3],
                    'qc_details': row[4],
                    'qc_advice': row[5],
                    'qc_metrics': json.loads(row[6]) if row[6] else {},
                    't21_res': row[7],
                    't18_res': row[8],
                    't13_res': row[9],
                    'sca_res': row[10],
                    'cnv_list': json.loads(row[11]) if row[11] else [],
                    'rat_list': json.loads(row[12]) if row[12] else [],
                    'full_z': json.loads(row[13]) if row[13] else {},
                    'final_summary': row[14],
                    'created_at': row[15]
                }
    except Exception:
        pass
    return None

def get_patient_details(patient_id: int) -> Optional[Dict]:
    """Get full patient details including all results (excluding deleted patients)."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.mrn_id, p.full_name, p.age, p.weight_kg, p.height_cm,
                       p.bmi, p.weeks, p.clinical_notes, p.created_at
                FROM patients p
                WHERE p.id = ? AND (p.is_deleted = 0 OR p.is_deleted IS NULL)
            """, (patient_id,))
            row = c.fetchone()
            if row:
                return {
                    'id': row[0],
                    'mrn': row[1],
                    'name': row[2],
                    'age': row[3],
                    'weight': row[4],
                    'height': row[5],
                    'bmi': row[6],
                    'weeks': row[7],
                    'notes': row[8],
                    'created_at': row[9]
                }
    except Exception:
        pass
    return None

def delete_record(report_id: int) -> Tuple[bool, str]:
    """Delete a result record with audit logging."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT patient_id FROM results WHERE id = ?", (report_id,))
            row = c.fetchone()
            if not row:
                return False, "Result not found"

            c.execute("DELETE FROM results WHERE id = ?", (report_id,))
            conn.commit()
            log_audit("DELETE_RESULT", f"Deleted result {report_id}", st.session_state.user['id'])
            return True, f"Deleted result {report_id}"
    except Exception as e:
        return False, str(e)

# ==================== PDF IMPORT FUNCTIONS ====================

# PDF validation constants
MAX_PDF_SIZE_MB = 50
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
MIN_TEXT_LENGTH = 100  # Minimum characters expected in a valid NIPT report

def validate_pdf_file(pdf_file, filename: str = "") -> Tuple[bool, str]:
    """Validate PDF file before processing.

    Returns:
        (is_valid, error_message)
    """
    # Check file extension
    if filename:
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{ext}' not in ALLOWED_PDF_EXTENSIONS:
            return False, f"Invalid file type: .{ext}. Only PDF files are allowed."

    # Check file size
    try:
        pdf_file.seek(0, 2)  # Seek to end
        size_bytes = pdf_file.tell()
        pdf_file.seek(0)  # Reset to beginning
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > MAX_PDF_SIZE_MB:
            return False, f"File too large: {size_mb:.1f}MB. Maximum allowed is {MAX_PDF_SIZE_MB}MB."
    except Exception:
        pass  # Can't check size, continue

    # Verify it's a valid PDF by checking header
    try:
        pdf_file.seek(0)
        header = pdf_file.read(8)
        pdf_file.seek(0)
        if isinstance(header, bytes):
            header = header.decode('latin-1', errors='ignore')
        if not header.startswith('%PDF'):
            return False, "Invalid PDF file: missing PDF header signature."
    except Exception:
        pass  # Can't read header, continue

    return True, ""

def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float."""
    try:
        # Remove common non-numeric characters
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default

def safe_int(value: str, default: int = 0) -> int:
    """Safely convert string to int."""
    try:
        cleaned = re.sub(r'[^\d\-]', '', str(value))
        return int(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default

def extract_with_fallback(text: str, patterns: List[str], group: int = 1,
                          flags: int = re.IGNORECASE) -> Optional[str]:
    """Try multiple regex patterns and return first match."""
    for pattern in patterns:
        try:
            match = re.search(pattern, text, flags)
            if match:
                return match.group(group).strip()
        except (re.error, IndexError):
            continue
    return None

def extract_data_from_pdf(pdf_file, filename: str = "") -> Optional[Dict]:
    """Extract comprehensive patient and test data from PDF report.

    Extracts:
    - Patient demographics (name, MRN, age, weight, height, BMI, gestational weeks)
    - Sample information (collection date, laboratory, referring physician)
    - Pregnancy information (singleton/multiple, indication for testing)
    - Sequencing metrics (reads, Cff, GC%, QS, unique rate, error rate)
    - Z-scores for all 22 autosomes plus sex chromosomes
    - SCA type detection with karyotype patterns
    - CNV findings with size, ratio, and chromosomal location
    - RAT findings with chromosome and Z-score
    - QC status and final interpretation
    - Clinical notes and recommendations

    Returns:
        Dict with extracted data or None if extraction fails
    """
    extraction_warnings = []

    # Validate PDF file first
    is_valid, error_msg = validate_pdf_file(pdf_file, filename)
    if not is_valid:
        log_audit("PDF_VALIDATION_FAILED", f"{filename}: {error_msg}", None)
        st.warning(f"PDF validation warning for {filename}: {error_msg}")
        # Continue anyway - might still be processable

    try:
        pdf_file.seek(0)  # Ensure we're at the beginning
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        if len(pdf_reader.pages) == 0:
            st.error(f"PDF file {filename} has no pages")
            return None

        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e:
                extraction_warnings.append(f"Could not extract text from page {page_num + 1}")

        # Check if we got any text
        if len(text.strip()) < MIN_TEXT_LENGTH:
            st.warning(f"Limited text extracted from {filename}. The PDF may be scanned/image-based.")
            extraction_warnings.append("Low text content - possible scanned PDF")

        # Clean up text - normalize whitespace and line endings
        text = re.sub(r'\s+', ' ', text)
        text_lines = text.replace('. ', '.\n').replace(': ', ': ')

        # Initialize comprehensive data structure
        data = {
            'source_file': filename,
            'patient_name': '',
            'mrn': '',
            'age': 0,
            'weight': 0.0,
            'height': 0,
            'bmi': 0.0,
            'weeks': 0,
            'panel': 'NIPT Standard',
            'reads': 0.0,
            'cff': 0.0,
            'gc': 0.0,
            'qs': 0.0,
            'unique_rate': 0.0,
            'error_rate': 0.0,
            'z_scores': {},
            'sca_type': 'XX',
            'cnv_findings': [],
            'rat_findings': [],
            'qc_status': '',
            'final_result': '',
            'notes': '',
            # New comprehensive fields
            'sample_date': '',
            'report_date': '',
            'laboratory': '',
            'referring_physician': '',
            'indication': '',
            'pregnancy_type': 'Singleton',
            'sample_type': '',
            'fetal_sex': '',
            'risk_t21': '',
            'risk_t18': '',
            'risk_t13': '',
            't21_direct': '',  # Direct result extraction (POSITIVE/LOW_RISK)
            't18_direct': '',  # Direct result extraction (POSITIVE/LOW_RISK)
            't13_direct': '',  # Direct result extraction (POSITIVE/LOW_RISK)
            'sensitivity_t21': '',
            'specificity_t21': '',
            'ppv_t21': '',
            'npv_t21': '',
            'microdeletion_results': [],
            'extraction_confidence': 'HIGH'
        }

        # ===== PATIENT DEMOGRAPHICS =====
        # Extract patient name (multiple patterns for different report formats)
        name_patterns = [
            r'(?:Patient|Patient\s+Name|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|ID|Age|DOB|Date|\||,|\n|$))',
            r'Full\s+Name[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|\n|$))',
            r'Name\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'(?:Mrs?\.?|Ms\.?|Dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                # Clean up name - remove trailing numbers, special chars
                name = re.sub(r'[\d\|\,]+$', '', name).strip()
                if len(name) > 2 and ' ' in name or len(name) > 5:
                    data['patient_name'] = name
                    break

        # Extract MRN / Patient ID (multiple patterns)
        mrn_patterns = [
            r'MRN[:\s#]+([A-Za-z0-9\-]+)',
            r'Medical\s+Record\s+(?:Number|No\.?)[:\s]+([A-Za-z0-9\-]+)',
            r'(?:Patient\s+)?ID[:\s#]+([A-Za-z0-9\-]{4,})',
            r'File\s+(?:Number|No\.?)[:\s]+([A-Za-z0-9\-]+)',
            r'Accession[:\s#]+([A-Za-z0-9\-]+)',
            r'Sample\s+ID[:\s]+([A-Za-z0-9\-]+)',
            r'Case\s+(?:Number|No\.?|ID)[:\s]+([A-Za-z0-9\-]+)',
        ]
        for pattern in mrn_patterns:
            mrn_match = re.search(pattern, text, re.IGNORECASE)
            if mrn_match:
                data['mrn'] = mrn_match.group(1).strip()
                break

        # Extract age (with validation)
        age_patterns = [
            r'(?:Maternal\s+)?Age[:\s]+(\d{1,2})\s*(?:years?|yrs?|y)?(?:\s|,|\.|$)',
            r'Age\s*\((?:years?|yrs?)\)[:\s]+(\d{1,2})',
            r'(\d{2})\s*(?:years?|yrs?)\s+old',
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                age = int(age_match.group(1))
                if 15 <= age <= 60:  # Reasonable maternal age range
                    data['age'] = age
                    break

        # Extract weight (with unit conversion if needed)
        weight_patterns = [
            r'Weight[:\s]+(\d+\.?\d*)\s*(?:kg|KG|kilograms?)',
            r'Weight[:\s]+(\d+\.?\d*)\s*(?:lbs?|pounds?)',  # Will need conversion
            r'(?:Maternal\s+)?Weight[:\s]+(\d+\.?\d*)',
        ]
        for pattern in weight_patterns:
            weight_match = re.search(pattern, text, re.IGNORECASE)
            if weight_match:
                weight = float(weight_match.group(1))
                # Convert lbs to kg if detected
                if 'lb' in pattern.lower() or weight > 150:
                    weight = weight * 0.453592
                if 30 <= weight <= 200:  # Reasonable weight range in kg
                    data['weight'] = round(weight, 1)
                    break

        # Extract height (with unit conversion if needed)
        height_patterns = [
            r'Height[:\s]+(\d{2,3})\s*(?:cm|CM|centimeters?)',
            r'Height[:\s]+(\d)[\'′](\d{1,2})[\"″]?',  # feet'inches" format
            r'(?:Maternal\s+)?Height[:\s]+(\d{2,3})',
        ]
        for pattern in height_patterns:
            height_match = re.search(pattern, text, re.IGNORECASE)
            if height_match:
                if "'" in pattern or "′" in pattern:
                    # Convert feet/inches to cm
                    feet = int(height_match.group(1))
                    inches = int(height_match.group(2)) if height_match.group(2) else 0
                    height = int((feet * 12 + inches) * 2.54)
                else:
                    height = int(height_match.group(1))
                if 100 <= height <= 220:  # Reasonable height range in cm
                    data['height'] = height
                    break

        # Extract BMI
        bmi_patterns = [
            r'BMI[:\s]+(\d+\.?\d*)',
            r'Body\s+Mass\s+Index[:\s]+(\d+\.?\d*)',
        ]
        for pattern in bmi_patterns:
            bmi_match = re.search(pattern, text, re.IGNORECASE)
            if bmi_match:
                bmi = float(bmi_match.group(1))
                if 15 <= bmi <= 60:  # Reasonable BMI range
                    data['bmi'] = round(bmi, 1)
                    break

        # Calculate BMI if weight and height available but BMI not extracted
        if not data['bmi'] and data['weight'] > 0 and data['height'] > 0:
            data['bmi'] = round(data['weight'] / ((data['height']/100)**2), 1)

        # Extract gestational weeks (multiple patterns)
        weeks_patterns = [
            r'(?:Gestational\s+Age|Gest\.?\s+Age|GA)[:\s]+(\d{1,2})\s*(?:\+\s*\d+)?(?:\s*weeks?|\s*wks?)?',
            r'(\d{1,2})\s*(?:\+\s*\d+)?\s*weeks?\s*(?:gestation|pregnant|GA)',
            r'Weeks?\s*(?:of\s+)?(?:Gestation|Pregnancy)[:\s]+(\d{1,2})',
            r'(?:at\s+)?(\d{1,2})\s*weeks?\s*(?:gestation)?',
        ]
        for pattern in weeks_patterns:
            weeks_match = re.search(pattern, text, re.IGNORECASE)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                if 9 <= weeks <= 42:  # Reasonable gestational age for NIPT
                    data['weeks'] = weeks
                    break

        # ===== SAMPLE & REPORT INFORMATION =====
        # Extract sample collection date
        date_patterns = [
            r'(?:Sample|Collection|Draw)\s+Date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:Date\s+)?(?:Collected|Drawn)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Collection[:\s]+(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})',
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                data['sample_date'] = date_match.group(1).strip()
                break

        # Extract report date
        report_date_patterns = [
            r'(?:Report|Reported)\s+Date[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Date\s+(?:of\s+)?Report[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        for pattern in report_date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                data['report_date'] = date_match.group(1).strip()
                break

        # Extract laboratory name
        lab_patterns = [
            r'(?:Laboratory|Lab)[:\s]+([A-Za-z][A-Za-z\s\-&]+?)(?:\n|$|Address)',
            r'Performed\s+(?:at|by)[:\s]+([A-Za-z][A-Za-z\s\-&]+?)(?:\n|$)',
            r'([A-Za-z]+\s+(?:Genetics|Genomics|Laboratory|Lab|Diagnostics)(?:\s+[A-Za-z]+)?)',
        ]
        for pattern in lab_patterns:
            lab_match = re.search(pattern, text, re.IGNORECASE)
            if lab_match:
                data['laboratory'] = lab_match.group(1).strip()[:100]
                break

        # Extract referring physician
        physician_patterns = [
            r'(?:Referring|Ordering)\s+(?:Physician|Provider|Doctor|MD)[:\s]+(?:Dr\.?\s+)?([A-Za-z][A-Za-z\s\-\.]+)',
            r'Physician[:\s]+(?:Dr\.?\s+)?([A-Za-z][A-Za-z\s\-\.]+?)(?:\n|$|,)',
            r'Ordered\s+[Bb]y[:\s]+(?:Dr\.?\s+)?([A-Za-z][A-Za-z\s\-\.]+)',
        ]
        for pattern in physician_patterns:
            phys_match = re.search(pattern, text, re.IGNORECASE)
            if phys_match:
                data['referring_physician'] = phys_match.group(1).strip()[:100]
                break

        # Extract indication for testing
        indication_patterns = [
            r'(?:Indication|Reason)[:\s]+(.+?)(?:\n|$|Panel|Test)',
            r'(?:Clinical\s+)?Indication[:\s]+(.+?)(?:\n|$)',
            r'Referred\s+for[:\s]+(.+?)(?:\n|$)',
        ]
        for pattern in indication_patterns:
            ind_match = re.search(pattern, text, re.IGNORECASE)
            if ind_match:
                data['indication'] = ind_match.group(1).strip()[:200]
                break

        # Extract pregnancy type (singleton/twin/multiple)
        if re.search(r'(?:twin|twins|multiple|dichorionic|monochorionic|dizygotic|monozygotic)', text, re.IGNORECASE):
            data['pregnancy_type'] = 'Multiple'
        elif re.search(r'singleton', text, re.IGNORECASE):
            data['pregnancy_type'] = 'Singleton'

        # Extract sample type
        sample_patterns = [
            r'(?:Sample|Specimen)\s+Type[:\s]+([A-Za-z\s]+?)(?:\n|$|,)',
            r'(?:Blood|Plasma|Serum|cfDNA)',
        ]
        for pattern in sample_patterns:
            sample_match = re.search(pattern, text, re.IGNORECASE)
            if sample_match:
                data['sample_type'] = sample_match.group(1).strip() if sample_match.lastindex else sample_match.group(0)
                break

        # ===== SEQUENCING METRICS =====
        # Extract panel type
        panel_patterns = [
            r'Panel[:\s]+(NIPT\s+\w+)',
            r'Test\s+(?:Type|Name)[:\s]+(NIPT\s+\w+)',
            r'(NIPT\s+(?:Basic|Standard|Plus|Pro|Extended|Expanded))',
            r'(?:Panorama|Harmony|MaterniT21|verifi|NIFTY|Natera)',  # Common brand names
        ]
        for pattern in panel_patterns:
            panel_match = re.search(pattern, text, re.IGNORECASE)
            if panel_match:
                panel = panel_match.group(1).strip()
                # Normalize panel name
                if any(kw in panel.lower() for kw in ['expanded', 'extended', 'plus', 'comprehensive']):
                    data['panel'] = 'NIPT Plus'
                elif any(kw in panel.lower() for kw in ['pro', 'genome', 'full']):
                    data['panel'] = 'NIPT Pro'
                elif 'basic' in panel.lower():
                    data['panel'] = 'NIPT Basic'
                else:
                    data['panel'] = 'NIPT Standard'
                break

        # Extract sequencing reads
        reads_patterns = [
            r'(?:Total\s+)?Reads?[:\s]+(\d+\.?\d*)\s*(?:M|million)',
            r'(?:Sequencing\s+)?Reads?[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*(?:M|million)\s+reads?',
        ]
        for pattern in reads_patterns:
            reads_match = re.search(pattern, text, re.IGNORECASE)
            if reads_match:
                reads = float(reads_match.group(1))
                if reads > 100:  # Likely in raw number, convert to millions
                    reads = reads / 1000000
                if 0.1 <= reads <= 100:  # Reasonable range
                    data['reads'] = round(reads, 2)
                    break

        # Extract fetal fraction (Cff)
        cff_patterns = [
            r'(?:Cff|FF|Fetal\s+Fraction|cfDNA\s+Fraction)[:\s]+(\d+\.?\d*)\s*%?',
            r'Fetal\s+(?:DNA\s+)?Fraction[:\s]+(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*%?\s*(?:fetal\s+fraction|FF)',
        ]
        for pattern in cff_patterns:
            cff_match = re.search(pattern, text, re.IGNORECASE)
            if cff_match:
                cff = float(cff_match.group(1))
                if 0.5 <= cff <= 50:  # Reasonable fetal fraction range
                    data['cff'] = round(cff, 2)
                    break

        # Extract GC content
        gc_patterns = [
            r'GC\s*(?:Content)?[:\s]+(\d+\.?\d*)\s*%?',
            r'GC%[:\s]+(\d+\.?\d*)',
        ]
        for pattern in gc_patterns:
            gc_match = re.search(pattern, text, re.IGNORECASE)
            if gc_match:
                gc = float(gc_match.group(1))
                if 20 <= gc <= 80:  # Reasonable GC content range
                    data['gc'] = round(gc, 2)
                    break

        # Extract quality score
        qs_patterns = [
            r'QS[:\s]+(\d+\.?\d*)',
            r'Quality\s+Score[:\s]+(\d+\.?\d*)',
            r'(?:Data\s+)?Quality[:\s]+(\d+\.?\d*)',
        ]
        for pattern in qs_patterns:
            qs_match = re.search(pattern, text, re.IGNORECASE)
            if qs_match:
                qs = float(qs_match.group(1))
                if 0 <= qs <= 10:  # Reasonable QS range
                    data['qs'] = round(qs, 3)
                    break

        # Extract unique read rate
        unique_patterns = [
            r'Unique\s*(?:Read)?\s*(?:Rate)?[:\s]+(\d+\.?\d*)\s*%?',
            r'Uniquely\s+Mapped[:\s]+(\d+\.?\d*)',
            r'Mapping\s+Rate[:\s]+(\d+\.?\d*)',
        ]
        for pattern in unique_patterns:
            unique_match = re.search(pattern, text, re.IGNORECASE)
            if unique_match:
                unique = float(unique_match.group(1))
                if 0 <= unique <= 100:
                    data['unique_rate'] = round(unique, 2)
                    break

        # Extract error rate
        error_patterns = [
            r'Error\s*(?:Rate)?[:\s]+(\d+\.?\d*)\s*%?',
            r'Sequencing\s+Error[:\s]+(\d+\.?\d*)',
        ]
        for pattern in error_patterns:
            error_match = re.search(pattern, text, re.IGNORECASE)
            if error_match:
                error = float(error_match.group(1))
                if 0 <= error <= 10:
                    data['error_rate'] = round(error, 3)
                    break

        # ===== Z-SCORES (ALL AUTOSOMES) =====
        # Helper function to extract Z-score with multiple attempts, preferring later matches (final results)
        def extract_z_score(patterns_list, search_text):
            """Extract Z-score using patterns, prefer later matches for final/corrected values."""
            all_matches = []
            for pattern in patterns_list:
                # Find all matches, not just first
                for match in re.finditer(pattern, search_text, re.IGNORECASE):
                    try:
                        z_val = float(match.group(1))
                        if -20 <= z_val <= 50:  # Reasonable Z-score range
                            all_matches.append((match.start(), z_val))
                    except (ValueError, IndexError):
                        continue
            if all_matches:
                # Return the LAST match (more likely to be the final/corrected value)
                all_matches.sort(key=lambda x: x[0])
                return round(all_matches[-1][1], 3)
            return None

        # Extract Z-scores for main trisomies (13, 18, 21)
        # Use word boundaries (\b) to prevent partial matches (e.g., Z1 matching in Z10)
        for chrom in [13, 18, 21]:
            z_patterns = [
                # Exact formats with word boundaries
                rf'Z[-\s]?{chrom}\b[:\s]+(-?\d+\.?\d*)',
                rf'Z{chrom}\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
                # Trisomy-specific patterns
                rf'Trisomy\s+{chrom}\b[^Z]*?Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
                rf'T{chrom}\b[^Z]*?Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
                # Chromosome-based patterns with word boundaries
                rf'Chr(?:omosome)?\s*{chrom}\b\s*Z[:\s]+(-?\d+\.?\d*)',
                rf'Chr(?:omosome)?\s*{chrom}\b[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
                # Result line patterns (common in tables)
                rf'{chrom}\s*[|,\t]\s*(-?\d+\.?\d*)\s*[|,\t]',
                # Z-score followed by chromosome
                rf'Z[-\s]?Score[:\s]+(-?\d+\.?\d*).*?(?:Chr|Chromosome|Trisomy)\s*{chrom}\b',
            ]
            z_val = extract_z_score(z_patterns, text)
            if z_val is not None:
                data['z_scores'][chrom] = z_val

        # Extract Z-scores for ALL other autosomes (1-22, excluding 13, 18, 21)
        for chrom in range(1, 23):
            if chrom in [13, 18, 21]:
                continue  # Already captured above

            z_patterns = [
                # Exact formats with word boundaries - critical for single digit chromosomes
                rf'Z[-\s]?{chrom}\b[:\s]+(-?\d+\.?\d*)',
                rf'Z{chrom}\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
                rf'Chr(?:omosome)?\s*{chrom}\b\s*Z[:\s]+(-?\d+\.?\d*)',
                rf'Chr(?:omosome)?\s*{chrom}\b[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            ]
            z_val = extract_z_score(z_patterns, text)
            if z_val is not None:
                data['z_scores'][chrom] = z_val

        # Extract SCA Z-scores (XX and XY) - improved patterns
        z_xx_patterns = [
            r'Z[-\s]?XX\b[:\s]+(-?\d+\.?\d*)',
            r'ZXX\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
            r'XX\s+Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
            r'(?:Sex\s+)?(?:Chromosome\s+)?XX[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            r'X\s+Chromosome[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
        ]
        z_val = extract_z_score(z_xx_patterns, text)
        if z_val is not None:
            data['z_scores']['XX'] = z_val

        z_xy_patterns = [
            r'Z[-\s]?XY\b[:\s]+(-?\d+\.?\d*)',
            r'ZXY\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
            r'XY\s+Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
            r'(?:Sex\s+)?(?:Chromosome\s+)?XY[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            r'Y\s+Chromosome[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
        ]
        z_val = extract_z_score(z_xy_patterns, text)
        if z_val is not None:
            data['z_scores']['XY'] = z_val

        # ===== SCA TYPE & FETAL SEX DETECTION =====
        # Order matters: more specific patterns should come first
        sca_patterns = [
            # Composite/mosaicism patterns (must come before simple patterns)
            (r'XXX\+XY|XXX\s*\+\s*XY|47[,\s]*XXX/46[,\s]*XY|Mosaicism.*XXX.*XY', 'XXX+XY'),
            (r'XO\+XY|XO\s*\+\s*XY|45[,\s]*X/46[,\s]*XY|Mosaicism.*X[O0].*XY', 'XO+XY'),
            # Standard abnormal patterns
            (r'Turner|Monosomy\s+X|45[,\s]*X(?:O)?(?!\s*\+)', 'XO'),
            (r'Triple\s+X|Trisomy\s+X|47[,\s]*XXX(?!\s*\+)', 'XXX'),
            (r'Klinefelter|47[,\s]*XXY', 'XXY'),
            (r'47[,\s]*XYY|Jacob(?:s)?(?:\s+syndrome)?', 'XYY'),
            # Normal patterns
            (r'(?:Fetal\s+)?Sex[:\s]+Male|(?:Fetal\s+)?Gender[:\s]+Male|XY\s+(?:Male|detected)|Y\s+chromosome\s+(?:detected|present)', 'XY'),
            (r'(?:Fetal\s+)?Sex[:\s]+Female|(?:Fetal\s+)?Gender[:\s]+Female|XX\s+(?:Female|detected)|No\s+Y\s+chromosome', 'XX'),
        ]
        for pattern, sca_type in sca_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                data['sca_type'] = sca_type
                # Also set fetal sex based on SCA type
                if sca_type in ['XY', 'XXY', 'XYY']:
                    data['fetal_sex'] = 'Male'
                elif sca_type in ['XX', 'XO', 'XXX']:
                    data['fetal_sex'] = 'Female'
                elif sca_type in ['XXX+XY', 'XO+XY']:
                    # Mosaicism - sex indeterminate, Y detected
                    data['fetal_sex'] = 'Indeterminate (Mosaicism)'
                break

        # Try to extract fetal sex separately if not determined
        if not data['fetal_sex']:
            sex_patterns = [
                (r'(?:Fetal\s+)?Sex[:\s]+Male|(?:Male|Boy)\s+fetus', 'Male'),
                (r'(?:Fetal\s+)?Sex[:\s]+Female|(?:Female|Girl)\s+fetus', 'Female'),
                (r'Y\s+chromosome\s+(?:detected|present|positive)', 'Male'),
                (r'Y\s+chromosome\s+(?:not\s+detected|absent|negative)', 'Female'),
            ]
            for pattern, sex in sex_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    data['fetal_sex'] = sex
                    break

        # ===== CNV FINDINGS =====
        # Look for CNV sections with more comprehensive patterns
        cnv_section_patterns = [
            r'CNV[:\s]+(.+?)(?:RAT|Rare|Final|Interpretation|Result|$)',
            r'Copy\s+Number\s+Variation[:\s]+(.+?)(?:RAT|Final|$)',
            r'Microdeletion/Microduplication[:\s]+(.+?)(?:Final|$)',
        ]
        for section_pattern in cnv_section_patterns:
            cnv_section = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)
            if cnv_section:
                cnv_text = cnv_section.group(1)

                # Extract CNV entries with various formats
                cnv_entry_patterns = [
                    r'(\d+\.?\d*)\s*(?:Mb|MB|megabases?).*?(\d+\.?\d*)\s*%',
                    r'(?:Size|Region)[:\s]+(\d+\.?\d*)\s*(?:Mb|MB).*?(?:Ratio|Score)[:\s]+(\d+\.?\d*)',
                    r'Chr(?:omosome)?\s*(\d+)[pq]?\d*.*?(\d+\.?\d*)\s*(?:Mb|MB)',
                ]
                for pattern in cnv_entry_patterns:
                    cnv_matches = re.finditer(pattern, cnv_text, re.IGNORECASE)
                    for match in cnv_matches:
                        try:
                            size = float(match.group(1))
                            ratio = float(match.group(2)) if match.lastindex >= 2 else 0
                            if 0.1 <= size <= 200:  # Reasonable CNV size
                                data['cnv_findings'].append({
                                    'size': round(size, 2),
                                    'ratio': round(ratio, 2)
                                })
                        except (ValueError, IndexError):
                            continue
                break

        # ===== RAT FINDINGS =====
        # Look for RAT/Rare Autosome sections
        rat_section_patterns = [
            r'(?:RAT|Rare\s+Auto(?:somal)?\s+Trisomy)[:\s]+(.+?)(?:Final|CNV|Interpretation|$)',
            r'Other\s+(?:Chromosomal|Autosomal)\s+Findings[:\s]+(.+?)(?:Final|$)',
        ]
        for section_pattern in rat_section_patterns:
            rat_section = re.search(section_pattern, text, re.IGNORECASE | re.DOTALL)
            if rat_section:
                rat_text = rat_section.group(1)

                # Extract RAT entries
                rat_entry_patterns = [
                    r'Chr(?:omosome)?\s*(\d+).*?Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
                    r'Trisomy\s+(\d+).*?Z[:\s]+(-?\d+\.?\d*)',
                ]
                for pattern in rat_entry_patterns:
                    rat_matches = re.finditer(pattern, rat_text, re.IGNORECASE)
                    for match in rat_matches:
                        try:
                            chrom = int(match.group(1))
                            z_score = float(match.group(2))
                            if chrom not in [13, 18, 21] and 1 <= chrom <= 22:
                                data['rat_findings'].append({
                                    'chr': chrom,
                                    'z': round(z_score, 3)
                                })
                        except (ValueError, IndexError):
                            continue
                break

        # ===== MICRODELETION SYNDROMES =====
        microdeletion_patterns = [
            (r'22q11\.?2\s+(?:deletion|DiGeorge)', '22q11.2 Deletion (DiGeorge)'),
            (r'1p36\s+deletion', '1p36 Deletion'),
            (r'5p[-\s]?(?:deletion)?|Cri[- ]du[- ]Chat', '5p Deletion (Cri-du-Chat)'),
            (r'15q11\.?2\s+(?:deletion)?|Prader[- ]Willi|Angelman', '15q11.2 Deletion (Prader-Willi/Angelman)'),
            (r'4p[-\s]?(?:deletion)?|Wolf[- ]Hirschhorn', '4p Deletion (Wolf-Hirschhorn)'),
        ]
        for pattern, syndrome in microdeletion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Check if positive or negative
                context = re.search(rf'{pattern}.{{0,100}}(positive|negative|detected|not\s+detected|high\s+risk|low\s+risk)',
                                   text, re.IGNORECASE)
                if context:
                    result = context.group(1).lower()
                    is_positive = result in ['positive', 'detected', 'high risk']
                    data['microdeletion_results'].append({
                        'syndrome': syndrome,
                        'result': 'Positive' if is_positive else 'Negative'
                    })

        # ===== QC STATUS & RESULTS =====
        qc_patterns = [
            r'QC\s+Status[:\s]+(\w+)',
            r'Quality\s+Control[:\s]+(\w+)',
            r'(?:Sample\s+)?Quality[:\s]+(PASS|FAIL|WARNING|ADEQUATE|INADEQUATE)',
        ]
        for pattern in qc_patterns:
            qc_match = re.search(pattern, text, re.IGNORECASE)
            if qc_match:
                qc_val = qc_match.group(1).upper()
                if qc_val in ['PASS', 'PASSED', 'ADEQUATE', 'ACCEPTABLE']:
                    data['qc_status'] = 'PASS'
                elif qc_val in ['FAIL', 'FAILED', 'INADEQUATE', 'REJECTED']:
                    data['qc_status'] = 'FAIL'
                else:
                    data['qc_status'] = 'WARNING'
                break

        # Extract final result/interpretation
        result_patterns = [
            r'(?:Final\s+)?(?:Interpretation|Result|Conclusion)[:\s]+([A-Za-z\s\(\)\-]+?)(?:\.|$|\n)',
            r'(?:Overall\s+)?(?:Risk|Assessment)[:\s]+((?:Low|High|Positive|Negative)[A-Za-z\s\(\)]*)',
            r'NIPT\s+Result[:\s]+([A-Za-z\s\(\)]+)',
        ]
        for pattern in result_patterns:
            result_match = re.search(pattern, text, re.IGNORECASE)
            if result_match:
                result = result_match.group(1).strip()
                if len(result) > 3:
                    data['final_result'] = result[:200]
                    break

        # Extract risk values if available
        risk_patterns = [
            (r'(?:T21|Trisomy\s*21|Down).*?Risk[:\s]+(?:1\s*(?:in|:)\s*)?(\d+)', 'risk_t21'),
            (r'(?:T18|Trisomy\s*18|Edwards).*?Risk[:\s]+(?:1\s*(?:in|:)\s*)?(\d+)', 'risk_t18'),
            (r'(?:T13|Trisomy\s*13|Patau).*?Risk[:\s]+(?:1\s*(?:in|:)\s*)?(\d+)', 'risk_t13'),
        ]
        for pattern, field in risk_patterns:
            risk_match = re.search(pattern, text, re.IGNORECASE)
            if risk_match:
                data[field] = f"1 in {risk_match.group(1)}"

        # ===== DIRECT TRISOMY RESULT EXTRACTION =====
        # Extract trisomy results directly from text (more reliable than Z-score interpretation)
        trisomy_result_patterns = [
            # T21 patterns
            (r'(?:T21|Trisomy\s*21|Down\s*Syndrome)[:\s]+[^,\n]{0,30}?(Positive|Negative|Low\s*Risk|High\s*Risk|Detected|Not\s*Detected)', 't21_direct'),
            (r'(?:Trisomy\s*21|T21|Down)[^,\n]{0,50}?(?:Result|Status|Risk)[:\s]+(Positive|Negative|Low|High)', 't21_direct'),
            # T18 patterns
            (r'(?:T18|Trisomy\s*18|Edwards\s*Syndrome)[:\s]+[^,\n]{0,30}?(Positive|Negative|Low\s*Risk|High\s*Risk|Detected|Not\s*Detected)', 't18_direct'),
            (r'(?:Trisomy\s*18|T18|Edwards)[^,\n]{0,50}?(?:Result|Status|Risk)[:\s]+(Positive|Negative|Low|High)', 't18_direct'),
            # T13 patterns
            (r'(?:T13|Trisomy\s*13|Patau\s*Syndrome)[:\s]+[^,\n]{0,30}?(Positive|Negative|Low\s*Risk|High\s*Risk|Detected|Not\s*Detected)', 't13_direct'),
            (r'(?:Trisomy\s*13|T13|Patau)[^,\n]{0,50}?(?:Result|Status|Risk)[:\s]+(Positive|Negative|Low|High)', 't13_direct'),
        ]
        for pattern, field in trisomy_result_patterns:
            result_match = re.search(pattern, text, re.IGNORECASE)
            if result_match:
                result_text = result_match.group(1).strip().lower()
                # Normalize the result
                if result_text in ['positive', 'detected', 'high', 'high risk']:
                    data[field] = 'POSITIVE'
                elif result_text in ['negative', 'not detected', 'low', 'low risk']:
                    data[field] = 'LOW_RISK'
                # Only store if not already set
                if field not in data or not data.get(field):
                    data[field] = data.get(field, '')

        # Extract clinical notes
        notes_patterns = [
            r'(?:Clinical\s+)?Notes?[:\s]+(.+?)(?:\n\n|={3,}|Disclaimer|Limitation|$)',
            r'Comments?[:\s]+(.+?)(?:\n\n|={3,}|$)',
            r'(?:Additional\s+)?(?:Information|Remarks)[:\s]+(.+?)(?:\n\n|$)',
        ]
        for pattern in notes_patterns:
            notes_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if notes_match:
                notes = notes_match.group(1).strip()
                # Clean up notes
                notes = re.sub(r'\s+', ' ', notes)
                if len(notes) > 5:
                    data['notes'] = notes[:500]
                    break

        # ===== EXTRACTION CONFIDENCE =====
        # Calculate confidence based on how much critical data was extracted
        critical_fields = {
            'patient_name': bool(data['patient_name']),
            'mrn': bool(data['mrn']),
            'age': data['age'] > 0,
            'weeks': data['weeks'] > 0,
            'cff': data['cff'] > 0,
            'z_scores': len(data['z_scores']) >= 3,
            'final_result': bool(data['final_result']),
        }

        extracted_count = sum(critical_fields.values())
        missing_fields = [k for k, v in critical_fields.items() if not v]

        if extracted_count >= 6:
            data['extraction_confidence'] = 'HIGH'
        elif extracted_count >= 4:
            data['extraction_confidence'] = 'MEDIUM'
        else:
            data['extraction_confidence'] = 'LOW'

        # Store extraction metadata
        data['_extraction_warnings'] = extraction_warnings
        data['_missing_fields'] = missing_fields
        data['_extracted_count'] = extracted_count

        # Log extraction result
        log_audit("PDF_EXTRACTED",
                 f"{filename}: confidence={data['extraction_confidence']}, "
                 f"fields={extracted_count}/7, mrn={data.get('mrn', 'NONE')}",
                 st.session_state.user['id'] if 'user' in st.session_state else None)

        return data

    except PyPDF2.errors.PdfReadError as e:
        error_msg = f"Invalid or corrupted PDF file {filename}: {str(e)}"
        st.error(error_msg)
        log_audit("PDF_READ_ERROR", error_msg, None)
        return None
    except Exception as e:
        error_msg = f"PDF extraction error in {filename}: {str(e)}"
        st.error(error_msg)
        log_audit("PDF_EXTRACTION_ERROR", error_msg, None)
        return None

def parse_pdf_batch(pdf_files: List) -> Dict[str, List[Dict]]:
    """Parse multiple PDF files and group by patient MRN."""
    # Dictionary to group by MRN
    patients = {}
    errors = []
    
    for pdf_file in pdf_files:
        filename = pdf_file.name if hasattr(pdf_file, 'name') else 'unknown.pdf'
        data = extract_data_from_pdf(pdf_file, filename)
        
        if data:
            if data['mrn']:
                # Group by MRN
                mrn = data['mrn']
                if mrn not in patients:
                    patients[mrn] = []
                patients[mrn].append(data)
            else:
                errors.append(f"No MRN found in {filename}")
        else:
            errors.append(f"Failed to extract data from {filename}")
    
    return {'patients': patients, 'errors': errors}

def get_maternal_age_risk(age: int) -> Dict[str, float]:
    """Calculate maternal age-based prior risk for common aneuploidies.
    Based on published maternal age-specific risk data."""
    # Prior risks per 1000 pregnancies based on maternal age
    # Data from Hook EB, 1981 and updated studies
    age_risk_table = {
        20: {'T21': 1/1441, 'T18': 1/10000, 'T13': 1/14300},
        25: {'T21': 1/1383, 'T18': 1/8300, 'T13': 1/12500},
        30: {'T21': 1/959, 'T18': 1/5900, 'T13': 1/9100},
        32: {'T21': 1/659, 'T18': 1/4500, 'T13': 1/7100},
        34: {'T21': 1/446, 'T18': 1/3300, 'T13': 1/5200},
        35: {'T21': 1/356, 'T18': 1/2700, 'T13': 1/4200},
        36: {'T21': 1/280, 'T18': 1/2200, 'T13': 1/3400},
        37: {'T21': 1/218, 'T18': 1/1800, 'T13': 1/2700},
        38: {'T21': 1/167, 'T18': 1/1400, 'T13': 1/2100},
        39: {'T21': 1/128, 'T18': 1/1100, 'T13': 1/1700},
        40: {'T21': 1/97, 'T18': 1/860, 'T13': 1/1300},
        41: {'T21': 1/73, 'T18': 1/670, 'T13': 1/1000},
        42: {'T21': 1/55, 'T18': 1/530, 'T13': 1/800},
        43: {'T21': 1/41, 'T18': 1/410, 'T13': 1/630},
        44: {'T21': 1/30, 'T18': 1/320, 'T13': 1/490},
        45: {'T21': 1/23, 'T18': 1/250, 'T13': 1/380},
    }

    # Find closest age bracket
    if age < 20:
        return age_risk_table[20]
    elif age >= 45:
        return age_risk_table[45]

    # Linear interpolation for ages between table values
    sorted_ages = sorted(age_risk_table.keys())
    for i, table_age in enumerate(sorted_ages):
        if age <= table_age:
            if age == table_age:
                return age_risk_table[table_age]
            # Interpolate
            prev_age = sorted_ages[i-1] if i > 0 else table_age
            next_age = table_age
            ratio = (age - prev_age) / (next_age - prev_age) if next_age != prev_age else 0
            prev_risks = age_risk_table.get(prev_age, age_risk_table[20])
            next_risks = age_risk_table.get(next_age, age_risk_table[45])
            return {
                'T21': prev_risks['T21'] + (next_risks['T21'] - prev_risks['T21']) * ratio,
                'T18': prev_risks['T18'] + (next_risks['T18'] - prev_risks['T18']) * ratio,
                'T13': prev_risks['T13'] + (next_risks['T13'] - prev_risks['T13']) * ratio,
            }

    return age_risk_table[45]


def get_clinical_recommendation(result: str, test_type: str) -> str:
    """Generate clinical recommendation based on test result."""
    recommendations = {
        'POSITIVE': {
            'T21': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Genetic counseling should be offered.",
            'T18': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.",
            'T13': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.",
            'SCA': "Genetic counseling recommended. Confirmatory testing may be considered based on clinical judgment.",
            'CNV': "Detailed ultrasound recommended. Genetic counseling and possible confirmatory testing advised.",
            'RAT': "Genetic counseling recommended. Clinical correlation and possible confirmatory testing advised."
        },
        'HIGH': {
            'default': "Re-analysis recommended. If persistent, consider confirmatory diagnostic testing."
        },
        'LOW': {
            'default': "No additional testing indicated based on NIPT result alone. Standard prenatal care recommended."
        }
    }

    if 'POSITIVE' in result.upper():
        return recommendations['POSITIVE'].get(test_type, recommendations['POSITIVE'].get('default', ''))
    elif 'HIGH' in result.upper() or 'AMBIGUOUS' in result.upper():
        return recommendations['HIGH']['default']
    else:
        return recommendations['LOW']['default']


def generate_pdf_report(report_id: int, lang: str = None) -> Optional[bytes]:
    """Generate comprehensive clinical PDF report for pathologist review.

    Args:
        report_id: The ID of the result to generate a report for
        lang: Language code ('en' for English, 'fr' for French). If None, uses config default.

    Returns:
        PDF bytes or None if report not found
    """
    try:
        # Get language from config if not specified
        config = load_config()
        if lang is None:
            lang = config.get('REPORT_LANGUAGE', 'en')

        # Helper function for translations
        def t(key: str) -> str:
            return get_translation(key, lang)

        with get_db_connection() as conn:
            query = """
                SELECT r.id, p.full_name, p.mrn_id, p.age, p.weeks, r.created_at, p.clinical_notes,
                       r.panel_type, r.qc_status, r.qc_details, r.qc_advice, r.qc_metrics_json,
                       r.t21_res, r.t18_res, r.t13_res, r.sca_res,
                       r.cnv_json, r.rat_json, r.full_z_json, r.final_summary,
                       p.weight_kg, p.height_cm, p.bmi,
                       u.full_name as technician_name,
                       r.qc_override, r.qc_override_reason, r.qc_override_at,
                       ov_user.full_name as qc_override_by_name
                FROM results r
                JOIN patients p ON p.id = r.patient_id
                LEFT JOIN users u ON u.id = r.created_by
                LEFT JOIN users ov_user ON ov_user.id = r.qc_override_by
                WHERE r.id = ?
            """
            df = pd.read_sql(query, conn, params=(report_id,))

        if df.empty: return None

        row = df.iloc[0]
        cnvs = json.loads(row['cnv_json']) if row['cnv_json'] else []
        rats = json.loads(row['rat_json']) if row['rat_json'] else []
        z_data = json.loads(row['full_z_json']) if row['full_z_json'] else {}
        qc_details = row['qc_details'] if row['qc_details'] else "[]"
        qc_metrics = json.loads(row['qc_metrics_json']) if row.get('qc_metrics_json') else {}

        # Check for QC override - if overridden, effective status is PASS
        qc_override = bool(row.get('qc_override'))
        qc_override_reason = row.get('qc_override_reason', '')
        qc_override_by = row.get('qc_override_by_name', '')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.4*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16,
                                     textColor=colors.HexColor('#1a5276'), alignment=TA_CENTER,
                                     spaceAfter=6)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10,
                                        alignment=TA_CENTER, textColor=colors.HexColor('#566573'))
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=11,
                                       textColor=colors.HexColor('#2c3e50'), spaceBefore=10, spaceAfter=4)
        small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8,
                                     textColor=colors.HexColor('#7f8c8d'))
        warning_style = ParagraphStyle('Warning', parent=styles['Normal'], fontSize=9,
                                       textColor=colors.HexColor('#c0392b'), fontName='Helvetica-Bold')
        # Cell style for wrapped text in tables
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8,
                                    leading=10, wordWrap='CJK')
        cell_style_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=8,
                                         leading=10, wordWrap='CJK', fontName='Helvetica-Bold')

        # ===== HEADER =====
        story.append(Paragraph(t('lab_title'), title_style))
        story.append(Paragraph(t('report_title'), subtitle_style))
        story.append(Spacer(1, 0.15*inch))

        # ===== REPORT METADATA =====
        report_date = row['created_at'][:10] if row['created_at'] else datetime.now().strftime('%Y-%m-%d')
        report_time = row['created_at'][11:19] if len(row['created_at']) > 10 else ''

        meta_data = [
            [t('report_id'), str(row['id']), t('report_date'), report_date],
            [t('panel_type'), row['panel_type'], t('report_time'), report_time],
        ]
        meta_table = Table(meta_data, colWidths=[1.1*inch, 2.2*inch, 1.1*inch, 2.1*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.1*inch))

        # ===== PATIENT INFORMATION =====
        story.append(Paragraph(t('patient_info'), section_style))

        # Calculate BMI if not present
        bmi_val = row['bmi'] if row['bmi'] else (
            round(row['weight_kg'] / ((row['height_cm']/100)**2), 1)
            if row['weight_kg'] and row['height_cm'] and row['height_cm'] > 0 else 'N/A'
        )

        # Get maternal age risk
        maternal_risk = get_maternal_age_risk(int(row['age'])) if row['age'] else {}

        patient_data = [
            [t('name'), str(row['full_name']), t('mrn'), str(row['mrn_id'])],
            [t('maternal_age'), f"{row['age']} {t('years')}", t('gestational_age'), f"{row['weeks']} {t('weeks')}"],
            [t('weight'), f"{row['weight_kg']} kg" if row['weight_kg'] else 'N/A',
             t('height'), f"{row['height_cm']} cm" if row['height_cm'] else 'N/A'],
            [t('bmi'), str(bmi_val), '', ''],
        ]
        patient_table = Table(patient_data, colWidths=[1.1*inch, 2.2*inch, 1.1*inch, 2.1*inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 0.1*inch))

        # ===== QUALITY CONTROL METRICS =====
        story.append(Paragraph(t('qc_assessment'), section_style))

        # Determine effective QC status (override takes precedence)
        original_qc_status = row['qc_status'] or 'N/A'
        if qc_override:
            qc_status = t('pass')
            qc_color = colors.HexColor('#27ae60')  # Green for PASS
        else:
            qc_status = t('pass') if original_qc_status == 'PASS' else (
                t('warning') if original_qc_status == 'WARNING' else t('fail'))
            qc_color = colors.HexColor('#27ae60') if original_qc_status == 'PASS' else (
                colors.HexColor('#f39c12') if original_qc_status == 'WARNING' else colors.HexColor('#e74c3c'))

        qc_header = [[t('qc_status'), t('parameter'), t('value'), t('reference_range'), t('status')]]
        qc_rows = []

        # Get thresholds from config
        thresholds = config['QC_THRESHOLDS']
        panel_limits = config['PANEL_READ_LIMITS']
        min_reads = panel_limits.get(row['panel_type'], 5)

        # Helper function to determine individual metric status
        def get_metric_status(param, value, ref_check):
            if value == 'N/A' or value is None:
                return 'N/A'
            try:
                return 'PASS' if ref_check(float(value)) else 'FAIL'
            except (ValueError, TypeError):
                return 'N/A'

        # Get actual values from qc_metrics
        cff_val = qc_metrics.get('cff', 'N/A')
        gc_val = qc_metrics.get('gc', 'N/A')
        reads_val = qc_metrics.get('reads', 'N/A')
        uniq_val = qc_metrics.get('unique_rate', 'N/A')
        error_val = qc_metrics.get('error_rate', 'N/A')
        qs_val = qc_metrics.get('qs', 'N/A')

        # Format values with units
        cff_display = f"{cff_val}%" if cff_val != 'N/A' else 'N/A'
        gc_display = f"{gc_val}%" if gc_val != 'N/A' else 'N/A'
        reads_display = f"{reads_val}M" if reads_val != 'N/A' else 'N/A'
        uniq_display = f"{uniq_val}%" if uniq_val != 'N/A' else 'N/A'
        error_display = f"{error_val}%" if error_val != 'N/A' else 'N/A'
        qs_display = str(qs_val) if qs_val != 'N/A' else 'N/A'

        # Determine status for each metric
        cff_status = get_metric_status('cff', cff_val, lambda v: v >= thresholds['MIN_CFF'])
        gc_status = get_metric_status('gc', gc_val, lambda v: thresholds['GC_RANGE'][0] <= v <= thresholds['GC_RANGE'][1])
        reads_status = get_metric_status('reads', reads_val, lambda v: v >= min_reads)
        uniq_status = get_metric_status('uniq', uniq_val, lambda v: v >= thresholds['MIN_UNIQ_RATE'])
        error_status = get_metric_status('error', error_val, lambda v: v <= thresholds['MAX_ERROR_RATE'])
        qs_status = get_metric_status('qs', qs_val, lambda v: v < thresholds['QS_LIMIT_NEG'])

        # Build QC items with actual values
        qc_items = [
            (t('fetal_fraction'), cff_display, f"≥ {thresholds['MIN_CFF']}%", cff_status),
            (t('gc_content'), gc_display, f"{thresholds['GC_RANGE'][0]}-{thresholds['GC_RANGE'][1]}%", gc_status),
            (t('seq_reads'), reads_display, f"≥ {min_reads}M", reads_status),
            (t('unique_rate'), uniq_display, f"≥ {thresholds['MIN_UNIQ_RATE']}%", uniq_status),
            (t('error_rate'), error_display, f"≤ {thresholds['MAX_ERROR_RATE']}%", error_status),
            (t('quality_score'), qs_display, f"< {thresholds['QS_LIMIT_NEG']}", qs_status),
        ]

        # Display status - add override indicator if QC was overridden
        qc_display_status = f"{qc_status} ({t('override')})" if qc_override else qc_status

        for i, (param, val, ref, status) in enumerate(qc_items):
            if i == 0:
                qc_rows.append([qc_display_status, param, val, ref, status])
            else:
                qc_rows.append(['', param, val, ref, status])

        qc_table_data = qc_header + qc_rows
        qc_table = Table(qc_table_data, colWidths=[0.9*inch, 1.5*inch, 0.9*inch, 1.5*inch, 1.0*inch])

        # Build table style with color-coded status cells
        table_style_list = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('BACKGROUND', (0, 1), (0, 1), qc_color),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.whitesmoke),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]

        # Color code the status column based on PASS/FAIL
        for row_idx, (_, _, _, status) in enumerate(qc_items):
            if status == 'PASS':
                table_style_list.append(('BACKGROUND', (4, row_idx + 1), (4, row_idx + 1), colors.HexColor('#d4edda')))
                table_style_list.append(('TEXTCOLOR', (4, row_idx + 1), (4, row_idx + 1), colors.HexColor('#155724')))
            elif status == 'FAIL':
                table_style_list.append(('BACKGROUND', (4, row_idx + 1), (4, row_idx + 1), colors.HexColor('#f8d7da')))
                table_style_list.append(('TEXTCOLOR', (4, row_idx + 1), (4, row_idx + 1), colors.HexColor('#721c24')))

        qc_table.setStyle(TableStyle(table_style_list))
        story.append(qc_table)

        if row['qc_advice'] and row['qc_advice'] != 'None' and not qc_override:
            story.append(Spacer(1, 0.05*inch))
            story.append(Paragraph(f"<b>{t('qc_recommendation')}</b> {row['qc_advice']}", warning_style))

        # Add QC override notice if applicable
        if qc_override:
            story.append(Spacer(1, 0.05*inch))
            override_style = ParagraphStyle('Override', parent=styles['Normal'], fontSize=9,
                                           textColor=colors.HexColor('#1a5276'), fontName='Helvetica-Bold')
            orig_status_translated = t('pass') if original_qc_status == 'PASS' else (
                t('warning') if original_qc_status == 'WARNING' else t('fail'))
            override_note = f"<b>{t('qc_override_applied')}</b> {t('original_status')} {orig_status_translated}. "
            if qc_override_by:
                override_note += f"{t('validated_by')} {qc_override_by}. "
            if qc_override_reason:
                override_note += f"{t('reason')} {qc_override_reason}"
            story.append(Paragraph(override_note, override_style))

        story.append(Spacer(1, 0.1*inch))

        # ===== MAIN RESULTS =====
        story.append(Paragraph(t('aneuploidy_results'), section_style))

        # Determine fetal sex from SCA result
        sca_result = row['sca_res'] or ''
        fetal_sex = t('male') if 'Male' in sca_result or 'XY' in sca_result else (
            t('female') if 'Female' in sca_result or 'XX' in sca_result else t('undetermined'))

        # Get Z-scores
        z21 = z_data.get('21', z_data.get(21, 'N/A'))
        z18 = z_data.get('18', z_data.get(18, 'N/A'))
        z13 = z_data.get('13', z_data.get(13, 'N/A'))
        z_xx = z_data.get('XX', 'N/A')
        z_xy = z_data.get('XY', 'N/A')

        # Helper to format Z-score
        def fmt_z(z):
            if isinstance(z, (int, float)):
                return f"{z:.2f}"
            return str(z)

        # Results table with reportable status - use Paragraph for text wrapping
        # Determine reportable status for each result
        effective_qc_status = 'PASS' if qc_override else (row['qc_status'] or 'PASS')
        t21_reportable, _ = get_reportable_status(str(row['t21_res']), effective_qc_status, qc_override)
        t18_reportable, _ = get_reportable_status(str(row['t18_res']), effective_qc_status, qc_override)
        t13_reportable, _ = get_reportable_status(str(row['t13_res']), effective_qc_status, qc_override)
        sca_reportable, _ = get_reportable_status(str(row['sca_res']), effective_qc_status, qc_override)

        results_header = [[
            Paragraph(f"<b>{t('condition')}</b>", cell_style),
            Paragraph(f"<b>{t('result')}</b>", cell_style),
            Paragraph(f"<b>{t('z_score')}</b>", cell_style),
            Paragraph(f"<b>{t('reportable')}</b>", cell_style),
            Paragraph(f"<b>{t('ref')}</b>", cell_style)
        ]]
        results_rows = [
            [Paragraph(t('trisomy_21'), cell_style),
             Paragraph(str(row['t21_res']), cell_style),
             Paragraph(fmt_z(z21), cell_style),
             Paragraph(t21_reportable, cell_style),
             Paragraph('Z &lt; 2.58', cell_style)],
            [Paragraph(t('trisomy_18'), cell_style),
             Paragraph(str(row['t18_res']), cell_style),
             Paragraph(fmt_z(z18), cell_style),
             Paragraph(t18_reportable, cell_style),
             Paragraph('Z &lt; 2.58', cell_style)],
            [Paragraph(t('trisomy_13'), cell_style),
             Paragraph(str(row['t13_res']), cell_style),
             Paragraph(fmt_z(z13), cell_style),
             Paragraph(t13_reportable, cell_style),
             Paragraph('Z &lt; 2.58', cell_style)],
            [Paragraph(t('sca'), cell_style),
             Paragraph(str(row['sca_res']), cell_style),
             Paragraph(f"XX:{fmt_z(z_xx)} XY:{fmt_z(z_xy)}", cell_style),
             Paragraph(sca_reportable, cell_style),
             Paragraph('Z &lt; 4.5', cell_style)],
        ]

        results_data = results_header + results_rows
        results_table = Table(results_data, colWidths=[1.6*inch, 1.6*inch, 1.0*inch, 1.2*inch, 0.8*inch])

        # Color code results
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]

        # Highlight results based on reportable status
        reportable_statuses = [t21_reportable, t18_reportable, t13_reportable, sca_reportable]
        result_texts = [str(row['t21_res']), str(row['t18_res']), str(row['t13_res']), str(row['sca_res'])]

        for idx, (reportable, result_text) in enumerate(zip(reportable_statuses, result_texts)):
            if 'POSITIVE' in result_text.upper():
                # Positive result - red background
                table_style.append(('BACKGROUND', (0, idx+1), (-1, idx+1), colors.HexColor('#fadbd8')))
            elif reportable == "No":
                # Not reportable (re-library, resample, etc.) - yellow/amber background
                table_style.append(('BACKGROUND', (0, idx+1), (-1, idx+1), colors.HexColor('#fff3cd')))

        results_table.setStyle(TableStyle(table_style))
        story.append(results_table)
        story.append(Spacer(1, 0.08*inch))

        # Fetal Sex
        story.append(Paragraph(f"<b>{t('fetal_sex')}</b> {fetal_sex}", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))

        # ===== CNV FINDINGS =====
        if cnvs and len(cnvs) > 0:
            story.append(Paragraph(t('cnv_findings'), section_style))
            cnv_header = [[Paragraph(f"<b>{t('finding')}</b>", cell_style), Paragraph(f"<b>{t('clinical_significance')}</b>", cell_style)]]
            cnv_rows = [[Paragraph(str(cnv), cell_style), Paragraph(t('rec_cnv_positive'), cell_style)] for cnv in cnvs]
            cnv_data = cnv_header + cnv_rows
            cnv_table = Table(cnv_data, colWidths=[2.5*inch, 4*inch])
            cnv_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8e44ad')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(cnv_table)
            story.append(Spacer(1, 0.1*inch))

        # ===== RAT FINDINGS =====
        if rats and len(rats) > 0:
            story.append(Paragraph(t('rat_findings'), section_style))
            rat_header = [[Paragraph(f"<b>{t('finding')}</b>", cell_style), Paragraph(f"<b>{t('clinical_significance')}</b>", cell_style)]]
            rat_rows = [[Paragraph(str(rat), cell_style), Paragraph(t('rec_rat_positive'), cell_style)] for rat in rats]
            rat_data = rat_header + rat_rows
            rat_table = Table(rat_data, colWidths=[2.5*inch, 4*inch])
            rat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d35400')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(rat_table)
            story.append(Spacer(1, 0.1*inch))

        # ===== MATERNAL FACTORS & AGE-BASED RISK =====
        story.append(Paragraph(t('maternal_factors'), section_style))

        # Build maternal factors text
        maternal_factors_list = []
        if row['age']:
            maternal_factors_list.append(f"<b>{t('maternal_age')}</b> {row['age']} {t('years')}")
        if bmi_val and bmi_val != 'N/A':
            bmi_category = ""
            try:
                bmi_num = float(bmi_val)
                if bmi_num < 18.5:
                    bmi_category = f" {t('bmi_underweight')}"
                elif bmi_num < 25:
                    bmi_category = f" {t('bmi_normal')}"
                elif bmi_num < 30:
                    bmi_category = f" {t('bmi_overweight')}"
                else:
                    bmi_category = f" {t('bmi_obese')}"
            except:
                pass
            maternal_factors_list.append(f"<b>{t('bmi')}</b> {bmi_val}{bmi_category}")
        if row['weeks']:
            maternal_factors_list.append(f"<b>{t('gestational_age')}</b> {row['weeks']} {t('weeks')}")

        if maternal_factors_list:
            story.append(Paragraph(" | ".join(maternal_factors_list), styles['Normal']))
            story.append(Spacer(1, 0.05*inch))

        # Age-based prior risk
        if maternal_risk and row['age']:
            risk_text = t('age_risk_text').format(
                age=row['age'],
                t21=int(1/maternal_risk['T21']),
                t18=int(1/maternal_risk['T18']),
                t13=int(1/maternal_risk['T13'])
            )
            story.append(Paragraph(risk_text, small_style))
        story.append(Spacer(1, 0.1*inch))

        # ===== FINAL INTERPRETATION =====
        story.append(Paragraph(t('final_interpretation'), section_style))

        final_summary = row['final_summary']
        final_color = colors.HexColor('#27ae60') if 'NEGATIVE' in str(final_summary).upper() else (
            colors.HexColor('#e74c3c') if 'POSITIVE' in str(final_summary).upper() else colors.HexColor('#f39c12'))

        # Create centered style for final box with text wrapping
        final_cell_style = ParagraphStyle('FinalCell', parent=styles['Normal'], fontSize=12,
                                          leading=14, alignment=TA_CENTER, textColor=colors.whitesmoke,
                                          fontName='Helvetica-Bold', wordWrap='CJK')
        final_box = Table([[Paragraph(str(final_summary), final_cell_style)]], colWidths=[6.5*inch])
        final_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), final_color),
            ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ('TOPPADDING', (0, 0), (0, 0), 10),
            ('LEFTPADDING', (0, 0), (0, 0), 10),
            ('RIGHTPADDING', (0, 0), (0, 0), 10),
        ]))
        story.append(final_box)
        story.append(Spacer(1, 0.1*inch))

        # ===== CLINICAL RECOMMENDATIONS =====
        story.append(Paragraph(t('clinical_recommendations'), section_style))

        recommendations = []
        if 'POSITIVE' in str(row['t21_res']).upper():
            recommendations.append(f"• {t('trisomy_21').split(' (')[0]}: {t('rec_t21_positive')}")
        if 'POSITIVE' in str(row['t18_res']).upper():
            recommendations.append(f"• {t('trisomy_18').split(' (')[0]}: {t('rec_t18_positive')}")
        if 'POSITIVE' in str(row['t13_res']).upper():
            recommendations.append(f"• {t('trisomy_13').split(' (')[0]}: {t('rec_t13_positive')}")
        if 'POSITIVE' in str(row['sca_res']).upper():
            recommendations.append(f"• {t('sca')}: {t('rec_sca_positive')}")

        if not recommendations:
            recommendations.append(f"• {t('no_high_risk')}")
            recommendations.append(f"• {t('nipt_screening')}")

        for rec in recommendations:
            story.append(Paragraph(rec, styles['Normal']))
        story.append(Spacer(1, 0.1*inch))

        # ===== CLINICAL NOTES =====
        if row['clinical_notes']:
            story.append(Paragraph(t('clinical_notes'), section_style))
            notes_text = str(row['clinical_notes'])
            # Create a styled box for clinical notes
            notes_style = ParagraphStyle('Notes', parent=styles['Normal'], fontSize=9,
                                         leading=12, wordWrap='CJK', leftIndent=10, rightIndent=10)
            notes_box = Table([[Paragraph(notes_text, notes_style)]], colWidths=[6.5*inch])
            notes_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8f9fa')),
                ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#dee2e6')),
                ('BOTTOMPADDING', (0, 0), (0, 0), 8),
                ('TOPPADDING', (0, 0), (0, 0), 8),
                ('LEFTPADDING', (0, 0), (0, 0), 8),
                ('RIGHTPADDING', (0, 0), (0, 0), 8),
            ]))
            story.append(notes_box)

            # Highlight key clinical markers if present
            key_markers = []
            notes_lower = notes_text.lower()
            if 'nuchal' in notes_lower or 'nt' in notes_lower:
                key_markers.append(t('nt_noted'))
            if 'fetal fraction' in notes_lower or 'ff' in notes_lower:
                key_markers.append(t('ff_concerns'))
            if 'ivf' in notes_lower or 'icsi' in notes_lower:
                key_markers.append(t('ivf_noted'))
            if 'twin' in notes_lower or 'multiple' in notes_lower:
                key_markers.append(t('multiple_noted'))

            if key_markers:
                story.append(Spacer(1, 0.05*inch))
                markers_text = f"<i>{t('key_markers')} " + ", ".join(key_markers) + "</i>"
                story.append(Paragraph(markers_text, small_style))

            story.append(Spacer(1, 0.1*inch))

        # ===== LIMITATIONS & DISCLAIMER =====
        story.append(Paragraph(t('limitations'), section_style))
        disclaimer_text = f"""
        <b>{t('important_info')}</b><br/>
        • {t('disclaimer_1')}<br/>
        • {t('disclaimer_2')}<br/>
        • {t('disclaimer_3')}<br/>
        • {t('disclaimer_4')}<br/>
        • {t('disclaimer_5')}<br/>
        • {t('disclaimer_6')}
        """
        story.append(Paragraph(disclaimer_text, small_style))
        story.append(Spacer(1, 0.15*inch))

        # ===== SIGNATURE SECTION =====
        story.append(Paragraph(t('authorization'), section_style))

        sig_data = [
            [t('performed_by'), row['technician_name'] or t('lab_staff'), t('date'), report_date],
            ['', '', '', ''],
            [t('reviewed_by'), '_' * 30, t('date'), '_' * 15],
            [t('clinical_pathologist'), '', '', ''],
            ['', '', '', ''],
            [t('approved_by'), '_' * 30, t('date'), '_' * 15],
            [t('lab_director'), '', '', ''],
        ]
        sig_table = Table(sig_data, colWidths=[1.2*inch, 2.3*inch, 0.8*inch, 2.2*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTSIZE', (0, 3), (0, 3), 8),
            ('FONTSIZE', (0, 6), (0, 6), 8),
            ('TEXTCOLOR', (0, 3), (0, 3), colors.HexColor('#7f8c8d')),
            ('TEXTCOLOR', (0, 6), (0, 6), colors.HexColor('#7f8c8d')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(sig_table)

        # ===== FOOTER =====
        story.append(Spacer(1, 0.2*inch))
        footer_text = f"{t('report_generated')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {t('version')}"
        story.append(Paragraph(footer_text, small_style))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return None

# ==================== ANALYTICS ====================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_analytics_data() -> Dict:
    """Fetch analytics data with caching for better performance."""
    try:
        with get_db_connection() as conn:
            # Combined query for basic stats to reduce database calls
            stats_query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN qc_status = 'PASS' THEN 1 ELSE 0 END) as qc_pass,
                    SUM(CASE WHEN qc_status = 'FAIL' THEN 1 ELSE 0 END) as qc_fail,
                    SUM(CASE WHEN qc_status = 'WARNING' THEN 1 ELSE 0 END) as qc_warning,
                    SUM(CASE WHEN t21_res LIKE '%POSITIVE%' THEN 1 ELSE 0 END) as t21,
                    SUM(CASE WHEN t18_res LIKE '%POSITIVE%' THEN 1 ELSE 0 END) as t18,
                    SUM(CASE WHEN t13_res LIKE '%POSITIVE%' THEN 1 ELSE 0 END) as t13
                FROM results
            """
            stats = pd.read_sql(stats_query, conn)

            # Get counts from combined query
            total = stats.iloc[0]['total'] if not stats.empty else 0

            # QC stats as DataFrame
            qc_stats = pd.DataFrame({
                'qc_status': ['PASS', 'FAIL', 'WARNING'],
                'count': [
                    stats.iloc[0]['qc_pass'] or 0,
                    stats.iloc[0]['qc_fail'] or 0,
                    stats.iloc[0]['qc_warning'] or 0
                ]
            })

            # Trisomy stats
            trisomies = pd.DataFrame({
                't21': [stats.iloc[0]['t21'] or 0],
                't18': [stats.iloc[0]['t18'] or 0],
                't13': [stats.iloc[0]['t13'] or 0]
            })

            # These queries still need to be separate
            outcomes = pd.read_sql(
                "SELECT final_summary, COUNT(*) as count FROM results GROUP BY final_summary",
                conn
            )
            recent = pd.read_sql("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM results
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """, conn)
            panels = pd.read_sql(
                "SELECT panel_type, COUNT(*) as count FROM results GROUP BY panel_type",
                conn
            )

            return {
                'total': total,
                'qc_stats': qc_stats,
                'outcomes': outcomes,
                'trisomies': trisomies,
                'recent': recent,
                'panels': panels
            }
    except Exception as e:
        st.error(f"Error loading analytics: {e}")
        return {
            'total': 0,
            'qc_stats': pd.DataFrame({'qc_status': [], 'count': []}),
            'outcomes': pd.DataFrame({'final_summary': [], 'count': []}),
            'trisomies': pd.DataFrame({'t21': [0], 't18': [0], 't13': [0]}),
            'recent': pd.DataFrame({'date': [], 'count': []}),
            'panels': pd.DataFrame({'panel_type': [], 'count': []})
        }

def render_analytics_dashboard():
    """Render analytics dashboard."""
    st.header("📊 Analytics Dashboard")
    
    data = get_analytics_data()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tests", data['total'])
    with col2:
        pass_rate = (data['qc_stats'][data['qc_stats']['qc_status'] == 'PASS']['count'].sum() / data['total'] * 100) if data['total'] > 0 else 0
        st.metric("QC Pass Rate", f"{pass_rate:.1f}%")
    with col3:
        pos = data['outcomes'][data['outcomes']['final_summary'].str.contains('POSITIVE', na=False)]['count'].sum()
        st.metric("Positive", pos)
    with col4:
        fail = data['qc_stats'][data['qc_stats']['qc_status'] == 'FAIL']['count'].sum()
        st.metric("QC Fail", fail)
    
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("QC Distribution")
        if not data['qc_stats'].empty:
            fig = px.pie(data['qc_stats'], values='count', names='qc_status',
                        color_discrete_map={'PASS': '#2ECC71', 'FAIL': '#E74C3C', 'WARNING': '#F39C12'})
            st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("Outcomes")
        if not data['outcomes'].empty:
            fig = px.bar(data['outcomes'], x='final_summary', y='count', text='count')
            st.plotly_chart(fig, use_container_width=True)
    
    c3, c4 = st.columns(2)
    
    with c3:
        st.subheader("Trisomy Detection")
        if not data['trisomies'].empty:
            tris_df = pd.DataFrame({
                'Type': ['T21', 'T18', 'T13'],
                'Count': [data['trisomies'].iloc[0]['t21'], 
                         data['trisomies'].iloc[0]['t18'],
                         data['trisomies'].iloc[0]['t13']]
            })
            fig = px.bar(tris_df, x='Type', y='Count', color='Type', text='Count')
            st.plotly_chart(fig, use_container_width=True)
    
    with c4:
        st.subheader("Panel Types")
        if not data['panels'].empty:
            fig = px.pie(data['panels'], values='count', names='panel_type')
            st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Activity (30 Days)")
    if not data['recent'].empty:
        fig = px.line(data['recent'], x='date', y='count', markers=True)
        st.plotly_chart(fig, use_container_width=True)

# ==================== UI MAIN ====================

# Session timeout in minutes
SESSION_TIMEOUT_MINUTES = 60

def check_session_timeout() -> bool:
    """Check if the session has timed out. Returns True if session is valid."""
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
        return True

    elapsed = (datetime.now() - st.session_state.last_activity).total_seconds() / 60
    if elapsed > SESSION_TIMEOUT_MINUTES:
        # Session expired
        st.session_state.authenticated = False
        st.session_state.user = None
        log_audit("SESSION_TIMEOUT", "Session expired due to inactivity",
                 st.session_state.get('user', {}).get('id'))
        return False

    # Update last activity
    st.session_state.last_activity = datetime.now()
    return True

def render_force_password_change():
    """Render password change dialog for first-time login."""
    st.markdown("<h1 style='text-align: center;'>🔑 Password Change Required</h1>", unsafe_allow_html=True)
    st.warning("You must change your password before continuing. This is required for security.")

    st.markdown("**Password Requirements:**")
    st.markdown("""
    - At least 8 characters long
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one number (0-9)
    """)

    with st.form("force_password_change_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")

        if st.form_submit_button("Change Password", type="primary"):
            if not new_password or not confirm_password:
                st.error("Both password fields are required")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                is_valid, error_msg = validate_password_strength(new_password)
                if not is_valid:
                    st.error(error_msg)
                else:
                    # Update password and clear must_change_password flag
                    try:
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            new_hash = hash_password(new_password)
                            c.execute("""
                                UPDATE users SET password_hash = ?, must_change_password = 0
                                WHERE id = ?
                            """, (new_hash, st.session_state.user['id']))
                            conn.commit()

                        st.session_state.user['must_change_password'] = False
                        log_audit("PASSWORD_CHANGED_FORCED", "User changed password on first login",
                                 st.session_state.user['id'])
                        st.success("Password changed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update password: {e}")

def render_login():
    """Login UI with security features."""
    st.markdown("<h1 style='text-align: center;'>🧬 NRIS v2.0</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>NIPT Result Interpretation System</p>", unsafe_allow_html=True)

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("🔐 Login", use_container_width=True, type="primary"):
        if username and password:
            user = authenticate_user(username, password)
            if user:
                # Check if there's an error (e.g., account locked)
                if isinstance(user, dict) and 'error' in user:
                    st.error(f"🔒 {user['error']}")
                else:
                    st.session_state.user = user
                    st.session_state.authenticated = True
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
            else:
                st.error("❌ Invalid username or password")
        else:
            st.warning("⚠️ Please enter both username and password")

    st.divider()
    st.info("💡 Default credentials:\n- Username: **admin**\n- Password: **admin123**\n\n"
            "⚠️ You will be required to change the default password on first login.")

def main():
    st.set_page_config(page_title="NRIS v2.0", layout="wide", page_icon="🧬")

    # Run startup data protection (once per session)
    if 'data_protection_status' not in st.session_state:
        st.session_state.data_protection_status = startup_data_protection()

    init_database()

    # Session state initialization
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'cnv_list' not in st.session_state:
        st.session_state.cnv_list = []
    if 'rat_list' not in st.session_state:
        st.session_state.rat_list = []
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'current_result' not in st.session_state:
        st.session_state.current_result = {}
    if 'last_report_id' not in st.session_state:
        st.session_state.last_report_id = None

    # Authentication check
    if not st.session_state.authenticated:
        render_login()
        return

    # Session timeout check
    if not check_session_timeout():
        st.warning("Your session has expired due to inactivity. Please log in again.")
        render_login()
        return

    # Force password change check
    if st.session_state.user.get('must_change_password', False):
        render_force_password_change()
        return

    # Sidebar
    with st.sidebar:
        st.title(f"👤 {st.session_state.user['name']}")
        st.caption(f"Role: {st.session_state.user['role']}")

        if st.button("🚪 Logout"):
            log_audit("LOGOUT", f"User {st.session_state.user['username']} logged out",
                     st.session_state.user['id'])
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

        st.divider()

        # Quick stats with caching
        try:
            with get_db_connection() as conn:
                total = pd.read_sql("SELECT COUNT(*) as c FROM results", conn).iloc[0]['c']
                today = pd.read_sql("SELECT COUNT(*) as c FROM results WHERE DATE(created_at) = DATE('now')", conn).iloc[0]['c']

            st.metric("Total Records", total)
            st.metric("Today", today)
        except Exception:
            st.metric("Total Records", "N/A")
            st.metric("Today", "N/A")
    
    # Main tabs
    tabs = st.tabs(["🔬 Analysis", "📊 Registry", "📈 Analytics", "📂 Batch", "⚙️ Settings"])
    
    config = load_config()
    
    # TAB 1: ANALYSIS
    with tabs[0]:
        st.title("🧬 NIPT Analysis")
        st.caption("Enter patient information and sequencing data to generate analysis results")

        with st.container():
            st.markdown("##### Patient Information")
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("Patient Name", help="Full name of the patient")
            p_id = c2.text_input("MRN", help="Medical Record Number - unique patient identifier")
            p_age = c3.number_input("Maternal Age", 15, 60, 30, help="Patient's age in years")

            c4, c5, c6, c7 = st.columns(4)
            p_weight = c4.number_input("Weight (kg)", 0.0, 200.0, 65.0, help="Patient weight for BMI calculation")
            p_height = c5.number_input("Height (cm)", 0, 250, 165, help="Patient height for BMI calculation")
            bmi = round(p_weight / ((p_height/100)**2), 2) if p_height > 0 else 0
            c6.metric("BMI", f"{bmi:.1f}" if bmi > 0 else "--", help="Calculated Body Mass Index")
            p_weeks = c7.number_input("Gestational Weeks", 0, 42, 12, help="Weeks of gestation (typically 10-22 weeks for NIPT)")
            p_notes = st.text_area("Clinical Notes", height=60, help="Optional notes about the patient or test conditions (e.g., IVF, twins, previous results)")
        
        st.markdown("---")
        
        st.subheader("Sequencing Metrics")
        panel_type = st.selectbox("Panel Type", list(config['PANEL_READ_LIMITS'].keys()),
                                  help="Select the NIPT panel used for this test")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        reads = m1.number_input("Reads (M)", 0.0, 100.0, 8.0, help="Total sequencing reads in millions")
        cff = m2.number_input("Cff %", 0.0, 50.0, 10.0, help="Cell-free fetal DNA fraction (must be >= 3.5%)")
        gc = m3.number_input("GC %", 0.0, 100.0, 40.0, help="GC content percentage (normal: 37-44%)")
        qs = m4.number_input("QS", 0.0, 10.0, 1.0, help="Quality Score (lower is better, < 1.7 for negative)")
        uniq_rate = m5.number_input("Unique %", 0.0, 100.0, 75.0, help="Unique read rate (must be >= 68%)")
        error_rate = m6.number_input("Error %", 0.0, 5.0, 0.1, help="Sequencing error rate (must be <= 1%)")
        
        # Validation
        val_errors = validate_inputs(reads, cff, gc, p_age)
        if val_errors:
            for err in val_errors:
                st.error(err)
        
        st.markdown("---")
        
        c_tri, c_sca = st.columns(2)
        with c_tri:
            st.subheader("Trisomy Z-Scores")
            st.caption("Z < 2.58 = Low Risk | Z >= 2.58 = High Risk")
            z21 = st.number_input("Z-21 (Chr 21)", -10.0, 50.0, 0.5, help="Z-score for Trisomy 21 (Down Syndrome)")
            z18 = st.number_input("Z-18 (Chr 18)", -10.0, 50.0, 0.5, help="Z-score for Trisomy 18 (Edwards Syndrome)")
            z13 = st.number_input("Z-13 (Chr 13)", -10.0, 50.0, 0.5, help="Z-score for Trisomy 13 (Patau Syndrome)")

        with c_sca:
            st.subheader("Sex Chromosomes")
            st.caption("Select detected SCA type and enter Z-scores")
            sca_type = st.selectbox("SCA Type", ["XX", "XY", "XO", "XXX", "XXY", "XYY", "XXX+XY", "XO+XY"],
                                   help="XX=Female, XY=Male, others indicate sex chromosome aneuploidy")
            z1, z2 = st.columns(2)
            z_xx = z1.number_input("Z-XX", -10.0, 50.0, 0.0, help="Z-score for X chromosome")
            z_xy = z2.number_input("Z-XY", -10.0, 50.0, 0.0, help="Z-score for Y chromosome")
        
        st.markdown("---")
        
        d1, d2 = st.columns(2)
        with d1:
            st.subheader("CNV Findings")
            with st.form("cnv_form"):
                sz = st.number_input("Size (Mb)", 0.0)
                rt = st.number_input("Ratio (%)", 0.0)
                if st.form_submit_button("Add CNV") and sz > 0:
                    st.session_state.cnv_list.append({"size": sz, "ratio": rt})
                    st.rerun()
            
            for i, item in enumerate(st.session_state.cnv_list):
                col_a, col_b = st.columns([4, 1])
                col_a.text(f"{i+1}. {item['size']}Mb | {item['ratio']}%")
                if col_b.button("❌", key=f"del_cnv_{i}"):
                    st.session_state.cnv_list.pop(i)
                    st.rerun()
        
        with d2:
            st.subheader("Rare Autosomes (RAT)")
            with st.form("rat_form"):
                r_chr = st.number_input("Chr #", 1, 22, 7)
                r_z = st.number_input("Z-Score", 0.0)
                if st.form_submit_button("Add RAT") and r_z > 0:
                    st.session_state.rat_list.append({"chr": r_chr, "z": r_z})
                    st.rerun()
            
            for i, item in enumerate(st.session_state.rat_list):
                col_a, col_b = st.columns([4, 1])
                col_a.text(f"{i+1}. Chr {item['chr']} | Z:{item['z']}")
                if col_b.button("❌", key=f"del_rat_{i}"):
                    st.session_state.rat_list.pop(i)
                    st.rerun()
        
        st.markdown("---")

        # Check for duplicate patient before save button
        patient_action = "create_new"  # Default action
        if p_id:
            exists, existing_patient = check_duplicate_patient(p_id)
            if exists:
                if existing_patient['result_count'] == 0:
                    # Orphan patient with no results
                    st.warning(f"⚠️ Patient ID '{p_id}' exists as '{existing_patient['name']}' but has **0 results**. "
                              f"This orphan record will be replaced with new patient data.")
                    patient_action = "replace_orphan"
                    st.session_state['orphan_patient_id'] = existing_patient['id']
                else:
                    # Patient with existing results
                    st.info(f"ℹ️ Patient ID '{p_id}' already exists as '{existing_patient['name']}' "
                           f"(Age: {existing_patient['age']}, Results: {existing_patient['result_count']}). "
                           f"A new result will be added to this patient's record.")
                    patient_action = "add_to_existing"

        if st.button("💾 SAVE & ANALYZE", type="primary", disabled=bool(val_errors)):
            t21_res, t21_risk = analyze_trisomy(config, z21, "21")
            t18_res, t18_risk = analyze_trisomy(config, z18, "18")
            t13_res, t13_risk = analyze_trisomy(config, z13, "13")
            sca_res, sca_risk = analyze_sca(config, sca_type, z_xx, z_xy, cff)

            analyzed_cnvs = []
            is_cnv_high = False
            for item in st.session_state.cnv_list:
                msg, _, risk = analyze_cnv(item['size'], item['ratio'])
                if risk == "HIGH": is_cnv_high = True
                analyzed_cnvs.append(f"{item['size']}Mb ({item['ratio']}%) -> {msg}")

            analyzed_rats = []
            is_rat_high = False
            for item in st.session_state.rat_list:
                msg, risk = analyze_rat(config, item['chr'], item['z'])
                if risk in ["POSITIVE", "HIGH"]: is_rat_high = True
                analyzed_rats.append(f"Chr {item['chr']} (Z:{item['z']}) -> {msg}")

            all_risks = [t21_risk, t18_risk, t13_risk, sca_risk]
            is_positive = "POSITIVE" in all_risks
            is_high_risk = "HIGH" in all_risks or is_cnv_high or is_rat_high

            qc_stat, qc_msg, qc_advice = check_qc_metrics(
                config, panel_type, reads, cff, gc, qs, uniq_rate, error_rate, is_positive or is_high_risk
            )

            final_summary = "NEGATIVE"
            if is_positive: final_summary = "POSITIVE DETECTED"
            elif is_high_risk: final_summary = "HIGH RISK (SEE ADVICE)"
            if qc_stat == "FAIL": final_summary = "INVALID (QC FAIL)"

            p_data = {'name': p_name, 'id': p_id, 'age': p_age, 'weight': p_weight,
                      'height': p_height, 'bmi': bmi, 'weeks': p_weeks, 'notes': p_notes}
            r_data = {'panel': panel_type, 'qc_status': qc_stat, 'qc_msgs': qc_msg, 'qc_advice': qc_advice}
            c_data = {'t21': t21_res, 't18': t18_res, 't13': t13_res, 'sca': sca_res,
                      'cnv_list': analyzed_cnvs, 'rat_list': analyzed_rats, 'final': final_summary}

            full_z = {13: z13, 18: z18, 21: z21, 'XX': z_xx, 'XY': z_xy}
            for r in st.session_state.rat_list: full_z[r['chr']] = r['z']

            # Store QC metrics for PDF report
            qc_metrics = {
                'reads': reads,
                'cff': cff,
                'gc': gc,
                'qs': qs,
                'unique_rate': uniq_rate,
                'error_rate': error_rate
            }

            # Handle orphan patient replacement
            if patient_action == "replace_orphan" and 'orphan_patient_id' in st.session_state:
                try:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("DELETE FROM patients WHERE id = ?", (st.session_state['orphan_patient_id'],))
                        conn.commit()
                    del st.session_state['orphan_patient_id']
                except Exception as e:
                    st.error(f"Failed to replace orphan patient: {e}")

            rid, msg = save_result(p_data, r_data, c_data, full_z, qc_metrics=qc_metrics)

            if rid:
                st.success("✅ Record Saved")
                st.session_state.last_report_id = rid
                st.session_state.current_result = {
                    'clinical': c_data,
                    'qc': {'status': qc_stat, 'msg': qc_msg, 'advice': qc_advice}
                }
                st.session_state.analysis_complete = True
                st.session_state.cnv_list = []
                st.session_state.rat_list = []
            else:
                st.error(f"Failed to save: {msg}")
        
        if st.session_state.analysis_complete:
            res = st.session_state.current_result['clinical']
            qc = st.session_state.current_result['qc']
            
            st.divider()
            
            if qc['status'] == "FAIL":
                st.error(f"❌ QC FAILED: {qc['msg']}")
                st.error(f"ACTION: {qc['advice']}")
            elif qc['status'] == "WARNING":
                st.warning(f"⚠️ QC WARNING: {qc['msg']}")
            else:
                st.success(f"✅ QC PASSED")

            # Calculate Reportable status for each result
            effective_qc = qc['status']
            t21_rep, _ = get_reportable_status(res['t21'], effective_qc)
            t18_rep, _ = get_reportable_status(res['t18'], effective_qc)
            t13_rep, _ = get_reportable_status(res['t13'], effective_qc)
            sca_rep, _ = get_reportable_status(res['sca'], effective_qc)

            rows = [
                ["Trisomy 21", res['t21'], t21_rep],
                ["Trisomy 18", res['t18'], t18_rep],
                ["Trisomy 13", res['t13'], t13_rep],
                ["Sex Chromosomes", res['sca'], sca_rep]
            ]
            for i in res['cnv_list']:
                cnv_rep, _ = get_reportable_status(i, effective_qc)
                rows.append(["CNV", i, cnv_rep])
            for i in res['rat_list']:
                rat_rep, _ = get_reportable_status(i, effective_qc)
                rows.append(["RAT", i, rat_rep])

            df_res = pd.DataFrame(rows, columns=["Test", "Result", "Reportable"])

            def color_rows(val):
                s = str(val)
                if "POSITIVE" in s: return 'background-color: #ffcccc; font-weight: bold'
                if "Re-library" in s or "Resample" in s: return 'background-color: #fff3cd'
                return ''

            st.dataframe(df_res.style.map(color_rows, subset=['Result']), use_container_width=True)
            st.info(f"📋 FINAL: {res['final']}")

            if st.session_state.last_report_id:
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    analysis_pdf_lang = st.selectbox(
                        "PDF Language",
                        options=["English", "Francais"],
                        index=0 if config.get('REPORT_LANGUAGE', 'en') == 'en' else 1,
                        key="analysis_pdf_lang"
                    )
                with col_b:
                    analysis_lang_code = 'en' if analysis_pdf_lang == "English" else 'fr'
                    pdf_data = generate_pdf_report(st.session_state.last_report_id, lang=analysis_lang_code)
                    if pdf_data:
                        lang_suffix = "_FR" if analysis_lang_code == 'fr' else "_EN"
                        st.download_button("📄 Download PDF", pdf_data,
                                         f"Report_{st.session_state.last_report_id}{lang_suffix}.pdf", "application/pdf")
                with col_c:
                    if st.button("🔄 New Analysis"):
                        st.session_state.analysis_complete = False
                        st.rerun()
    
    # TAB 2: REGISTRY
    with tabs[1]:
        st.header("📊 Patient Registry")
        
        col_search, col_refresh = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("🔍 Search (Name/MRN)", "")
        with col_refresh:
            st.write("")
            if st.button("🔄 Refresh Data", help="Refresh to see latest patient data"):
                st.rerun()

        with get_db_connection() as conn:
            query = """
                SELECT r.id, r.created_at, p.full_name, p.mrn_id, r.panel_type,
                       r.qc_status, r.qc_override, r.final_summary, r.full_z_json, r.t21_res
                FROM results r
                JOIN patients p ON p.id = r.patient_id
                WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
                ORDER BY r.id DESC
            """
            df = pd.read_sql(query, conn)

        if not df.empty:
            if search_term:
                df = df[df['full_name'].str.contains(search_term, case=False, na=False) |
                       df['mrn_id'].str.contains(search_term, case=False, na=False)]

            df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

            # Extract T21 Z-score from full_z_json for display
            def extract_t21_z(z_json):
                try:
                    if z_json and z_json != '{}':
                        z_data = json.loads(z_json)
                        z21 = z_data.get('21', z_data.get(21, None))
                        if z21 is not None:
                            return f"{float(z21):.2f}"
                except:
                    pass
                return 'N/A'

            df['T21_Z'] = df['full_z_json'].apply(extract_t21_z)

            # Calculate Reportable status for T21 result
            def get_t21_reportable(row):
                qc_status = row['qc_status'] or 'PASS'
                qc_override = bool(row.get('qc_override', 0))
                effective_qc = 'PASS' if qc_override else qc_status
                reportable, _ = get_reportable_status(str(row['t21_res']), effective_qc, qc_override)
                return reportable

            df['Reportable'] = df.apply(get_t21_reportable, axis=1)

            # Reorder columns for display (exclude raw JSON column)
            display_df = df[['id', 'created_at', 'full_name', 'mrn_id', 'panel_type', 'qc_status', 't21_res', 'T21_Z', 'Reportable', 'final_summary']]
            display_df.columns = ['ID', 'Date', 'Name', 'MRN', 'Panel', 'QC', 'T21 Result', 'T21 Z-Score', 'Reportable', 'Final Summary']

            st.dataframe(display_df, use_container_width=True, height=400)

            st.divider()

            col_exp, col_json, col_del, col_pdf = st.columns(4)

            with col_exp:
                with get_db_connection() as exp_conn:
                    full_dump = pd.read_sql("""
                        SELECT * FROM results r
                        JOIN patients p ON p.id = r.patient_id
                        WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
                    """, exp_conn)
                st.download_button("📥 Export CSV", full_dump.to_csv(index=False),
                                 "nipt_registry.csv", "text/csv")

            with col_json:
                # Generate comprehensive JSON export
                with get_db_connection() as json_conn:
                    json_query = """
                        SELECT r.id as report_id, r.created_at as report_date,
                               p.full_name, p.mrn_id, p.age, p.weight_kg, p.height_cm, p.bmi, p.weeks,
                               p.clinical_notes, r.panel_type, r.qc_status, r.qc_details, r.qc_advice,
                               r.t21_res, r.t18_res, r.t13_res, r.sca_res,
                               r.cnv_json, r.rat_json, r.full_z_json, r.final_summary
                        FROM results r
                        JOIN patients p ON p.id = r.patient_id
                        ORDER BY r.id DESC
                    """
                    json_df = pd.read_sql(json_query, json_conn)

                    # Convert to structured JSON
                    json_records = []
                    for _, row in json_df.iterrows():
                        record = {
                            'report_id': int(row['report_id']) if pd.notna(row['report_id']) else None,
                            'report_date': str(row['report_date']) if pd.notna(row['report_date']) else None,
                            'patient': {
                                'name': str(row['full_name']) if pd.notna(row['full_name']) else None,
                                'mrn': str(row['mrn_id']) if pd.notna(row['mrn_id']) else None,
                                'age': int(row['age']) if pd.notna(row['age']) else None,
                                'weight_kg': float(row['weight_kg']) if pd.notna(row['weight_kg']) else None,
                                'height_cm': int(row['height_cm']) if pd.notna(row['height_cm']) else None,
                                'bmi': float(row['bmi']) if pd.notna(row['bmi']) else None,
                                'gestational_weeks': int(row['weeks']) if pd.notna(row['weeks']) else None,
                                'clinical_notes': str(row['clinical_notes']) if pd.notna(row['clinical_notes']) else None,
                            },
                            'test_info': {
                                'panel_type': str(row['panel_type']) if pd.notna(row['panel_type']) else None,
                                'qc_status': str(row['qc_status']) if pd.notna(row['qc_status']) else None,
                                'qc_details': str(row['qc_details']) if pd.notna(row['qc_details']) else None,
                                'qc_advice': str(row['qc_advice']) if pd.notna(row['qc_advice']) else None,
                            },
                            'results': {
                                'trisomy_21': str(row['t21_res']) if pd.notna(row['t21_res']) else None,
                                'trisomy_18': str(row['t18_res']) if pd.notna(row['t18_res']) else None,
                                'trisomy_13': str(row['t13_res']) if pd.notna(row['t13_res']) else None,
                                'sca': str(row['sca_res']) if pd.notna(row['sca_res']) else None,
                                'cnv_findings': json.loads(row['cnv_json']) if pd.notna(row['cnv_json']) else [],
                                'rat_findings': json.loads(row['rat_json']) if pd.notna(row['rat_json']) else [],
                                'z_scores': json.loads(row['full_z_json']) if pd.notna(row['full_z_json']) else {},
                                'final_summary': str(row['final_summary']) if pd.notna(row['final_summary']) else None,
                            }
                        }
                        json_records.append(record)

                    json_export = {
                        'export_date': datetime.now().isoformat(),
                        'total_records': len(json_records),
                        'exported_by': st.session_state.user['username'],
                        'records': json_records
                    }

                st.download_button("📤 Export JSON", json.dumps(json_export, indent=2),
                                 "nipt_registry.json", "application/json")
            
            with col_del:
                with st.expander("🗑️ Delete Record"):
                    del_id = st.number_input("Report ID", 1, key="del_input")
                    if st.button("Confirm Delete", type="secondary"):
                        ok, msg = delete_record(del_id)
                        if ok: 
                            st.success(msg)
                            st.rerun()
                        else: 
                            st.error(msg)
            
            with col_pdf:
                with st.expander("📄 Generate PDF"):
                    pdf_id = st.number_input("Report ID", 1, key="pdf_input")
                    pdf_lang = st.selectbox(
                        "Report Language",
                        options=["English", "Francais"],
                        index=0 if config.get('REPORT_LANGUAGE', 'en') == 'en' else 1,
                        key="pdf_lang_registry",
                        help="Select the language for the PDF report"
                    )
                    lang_code = 'en' if pdf_lang == "English" else 'fr'
                    if st.button("Generate"):
                        pdf_data = generate_pdf_report(pdf_id, lang=lang_code)
                        if pdf_data:
                            lang_suffix = "_FR" if lang_code == 'fr' else "_EN"
                            st.download_button("Download PDF", pdf_data,
                                             f"Report_{pdf_id}{lang_suffix}.pdf", "application/pdf")
                        else:
                            st.error("Report not found")

            # ===== PATIENT VIEW/EDIT SECTION =====
            st.divider()
            st.subheader("👤 Patient Details & Edit")

            # Get list of unique patients (excluding deleted)
            with get_db_connection() as patient_conn:
                patients_query = """
                    SELECT DISTINCT p.id, p.mrn_id, p.full_name, COUNT(r.id) as result_count
                    FROM patients p
                    LEFT JOIN results r ON r.patient_id = p.id
                    WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
                    GROUP BY p.id
                    ORDER BY p.full_name
                """
                patients_df = pd.read_sql(patients_query, patient_conn)

            if not patients_df.empty:
                # Create selection options
                patient_options = {f"{row['mrn_id']} - {row['full_name']} ({row['result_count']} results)": row['id']
                                   for _, row in patients_df.iterrows()}

                selected_patient_label = st.selectbox(
                    "Select Patient to View/Edit",
                    options=["-- Select a patient --"] + list(patient_options.keys()),
                    key="patient_selector"
                )

                if selected_patient_label != "-- Select a patient --":
                    patient_id = patient_options[selected_patient_label]
                    patient_details = get_patient_details(patient_id)

                    if patient_details:
                        with st.expander("📋 View & Edit Patient Information", expanded=True):
                            st.info(f"Patient ID: {patient_details['mrn']} | Created: {patient_details.get('created_at', 'N/A')[:10] if patient_details.get('created_at') else 'N/A'}")

                            with st.form(key="edit_patient_form"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    edit_name = st.text_input("Full Name", value=patient_details.get('name', ''))
                                    edit_age = st.number_input("Age", min_value=15, max_value=60,
                                        value=int(patient_details.get('age', 30)) if patient_details.get('age') else 30)
                                    edit_weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0,
                                        value=float(patient_details.get('weight', 65.0)) if patient_details.get('weight') else 65.0)
                                with col2:
                                    edit_weeks = st.number_input("Gestational Weeks", min_value=9, max_value=42,
                                        value=int(patient_details.get('weeks', 12)) if patient_details.get('weeks') else 12)
                                    edit_height = st.number_input("Height (cm)", min_value=100, max_value=220,
                                        value=int(patient_details.get('height', 165)) if patient_details.get('height') else 165)
                                    if edit_weight > 0 and edit_height > 0:
                                        edit_bmi = round(edit_weight / ((edit_height/100)**2), 1)
                                        st.metric("BMI (calculated)", edit_bmi)
                                    else:
                                        edit_bmi = 0.0

                                edit_notes = st.text_area("Clinical Notes",
                                    value=patient_details.get('notes', '') or '',
                                    height=100)

                                if st.form_submit_button("💾 Update Patient Information", type="primary"):
                                    update_data = {
                                        'name': edit_name,
                                        'age': edit_age,
                                        'weight': edit_weight,
                                        'height': edit_height,
                                        'bmi': edit_bmi,
                                        'weeks': edit_weeks,
                                        'notes': edit_notes
                                    }
                                    success, message = update_patient(patient_id, update_data)
                                    if success:
                                        st.success(f"✅ {message}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to update: {message}")

                        # Show patient's test results with editing capability
                        with st.expander("📊 Patient Test Results (View & Edit)", expanded=False):
                            with get_db_connection() as results_conn:
                                results_query = """
                                    SELECT r.id, r.created_at, r.panel_type, r.qc_status,
                                           r.t21_res, r.t18_res, r.t13_res, r.sca_res, r.final_summary,
                                           r.qc_override, r.qc_override_reason
                                    FROM results r
                                    WHERE r.patient_id = ?
                                    ORDER BY r.created_at DESC
                                """
                                patient_results = pd.read_sql(results_query, results_conn, params=(patient_id,))

                            if not patient_results.empty:
                                patient_results['created_at'] = pd.to_datetime(patient_results['created_at']).dt.strftime('%Y-%m-%d %H:%M')
                                # Show effective QC status (with override indicator)
                                patient_results['QC Display'] = patient_results.apply(
                                    lambda r: f"PASS (Override)" if r.get('qc_override') else r['qc_status'], axis=1
                                )
                                display_cols = ['id', 'created_at', 'panel_type', 'QC Display', 't21_res', 't18_res', 't13_res', 'sca_res', 'final_summary']
                                st.dataframe(patient_results[display_cols], use_container_width=True)

                                # Result selection for editing
                                st.markdown("---")
                                st.subheader("✏️ Edit Test Result")
                                result_options = {f"Result #{row['id']} - {row['created_at']} ({row['panel_type']})": row['id']
                                                  for _, row in patient_results.iterrows()}
                                selected_result_label = st.selectbox(
                                    "Select Result to Edit",
                                    options=["-- Select a result --"] + list(result_options.keys()),
                                    key="result_selector"
                                )

                                if selected_result_label != "-- Select a result --":
                                    result_id = result_options[selected_result_label]
                                    result_details = get_result_details(result_id)

                                    if result_details:
                                        # Get QC metrics with defaults
                                        qc_m = result_details.get('qc_metrics', {})
                                        full_z = result_details.get('full_z', {})

                                        with st.form(key=f"edit_result_form_{result_id}"):
                                            st.markdown("**Panel & Sequencing Metrics**")
                                            panel_col, reads_col, cff_col = st.columns(3)
                                            edit_panel = panel_col.selectbox("Panel Type",
                                                options=list(config['PANEL_READ_LIMITS'].keys()),
                                                index=list(config['PANEL_READ_LIMITS'].keys()).index(result_details['panel_type']) if result_details['panel_type'] in config['PANEL_READ_LIMITS'] else 0)
                                            edit_reads = reads_col.number_input("Reads (M)", min_value=0.0, max_value=100.0,
                                                value=float(qc_m.get('reads', 8.0)))
                                            edit_cff = cff_col.number_input("Cff %", min_value=0.0, max_value=50.0,
                                                value=float(qc_m.get('cff', 10.0)))

                                            gc_col, qs_col, uniq_col, err_col = st.columns(4)
                                            edit_gc = gc_col.number_input("GC %", min_value=0.0, max_value=100.0,
                                                value=float(qc_m.get('gc', 40.0)))
                                            edit_qs = qs_col.number_input("QS", min_value=0.0, max_value=10.0,
                                                value=float(qc_m.get('qs', 1.0)))
                                            edit_uniq = uniq_col.number_input("Unique %", min_value=0.0, max_value=100.0,
                                                value=float(qc_m.get('unique_rate', 75.0)))
                                            edit_err = err_col.number_input("Error %", min_value=0.0, max_value=5.0,
                                                value=float(qc_m.get('error_rate', 0.1)))

                                            st.markdown("---")
                                            st.markdown("**Trisomy Z-Scores**")
                                            z21_col, z18_col, z13_col = st.columns(3)
                                            edit_z21 = z21_col.number_input("Z-21", min_value=-10.0, max_value=50.0,
                                                value=float(full_z.get('21', full_z.get(21, 0.5))))
                                            edit_z18 = z18_col.number_input("Z-18", min_value=-10.0, max_value=50.0,
                                                value=float(full_z.get('18', full_z.get(18, 0.5))))
                                            edit_z13 = z13_col.number_input("Z-13", min_value=-10.0, max_value=50.0,
                                                value=float(full_z.get('13', full_z.get(13, 0.5))))

                                            st.markdown("**Sex Chromosome Analysis**")
                                            sca_col, zxx_col, zxy_col = st.columns(3)
                                            # Extract SCA type from result
                                            current_sca = result_details.get('sca_res', '')
                                            sca_types = ["XX", "XY", "XO", "XXX", "XXY", "XYY", "XXX+XY", "XO+XY"]
                                            detected_sca = "XX"
                                            # Check mosaicism types first (more specific)
                                            if "XXX+XY" in current_sca.upper():
                                                detected_sca = "XXX+XY"
                                            elif "XO+XY" in current_sca.upper():
                                                detected_sca = "XO+XY"
                                            else:
                                                for st_type in sca_types[:6]:  # Check non-mosaicism types
                                                    if st_type in current_sca.upper():
                                                        detected_sca = st_type
                                                        break
                                            edit_sca_type = sca_col.selectbox("SCA Type", options=sca_types,
                                                index=sca_types.index(detected_sca) if detected_sca in sca_types else 0)
                                            edit_zxx = zxx_col.number_input("Z-XX", min_value=-10.0, max_value=50.0,
                                                value=float(full_z.get('XX', 0.0)))
                                            edit_zxy = zxy_col.number_input("Z-XY", min_value=-10.0, max_value=50.0,
                                                value=float(full_z.get('XY', 0.0)))

                                            st.markdown("---")
                                            st.markdown("**Findings (CNV & RAT)**")
                                            # Parse CNV list
                                            cnv_list = result_details.get('cnv_list', [])
                                            if cnv_list and isinstance(cnv_list, list):
                                                cnv_text = "; ".join(cnv_list) if isinstance(cnv_list[0], str) else "; ".join([f"{c.get('size', 0)}Mb ({c.get('ratio', 0)}%)" for c in cnv_list])
                                            else:
                                                cnv_text = ""
                                            edit_cnv = st.text_area("CNV Findings (format: size Mb (ratio%); ...)", value=cnv_text, height=60,
                                                help="Enter CNV findings separated by semicolons, e.g., '5Mb (8%); 10Mb (12%)'")

                                            # Parse RAT list
                                            rat_list = result_details.get('rat_list', [])
                                            if rat_list and isinstance(rat_list, list):
                                                rat_text = "; ".join(rat_list) if isinstance(rat_list[0], str) else "; ".join([f"Chr {r.get('chr', 0)} (Z:{r.get('z', 0)})" for r in rat_list])
                                            else:
                                                rat_text = ""
                                            edit_rat = st.text_area("RAT Findings (format: Chr # (Z:score); ...)", value=rat_text, height=60,
                                                help="Enter RAT findings separated by semicolons, e.g., 'Chr 7 (Z:4.5); Chr 16 (Z:5.2)'")

                                            st.markdown("---")
                                            recalc_results = st.checkbox("Recalculate test results from Z-scores", value=True,
                                                help="If checked, T21/T18/T13/SCA results and QC will be recalculated based on the edited Z-scores and metrics")

                                            if st.form_submit_button("💾 Update Test Result", type="primary"):
                                                # Prepare updated QC metrics
                                                new_qc_metrics = {
                                                    'reads': edit_reads,
                                                    'cff': edit_cff,
                                                    'gc': edit_gc,
                                                    'qs': edit_qs,
                                                    'unique_rate': edit_uniq,
                                                    'error_rate': edit_err
                                                }

                                                # Prepare updated Z-scores
                                                new_full_z = {
                                                    '21': edit_z21, '18': edit_z18, '13': edit_z13,
                                                    'XX': edit_zxx, 'XY': edit_zxy
                                                }
                                                # Preserve other z-scores from original
                                                for k, v in full_z.items():
                                                    if str(k) not in ['21', '18', '13', 'XX', 'XY']:
                                                        new_full_z[str(k)] = v

                                                if recalc_results:
                                                    # Recalculate clinical results
                                                    t21_res, t21_risk = analyze_trisomy(config, edit_z21, "21")
                                                    t18_res, t18_risk = analyze_trisomy(config, edit_z18, "18")
                                                    t13_res, t13_risk = analyze_trisomy(config, edit_z13, "13")
                                                    sca_res, sca_risk = analyze_sca(config, edit_sca_type, edit_zxx, edit_zxy, edit_cff)

                                                    # Parse and analyze CNV
                                                    analyzed_cnvs = []
                                                    is_cnv_high = False
                                                    if edit_cnv.strip():
                                                        for cnv_item in edit_cnv.split(';'):
                                                            cnv_item = cnv_item.strip()
                                                            if cnv_item:
                                                                # Try to parse "XMb (Y%)" format
                                                                import re
                                                                match = re.search(r'([\d.]+)\s*[Mm]b.*?([\d.]+)\s*%', cnv_item)
                                                                if match:
                                                                    sz, rt = float(match.group(1)), float(match.group(2))
                                                                    msg, _, risk = analyze_cnv(sz, rt)
                                                                    if risk == "HIGH": is_cnv_high = True
                                                                    analyzed_cnvs.append(f"{sz}Mb ({rt}%) -> {msg}")
                                                                else:
                                                                    analyzed_cnvs.append(cnv_item)

                                                    # Parse and analyze RAT
                                                    analyzed_rats = []
                                                    is_rat_high = False
                                                    if edit_rat.strip():
                                                        for rat_item in edit_rat.split(';'):
                                                            rat_item = rat_item.strip()
                                                            if rat_item:
                                                                match = re.search(r'[Cc]hr\s*(\d+).*?[Zz]:\s*([\d.]+)', rat_item)
                                                                if match:
                                                                    r_chr, r_z = int(match.group(1)), float(match.group(2))
                                                                    msg, risk = analyze_rat(config, r_chr, r_z)
                                                                    if risk in ["POSITIVE", "HIGH"]: is_rat_high = True
                                                                    analyzed_rats.append(f"Chr {r_chr} (Z:{r_z}) -> {msg}")
                                                                    new_full_z[str(r_chr)] = r_z
                                                                else:
                                                                    analyzed_rats.append(rat_item)

                                                    # Determine final summary
                                                    all_risks = [t21_risk, t18_risk, t13_risk, sca_risk]
                                                    is_positive = "POSITIVE" in all_risks
                                                    is_high_risk = "HIGH" in all_risks or is_cnv_high or is_rat_high

                                                    qc_stat, qc_msg, qc_advice = check_qc_metrics(
                                                        config, edit_panel, edit_reads, edit_cff, edit_gc,
                                                        edit_qs, edit_uniq, edit_err, is_positive or is_high_risk
                                                    )

                                                    final_summary = "NEGATIVE"
                                                    if is_positive: final_summary = "POSITIVE DETECTED"
                                                    elif is_high_risk: final_summary = "HIGH RISK (SEE ADVICE)"
                                                    if qc_stat == "FAIL": final_summary = "INVALID (QC FAIL)"
                                                else:
                                                    # Keep existing results, just update metrics/z-scores
                                                    t21_res = result_details['t21_res']
                                                    t18_res = result_details['t18_res']
                                                    t13_res = result_details['t13_res']
                                                    sca_res = result_details['sca_res']
                                                    analyzed_cnvs = cnv_list if isinstance(cnv_list, list) else []
                                                    analyzed_rats = rat_list if isinstance(rat_list, list) else []
                                                    qc_stat = result_details['qc_status']
                                                    qc_msg = result_details['qc_details']
                                                    qc_advice = result_details['qc_advice']
                                                    final_summary = result_details['final_summary']

                                                # Prepare update data
                                                update_data = {
                                                    'panel_type': edit_panel,
                                                    'qc_status': qc_stat,
                                                    'qc_details': str(qc_msg) if recalc_results else qc_msg,
                                                    'qc_advice': qc_advice,
                                                    'qc_metrics': new_qc_metrics,
                                                    't21_res': t21_res,
                                                    't18_res': t18_res,
                                                    't13_res': t13_res,
                                                    'sca_res': sca_res,
                                                    'cnv_list': analyzed_cnvs,
                                                    'rat_list': analyzed_rats,
                                                    'full_z': new_full_z,
                                                    'final_summary': final_summary
                                                }

                                                success, message = update_result(result_id, update_data, st.session_state.user['id'])
                                                if success:
                                                    st.success(f"✅ {message}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed to update: {message}")
                            else:
                                st.info("No test results found for this patient")

                        # QC Override Section
                        with st.expander("🔧 QC Override (Staff Validation)", expanded=False):
                            st.markdown("**Override QC status for validation purposes.** Staff can force pass QC when clinical judgment warrants it.")
                            with get_db_connection() as qc_conn:
                                qc_query = """
                                    SELECT r.id, r.qc_status, r.qc_override, r.qc_override_reason,
                                           r.qc_override_at, u.full_name as override_by
                                    FROM results r
                                    LEFT JOIN users u ON r.qc_override_by = u.id
                                    WHERE r.patient_id = ?
                                    ORDER BY r.created_at DESC
                                """
                                qc_results = pd.read_sql(qc_query, qc_conn, params=(patient_id,))

                            if not qc_results.empty:
                                for _, qc_row in qc_results.iterrows():
                                    result_id = qc_row['id']
                                    original_status = qc_row['qc_status']
                                    is_overridden = bool(qc_row.get('qc_override'))

                                    st.markdown(f"**Result ID: {result_id}** - Original QC: `{original_status}`")

                                    if is_overridden:
                                        st.success(f"✅ QC Overridden to PASS by {qc_row.get('override_by', 'Unknown')}")
                                        st.caption(f"Reason: {qc_row.get('qc_override_reason', 'N/A')}")
                                        st.caption(f"Override date: {qc_row.get('qc_override_at', 'N/A')[:16] if qc_row.get('qc_override_at') else 'N/A'}")
                                        if st.button(f"Remove Override", key=f"remove_override_{result_id}"):
                                            ok, msg = remove_qc_override(result_id, st.session_state.user['id'])
                                            if ok:
                                                st.success(msg)
                                                st.rerun()
                                            else:
                                                st.error(msg)
                                    else:
                                        if original_status in ['FAIL', 'WARNING']:
                                            with st.form(key=f"override_form_{result_id}"):
                                                override_reason = st.text_input(
                                                    "Override Reason (required)",
                                                    placeholder="e.g., Clinical judgment, repeat testing confirms negative",
                                                    key=f"reason_{result_id}"
                                                )
                                                if st.form_submit_button(f"Override QC to PASS"):
                                                    if override_reason.strip():
                                                        ok, msg = override_qc_status(result_id, override_reason.strip(), st.session_state.user['id'])
                                                        if ok:
                                                            st.success(msg)
                                                            st.rerun()
                                                        else:
                                                            st.error(msg)
                                                    else:
                                                        st.error("Please provide a reason for the override")
                                        else:
                                            st.info("QC already PASS - no override needed")
                                    st.divider()

                        # Delete Patient Section
                        with st.expander("🗑️ Delete Patient", expanded=False):
                            st.warning("**Warning:** This will permanently delete the patient and ALL their test results. This action cannot be undone.")

                            # Show how many results will be deleted
                            with get_db_connection() as del_conn:
                                result_count_query = "SELECT COUNT(*) FROM results WHERE patient_id = ?"
                                result_count = pd.read_sql(result_count_query, del_conn, params=(patient_id,)).iloc[0, 0]

                            st.info(f"This patient has **{result_count}** test result(s) that will be deleted.")

                            confirm_delete = st.checkbox(f"I confirm I want to permanently delete patient '{patient_details['mrn']}'", key=f"confirm_del_{patient_id}")

                            if st.button("🗑️ Delete Patient Permanently", type="secondary", disabled=not confirm_delete, key=f"delete_patient_{patient_id}"):
                                ok, msg = delete_patient(patient_id, hard_delete=True)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
        else:
            st.info("No records found")
    
    # TAB 3: ANALYTICS
    with tabs[2]:
        render_analytics_dashboard()
    
    # TAB 4: BATCH IMPORT
    with tabs[3]:
        st.header("📂 Batch Import")
        
        import_method = st.radio("Import Method", 
                                 ["📄 From PDF Reports", "📊 From CSV/Excel Template"],
                                 horizontal=True)
        
        st.divider()
        
        # ===== PDF IMPORT =====
        if import_method == "📄 From PDF Reports":
            st.subheader("Import from PDF Reports")
            st.markdown("""
            Upload one or multiple PDF reports. The system extracts:
            - **Patient Info**: Name, MRN/File Number, Age, Weight, Height, BMI, Gestational Weeks
            - **Sequencing Metrics**: Reads, Cff, GC%, QS, Unique Rate, Error Rate
            - **Z-Scores**: All 22 autosomes + XX/XY
            - **Findings**: CNVs, RATs, SCA type
            - **Results**: QC Status, Final Interpretation
            
            Files are automatically **grouped by patient MRN/File Number**.
            """)
            
            uploaded_pdfs = st.file_uploader(
                "Upload PDF Report(s)",
                type=['pdf'],
                accept_multiple_files=True,
                help="Select one or more PDF files - they will be grouped by patient file number"
            )

            # Helper functions defined at module level for reuse
            def safe_int(val, default=0):
                try:
                    return int(val) if val and val > 0 else default
                except (TypeError, ValueError):
                    return default

            def safe_float(val, default=0.0):
                try:
                    return float(val) if val and val > 0 else default
                except (TypeError, ValueError):
                    return default

            if uploaded_pdfs:
                st.info(f"📁 {len(uploaded_pdfs)} file(s) selected")

                if st.button("🔍 Extract & Preview Data", type="primary"):
                    with st.spinner("Extracting comprehensive data from PDFs..."):
                        result = parse_pdf_batch(uploaded_pdfs)

                    patients = result['patients']
                    errors = result['errors']

                    # Store in session state for persistence across reruns
                    st.session_state.pdf_import_data = patients
                    st.session_state.pdf_import_errors = errors
                    st.rerun()

            # Display extracted data from session state (persists across button clicks)
            if 'pdf_import_data' in st.session_state and st.session_state.pdf_import_data:
                patients = st.session_state.pdf_import_data
                errors = st.session_state.get('pdf_import_errors', [])

                if errors:
                    st.warning(f"⚠️ {len(errors)} file(s) had issues:")
                    for err in errors:
                        st.caption(f"• {err}")

                st.success(f"✅ Extracted data for {len(patients)} patient(s)")
                st.info("📝 **Edit Mode**: You can modify any extracted values before importing. Changes are saved when you click 'Confirm & Import'.")

                # Check for duplicates and show warnings/errors
                duplicate_mrns = []
                orphan_mrns = []  # Patients with 0 results (can be replaced)
                for mrn in patients.keys():
                    exists, existing_patient = check_duplicate_patient(mrn)
                    if exists:
                        if existing_patient['result_count'] == 0:
                            # Patient exists but has no results - it's an orphan, can be cleaned up
                            orphan_mrns.append(mrn)
                            st.warning(f"⚠️ Patient ID '{mrn}' exists as '{existing_patient['name']}' but has 0 results. "
                                       f"This orphan record will be replaced during import.")
                        else:
                            duplicate_mrns.append(mrn)
                            st.error(f"🚫 Patient ID '{mrn}' already exists as '{existing_patient['name']}' "
                                      f"with {existing_patient['result_count']} result(s). "
                                      f"This patient will be SKIPPED during import (Patient ID must be unique).")

                # Show patients grouped by MRN with editable fields using forms
                for mrn, records in patients.items():
                    is_duplicate = mrn in duplicate_mrns
                    expander_title = f"📋 Patient: {mrn} - {records[0]['patient_name']} ({len(records)} file(s))"
                    if is_duplicate:
                        expander_title = f"🚫 [DUPLICATE] {expander_title}"

                    with st.expander(expander_title, expanded=not is_duplicate):
                        if is_duplicate:
                            st.error("This patient ID already exists in the registry and will be skipped.")

                        for idx, record in enumerate(records, 1):
                            edit_key = f"{mrn}_{idx}"
                            st.markdown(f"**File {idx}: {record['source_file']}**")

                            # Use form to prevent crashes on edit
                            with st.form(key=f"form_{edit_key}"):
                                st.markdown("##### Patient Information")
                                p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                                with p_col1:
                                    edit_name = st.text_input("Name", value=record.get('patient_name', ''))
                                with p_col2:
                                    edit_age = st.number_input("Age", min_value=15, max_value=60,
                                        value=safe_int(record.get('age'), 30))
                                with p_col3:
                                    edit_weeks = st.number_input("Weeks", min_value=9, max_value=24,
                                        value=safe_int(record.get('weeks'), 12))
                                with p_col4:
                                    panel_options = ["NIPT Basic", "NIPT Standard", "NIPT Plus", "NIPT Pro"]
                                    current_panel = record.get('panel', 'NIPT Standard')
                                    panel_idx = panel_options.index(current_panel) if current_panel in panel_options else 1
                                    edit_panel = st.selectbox("Panel", panel_options, index=panel_idx)

                                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                                with m_col1:
                                    edit_weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0,
                                        value=safe_float(record.get('weight'), 65.0))
                                with m_col2:
                                    edit_height = st.number_input("Height (cm)", min_value=100, max_value=220,
                                        value=safe_int(record.get('height'), 165))
                                with m_col3:
                                    if edit_weight > 0 and edit_height > 0:
                                        edit_bmi = round(edit_weight / ((edit_height/100)**2), 1)
                                        st.metric("BMI (auto)", edit_bmi)
                                    else:
                                        edit_bmi = 0.0
                                        st.metric("BMI", "N/A")
                                with m_col4:
                                    sca_options = ["XX", "XY", "XO", "XXX", "XXY", "XYY", "XXX+XY", "XO+XY"]
                                    current_sca = record.get('sca_type', 'XX')
                                    sca_idx = sca_options.index(current_sca) if current_sca in sca_options else 0
                                    edit_sca = st.selectbox("SCA Type", sca_options, index=sca_idx)

                                st.markdown("##### Sequencing Metrics")
                                q_col1, q_col2, q_col3, q_col4, q_col5, q_col6 = st.columns(6)
                                with q_col1:
                                    edit_reads = st.number_input("Reads (M)", min_value=0.0, max_value=100.0,
                                        value=safe_float(record.get('reads'), 10.0))
                                with q_col2:
                                    edit_cff = st.number_input("Cff %", min_value=0.0, max_value=50.0,
                                        value=safe_float(record.get('cff'), 10.0))
                                with q_col3:
                                    edit_gc = st.number_input("GC %", min_value=0.0, max_value=100.0,
                                        value=safe_float(record.get('gc'), 41.0))
                                with q_col4:
                                    edit_qs = st.number_input("QS", min_value=0.0, max_value=10.0,
                                        value=safe_float(record.get('qs'), 1.0))
                                with q_col5:
                                    edit_uniq = st.number_input("Unique %", min_value=0.0, max_value=100.0,
                                        value=safe_float(record.get('unique_rate'), 80.0))
                                with q_col6:
                                    edit_error = st.number_input("Error %", min_value=0.0, max_value=10.0,
                                        value=safe_float(record.get('error_rate'), 0.2))

                                st.markdown("##### Z-Scores (Trisomies)")
                                z_col1, z_col2, z_col3, z_col4, z_col5 = st.columns(5)
                                z_scores_orig = record.get('z_scores', {})
                                with z_col1:
                                    edit_z21 = st.number_input("Z-21", min_value=-10.0, max_value=20.0,
                                        value=safe_float(z_scores_orig.get(21, z_scores_orig.get('21', 0.0))), format="%.2f")
                                with z_col2:
                                    edit_z18 = st.number_input("Z-18", min_value=-10.0, max_value=20.0,
                                        value=safe_float(z_scores_orig.get(18, z_scores_orig.get('18', 0.0))), format="%.2f")
                                with z_col3:
                                    edit_z13 = st.number_input("Z-13", min_value=-10.0, max_value=20.0,
                                        value=safe_float(z_scores_orig.get(13, z_scores_orig.get('13', 0.0))), format="%.2f")
                                with z_col4:
                                    edit_zxx = st.number_input("Z-XX", min_value=-10.0, max_value=20.0,
                                        value=safe_float(z_scores_orig.get('XX', 0.0)), format="%.2f")
                                with z_col5:
                                    edit_zxy = st.number_input("Z-XY", min_value=-10.0, max_value=20.0,
                                        value=safe_float(z_scores_orig.get('XY', 0.0)), format="%.2f")

                                edit_notes = st.text_area("Clinical Notes",
                                    value=record.get('notes', ''),
                                    help="Enter clinical observations like NT measurements, ultrasound findings, etc.")

                                # Save form data button
                                if st.form_submit_button("💾 Save Changes for this Record"):
                                    # Store edited data in session state
                                    if 'pdf_edit_data' not in st.session_state:
                                        st.session_state.pdf_edit_data = {}
                                    st.session_state.pdf_edit_data[edit_key] = {
                                        'patient_name': edit_name,
                                        'age': edit_age,
                                        'weeks': edit_weeks,
                                        'panel': edit_panel,
                                        'weight': edit_weight,
                                        'height': edit_height,
                                        'bmi': edit_bmi,
                                        'sca_type': edit_sca,
                                        'reads': edit_reads,
                                        'cff': edit_cff,
                                        'gc': edit_gc,
                                        'qs': edit_qs,
                                        'unique_rate': edit_uniq,
                                        'error_rate': edit_error,
                                        'z_scores': {21: edit_z21, 18: edit_z18, 13: edit_z13, 'XX': edit_zxx, 'XY': edit_zxy},
                                        'notes': edit_notes,
                                        'cnv_findings': record.get('cnv_findings', []),
                                        'rat_findings': record.get('rat_findings', []),
                                        'source_file': record.get('source_file', '')
                                    }
                                    st.success(f"✅ Changes saved for {edit_name}")

                            # Show CNV/RAT findings outside form
                            if record.get('cnv_findings') or record.get('rat_findings'):
                                with st.expander("View CNV/RAT Findings"):
                                    if record.get('cnv_findings'):
                                        st.markdown("**CNV Findings:**")
                                        for cnv in record['cnv_findings']:
                                            st.caption(f"• Size: {cnv['size']} Mb, Ratio: {cnv['ratio']}%")
                                    if record.get('rat_findings'):
                                        st.markdown("**RAT Findings:**")
                                        for rat in record['rat_findings']:
                                            st.caption(f"• Chr {rat['chr']}: Z = {rat['z']}")

                            st.divider()

                st.warning("⚠️ Click 'Save Changes' in each record form to save edits, then click 'Import All' below")
                if duplicate_mrns:
                    st.error(f"⚠️ {len(duplicate_mrns)} patient(s) with duplicate IDs will be SKIPPED: {', '.join(duplicate_mrns)}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirm & Import All to Registry", type="primary"):
                        success, fail, skipped, replaced = 0, 0, 0, 0
                        config = load_config()
                        edit_data = st.session_state.get('pdf_edit_data', {})

                        for mrn, records in patients.items():
                            # Check if patient exists
                            exists, existing_patient = check_duplicate_patient(mrn)
                            if exists:
                                if existing_patient['result_count'] == 0:
                                    # Orphan patient with no results - delete it first
                                    try:
                                        with get_db_connection() as conn:
                                            c = conn.cursor()
                                            c.execute("DELETE FROM patients WHERE id = ?", (existing_patient['id'],))
                                            conn.commit()
                                        replaced += 1
                                        st.info(f"🔄 Replaced orphan patient record '{mrn}'")
                                    except Exception as e:
                                        st.error(f"Failed to replace orphan patient '{mrn}': {e}")
                                        skipped += len(records)
                                        continue
                                else:
                                    # Patient with results - skip
                                    skipped += len(records)
                                    st.warning(f"⚠️ Skipped patient ID '{mrn}' - already exists with {existing_patient['result_count']} result(s)")
                                    continue

                            for idx, original_data in enumerate(records, 1):
                                try:
                                    edit_key = f"{mrn}_{idx}"
                                    # Use edited data if available, otherwise use original
                                    data = edit_data.get(edit_key, original_data)

                                    # Get Z-scores
                                    z_scores = data.get('z_scores', {})
                                    z_21 = safe_float(z_scores.get(21, z_scores.get('21', 0.0)))
                                    z_18 = safe_float(z_scores.get(18, z_scores.get('18', 0.0)))
                                    z_13 = safe_float(z_scores.get(13, z_scores.get('13', 0.0)))
                                    z_xx = safe_float(z_scores.get('XX', 0.0))
                                    z_xy = safe_float(z_scores.get('XY', 0.0))

                                    # Analyze
                                    t21, _ = analyze_trisomy(config, z_21, "21")
                                    t18, _ = analyze_trisomy(config, z_18, "18")
                                    t13, _ = analyze_trisomy(config, z_13, "13")
                                    cff_val = safe_float(data.get('cff'), 10.0)
                                    sca, _ = analyze_sca(config, data.get('sca_type', 'XX'), z_xx, z_xy, cff_val)

                                    # Process CNVs and RATs
                                    analyzed_cnvs = []
                                    for cnv in data.get('cnv_findings', []):
                                        msg, _, _ = analyze_cnv(cnv['size'], cnv['ratio'])
                                        analyzed_cnvs.append(f"{cnv['size']}Mb ({cnv['ratio']}%) -> {msg}")

                                    analyzed_rats = []
                                    for rat in data.get('rat_findings', []):
                                        msg, _ = analyze_rat(config, rat['chr'], rat['z'])
                                        analyzed_rats.append(f"Chr {rat['chr']} (Z:{rat['z']}) -> {msg}")

                                    # Run QC
                                    reads_val = safe_float(data.get('reads'), 10.0)
                                    gc_val = safe_float(data.get('gc'), 41.0)
                                    qs_val = safe_float(data.get('qs'), 1.0)
                                    uniq_val = safe_float(data.get('unique_rate'), 80.0)
                                    error_val = safe_float(data.get('error_rate'), 0.2)

                                    qc_s, qc_m, qc_a = check_qc_metrics(
                                        config, data.get('panel', 'NIPT Standard'),
                                        reads_val, cff_val, gc_val, qs_val, uniq_val, error_val, False
                                    )

                                    # Determine final result
                                    final = "NEGATIVE"
                                    if "POSITIVE" in (t21 + t18 + t13 + sca):
                                        final = "POSITIVE DETECTED"
                                    if qc_s == "FAIL":
                                        final = "INVALID (QC FAIL)"

                                    p_data = {
                                        'name': data.get('patient_name', 'Unknown'),
                                        'id': mrn,
                                        'age': safe_int(data.get('age'), 30),
                                        'weight': safe_float(data.get('weight'), 65.0),
                                        'height': safe_int(data.get('height'), 165),
                                        'bmi': safe_float(data.get('bmi'), 0.0),
                                        'weeks': safe_int(data.get('weeks'), 12),
                                        'notes': f"Imported from: {data.get('source_file', 'PDF')}. {data.get('notes', '')}"
                                    }

                                    r_data = {
                                        'panel': data.get('panel', 'NIPT Standard'),
                                        'qc_status': qc_s,
                                        'qc_msgs': qc_m,
                                        'qc_advice': qc_a
                                    }

                                    c_data = {
                                        't21': t21, 't18': t18, 't13': t13, 'sca': sca,
                                        'cnv_list': analyzed_cnvs, 'rat_list': analyzed_rats, 'final': final
                                    }

                                    full_z = {21: z_21, 18: z_18, 13: z_13, 'XX': z_xx, 'XY': z_xy}

                                    # QC metrics for PDF report
                                    qc_metrics = {
                                        'reads': reads_val, 'cff': cff_val, 'gc': gc_val,
                                        'qs': qs_val, 'unique_rate': uniq_val, 'error_rate': error_val
                                    }

                                    # Use allow_duplicate=False to enforce uniqueness
                                    rid, msg = save_result(p_data, r_data, c_data, full_z, qc_metrics=qc_metrics, allow_duplicate=False)
                                    if rid:
                                        success += 1
                                    else:
                                        st.warning(f"⚠️ {data.get('patient_name', 'Unknown')}: {msg}")
                                        fail += 1

                                except Exception as e:
                                    st.error(f"Failed to import {data.get('patient_name', 'Unknown')}: {e}")
                                    fail += 1

                        result_msg = f"✅ Import Complete: {success} records imported"
                        if replaced > 0:
                            result_msg += f", {replaced} orphan records replaced"
                        if fail > 0:
                            result_msg += f", {fail} failed"
                        if skipped > 0:
                            result_msg += f", {skipped} skipped (duplicate IDs)"
                        st.success(result_msg)
                        log_audit("PDF_IMPORT", f"Imported {success} records, {replaced} orphans replaced, {fail} failed, {skipped} skipped (duplicates)",
                                 st.session_state.user['id'])

                        # Clean up session state
                        for key in ['pdf_import_data', 'pdf_edit_data', 'pdf_import_errors']:
                            if key in st.session_state:
                                del st.session_state[key]

                with col2:
                    if st.button("❌ Cancel"):
                        for key in ['pdf_import_data', 'pdf_edit_data', 'pdf_import_errors']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
            
            st.divider()
            st.markdown("""
            **📋 Comprehensive Extraction Includes:**
            - ✅ All patient demographics (name, MRN, age, weight, height, BMI, weeks)
            - ✅ Complete sequencing metrics (reads, Cff, GC, QS, unique rate, error rate)
            - ✅ Z-scores for all 22 autosomes (Chr 1-22)
            - ✅ Sex chromosome Z-scores (XX, XY)
            - ✅ CNV findings with size and ratio
            - ✅ RAT findings with chromosome and Z-score
            - ✅ QC status and final results
            - ✅ Clinical notes (nuchal translucency, ultrasound findings, etc.)

            **📝 Edit Before Import:**
            - All extracted values are **editable** before import
            - Modify patient info, sequencing metrics, Z-scores
            - Add clinical notes including NT measurements
            - BMI auto-calculates from weight/height

            **📁 Intelligent Grouping:**
            - Files are automatically grouped by **Patient MRN/File Number**
            - Multiple reports for the same patient are shown together
            - Each file is processed separately but organized by patient

            **⚠️ Requirements:**
            - PDFs must contain **searchable text** (not scanned images)
            - Patient MRN/File Number must be present for grouping
            """)
        
        # ===== CSV/EXCEL IMPORT =====
        else:
            st.subheader("Import from CSV/Excel Template")
        template = {
            'Patient Name': ['Example'], 'MRN': ['12345'], 'Age': [30], 
            'Weight': [65], 'Height': [165], 'Weeks': [12], 'Panel': ['NIPT Standard'],
            'Reads': [10.5], 'Cff': [12.0], 'GC': [41.0], 'QS': [1.2], 
            'Unique': [80.0], 'Error': [0.2],
            'SCA Type': ['XX'], 'Z-XX': [0.0], 'Z-XY': [0.0]
        }
        for i in range(1, 23): template[f'Z-{i}'] = [0.0]
        
        template_df = pd.DataFrame(template)
        st.download_button("📥 Download Template", 
                          template_df.to_csv(index=False), 
                          "NIPT_Template.csv", "text/csv")

        st.markdown("#### 2. Upload File")
        uploaded = st.file_uploader("Upload CSV/Excel", type=['csv', 'xlsx'])
        
        if uploaded and st.button("▶️ Process Batch"):
            try:
                if uploaded.name.endswith('.csv'):
                    df_in = pd.read_csv(uploaded)
                else:
                    df_in = pd.read_excel(uploaded)
                
                success, fail = 0, 0
                bar = st.progress(0)
                status = st.empty()
                
                for idx, row in df_in.iterrows():
                    try:
                        status.text(f"Processing {idx+1}/{len(df_in)}")
                        
                        p_data = {
                            'name': row.get('Patient Name'), 'id': str(row.get('MRN')), 
                            'age': row.get('Age'), 'weight': row.get('Weight'), 
                            'height': row.get('Height'), 'bmi': 0, 
                            'weeks': row.get('Weeks'), 'notes': ''
                        }
                        
                        z_map = {i: row.get(f'Z-{i}', 0.0) for i in range(1, 23)}
                        z_map['XX'] = row.get('Z-XX', 0.0)
                        z_map['XY'] = row.get('Z-XY', 0.0)

                        t21, _ = analyze_trisomy(config, z_map[21], "21")
                        t18, _ = analyze_trisomy(config, z_map[18], "18")
                        t13, _ = analyze_trisomy(config, z_map[13], "13")
                        sca, _ = analyze_sca(config, row.get('SCA Type', 'XX'), 
                                           z_map['XX'], z_map['XY'], row.get('Cff', 10))

                        rats = []
                        for ch, z in z_map.items():
                            if isinstance(ch, int) and ch not in [13, 18, 21]:
                                msg, _ = analyze_rat(config, ch, z)
                                if "POSITIVE" in msg or "Ambiguous" in msg:
                                    rats.append(f"Chr {ch} (Z:{z}) -> {msg}")

                        qc_s, qc_m, qc_a = check_qc_metrics(
                            config, row.get('Panel'), row.get('Reads'), row.get('Cff'), 
                            row.get('GC'), row.get('QS'), row.get('Unique'), 
                            row.get('Error'), False
                        )
                        
                        final = "NEGATIVE"
                        if "POSITIVE" in (t21 + t18 + t13 + sca): final = "POSITIVE"
                        if qc_s == "FAIL": final = "INVALID"

                        save_result(p_data, 
                                   {'panel': row.get('Panel'), 'qc_status': qc_s, 
                                    'qc_msgs': qc_m, 'qc_advice': qc_a},
                                   {'t21': t21, 't18': t18, 't13': t13, 'sca': sca, 
                                    'cnv_list': [], 'rat_list': rats, 'final': final},
                                   full_z=z_map)
                        success += 1
                    except:
                        fail += 1
                    bar.progress((idx + 1) / len(df_in))
                
                status.empty()
                st.success(f"✅ Success: {success} | ❌ Failed: {fail}")
                log_audit("BATCH_IMPORT", f"Processed {success}/{len(df_in)}", 
                         st.session_state.user['id'])
            except Exception as e:
                st.error(f"Error: {e}")
    
    # TAB 5: SETTINGS
    with tabs[4]:
        st.header("⚙️ Settings")
        
        st.subheader("Clinical Thresholds")
        
        with st.form("config_form"):
            st.markdown("**QC Thresholds**")
            c1, c2 = st.columns(2)
            new_cff = c1.number_input("Min CFF (%)", 0.0, 10.0, 
                                      config['QC_THRESHOLDS']['MIN_CFF'])
            gc_min = c2.number_input("GC Min (%)", 0.0, 50.0, 
                                     config['QC_THRESHOLDS']['GC_RANGE'][0])
            gc_max = c2.number_input("GC Max (%)", 0.0, 50.0, 
                                     config['QC_THRESHOLDS']['GC_RANGE'][1])
            
            st.markdown("**Panel Read Limits (M)**")
            c3, c4, c5, c6 = st.columns(4)
            basic = c3.number_input("Basic", 1, 20, config['PANEL_READ_LIMITS']['NIPT Basic'])
            standard = c4.number_input("Standard", 1, 20, config['PANEL_READ_LIMITS']['NIPT Standard'])
            plus = c5.number_input("Plus", 1, 20, config['PANEL_READ_LIMITS']['NIPT Plus'])
            pro = c6.number_input("Pro", 1, 20, config['PANEL_READ_LIMITS']['NIPT Pro'])
            
            st.markdown("**Clinical Thresholds**")
            c7, c8 = st.columns(2)
            tris_low = c7.number_input("Trisomy Low Risk", 0.0, 10.0, 
                                       config['CLINICAL_THRESHOLDS']['TRISOMY_LOW'])
            tris_amb = c7.number_input("Trisomy Ambiguous", 0.0, 10.0, 
                                       config['CLINICAL_THRESHOLDS']['TRISOMY_AMBIGUOUS'])
            sca_thresh = c8.number_input("SCA Threshold", 0.0, 10.0, 
                                         config['CLINICAL_THRESHOLDS']['SCA_THRESHOLD'])
            rat_pos = c8.number_input("RAT Positive", 0.0, 15.0, 
                                      config['CLINICAL_THRESHOLDS']['RAT_POSITIVE'])
            
            if st.form_submit_button("💾 Save Configuration"):
                new_config = DEFAULT_CONFIG.copy()
                new_config['QC_THRESHOLDS']['MIN_CFF'] = new_cff
                new_config['QC_THRESHOLDS']['GC_RANGE'] = [gc_min, gc_max]
                new_config['PANEL_READ_LIMITS'] = {
                    'NIPT Basic': basic, 'NIPT Standard': standard,
                    'NIPT Plus': plus, 'NIPT Pro': pro
                }
                new_config['CLINICAL_THRESHOLDS']['TRISOMY_LOW'] = tris_low
                new_config['CLINICAL_THRESHOLDS']['TRISOMY_AMBIGUOUS'] = tris_amb
                new_config['CLINICAL_THRESHOLDS']['SCA_THRESHOLD'] = sca_thresh
                new_config['CLINICAL_THRESHOLDS']['RAT_POSITIVE'] = rat_pos
                
                if save_config(new_config):
                    st.success("✅ Configuration saved")
                    log_audit("CONFIG_UPDATE", "Updated thresholds",
                             st.session_state.user['id'])
                    st.rerun()
                else:
                    st.error("Failed to save")

        st.divider()

        st.subheader("Report Settings")

        st.markdown("**PDF Report Language**")
        st.markdown("Select the default language for generated PDF reports.")

        # Language options
        language_options = {"English": "en", "Francais": "fr"}
        current_lang = config.get('REPORT_LANGUAGE', 'en')
        current_lang_display = "English" if current_lang == 'en' else "Francais"

        selected_lang_display = st.selectbox(
            "Default Report Language",
            options=list(language_options.keys()),
            index=list(language_options.keys()).index(current_lang_display),
            help="This sets the default language for PDF reports. You can also choose a different language when generating individual reports."
        )

        if language_options[selected_lang_display] != current_lang:
            if st.button("Save Language Preference"):
                new_config = config.copy()
                new_config['REPORT_LANGUAGE'] = language_options[selected_lang_display]
                if save_config(new_config):
                    st.success(f"✅ Report language set to {selected_lang_display}")
                    log_audit("CONFIG_UPDATE", f"Changed report language to {selected_lang_display}",
                             st.session_state.user['id'])
                    st.rerun()
                else:
                    st.error("Failed to save language preference")

        st.divider()

        st.subheader("User Management")

        # Password Change Section (available to all users)
        st.markdown("**🔑 Change Password**")
        st.markdown("""
        Password requirements:
        - At least 8 characters long
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one number (0-9)
        """)
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password", key="curr_pwd")
            new_password_1 = st.text_input("New Password", type="password", key="new_pwd1")
            new_password_2 = st.text_input("Confirm New Password", type="password", key="new_pwd2")

            if st.form_submit_button("Update Password"):
                if not current_password or not new_password_1 or not new_password_2:
                    st.error("All fields are required")
                elif new_password_1 != new_password_2:
                    st.error("New passwords do not match")
                else:
                    # Validate password strength
                    is_valid, error_msg = validate_password_strength(new_password_1)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        # Verify current password
                        with get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute("SELECT password_hash FROM users WHERE id = ?",
                                     (st.session_state.user['id'],))
                            row = c.fetchone()
                            if row and verify_password(current_password, row[0]):
                                # Update password
                                new_hash = hash_password(new_password_1)
                                c.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                                         (new_hash, st.session_state.user['id']))
                                conn.commit()
                                st.success("✅ Password updated successfully")
                                log_audit("PASSWORD_CHANGE", "User changed password",
                                         st.session_state.user['id'])
                            else:
                                st.error("Current password is incorrect")

        st.divider()

        # Admin-only user management
        if st.session_state.user['role'] == 'admin':
            st.markdown("**👥 Create New User**")
            with st.form("new_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_fullname = st.text_input("Full Name")
                new_role = st.selectbox("Role", ["technician", "geneticist", "admin"],
                                       help="Technician: Data entry and analysis. Geneticist: Analysis, review and approval. Admin: Full access including user management.")
                require_pwd_change = st.checkbox("Require password change on first login", value=True)

                if st.form_submit_button("Create User"):
                    if new_username and new_password:
                        is_valid, error_msg = validate_password_strength(new_password)
                        if not is_valid:
                            st.error(error_msg)
                        else:
                            try:
                                with get_db_connection() as conn:
                                    c = conn.cursor()
                                    c.execute("""
                                        INSERT INTO users (username, password_hash, full_name, role, created_at, must_change_password)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (new_username, hash_password(new_password),
                                         new_fullname, new_role, datetime.now().isoformat(),
                                         1 if require_pwd_change else 0))
                                    conn.commit()
                                    st.success(f"✅ User '{new_username}' created with role '{new_role}'")
                                    log_audit("CREATE_USER", f"Created user {new_username} with role {new_role}",
                                             st.session_state.user['id'])
                            except sqlite3.IntegrityError:
                                st.error("Username already exists")
                    else:
                        st.error("Username and password required")

            # List existing users
            st.markdown("**📋 Existing Users**")
            with get_db_connection() as conn:
                users_df = pd.read_sql("""
                    SELECT id, username, full_name, role, created_at, last_login
                    FROM users ORDER BY id
                """, conn)

            if not users_df.empty:
                st.dataframe(users_df, use_container_width=True, height=200)

        else:
            st.info("Admin access required for user management")

        st.divider()

        st.subheader("Audit Log")
        with get_db_connection() as conn:
            audit = pd.read_sql("""
                SELECT a.timestamp, u.username, a.action, a.details
                FROM audit_log a
                LEFT JOIN users u ON u.id = a.user_id
                ORDER BY a.id DESC LIMIT 50
            """, conn)

        if not audit.empty:
            st.dataframe(audit, use_container_width=True, height=300)
        else:
            st.info("No audit entries")

        st.divider()

        # Data Protection Section
        st.subheader("Data Protection")

        # Show startup protection status
        if 'data_protection_status' in st.session_state:
            status = st.session_state.data_protection_status
            if status['backup_created']:
                st.success(f"Startup backup created: {status['backup_path']}")
            if status['integrity_ok']:
                st.success(f"Database integrity: {status['integrity_message']}")
            else:
                st.warning(f"Database integrity: {status['integrity_message']}")

        st.markdown("**Backup Management**")
        st.markdown("""
        Backups are automatically created:
        - On each application startup
        - Before batch imports
        - Before database restores

        The system keeps the last 10 backups automatically.
        """)

        col_backup1, col_backup2 = st.columns(2)

        with col_backup1:
            if st.button("Create Manual Backup"):
                backup_path = create_backup("manual")
                if backup_path:
                    st.success(f"Backup created: {backup_path}")
                    log_audit("MANUAL_BACKUP", f"Created manual backup: {backup_path}",
                             st.session_state.user['id'])
                else:
                    st.error("Failed to create backup")

        with col_backup2:
            if st.button("Verify Database Integrity"):
                is_ok, message = verify_database_integrity()
                if is_ok:
                    st.success(message)
                else:
                    st.error(message)

        # List available backups
        st.markdown("**Available Backups**")
        backups = list_backups()

        if backups:
            backup_df = pd.DataFrame(backups)
            st.dataframe(backup_df[['filename', 'size_mb', 'created']],
                        use_container_width=True, height=200)

            # Restore functionality (admin only)
            if st.session_state.user['role'] == 'admin':
                st.markdown("**Restore from Backup** (Admin only)")
                st.warning("Restoring will replace all current data. A backup of the current state will be created first.")

                backup_options = {b['filename']: b['path'] for b in backups}
                selected_backup = st.selectbox("Select backup to restore",
                                               options=list(backup_options.keys()))

                if st.button("Restore Selected Backup", type="secondary"):
                    if selected_backup:
                        success, message = restore_backup(backup_options[selected_backup])
                        if success:
                            st.success(message)
                            log_audit("RESTORE_BACKUP", f"Restored from {selected_backup}",
                                     st.session_state.user['id'])
                            st.info("Please refresh the page to see restored data.")
                        else:
                            st.error(message)
        else:
            st.info("No backups available yet. Backups are created automatically on startup.")

if __name__ == "__main__":
    main()
