"""
NIPT Result Interpretation Software (NRIS) v2.4 - Simplified Patient Management Edition
By AzizElGhezal
---------------------------
Advanced clinical genetics dashboard with authentication, analytics,
PDF reports, visualizations, and comprehensive audit logging.

v2.4.1 Changes (Simplified Patient Sorting System):
- Patient IDs: Chronological, never reused (ghost IDs after deletion)
- MRN Validation: Configurable (numerical-only or alphanumeric)
- Simplified Deletion: Hard delete only, no soft delete complexity
- Sorting Options: Sort patients by ID (chronological) or MRN
- Multiple Results per MRN: Full support for patient test history
- Removed: Complex ID reuse logic, orphan cleanup, restore functions
- Improved: Real-time MRN validation, clearer UI messaging, better help text
"""

import sqlite3
import json
import io
import hashlib
import secrets
import re
import shutil
import os
import copy
import html as html_module
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
        'SCA_XY_THRESHOLD': 6.0,
        'RAT_POSITIVE': 8.0,
        'RAT_AMBIGUOUS': 4.5
    },
    # Test-specific thresholds for 1st, 2nd, and 3rd tests
    'TEST_SPECIFIC_THRESHOLDS': {
        # Trisomy thresholds (chr21/18/13)
        'TRISOMY': {
            1: {'low': 2.58, 'ambiguous': 6.0},  # 1st test
            2: {'low': 2.58, 'medium': 3.0, 'high': 4.0, 'positive': 6.0},  # 2nd test
            3: {'low': 2.58, 'medium': 3.0, 'high': 4.0, 'positive': 6.0}   # 3rd test (same as 2nd)
        },
        # RAT thresholds (Rare Autosomal Trisomy)
        'RAT': {
            1: {'low': 4.5, 'positive': 8.0},  # 1st test
            2: {'low': 4.5, 'positive': 8.0},  # 2nd test
            3: {'low': 4.5, 'positive': 8.0}   # 3rd test
        },
        # SCA thresholds (Sex Chromosome Aneuploidies)
        'SCA': {
            1: {'xx_threshold': 4.5, 'xy_threshold': 6.0},  # 1st test
            2: {'xx_threshold': 4.5, 'xy_threshold': 6.0},  # 2nd test
            3: {'xx_threshold': 4.5, 'xy_threshold': 6.0}   # 3rd test
        },
        # CNV thresholds by size (in Mb)
        'CNV': {
            1: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0},  # 1st test
            2: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0},  # 2nd test
            3: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0}   # 3rd test
        }
    },
    'REPORT_LANGUAGE': 'en',  # Default language for PDF reports: 'en' or 'fr'
    'ALLOW_ALPHANUMERIC_MRN': False,  # If True, allows letters/numbers in MRN. If False, only digits.
    'DEFAULT_SORT': 'id'  # Default sort order for registry: 'id' (chronological) or 'mrn' (by MRN)
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
        'test_number': 'Test Number:',
        'first_test': '1st Test',
        'second_test': '2nd Test',
        'third_test': '3rd Test',

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
        'version': 'NRIS v2.4 Enhanced Edition',
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
        'test_number': 'Numéro de test:',
        'first_test': '1er Test',
        'second_test': '2ème Test',
        'third_test': '3ème Test',

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
        'clinical_pathologist': 'Medecin responsable',
        'lab_director': 'Directeur du laboratoire',
        'lab_staff': 'Personnel du laboratoire',

        # Footer
        'report_generated': 'Rapport genere:',
        'version': 'NRIS v2.4 Edition Amelioree',
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

        # Migration: Add test_number column (1 for first test, 2 for second test)
        try:
            c.execute("ALTER TABLE results ADD COLUMN test_number INTEGER DEFAULT 1")
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
        return copy.deepcopy(DEFAULT_CONFIG)

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

def analyze_trisomy(config: Dict, z_score: float, chrom: str, test_number: int = 1) -> Tuple[str, str]:
    """Returns (result, risk_level).

    Args:
        config: Configuration dictionary with clinical thresholds
        z_score: Z-score value for the chromosome
        chrom: Chromosome identifier (e.g., "21", "18", "13")
        test_number: 1 for first test, 2 for second test, 3 for third test

    Returns:
        Tuple of (result_text, risk_level)
    """
    if pd.isna(z_score): return "Invalid Data", "UNKNOWN"

    # Get test-specific thresholds if available, otherwise use defaults
    test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('TRISOMY', {})

    # First test logic
    if test_number == 1:
        t = test_thresholds.get(1, {'low': 2.58, 'ambiguous': 6.0})
        if z_score < t['low']:
            return "Low Risk", "LOW"
        if z_score < t['ambiguous']:
            return f"High Risk (Z:{z_score:.2f}) -> Re-library", "HIGH"
        return "POSITIVE", "POSITIVE"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"
        t = test_thresholds.get(test_number, {'low': 2.58, 'medium': 3.0, 'high': 4.0, 'positive': 6.0})

        if z_score < t['low']:
            return f"Negative ({test_label})", "LOW"
        elif z_score < t.get('medium', 3.0):
            return f"High Risk (Z:{z_score:.2f}) -> Resample for verification", "HIGH"
        elif z_score < t.get('high', 4.0):
            return f"High Risk (Z:{z_score:.2f}) -> Resample for verification", "HIGH"
        elif z_score < t['positive']:
            return f"High Risk (Z:{z_score:.2f}) -> Report Positive if consistent", "HIGH"
        else:
            return f"POSITIVE ({test_label})", "POSITIVE"

def analyze_sca(config: Dict, sca_type: str, z_xx: float, z_xy: float, cff: float, test_number: int = 1) -> Tuple[str, str]:
    """Enhanced SCA (Sex Chromosomal Aneuploidies) analysis.

    Args:
        config: Configuration dictionary with clinical thresholds
        sca_type: Type of SCA detected (XX, XY, XO, XXX, XXY, XYY, XXX+XY, XO+XY)
        z_xx: Z-score for XX
        z_xy: Z-score for XY
        cff: Cell-free fetal DNA concentration percentage
        test_number: 1 for first test, 2 for second test, 3 for third test

    Returns:
        Tuple of (result_text, risk_level)

    SCA decision logic:
    First test:
    - XX/XY: Report Negative
    - XYY/XXY/XXX+XY: Report Positive
    - XO: If Z-score(XX) >= 4.5, report XO; else re-library
    - XXX: If Z-score(XX) >= 4.5, report XXX; else re-library
    - XO+XY: If Z-score(XY) >= 6, report XO+XY; else re-library

    Second/Third test:
    - Low CFF (<3.5%): Do not refer to first result
    - When CFF >= 3.5%: More stringent interpretation
    """
    min_cff = config['QC_THRESHOLDS']['MIN_CFF']

    # Get test-specific thresholds if available, otherwise use defaults
    test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('SCA', {})
    t = test_thresholds.get(test_number, {'xx_threshold': 4.5, 'xy_threshold': 6.0})
    threshold = t['xx_threshold']
    xy_threshold = t['xy_threshold']

    # First test logic
    if test_number == 1:
        if cff < min_cff:
            return "INVALID (Cff < 3.5%) -> Resample", "INVALID"

        if sca_type == "XX": return "Negative (Female)", "LOW"
        if sca_type == "XY": return "Negative (Male)", "LOW"

        if sca_type == "XO":
            return ("POSITIVE (Turner XO)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XO -> Re-library", "HIGH")

        if sca_type == "XXX":
            return ("POSITIVE (Triple X)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XXX -> Re-library", "HIGH")

        if sca_type == "XXX+XY":
            return "POSITIVE (XXX+XY)", "POSITIVE"

        if sca_type == "XO+XY":
            return ("POSITIVE (XO+XY)", "POSITIVE") if z_xy >= xy_threshold else ("Ambiguous XO+XY -> Re-library", "HIGH")

        if sca_type in ["XXY", "XYY"]:
            return f"POSITIVE ({sca_type})", "POSITIVE"

        return "Ambiguous SCA -> Re-library", "HIGH"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"

        if cff < min_cff:
            return f"INVALID (Cff < 3.5%) -> Do not refer to previous result", "INVALID"

        # Normal karyotypes
        if sca_type == "XX": return f"Negative (Female, {test_label})", "LOW"
        if sca_type == "XY": return f"Negative (Male, {test_label})", "LOW"

        # Always positive SCAs
        if sca_type in ["XYY", "XXY", "XXX+XY"]:
            return f"POSITIVE ({sca_type}, {test_label})", "POSITIVE"

        # XO: Needs verification based on Z-score consistency
        if sca_type == "XO":
            if z_xx >= threshold:
                return f"POSITIVE (Turner XO, {test_label})", "POSITIVE"
            else:
                return f"XO (Z:{z_xx:.2f}) -> Resample for verification", "HIGH"

        # XXX: Needs verification based on Z-score consistency
        if sca_type == "XXX":
            if z_xx >= threshold:
                return f"POSITIVE (Triple X, {test_label})", "POSITIVE"
            else:
                return f"XXX (Z:{z_xx:.2f}) -> Resample for verification", "HIGH"

        # XO+XY: Needs verification based on Z-score consistency
        if sca_type == "XO+XY":
            if z_xy >= xy_threshold:
                return f"POSITIVE (XO+XY, {test_label})", "POSITIVE"
            else:
                return f"XO+XY (Z:{z_xy:.2f}) -> Resample for verification", "HIGH"

        return f"Ambiguous SCA -> Resample for verification", "HIGH"

def analyze_rat(config: Dict, chrom: int, z_score: float, test_number: int = 1) -> Tuple[str, str]:
    """RAT (Rare Autosomal Trisomy) analysis.

    Args:
        config: Configuration dictionary with clinical thresholds
        chrom: Chromosome number
        z_score: Z-score value
        test_number: 1 for first test, 2 for second test, 3 for third test

    Returns:
        Tuple of (result_text, risk_level)
    """
    # Get test-specific thresholds if available, otherwise use defaults
    test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('RAT', {})

    # First test logic
    if test_number == 1:
        t = test_thresholds.get(1, {'low': 4.5, 'positive': 8.0})
        if z_score >= t['positive']:
            return "POSITIVE", "POSITIVE"
        if z_score > t['low']:
            return "Ambiguous -> Re-library", "HIGH"
        return "Low Risk", "LOW"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"
        t = test_thresholds.get(test_number, {'low': 4.5, 'positive': 8.0})

        if z_score <= t['low']:
            return f"Negative ({test_label})", "LOW"
        elif z_score < t['positive']:
            return f"High Risk (Z:{z_score:.2f}) -> Resample for verification", "HIGH"
        else:
            return f"POSITIVE ({test_label})", "POSITIVE"

def analyze_cnv(size: float, ratio: float, test_number: int = 1, config: Dict = None) -> Tuple[str, float, str]:
    """CNV (Copy Number Variation) analysis.

    Args:
        size: Size of CNV in megabases (Mb)
        ratio: Abnormal ratio percentage
        test_number: 1 for first test, 2 for second test, 3 for third test
        config: Configuration dictionary (optional, for test-specific thresholds)

    Returns:
        Tuple of (result_text, threshold, risk_level)
    """
    # Get test-specific thresholds if available
    if config:
        test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('CNV', {})
        cnv_thresholds = test_thresholds.get(test_number, {
            '>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0
        })
    else:
        cnv_thresholds = {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0}

    # Determine threshold based on CNV size
    if size >= 10:
        threshold = cnv_thresholds.get('>= 10', 6.0)
    elif size > 7:
        threshold = cnv_thresholds.get('> 7', 8.0)
    elif size > 3.5:
        threshold = cnv_thresholds.get('> 3.5', 10.0)
    else:
        threshold = cnv_thresholds.get('<= 3.5', 12.0)

    # First test logic
    if test_number == 1:
        if ratio >= threshold:
            return f"High Risk -> Re-library", threshold, "HIGH"
        return "Low Risk", threshold, "LOW"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"
        if ratio >= threshold:
            return f"POSITIVE (Ratio:{ratio:.1f}%, {test_label})", threshold, "POSITIVE"
        else:
            return f"High Risk (Ratio:{ratio:.1f}%) -> Resample for verification", threshold, "HIGH"


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

def validate_mrn(mrn: str, allow_alphanumeric: bool = False) -> Tuple[bool, str]:
    """Validate MRN format for clinical use.

    Args:
        mrn: The MRN string to validate
        allow_alphanumeric: If True, allows letters, digits, hyphens, and underscores
                          If False (default), only allows digits (strict numerical mode)

    Returns:
        (is_valid, error_message)

    Note: For clinical systems, numerical MRNs are recommended to avoid confusion.
          Leading zeros are preserved (e.g., "00123" is different from "123").
    """
    if not mrn or not mrn.strip():
        return False, "MRN cannot be empty"

    mrn = mrn.strip()

    if len(mrn) > 50:
        return False, "MRN too long (max 50 characters)"

    if allow_alphanumeric:
        # Allow alphanumeric MRNs for backward compatibility
        # Format: letters, digits, hyphens, underscores only
        if not all(c.isalnum() or c in '-_' for c in mrn):
            return False, "MRN can only contain letters, digits, hyphens, and underscores"
    else:
        # Strict numerical mode (default for clinical consistency)
        if not mrn.isdigit():
            return False, "MRN must be numerical (digits only). Use 'Allow Alphanumeric MRNs' in Settings if needed."

    return True, ""

def check_duplicate_patient(mrn: str) -> Tuple[bool, Optional[Dict]]:
    """Check if a patient with this MRN already exists. Returns (exists, patient_info).
    With simplified system: only active patients exist (no soft deletes)."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.full_name, p.mrn_id, p.age, p.weeks, COUNT(r.id) as result_count
                FROM patients p
                LEFT JOIN results r ON r.patient_id = p.id
                WHERE p.mrn_id = ?
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

def delete_patient(patient_id: int, hard_delete: bool = True) -> Tuple[bool, str]:
    """Delete a patient and all associated results.
    Patient ID is never reused (ghost patient - ID stays occupied).

    Args:
        patient_id: The database ID of the patient
        hard_delete: Kept for backwards compatibility but always does hard delete

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

            # Count results for audit log
            c.execute("SELECT COUNT(*) FROM results WHERE patient_id = ?", (patient_id,))
            result_count = c.fetchone()[0]

            # Delete all associated results first
            c.execute("DELETE FROM results WHERE patient_id = ?", (patient_id,))

            # Delete the patient (ID will never be reused - becomes ghost patient)
            c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))

            conn.commit()
            log_audit("DELETE_PATIENT",
                     f"Deleted patient {mrn} ({name}) and {result_count} results. ID {patient_id} now ghost (never reused).",
                     st.session_state.user['id'] if 'user' in st.session_state else None)
            return True, f"Deleted patient {mrn} and {result_count} associated results"

    except Exception as e:
        return False, f"Delete failed: {str(e)}"

# Removed restore_patient and cleanup_orphaned_patients functions
# With simplified system: IDs are never reused, no soft delete, no orphan cleanup needed

# Removed get_next_patient_id - now using SQLite AUTOINCREMENT for chronological IDs that are never reused

def save_result(patient: Dict, results: Dict, clinical: Dict, full_z: Optional[Dict] = None,
                qc_metrics: Optional[Dict] = None, allow_duplicate: bool = True, test_number: int = 1) -> Tuple[int, str]:
    """Save with audit logging and transaction support. Returns (result_id, message).

    Args:
        patient: Patient information dictionary
        results: Test results dictionary
        clinical: Clinical interpretation dictionary
        full_z: Full Z-scores dictionary (optional)
        qc_metrics: QC metrics dictionary (optional)
        allow_duplicate: Allow duplicate patients (default True)
        test_number: Test number (1 for first test, 2 for second test, default 1)

    Returns:
        Tuple of (result_id, message)
    """
    conn = None
    try:
        # Validate MRN format based on config
        config = load_config()
        allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
        is_valid, error_msg = validate_mrn(patient['id'], allow_alphanumeric=allow_alphanum)
        if not is_valid:
            return 0, f"Invalid MRN: {error_msg}"

        conn = get_db_connection()
        c = conn.cursor()

        # Start transaction
        c.execute("BEGIN TRANSACTION")

        # Check for existing patient
        c.execute("""
            SELECT id, full_name FROM patients
            WHERE mrn_id = ?
        """, (patient['id'],))
        existing = c.fetchone()

        if existing:
            patient_db_id = existing[0]
            existing_name = existing[1]
            if not allow_duplicate:
                conn.rollback()
                return 0, f"Patient with MRN '{patient['id']}' already exists in registry as '{existing_name}'"
        else:
            # Create new patient - let SQLite AUTOINCREMENT handle ID assignment (never reused)
            c.execute("""
                INSERT INTO patients
                (mrn_id, full_name, age, weight_kg, height_cm, bmi, weeks, clinical_notes, created_at, created_by, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                patient['id'], patient['name'], patient['age'], patient['weight'],
                patient['height'], patient['bmi'], patient['weeks'], patient['notes'],
                datetime.now().isoformat(), st.session_state.user['id']
            ))
            patient_db_id = c.lastrowid

        # Prepare QC metrics JSON
        qc_metrics_json = json.dumps(qc_metrics) if qc_metrics else "{}"

        c.execute("""
            INSERT INTO results
            (patient_id, panel_type, qc_status, qc_details, qc_advice, qc_metrics_json,
             t21_res, t18_res, t13_res, sca_res,
             cnv_json, rat_json, full_z_json, final_summary, created_at, created_by, test_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            patient_db_id, results['panel'], results['qc_status'],
            str(results['qc_msgs']), results['qc_advice'], qc_metrics_json,
            clinical['t21'], clinical['t18'], clinical['t13'], clinical['sca'],
            json.dumps(clinical['cnv_list']), json.dumps(clinical['rat_list']),
            json.dumps(full_z) if full_z else "{}", clinical['final'],
            datetime.now().isoformat(), st.session_state.user['id'], test_number
        ))
        result_id = c.lastrowid

        # Commit transaction
        conn.commit()

        log_audit("SAVE_RESULT", f"Created result {result_id} for patient {patient['id']} (Test #{test_number})", st.session_state.user['id'])
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
                WHERE id = ?
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
                       cnv_json, rat_json, full_z_json, final_summary, created_at, test_number
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
                    'created_at': row[15],
                    'test_number': row[16] if len(row) > 16 and row[16] is not None else 1
                }
    except Exception:
        pass
    return None

def get_result_for_card(result_id: int) -> Optional[Dict]:
    """Get combined result and patient data for card display."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT r.id, r.created_at, p.full_name, p.mrn_id, p.age, p.weeks,
                       r.panel_type, r.qc_status, r.qc_override, r.final_summary,
                       r.full_z_json, r.t21_res, r.t18_res, r.t13_res, r.sca_res
                FROM results r
                JOIN patients p ON p.id = r.patient_id
                WHERE r.id = ?
            """, (result_id,))
            row = c.fetchone()
            if row:
                return {
                    'id': row[0],
                    'created_at': row[1],
                    'full_name': row[2],
                    'mrn_id': row[3],
                    'age': row[4],
                    'weeks': row[5],
                    'panel_type': row[6],
                    'qc_status': row[7],
                    'qc_override': row[8],
                    'final_summary': row[9],
                    'full_z_json': row[10],
                    't21_res': row[11],
                    't18_res': row[12],
                    't13_res': row[13],
                    'sca_res': row[14]
                }
    except Exception:
        pass
    return None

def get_patient_details(patient_id: int) -> Optional[Dict]:
    """Get full patient details including all results."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT p.id, p.mrn_id, p.full_name, p.age, p.weight_kg, p.height_cm,
                       p.bmi, p.weeks, p.clinical_notes, p.created_at
                FROM patients p
                WHERE p.id = ?
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
                # Common report format: "High Risk (Z:5.00)" or "(Z: 5.00)"
                rf'(?:Trisomy\s*)?{chrom}[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
                rf'T{chrom}[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
                # Format: "Z-score: 9.00" near trisomy reference
                rf'(?:Trisomy\s*)?{chrom}\b.*?Z[-\s]?score[:\s]*(-?\d+\.?\d*)',
                rf'T{chrom}\b.*?Z[-\s]?score[:\s]*(-?\d+\.?\d*)',
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
            # Common report format: "Z-XX: 6.00" or "Z-XX 6.00"
            r'Z[-\s]?XX\b[:\s]*(-?\d+\.?\d*)',
            r'ZXX\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
            # Format with label: "XX Z-score: 6.00"
            r'XX\s+Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
            # Sex chromosome section patterns
            r'(?:Sex\s+)?(?:Chromosome\s+)?XX[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            r'X\s+Chromosome[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            # Table format: XX | 6.00 or XX, 6.00
            r'\bXX\b\s*[|,:\s]\s*(-?\d+\.?\d*)(?:\s|$|[|,])',
        ]
        z_val = extract_z_score(z_xx_patterns, text)
        if z_val is not None:
            data['z_scores']['XX'] = z_val

        z_xy_patterns = [
            # Common report format: "Z-XY: 0.00" or "Z-XY 0.00"
            r'Z[-\s]?XY\b[:\s]*(-?\d+\.?\d*)',
            r'ZXY\b[:\s]*[=:]\s*(-?\d+\.?\d*)',
            # Format with label: "XY Z-score: 0.00"
            r'XY\s+Z[-\s]?(?:Score)?[:\s]+(-?\d+\.?\d*)',
            # Sex chromosome section patterns
            r'(?:Sex\s+)?(?:Chromosome\s+)?XY[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            r'Y\s+Chromosome[:\s]+[^Z]*?Z[:\s]+(-?\d+\.?\d*)',
            # Table format: XY | 0.00 or XY, 0.00
            r'\bXY\b\s*[|,:\s]\s*(-?\d+\.?\d*)(?:\s|$|[|,])',
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

        # Extract clinical notes - more restrictive to avoid capturing unrelated sections
        notes_patterns = [
            r'(?:Clinical\s+)?Notes?[:\s]+(.+?)(?:OBSERVATION|RESULT|Disclaimer|Limitation|Panel|Test\s+Type|QC|Quality|Summary|Interpretation|$)',
            r'Comments?[:\s]+(.+?)(?:OBSERVATION|RESULT|Disclaimer|$)',
            r'(?:Additional\s+)?Remarks[:\s]+(.+?)(?:OBSERVATION|RESULT|$)',
        ]
        for pattern in notes_patterns:
            notes_match = re.search(pattern, text, re.IGNORECASE)
            if notes_match:
                notes = notes_match.group(1).strip()
                # Clean up notes - remove section headers and markers that got captured
                notes = re.sub(r'\s+', ' ', notes)
                # Remove common unwanted phrases that indicate section boundaries
                unwanted_phrases = [
                    r'&\s*OBSERVATIONS?',
                    r'Nuchal\s+(?:Clarity|Translucency)',
                    r'Key\s+clinical\s+markers:?',
                    r'Clinical\s+markers:?',
                    r'PATIENT\s+INFORMATION',
                    r'SAMPLE\s+INFORMATION',
                    r'TEST\s+RESULTS?',
                ]
                for phrase in unwanted_phrases:
                    notes = re.sub(phrase, '', notes, flags=re.IGNORECASE)
                # Clean up any resulting double spaces or leading/trailing punctuation
                notes = re.sub(r'\s+', ' ', notes).strip()
                notes = re.sub(r'^[&\s,;:]+|[&\s,;:]+$', '', notes).strip()
                if len(notes) > 5 and not notes.upper().startswith(('OBSERVATION', 'RESULT', 'QC')):
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
                       ov_user.full_name as qc_override_by_name,
                       r.test_number
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

        # Get test number (default to 1 if not present)
        test_num = row.get('test_number', 1)
        if test_num == 1:
            test_num_label = t('first_test')
        elif test_num == 2:
            test_num_label = t('second_test')
        else:
            test_num_label = t('third_test')

        meta_data = [
            [t('report_id'), str(row['id']), t('report_date'), report_date],
            [t('panel_type'), row['panel_type'], t('report_time'), report_time],
            [t('test_number'), test_num_label, '', ''],
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

        # Use Paragraph for QC status to enable text wrapping in the cell
        qc_status_para = Paragraph(f"<b>{qc_display_status}</b>", cell_style)

        for i, (param, val, ref, status) in enumerate(qc_items):
            if i == 0:
                qc_rows.append([qc_status_para, param, val, ref, status])
            else:
                qc_rows.append(['', param, val, ref, status])

        qc_table_data = qc_header + qc_rows
        qc_table = Table(qc_table_data, colWidths=[1.1*inch, 1.4*inch, 0.9*inch, 1.4*inch, 1.0*inch])

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

# ==================== PATIENT INFO CARD RENDERING ====================

def render_patient_info_card(record: Dict, show_full_details: bool = False, card_key: str = ""):
    """Render a styled patient information card.

    Args:
        record: Dictionary containing patient/result data
        show_full_details: Whether to show all details or a compact view
        card_key: Unique key for interactive elements
    """
    # Helper function to safely escape HTML
    def esc(val):
        return html_module.escape(str(val)) if val is not None else 'N/A'

    # Determine color based on final summary
    summary = str(record.get('final_summary', '')).upper()
    qc_status = str(record.get('qc_status', 'PASS')).upper()

    if 'POSITIVE' in summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_emoji = "🔴"
    elif 'FAIL' in qc_status or 'INVALID' in summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_emoji = "⚠️"
    elif 'WARNING' in qc_status or 'HIGH RISK' in summary:
        border_color = "#F39C12"
        bg_color = "#FEF9E7"
        status_emoji = "🟠"
    else:
        border_color = "#27AE60"
        bg_color = "#EAFAF1"
        status_emoji = "🟢"

    # Extract z-scores from JSON
    full_z = record.get('full_z_json', '{}')
    if isinstance(full_z, str):
        try:
            z_data = json.loads(full_z) if full_z and full_z != '{}' else {}
        except:
            z_data = {}
    else:
        z_data = full_z or {}

    z21 = z_data.get('21', z_data.get(21, 'N/A'))
    z18 = z_data.get('18', z_data.get(18, 'N/A'))
    z13 = z_data.get('13', z_data.get(13, 'N/A'))

    # Format z-scores
    z21_str = f"{float(z21):.2f}" if z21 != 'N/A' and z21 is not None else 'N/A'
    z18_str = f"{float(z18):.2f}" if z18 != 'N/A' and z18 is not None else 'N/A'
    z13_str = f"{float(z13):.2f}" if z13 != 'N/A' and z13 is not None else 'N/A'

    # Get reportable status
    t21_res = record.get('t21_res', '')
    qc_override = bool(record.get('qc_override', 0))
    effective_qc = 'PASS' if qc_override else qc_status
    reportable, reportable_reason = get_reportable_status(str(t21_res), effective_qc, qc_override)

    # Pre-compute values for cleaner HTML
    full_name = esc(record.get('full_name', 'Unknown'))
    record_id = esc(record.get('id', 'N/A'))
    created_at = record.get('created_at', 'N/A')
    created_at_str = esc(created_at[:16]) if created_at and len(str(created_at)) >= 16 else esc(created_at)
    mrn_id = esc(record.get('mrn_id', 'N/A'))
    panel_type = esc(record.get('panel_type', 'N/A'))
    t21_res_str = esc(record.get('t21_res', 'N/A'))
    t18_res_str = esc(record.get('t18_res', 'N/A'))
    t13_res_str = esc(record.get('t13_res', 'N/A'))
    sca_res_str = esc(record.get('sca_res', 'N/A'))
    final_summary_str = esc(record.get('final_summary', 'N/A'))

    # Compute colors
    qc_color = '#27AE60' if effective_qc == 'PASS' else '#E74C3C' if effective_qc == 'FAIL' else '#F39C12'
    qc_display = effective_qc + ('*' if qc_override else '')
    reportable_color = '#27AE60' if reportable == 'Yes' else '#E74C3C'
    reportable_display = reportable + (f' ({reportable_reason})' if reportable == 'No' else '')
    summary_bg = '#27AE60' if 'NEGATIVE' in summary else '#E74C3C' if 'POSITIVE' in summary or 'INVALID' in summary else '#F39C12'

    # Build HTML card
    card_html = f'''
    <div style="border: 2px solid {border_color}; border-radius: 12px; padding: 16px; margin: 10px 0; background-color: {bg_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
                <span style="font-size: 1.3em; font-weight: bold; color: #2C3E50;">{status_emoji} {full_name}</span>
                <span style="background: #3498DB; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; margin-left: 10px;">ID #{record_id}</span>
            </div>
            <div style="text-align: right; color: #7F8C8D; font-size: 0.9em;">{created_at_str}</div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">MRN</div>
                <div style="font-weight: 600; color: #2C3E50;">{mrn_id}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">Panel</div>
                <div style="font-weight: 600; color: #2C3E50;">{panel_type}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">QC Status</div>
                <div style="font-weight: 600; color: {qc_color};">{qc_display}</div>
            </div>
        </div>
        <div style="background: white; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
            <div style="font-size: 0.85em; color: #7F8C8D; margin-bottom: 8px;">Trisomy Results</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                <div style="text-align: center;">
                    <div style="font-size: 0.75em; color: #95A5A6;">T21</div>
                    <div style="font-weight: 600; color: #2C3E50;">{t21_res_str}</div>
                    <div style="font-size: 0.75em; color: #7F8C8D;">Z: {z21_str}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 0.75em; color: #95A5A6;">T18</div>
                    <div style="font-weight: 600; color: #2C3E50;">{t18_res_str}</div>
                    <div style="font-size: 0.75em; color: #7F8C8D;">Z: {z18_str}</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 0.75em; color: #95A5A6;">T13</div>
                    <div style="font-weight: 600; color: #2C3E50;">{t13_res_str}</div>
                    <div style="font-size: 0.75em; color: #7F8C8D;">Z: {z13_str}</div>
                </div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="background: white; padding: 10px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">SCA Result</div>
                <div style="font-weight: 600; color: #2C3E50;">{sca_res_str}</div>
            </div>
            <div style="background: white; padding: 10px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">Reportable</div>
                <div style="font-weight: 600; color: {reportable_color};">{reportable_display}</div>
            </div>
        </div>
        <div style="margin-top: 12px; padding: 10px; background: {summary_bg}; border-radius: 6px; text-align: center;">
            <span style="color: white; font-weight: 700; font-size: 1.1em;">{final_summary_str}</span>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)


def render_test_result_card(result: Dict, show_actions: bool = False, card_key: str = ""):
    """Render a styled test result card for the patient details section.

    Args:
        result: Dictionary containing test result data
        show_actions: Whether to show action buttons
        card_key: Unique key for interactive elements
    """
    # Helper function to safely escape HTML
    def esc(val):
        return html_module.escape(str(val)) if val is not None else 'N/A'

    # Determine color based on status
    qc_status = str(result.get('qc_status', 'PASS')).upper()
    qc_override = bool(result.get('qc_override', 0))
    final_summary = str(result.get('final_summary', '')).upper()

    effective_qc = 'PASS' if qc_override else qc_status

    if 'POSITIVE' in final_summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_icon = "🔴"
    elif 'FAIL' in effective_qc or 'INVALID' in final_summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_icon = "⚠️"
    elif 'WARNING' in effective_qc or 'HIGH RISK' in final_summary:
        border_color = "#F39C12"
        bg_color = "#FEF9E7"
        status_icon = "🟠"
    else:
        border_color = "#27AE60"
        bg_color = "#EAFAF1"
        status_icon = "🟢"

    # Pre-compute values
    created_at = result.get('created_at', 'N/A')
    if isinstance(created_at, str) and len(created_at) > 16:
        created_at = created_at[:16]
    created_at_str = esc(created_at)

    result_id = esc(result.get('id', 'N/A'))
    panel_type = esc(result.get('panel_type', 'N/A'))
    test_number = result.get('test_number', 1)
    test_label = f"{'1st' if test_number == 1 else '2nd' if test_number == 2 else '3rd'} Test"
    t21_res = esc(result.get('t21_res', 'N/A'))
    t18_res = esc(result.get('t18_res', 'N/A'))
    t13_res = esc(result.get('t13_res', 'N/A'))
    sca_res = esc(result.get('sca_res', 'N/A'))
    final_summary_str = esc(result.get('final_summary', 'N/A'))

    qc_color = '#27AE60' if effective_qc == 'PASS' else '#E74C3C' if effective_qc == 'FAIL' else '#F39C12'
    qc_display = effective_qc + ('*' if qc_override else '')
    summary_bg = '#27AE60' if 'NEGATIVE' in final_summary else '#E74C3C' if 'POSITIVE' in final_summary or 'INVALID' in final_summary else '#F39C12'
    test_color = '#3498DB' if test_number == 1 else '#E67E22' if test_number == 2 else '#E74C3C'

    card_html = f'''
    <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 14px; margin: 8px 0; background-color: {bg_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div>
                <span style="font-weight: bold; font-size: 1.1em;">{status_icon} Result #{result_id}</span>
                <span style="background: #9B59B6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">{panel_type}</span>
                <span style="background: {test_color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 4px;">{test_label}</span>
            </div>
            <div style="color: #7F8C8D; font-size: 0.85em;">{created_at_str}</div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 10px;">
            <div style="background: white; padding: 6px; border-radius: 4px; text-align: center;">
                <div style="font-size: 0.7em; color: #95A5A6;">T21</div>
                <div style="font-size: 0.9em; font-weight: 600;">{t21_res}</div>
            </div>
            <div style="background: white; padding: 6px; border-radius: 4px; text-align: center;">
                <div style="font-size: 0.7em; color: #95A5A6;">T18</div>
                <div style="font-size: 0.9em; font-weight: 600;">{t18_res}</div>
            </div>
            <div style="background: white; padding: 6px; border-radius: 4px; text-align: center;">
                <div style="font-size: 0.7em; color: #95A5A6;">T13</div>
                <div style="font-size: 0.9em; font-weight: 600;">{t13_res}</div>
            </div>
            <div style="background: white; padding: 6px; border-radius: 4px; text-align: center;">
                <div style="font-size: 0.7em; color: #95A5A6;">SCA</div>
                <div style="font-size: 0.9em; font-weight: 600;">{sca_res}</div>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="background: white; padding: 6px 12px; border-radius: 4px;">
                <span style="font-size: 0.8em; color: #7F8C8D;">QC: </span>
                <span style="font-weight: 600; color: {qc_color};">{qc_display}</span>
            </div>
            <div style="padding: 6px 12px; border-radius: 4px; background: {summary_bg}; color: white; font-weight: 600;">{final_summary_str}</div>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)


# ==================== ANALYTICS ====================

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_analytics_data() -> Dict:
    """Fetch comprehensive analytics data with proper multi-anomaly handling."""
    try:
        with get_db_connection() as conn:
            # Fetch all results for detailed analysis
            all_results = pd.read_sql("""
                SELECT r.id, r.created_at, r.panel_type, r.qc_status, r.qc_override,
                       r.t21_res, r.t18_res, r.t13_res, r.sca_res, r.final_summary,
                       r.cnv_json, r.rat_json, r.full_z_json
                FROM results r
            """, conn)

            if all_results.empty:
                return get_empty_analytics()

            total = len(all_results)

            # QC stats (accounting for overrides)
            all_results['effective_qc'] = all_results.apply(
                lambda r: 'PASS' if r.get('qc_override') else r['qc_status'], axis=1
            )
            qc_stats = all_results['effective_qc'].value_counts().reset_index()
            qc_stats.columns = ['qc_status', 'count']

            # Ensure all QC statuses are present
            for status in ['PASS', 'FAIL', 'WARNING']:
                if status not in qc_stats['qc_status'].values:
                    qc_stats = pd.concat([qc_stats, pd.DataFrame({'qc_status': [status], 'count': [0]})])

            # Analyze each sample for anomalies
            def analyze_sample_anomalies(row):
                anomalies = []
                t21 = str(row.get('t21_res', '')).upper()
                t18 = str(row.get('t18_res', '')).upper()
                t13 = str(row.get('t13_res', '')).upper()
                sca = str(row.get('sca_res', '')).upper()

                if 'POSITIVE' in t21 or 'HIGH' in t21:
                    anomalies.append('T21')
                if 'POSITIVE' in t18 or 'HIGH' in t18:
                    anomalies.append('T18')
                if 'POSITIVE' in t13 or 'HIGH' in t13:
                    anomalies.append('T13')
                # SCA anomalies (exclude normal XX/XY)
                if sca and 'POSITIVE' in sca or any(x in sca for x in ['XO', 'XXX', 'XXY', 'XYY', 'MOSAIC']):
                    anomalies.append('SCA')

                # Check for CNV findings
                cnv_json = row.get('cnv_json', '[]')
                if cnv_json and cnv_json != '[]':
                    try:
                        cnv_list = json.loads(cnv_json) if isinstance(cnv_json, str) else cnv_json
                        if cnv_list and len(cnv_list) > 0:
                            anomalies.append('CNV')
                    except:
                        pass

                # Check for RAT findings
                rat_json = row.get('rat_json', '[]')
                if rat_json and rat_json != '[]':
                    try:
                        rat_list = json.loads(rat_json) if isinstance(rat_json, str) else rat_json
                        if rat_list and len(rat_list) > 0:
                            anomalies.append('RAT')
                    except:
                        pass

                return anomalies

            all_results['anomalies'] = all_results.apply(analyze_sample_anomalies, axis=1)
            all_results['anomaly_count'] = all_results['anomalies'].apply(len)

            # Multi-anomaly breakdown
            anomaly_count_dist = all_results['anomaly_count'].value_counts().reset_index()
            anomaly_count_dist.columns = ['anomaly_count', 'samples']
            anomaly_count_dist = anomaly_count_dist.sort_values('anomaly_count')

            # Individual anomaly counts (samples can have multiple)
            anomaly_types = {'T21': 0, 'T18': 0, 'T13': 0, 'SCA': 0, 'CNV': 0, 'RAT': 0}
            for anomaly_list in all_results['anomalies']:
                for anomaly in anomaly_list:
                    if anomaly in anomaly_types:
                        anomaly_types[anomaly] += 1

            anomaly_breakdown = pd.DataFrame({
                'Anomaly Type': list(anomaly_types.keys()),
                'Count': list(anomaly_types.values())
            })

            # SCA type breakdown
            def extract_sca_type(sca_res):
                sca = str(sca_res).upper()
                if 'XO+XY' in sca or 'XXX+XY' in sca:
                    return 'Mosaic'
                elif 'XO' in sca or 'TURNER' in sca:
                    return 'XO (Turner)'
                elif 'XXY' in sca or 'KLINEFELTER' in sca:
                    return 'XXY (Klinefelter)'
                elif 'XXX' in sca:
                    return 'XXX (Triple X)'
                elif 'XYY' in sca:
                    return 'XYY (Jacob)'
                elif 'FEMALE' in sca or 'XX' in sca:
                    return 'XX (Female)'
                elif 'MALE' in sca or 'XY' in sca:
                    return 'XY (Male)'
                else:
                    return 'Unknown'

            all_results['sca_type'] = all_results['sca_res'].apply(extract_sca_type)
            sca_breakdown = all_results['sca_type'].value_counts().reset_index()
            sca_breakdown.columns = ['SCA Type', 'Count']

            # Outcomes
            outcomes = all_results['final_summary'].value_counts().reset_index()
            outcomes.columns = ['final_summary', 'count']

            # Recent activity (30 days)
            all_results['date'] = pd.to_datetime(all_results['created_at']).dt.date
            thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
            recent_results = all_results[all_results['date'] >= thirty_days_ago]
            recent = recent_results.groupby('date').size().reset_index(name='count')
            recent['date'] = pd.to_datetime(recent['date'])

            # Panel distribution
            panels = all_results['panel_type'].value_counts().reset_index()
            panels.columns = ['panel_type', 'count']

            # Multi-anomaly samples detail
            multi_anomaly_samples = all_results[all_results['anomaly_count'] > 1][
                ['id', 'anomalies', 'anomaly_count', 'final_summary']
            ].copy()
            multi_anomaly_samples['anomalies'] = multi_anomaly_samples['anomalies'].apply(lambda x: ', '.join(x))

            # Trisomy stats for backward compatibility
            trisomies = pd.DataFrame({
                't21': [anomaly_types['T21']],
                't18': [anomaly_types['T18']],
                't13': [anomaly_types['T13']]
            })

            return {
                'total': total,
                'qc_stats': qc_stats,
                'outcomes': outcomes,
                'trisomies': trisomies,
                'recent': recent,
                'panels': panels,
                'anomaly_breakdown': anomaly_breakdown,
                'anomaly_count_dist': anomaly_count_dist,
                'sca_breakdown': sca_breakdown,
                'multi_anomaly_samples': multi_anomaly_samples,
                'samples_with_anomalies': len(all_results[all_results['anomaly_count'] > 0]),
                'multi_anomaly_count': len(all_results[all_results['anomaly_count'] > 1])
            }
    except Exception as e:
        st.error(f"Error loading analytics: {e}")
        return get_empty_analytics()


def get_empty_analytics() -> Dict:
    """Return empty analytics data structure."""
    return {
        'total': 0,
        'qc_stats': pd.DataFrame({'qc_status': ['PASS', 'FAIL', 'WARNING'], 'count': [0, 0, 0]}),
        'outcomes': pd.DataFrame({'final_summary': [], 'count': []}),
        'trisomies': pd.DataFrame({'t21': [0], 't18': [0], 't13': [0]}),
        'recent': pd.DataFrame({'date': [], 'count': []}),
        'panels': pd.DataFrame({'panel_type': [], 'count': []}),
        'anomaly_breakdown': pd.DataFrame({'Anomaly Type': [], 'Count': []}),
        'anomaly_count_dist': pd.DataFrame({'anomaly_count': [], 'samples': []}),
        'sca_breakdown': pd.DataFrame({'SCA Type': [], 'Count': []}),
        'multi_anomaly_samples': pd.DataFrame({'id': [], 'anomalies': [], 'anomaly_count': [], 'final_summary': []}),
        'samples_with_anomalies': 0,
        'multi_anomaly_count': 0
    }


def render_analytics_dashboard():
    """Render comprehensive analytics dashboard with multi-anomaly support."""
    st.header("📊 Analytics Dashboard")

    data = get_analytics_data()

    # Top-level metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📋 Total Tests", data['total'])
    with col2:
        qc_pass = data['qc_stats'][data['qc_stats']['qc_status'] == 'PASS']['count'].sum()
        pass_rate = (qc_pass / data['total'] * 100) if data['total'] > 0 else 0
        st.metric("✅ QC Pass Rate", f"{pass_rate:.1f}%")
    with col3:
        st.metric("🔬 Samples w/ Anomalies", data['samples_with_anomalies'])
    with col4:
        st.metric("⚠️ Multi-Anomaly", data['multi_anomaly_count'])
    with col5:
        qc_fail = data['qc_stats'][data['qc_stats']['qc_status'] == 'FAIL']['count'].sum()
        st.metric("❌ QC Fail", int(qc_fail))

    st.divider()

    # Row 1: QC and Outcomes
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🔍 QC Status Distribution")
        if not data['qc_stats'].empty and data['qc_stats']['count'].sum() > 0:
            fig = px.pie(
                data['qc_stats'],
                values='count',
                names='qc_status',
                color='qc_status',
                color_discrete_map={'PASS': '#27AE60', 'FAIL': '#E74C3C', 'WARNING': '#F39C12'},
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+value')
            fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No QC data available")

    with c2:
        st.subheader("📊 Test Outcomes")
        if not data['outcomes'].empty:
            # Color mapping for outcomes
            outcome_colors = {
                'NEGATIVE': '#27AE60',
                'POSITIVE DETECTED': '#E74C3C',
                'HIGH RISK (SEE ADVICE)': '#F39C12',
                'INVALID (QC FAIL)': '#95A5A6'
            }
            fig = px.bar(
                data['outcomes'],
                x='final_summary',
                y='count',
                text='count',
                color='final_summary',
                color_discrete_map=outcome_colors
            )
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outcome data available")

    st.divider()

    # Row 2: Anomaly Analysis (NEW - handles multiple anomalies per sample)
    st.subheader("🧬 Anomaly Analysis")
    st.caption("*Note: Samples can have multiple anomalies, so totals may exceed sample count*")

    c3, c4 = st.columns(2)

    with c3:
        st.markdown("**Anomaly Type Breakdown**")
        if not data['anomaly_breakdown'].empty and data['anomaly_breakdown']['Count'].sum() > 0:
            # Filter to show only non-zero anomalies
            filtered_anomalies = data['anomaly_breakdown'][data['anomaly_breakdown']['Count'] > 0]
            if not filtered_anomalies.empty:
                fig = px.bar(
                    filtered_anomalies,
                    x='Anomaly Type',
                    y='Count',
                    text='Count',
                    color='Anomaly Type',
                    color_discrete_map={
                        'T21': '#3498DB',
                        'T18': '#9B59B6',
                        'T13': '#1ABC9C',
                        'SCA': '#E74C3C',
                        'CNV': '#F39C12',
                        'RAT': '#34495E'
                    }
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Occurrences")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No anomalies detected in any samples")
        else:
            st.success("No anomalies detected in any samples")

    with c4:
        st.markdown("**Samples by Anomaly Count**")
        if not data['anomaly_count_dist'].empty:
            # Create labels
            data['anomaly_count_dist']['label'] = data['anomaly_count_dist']['anomaly_count'].apply(
                lambda x: 'Normal (0)' if x == 0 else f'{x} Anomaly' if x == 1 else f'{x} Anomalies'
            )
            fig = px.pie(
                data['anomaly_count_dist'],
                values='samples',
                names='label',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig.update_traces(textposition='inside', textinfo='percent+value')
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.3))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No distribution data available")

    st.divider()

    # Row 3: SCA and Panel Distribution
    c5, c6 = st.columns(2)

    with c5:
        st.subheader("🧬 Sex Chromosome Analysis")
        if not data['sca_breakdown'].empty:
            # Separate normal from abnormal SCA
            normal_sca = data['sca_breakdown'][data['sca_breakdown']['SCA Type'].isin(['XX (Female)', 'XY (Male)'])]
            abnormal_sca = data['sca_breakdown'][~data['sca_breakdown']['SCA Type'].isin(['XX (Female)', 'XY (Male)', 'Unknown'])]

            if not abnormal_sca.empty and abnormal_sca['Count'].sum() > 0:
                st.markdown("**SCA Anomalies Detected:**")
                fig = px.bar(
                    abnormal_sca,
                    x='SCA Type',
                    y='Count',
                    text='Count',
                    color='SCA Type',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No SCA anomalies detected")

            # Show normal distribution
            if not normal_sca.empty:
                total_normal = normal_sca['Count'].sum()
                xx_count = normal_sca[normal_sca['SCA Type'] == 'XX (Female)']['Count'].sum()
                xy_count = normal_sca[normal_sca['SCA Type'] == 'XY (Male)']['Count'].sum()
                st.caption(f"Normal SCA: {int(xx_count)} Female (XX) | {int(xy_count)} Male (XY)")
        else:
            st.info("No SCA data available")

    with c6:
        st.subheader("📦 Panel Type Distribution")
        if not data['panels'].empty:
            fig = px.pie(
                data['panels'],
                values='count',
                names='panel_type',
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No panel data available")

    st.divider()

    # Row 4: Activity and Multi-Anomaly Details
    st.subheader("📈 Testing Activity (Last 30 Days)")
    if not data['recent'].empty:
        fig = px.area(
            data['recent'],
            x='date',
            y='count',
            markers=True,
            line_shape='spline'
        )
        fig.update_traces(fill='tozeroy', line_color='#3498DB')
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Tests Performed",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No recent activity data")

    # Multi-anomaly samples table
    if data['multi_anomaly_count'] > 0:
        st.divider()
        st.subheader("⚠️ Multi-Anomaly Samples")
        st.caption("Samples with more than one detected anomaly requiring special attention")

        multi_df = data['multi_anomaly_samples'].copy()
        multi_df.columns = ['Result ID', 'Anomalies', 'Count', 'Final Summary']

        # Style the dataframe
        st.dataframe(
            multi_df,
            use_container_width=True,
            column_config={
                'Result ID': st.column_config.NumberColumn('ID', format='%d'),
                'Anomalies': st.column_config.TextColumn('Detected Anomalies', width='medium'),
                'Count': st.column_config.NumberColumn('# Anomalies', format='%d'),
                'Final Summary': st.column_config.TextColumn('Summary', width='medium')
            },
            hide_index=True
        )

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

        # Helpful info box
        with st.expander("ℹ️ About MRNs and Patient Management", expanded=False):
            st.markdown("""
            **Medical Record Number (MRN)**: Your facility's unique patient identifier
            - If the MRN already exists, a new result will be added to that patient's record
            - If the MRN is new, a new patient will be created
            - Multiple test results can be associated with the same MRN
            - Current setting: """ + ("Alphanumeric MRNs allowed" if config.get('ALLOW_ALPHANUMERIC_MRN', False) else "Numerical MRNs only") + """

            💡 **Tip**: You can change MRN validation rules in Settings if your facility uses alphanumeric identifiers.
            """)

        with st.container():
            st.markdown("##### Patient Information")
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("Patient Name", help="Full name of the patient")

            # MRN field with validation
            allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
            mrn_help = "Medical Record Number - unique identifier"
            if not allow_alphanum:
                mrn_help += " (digits only)"
            p_id = c2.text_input("MRN", help=mrn_help)

            # Validate MRN in real-time
            mrn_valid = True
            if p_id:
                is_valid, error_msg = validate_mrn(p_id, allow_alphanumeric=allow_alphanum)
                if not is_valid:
                    c2.error(error_msg)
                    mrn_valid = False

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

        # Test number selection
        col_test1, col_test2 = st.columns([1, 2])
        with col_test1:
            test_number = st.radio(
                "Test Number",
                options=[1, 2, 3],
                format_func=lambda x: f"{'1st' if x == 1 else '2nd' if x == 2 else '3rd'} Test",
                horizontal=True,
                help="Select test iteration: 1st (initial), 2nd (re-library), or 3rd (final verification)"
            )
        with col_test2:
            if test_number == 1:
                st.info("📋 **First Test**: Standard interpretation criteria will be applied.")
            elif test_number == 2:
                st.info("📋 **Second Test**: More stringent interpretation criteria for re-library results.")
            else:
                st.info("📋 **Third Test**: Final verification with stringent interpretation criteria.")

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
        analysis_dup_choice = 'add_to_existing'  # Default
        analysis_new_mrn = None
        patient_exists = False

        if p_id and mrn_valid:
            exists, existing_patient = check_duplicate_patient(p_id)
            if exists:
                patient_exists = True
                st.warning(f"⚠️ **Duplicate MRN Detected:** MRN '{p_id}' already exists as '{existing_patient['name']}' "
                          f"(Age: {existing_patient['age']}, Results: {existing_patient['result_count']})")

                dup_col1, dup_col2 = st.columns([1, 1])
                with dup_col1:
                    analysis_dup_choice = st.radio(
                        "How do you want to handle this?",
                        options=['add_to_existing', 'create_new'],
                        format_func=lambda x: "Add as new test result to existing patient" if x == 'add_to_existing' else "Create new patient with different MRN",
                        key="analysis_dup_choice",
                        horizontal=True
                    )

                if analysis_dup_choice == 'create_new':
                    with dup_col2:
                        # Suggest next available MRN
                        suggested_mrn = p_id
                        suffix = 1
                        while True:
                            test_mrn = f"{p_id}_{suffix}"
                            exists_test, _ = check_duplicate_patient(test_mrn)
                            if not exists_test:
                                suggested_mrn = test_mrn
                                break
                            suffix += 1
                            if suffix > 100:
                                break

                        analysis_new_mrn = st.text_input(
                            "New MRN",
                            value=suggested_mrn,
                            key="analysis_new_mrn",
                            help=f"Enter a new MRN for this patient. Suggested: {suggested_mrn}"
                        )

                        # Validate new MRN
                        if analysis_new_mrn:
                            allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
                            new_mrn_valid, new_mrn_err = validate_mrn(analysis_new_mrn, allow_alphanumeric=allow_alphanum)
                            if not new_mrn_valid:
                                st.error(f"Invalid MRN: {new_mrn_err}")
                            else:
                                dup_exists, _ = check_duplicate_patient(analysis_new_mrn)
                                if dup_exists:
                                    st.error(f"MRN '{analysis_new_mrn}' also exists. Choose a different MRN.")
                                else:
                                    st.success(f"✓ MRN '{analysis_new_mrn}' is available")

        # Determine if save should be disabled
        save_disabled = bool(val_errors) or not mrn_valid
        if patient_exists and analysis_dup_choice == 'create_new':
            if not analysis_new_mrn:
                save_disabled = True
            else:
                allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
                new_valid, _ = validate_mrn(analysis_new_mrn, allow_alphanumeric=allow_alphanum)
                dup_exists, _ = check_duplicate_patient(analysis_new_mrn) if new_valid else (True, None)
                if not new_valid or dup_exists:
                    save_disabled = True

        if st.button("💾 SAVE & ANALYZE", type="primary", disabled=save_disabled):
            t21_res, t21_risk = analyze_trisomy(config, z21, "21", test_number)
            t18_res, t18_risk = analyze_trisomy(config, z18, "18", test_number)
            t13_res, t13_risk = analyze_trisomy(config, z13, "13", test_number)
            sca_res, sca_risk = analyze_sca(config, sca_type, z_xx, z_xy, cff, test_number)

            analyzed_cnvs = []
            is_cnv_high = False
            for item in st.session_state.cnv_list:
                msg, _, risk = analyze_cnv(item['size'], item['ratio'], test_number, config)
                if risk == "HIGH": is_cnv_high = True
                analyzed_cnvs.append(f"{item['size']}Mb ({item['ratio']}%) -> {msg}")

            analyzed_rats = []
            is_rat_high = False
            for item in st.session_state.rat_list:
                msg, risk = analyze_rat(config, item['chr'], item['z'], test_number)
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

            # Determine MRN based on user's duplicate handling choice
            # Read from session state to get the actual user selection
            use_mrn = p_id
            allow_dup = True  # Default: allow adding to existing patient

            # Re-check if patient exists and get user's choice from session state
            dup_exists_check, _ = check_duplicate_patient(p_id) if p_id else (False, None)
            user_dup_choice = st.session_state.get('analysis_dup_choice', 'add_to_existing')
            user_new_mrn = st.session_state.get('analysis_new_mrn', None)

            if dup_exists_check and user_dup_choice == 'create_new' and user_new_mrn:
                use_mrn = user_new_mrn
                allow_dup = False  # New patient, don't allow duplicate

            p_data = {'name': p_name, 'id': use_mrn, 'age': p_age, 'weight': p_weight,
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

            # Save result using user's duplicate handling choice
            rid, msg = save_result(p_data, r_data, c_data, full_z, qc_metrics=qc_metrics, allow_duplicate=allow_dup, test_number=test_number)

            if rid:
                # Show appropriate success message based on what happened
                if dup_exists_check and user_dup_choice == 'create_new':
                    st.success(f"✅ Record Saved - New patient created with MRN: {use_mrn}")
                elif dup_exists_check:
                    st.success(f"✅ Record Saved - Added as new test result to existing patient (MRN: {use_mrn})")
                else:
                    st.success("✅ Record Saved")

                st.session_state.last_report_id = rid
                st.session_state.current_result = {
                    'clinical': c_data,
                    'qc': {'status': qc_stat, 'msg': qc_msg, 'advice': qc_advice}
                }
                st.session_state.analysis_complete = True
                st.session_state.cnv_list = []
                st.session_state.rat_list = []

                # Clean up duplicate handling session state
                for key in ['analysis_dup_choice', 'analysis_new_mrn']:
                    if key in st.session_state:
                        del st.session_state[key]
            else:
                st.error(f"Failed to save: {msg}")
        
        if st.session_state.analysis_complete:
            res = st.session_state.current_result['clinical']
            qc = st.session_state.current_result['qc']

            st.divider()
            st.subheader("📋 Analysis Report")

            # Get full result data for comprehensive display
            if st.session_state.last_report_id:
                with get_db_connection() as conn:
                    report_query = """
                        SELECT r.id, r.created_at, p.full_name, p.mrn_id, p.age, p.weeks, p.weight_kg, p.height_cm, p.bmi,
                               p.clinical_notes, r.panel_type, r.qc_status, r.qc_details, r.qc_advice,
                               r.qc_metrics_json, r.full_z_json, r.t21_res, r.t18_res, r.t13_res, r.sca_res,
                               r.cnv_json, r.rat_json, r.final_summary
                        FROM results r
                        JOIN patients p ON p.id = r.patient_id
                        WHERE r.id = ?
                    """
                    report_data = pd.read_sql(report_query, conn, params=(st.session_state.last_report_id,))

                if not report_data.empty:
                    row = report_data.iloc[0]
                    qc_metrics = json.loads(row['qc_metrics_json']) if row['qc_metrics_json'] else {}
                    full_z = json.loads(row['full_z_json']) if row['full_z_json'] else {}

                    # QC Status banner
                    if qc['status'] == "FAIL":
                        st.error(f"❌ QC FAILED: {qc['msg']}")
                        st.error(f"**Recommended Action:** {qc['advice']}")
                    elif qc['status'] == "WARNING":
                        st.warning(f"⚠️ QC WARNING: {qc['msg']}")
                    else:
                        st.success(f"✅ QC PASSED - Results are valid")

                    # Patient Information Section - Compact card layout
                    st.markdown("#### Patient Information")
                    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                    with p_col1:
                        st.caption("Patient Name")
                        st.markdown(f"**{row['full_name'] or 'N/A'}**")
                    with p_col2:
                        st.caption("MRN")
                        st.markdown(f"**{row['mrn_id'] or 'N/A'}**")
                    with p_col3:
                        st.caption("Age")
                        st.markdown(f"**{row['age']} years**" if row['age'] else "**N/A**")
                    with p_col4:
                        st.caption("Gestational Weeks")
                        st.markdown(f"**{row['weeks']} weeks**" if row['weeks'] else "**N/A**")

                    # QC Metrics Section - Compact grid
                    st.markdown("#### QC Metrics")
                    qc_cols = st.columns(6)
                    qc_cols[0].metric("Reads (M)", f"{qc_metrics.get('reads', 'N/A')}")
                    qc_cols[1].metric("Cff %", f"{qc_metrics.get('cff', 'N/A')}")
                    qc_cols[2].metric("GC %", f"{qc_metrics.get('gc', 'N/A')}")
                    qc_cols[3].metric("QS", f"{qc_metrics.get('qs', 'N/A')}")
                    qc_cols[4].metric("Unique %", f"{qc_metrics.get('unique_rate', 'N/A')}")
                    qc_cols[5].metric("Error %", f"{qc_metrics.get('error_rate', 'N/A')}")

                    # Trisomy Results Section - Card style with color coding
                    st.markdown("#### Trisomy Analysis Results")
                    tri_cols = st.columns(3)

                    # T21
                    z21 = full_z.get('21', full_z.get(21, 'N/A'))
                    z21_str = f"{float(z21):.2f}" if z21 != 'N/A' and z21 is not None else 'N/A'
                    t21_val = row['t21_res'] or "N/A"
                    t21_is_neg = "NEG" in str(t21_val).upper() or "LOW" in str(t21_val).upper()
                    with tri_cols[0]:
                        st.caption("Trisomy 21 (Down)")
                        if t21_is_neg:
                            st.success(f"**{t21_val}**")
                        else:
                            st.error(f"**{t21_val}**")
                        st.caption(f"Z-score: {z21_str}")

                    # T18
                    z18 = full_z.get('18', full_z.get(18, 'N/A'))
                    z18_str = f"{float(z18):.2f}" if z18 != 'N/A' and z18 is not None else 'N/A'
                    t18_val = row['t18_res'] or "N/A"
                    t18_is_neg = "NEG" in str(t18_val).upper() or "LOW" in str(t18_val).upper()
                    with tri_cols[1]:
                        st.caption("Trisomy 18 (Edwards)")
                        if t18_is_neg:
                            st.success(f"**{t18_val}**")
                        else:
                            st.error(f"**{t18_val}**")
                        st.caption(f"Z-score: {z18_str}")

                    # T13
                    z13 = full_z.get('13', full_z.get(13, 'N/A'))
                    z13_str = f"{float(z13):.2f}" if z13 != 'N/A' and z13 is not None else 'N/A'
                    t13_val = row['t13_res'] or "N/A"
                    t13_is_neg = "NEG" in str(t13_val).upper() or "LOW" in str(t13_val).upper()
                    with tri_cols[2]:
                        st.caption("Trisomy 13 (Patau)")
                        if t13_is_neg:
                            st.success(f"**{t13_val}**")
                        else:
                            st.error(f"**{t13_val}**")
                        st.caption(f"Z-score: {z13_str}")

                    # SCA Section - Card style
                    st.markdown("#### Sex Chromosome Analysis")
                    sca_cols = st.columns(3)
                    sca_val = row['sca_res'] or "N/A"
                    z_xx = full_z.get('XX', 'N/A')
                    z_xy = full_z.get('XY', 'N/A')
                    with sca_cols[0]:
                        st.caption("SCA Result")
                        # Truncate long SCA results
                        sca_display = sca_val[:30] + "..." if len(str(sca_val)) > 30 else sca_val
                        st.markdown(f"**{sca_display}**")
                    with sca_cols[1]:
                        st.caption("Z-XX")
                        st.markdown(f"**{float(z_xx):.2f}**" if z_xx != 'N/A' and z_xx is not None else "**N/A**")
                    with sca_cols[2]:
                        st.caption("Z-XY")
                        st.markdown(f"**{float(z_xy):.2f}**" if z_xy != 'N/A' and z_xy is not None else "**N/A**")

                    # CNV and RAT findings
                    if res['cnv_list'] or res['rat_list']:
                        st.markdown("#### Additional Findings")
                        finding_cols = st.columns(2)

                        with finding_cols[0]:
                            if res['cnv_list']:
                                st.markdown("**CNV Findings:**")
                                for cnv in res['cnv_list']:
                                    cnv_rep, _ = get_reportable_status(cnv, qc['status'])
                                    icon = "✅" if cnv_rep == "Yes" else "⚠️"
                                    st.markdown(f"- {icon} {cnv}")
                            else:
                                st.markdown("**CNV Findings:** None detected")

                        with finding_cols[1]:
                            if res['rat_list']:
                                st.markdown("**RAT Findings:**")
                                for rat in res['rat_list']:
                                    rat_rep, _ = get_reportable_status(rat, qc['status'])
                                    icon = "✅" if rat_rep == "Yes" else "⚠️"
                                    st.markdown(f"- {icon} {rat}")
                            else:
                                st.markdown("**RAT Findings:** None detected")

                    # Final Summary with styled box
                    summary = str(row['final_summary']).upper()
                    if 'POSITIVE' in summary:
                        st.error(f"### Final Result: {row['final_summary']}")
                    elif 'INVALID' in summary or 'FAIL' in summary:
                        st.error(f"### Final Result: {row['final_summary']}")
                    elif 'HIGH RISK' in summary:
                        st.warning(f"### Final Result: {row['final_summary']}")
                    else:
                        st.success(f"### Final Result: {row['final_summary']}")

                    # Reportable status
                    reportable, reason = get_reportable_status(str(row['t21_res']), qc['status'])
                    if reportable == "Yes":
                        st.info(f"✅ **Reportable:** Yes - Result is ready for clinical reporting")
                    else:
                        st.warning(f"⚠️ **Reportable:** No - {reason}")
                else:
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
    
    # TAB 2: REGISTRY - REDESIGNED FOR SCALABILITY
    with tabs[1]:
        # Header with global refresh button
        header_col, refresh_col = st.columns([4, 1])
        with header_col:
            st.header("📊 Patient Registry")
        with refresh_col:
            if st.button("🔄 Refresh", use_container_width=True, key="registry_refresh"):
                st.rerun()

        # Initialize session states for registry
        if 'registry_view' not in st.session_state:
            st.session_state.registry_view = 'browse'
        if 'selected_patient_id' not in st.session_state:
            st.session_state.selected_patient_id = None
        if 'selected_result_id' not in st.session_state:
            st.session_state.selected_result_id = None
        if 'registry_page' not in st.session_state:
            st.session_state.registry_page = 1

        # Sub-navigation tabs for organization
        registry_tabs = st.tabs(["👤 Patient Details", "📥 Export & Tools"])

        # ==================== TAB 1: PATIENT DETAILS ====================
        with registry_tabs[0]:
            # Show currently selected patient banner if applicable
            if st.session_state.get('selected_patient_id'):
                st.info(f"📌 **Patient Selected** - Scroll down to view/edit patient details. Use search below to select a different patient.")

            st.markdown("### Find Patient")

            patient_search_col, sort_col, patient_btn_col = st.columns([2, 1, 1])
            with patient_search_col:
                patient_search = st.text_input("Search Patient", placeholder="Enter patient name or MRN...", key="patient_detail_search", label_visibility="collapsed")
            with sort_col:
                default_sort = config.get('DEFAULT_SORT', 'id')
                sort_by = st.selectbox("Sort by", options=["ID", "MRN"],
                                      index=0 if default_sort == 'id' else 1,
                                      key="patient_sort_order",
                                      help="ID: Chronological order | MRN: Alphabetical by MRN")
            with patient_btn_col:
                search_clicked = st.button("🔍 Search", use_container_width=True)

            # Get patients list with sorting
            with get_db_connection() as conn:
                # Determine sort order based on selection
                if sort_by == "ID":
                    order_by = "p.id DESC"  # Most recent first for ID
                else:  # MRN
                    order_by = "CAST(p.mrn_id AS INTEGER) ASC" if not config.get('ALLOW_ALPHANUMERIC_MRN', False) else "p.mrn_id ASC"

                if patient_search:
                    patients_query = f"""
                        SELECT p.id, p.mrn_id, p.full_name, p.age, p.weeks,
                               COUNT(r.id) as result_count, MAX(r.created_at) as last_test
                        FROM patients p
                        LEFT JOIN results r ON r.patient_id = p.id
                        WHERE (p.full_name LIKE ? OR p.mrn_id LIKE ?)
                        GROUP BY p.id ORDER BY {order_by} LIMIT 100
                    """
                    search_pattern = f"%{patient_search}%"
                    patients_df = pd.read_sql(patients_query, conn, params=(search_pattern, search_pattern))
                else:
                    # Show recent patients when no search (sorted by selection)
                    patients_query = f"""
                        SELECT p.id, p.mrn_id, p.full_name, p.age, p.weeks,
                               COUNT(r.id) as result_count, MAX(r.created_at) as last_test
                        FROM patients p
                        LEFT JOIN results r ON r.patient_id = p.id
                        GROUP BY p.id ORDER BY {order_by} LIMIT 20
                    """
                    patients_df = pd.read_sql(patients_query, conn)

            # Show search results or selected patient
            if not patients_df.empty and not st.session_state.get('selected_patient_id'):
                if patient_search:
                    st.markdown(f"**Found {len(patients_df)} patient(s)**")
                else:
                    st.markdown(f"**Recent Patients** (showing {len(patients_df)})")

                for _, p_row in patients_df.iterrows():
                    with st.container():
                        cols = st.columns([2, 1, 1, 1, 1, 1])
                        with cols[0]:
                            st.markdown(f"**{p_row['full_name']}**")
                        with cols[1]:
                            st.caption(f"ID: {p_row['id']}")
                        with cols[2]:
                            st.caption(f"MRN: {p_row['mrn_id']}")
                        with cols[3]:
                            st.caption(f"Age: {p_row['age'] or 'N/A'}")
                        with cols[4]:
                            st.caption(f"Tests: {p_row['result_count']}")
                        with cols[5]:
                            if st.button("Select", key=f"sel_patient_{p_row['id']}"):
                                st.session_state.selected_patient_id = p_row['id']
                                st.rerun()
                        st.divider()

            elif patients_df.empty and not st.session_state.get('selected_patient_id'):
                st.info("No patients found. Add patients through the Analysis tab or PDF Import.")

            # Show selected patient details
            if st.session_state.get('selected_patient_id'):
                patient_id = st.session_state.selected_patient_id
                patient_details = get_patient_details(patient_id)

                if patient_details:
                    header_cols = st.columns([3, 1])
                    with header_cols[0]:
                        st.markdown(f"## 👤 {patient_details.get('name', 'Unknown')}")
                        st.caption(f"MRN: {patient_details['mrn']} | Created: {str(patient_details.get('created_at', 'N/A'))[:10]}")
                    with header_cols[1]:
                        if st.button("✖ Close Patient", use_container_width=True):
                            st.session_state.selected_patient_id = None
                            st.session_state.selected_result_id = None
                            st.rerun()

                    st.divider()

                    # Patient info and actions in tabs
                    detail_tabs = st.tabs(["📋 Information", "📊 Test Results", "🔧 QC Override", "⚠️ Delete"])

                    # --- Patient Information Tab ---
                    with detail_tabs[0]:
                        with st.form(key="edit_patient_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edit_name = st.text_input("Full Name", value=patient_details.get('name', ''))
                                edit_age = st.number_input("Age", min_value=15, max_value=60, value=int(patient_details.get('age', 30)) if patient_details.get('age') else 30)
                                edit_weight = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=float(patient_details.get('weight', 65.0)) if patient_details.get('weight') else 65.0)
                            with col2:
                                edit_weeks = st.number_input("Gestational Weeks", min_value=9, max_value=42, value=int(patient_details.get('weeks', 12)) if patient_details.get('weeks') else 12)
                                edit_height = st.number_input("Height (cm)", min_value=100, max_value=220, value=int(patient_details.get('height', 165)) if patient_details.get('height') else 165)
                                if edit_weight > 0 and edit_height > 0:
                                    edit_bmi = round(edit_weight / ((edit_height/100)**2), 1)
                                    st.metric("BMI (calculated)", edit_bmi)
                                else:
                                    edit_bmi = 0.0

                            edit_notes = st.text_area("Clinical Notes", value=patient_details.get('notes', '') or '', height=100)

                            if st.form_submit_button("💾 Update Patient", type="primary"):
                                update_data = {'name': edit_name, 'age': edit_age, 'weight': edit_weight, 'height': edit_height, 'bmi': edit_bmi, 'weeks': edit_weeks, 'notes': edit_notes}
                                success, message = update_patient(patient_id, update_data)
                                if success:
                                    st.success(f"✅ {message}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")

                    # --- Test Results Tab ---
                    with detail_tabs[1]:
                        with get_db_connection() as conn:
                            results_query = """
                                SELECT r.id, r.created_at, r.panel_type, r.qc_status,
                                       r.t21_res, r.t18_res, r.t13_res, r.sca_res, r.final_summary,
                                       r.qc_override, r.qc_override_reason, r.test_number
                                FROM results r WHERE r.patient_id = ? ORDER BY r.created_at DESC
                            """
                            patient_results = pd.read_sql(results_query, conn, params=(patient_id,))

                        if not patient_results.empty:
                            st.markdown(f"**{len(patient_results)} Test Result(s)** - Select a result to edit or generate PDF")

                            for _, r_row in patient_results.iterrows():
                                result_dict = r_row.to_dict()
                                result_dict['created_at'] = str(result_dict['created_at'])[:16] if result_dict['created_at'] else 'N/A'

                                with st.container():
                                    render_test_result_card(result_dict, card_key=f"res_{r_row['id']}")
                                    btn_cols = st.columns([1, 1, 1, 3])
                                    with btn_cols[0]:
                                        if st.button(f"✏️ Edit", key=f"edit_res_{r_row['id']}", use_container_width=True):
                                            st.session_state.selected_result_id = r_row['id']
                                            st.rerun()
                                    with btn_cols[1]:
                                        pdf_en = generate_pdf_report(r_row['id'], lang='en')
                                        if pdf_en:
                                            st.download_button("📄 PDF EN", pdf_en, f"Report_{r_row['id']}_EN.pdf", "application/pdf", key=f"pdf_en_{r_row['id']}", use_container_width=True)
                                    with btn_cols[2]:
                                        pdf_fr = generate_pdf_report(r_row['id'], lang='fr')
                                        if pdf_fr:
                                            st.download_button("📄 PDF FR", pdf_fr, f"Report_{r_row['id']}_FR.pdf", "application/pdf", key=f"pdf_fr_{r_row['id']}", use_container_width=True)
                                    st.markdown("---")

                            # Edit form for selected result
                            if st.session_state.get('selected_result_id'):
                                st.divider()
                                result_id = st.session_state.selected_result_id

                                col_title, col_cancel = st.columns([3, 1])
                                with col_title:
                                    st.subheader(f"✏️ Editing Result #{result_id}")
                                with col_cancel:
                                    if st.button("Cancel Edit"):
                                        st.session_state.selected_result_id = None
                                        st.rerun()

                                result_details = get_result_details(result_id)

                                if result_details:
                                    qc_m = result_details.get('qc_metrics', {})
                                    full_z = result_details.get('full_z', {})

                                    with st.form(key=f"edit_result_form_{result_id}"):
                                        st.markdown("**Panel & Sequencing Metrics**")
                                        c1, c2, c3 = st.columns(3)
                                        edit_panel = c1.selectbox("Panel Type", options=list(config['PANEL_READ_LIMITS'].keys()),
                                            index=list(config['PANEL_READ_LIMITS'].keys()).index(result_details['panel_type']) if result_details['panel_type'] in config['PANEL_READ_LIMITS'] else 0)
                                        edit_reads = c2.number_input("Reads (M)", min_value=0.0, max_value=100.0, value=float(qc_m.get('reads', 8.0)))
                                        edit_cff = c3.number_input("Cff %", min_value=0.0, max_value=50.0, value=float(qc_m.get('cff', 10.0)))

                                        c4, c5, c6, c7 = st.columns(4)
                                        edit_gc = c4.number_input("GC %", min_value=0.0, max_value=100.0, value=float(qc_m.get('gc', 40.0)))
                                        edit_qs = c5.number_input("QS", min_value=0.0, max_value=10.0, value=float(qc_m.get('qs', 1.0)))
                                        edit_uniq = c6.number_input("Unique %", min_value=0.0, max_value=100.0, value=float(qc_m.get('unique_rate', 75.0)))
                                        edit_err = c7.number_input("Error %", min_value=0.0, max_value=5.0, value=float(qc_m.get('error_rate', 0.1)))

                                        st.markdown("**Z-Scores**")
                                        z1, z2, z3 = st.columns(3)
                                        edit_z21 = z1.number_input("Z-21", min_value=-10.0, max_value=50.0, value=float(full_z.get('21', full_z.get(21, 0.5))))
                                        edit_z18 = z2.number_input("Z-18", min_value=-10.0, max_value=50.0, value=float(full_z.get('18', full_z.get(18, 0.5))))
                                        edit_z13 = z3.number_input("Z-13", min_value=-10.0, max_value=50.0, value=float(full_z.get('13', full_z.get(13, 0.5))))

                                        st.markdown("**Sex Chromosome Analysis**")
                                        s1, s2, s3 = st.columns(3)
                                        current_sca = result_details.get('sca_res', '')
                                        sca_types = ["XX", "XY", "XO", "XXX", "XXY", "XYY", "XXX+XY", "XO+XY"]
                                        detected_sca = "XX"
                                        if "XXX+XY" in current_sca.upper(): detected_sca = "XXX+XY"
                                        elif "XO+XY" in current_sca.upper(): detected_sca = "XO+XY"
                                        else:
                                            for st_type in sca_types[:6]:
                                                if st_type in current_sca.upper():
                                                    detected_sca = st_type
                                                    break
                                        edit_sca_type = s1.selectbox("SCA Type", options=sca_types, index=sca_types.index(detected_sca) if detected_sca in sca_types else 0)
                                        edit_zxx = s2.number_input("Z-XX", min_value=-10.0, max_value=50.0, value=float(full_z.get('XX', 0.0)))
                                        edit_zxy = s3.number_input("Z-XY", min_value=-10.0, max_value=50.0, value=float(full_z.get('XY', 0.0)))

                                        st.markdown("**Findings (CNV & RAT)**")
                                        cnv_list = result_details.get('cnv_list', [])
                                        cnv_text = "; ".join(cnv_list) if cnv_list and isinstance(cnv_list, list) and len(cnv_list) > 0 and isinstance(cnv_list[0], str) else ""
                                        edit_cnv = st.text_area("CNV Findings", value=cnv_text, height=60, help="Format: 5Mb (8%); 10Mb (12%)")

                                        rat_list = result_details.get('rat_list', [])
                                        rat_text = "; ".join(rat_list) if rat_list and isinstance(rat_list, list) and len(rat_list) > 0 and isinstance(rat_list[0], str) else ""
                                        edit_rat = st.text_area("RAT Findings", value=rat_text, height=60, help="Format: Chr 7 (Z:4.5); Chr 16 (Z:5.2)")

                                        recalc_results = st.checkbox("Recalculate results from Z-scores", value=True)

                                        if st.form_submit_button("💾 Update Result", type="primary"):
                                            new_qc_metrics = {'reads': edit_reads, 'cff': edit_cff, 'gc': edit_gc, 'qs': edit_qs, 'unique_rate': edit_uniq, 'error_rate': edit_err}
                                            new_full_z = {'21': edit_z21, '18': edit_z18, '13': edit_z13, 'XX': edit_zxx, 'XY': edit_zxy}
                                            for k, v in full_z.items():
                                                if str(k) not in ['21', '18', '13', 'XX', 'XY']:
                                                    new_full_z[str(k)] = v

                                            if recalc_results:
                                                # Get test_number from result_details (default to 1 for backward compatibility)
                                                edit_test_num = result_details.get('test_number', 1)

                                                t21_res, t21_risk = analyze_trisomy(config, edit_z21, "21", edit_test_num)
                                                t18_res, t18_risk = analyze_trisomy(config, edit_z18, "18", edit_test_num)
                                                t13_res, t13_risk = analyze_trisomy(config, edit_z13, "13", edit_test_num)
                                                sca_res, sca_risk = analyze_sca(config, edit_sca_type, edit_zxx, edit_zxy, edit_cff, edit_test_num)

                                                analyzed_cnvs, is_cnv_high = [], False
                                                if edit_cnv.strip():
                                                    for cnv_item in edit_cnv.split(';'):
                                                        cnv_item = cnv_item.strip()
                                                        if cnv_item:
                                                            match = re.search(r'([\d.]+)\s*[Mm]b.*?([\d.]+)\s*%', cnv_item)
                                                            if match:
                                                                sz, rt = float(match.group(1)), float(match.group(2))
                                                                msg, _, risk = analyze_cnv(sz, rt, edit_test_num, config)
                                                                if risk == "HIGH": is_cnv_high = True
                                                                analyzed_cnvs.append(f"{sz}Mb ({rt}%) -> {msg}")
                                                            else:
                                                                analyzed_cnvs.append(cnv_item)

                                                analyzed_rats, is_rat_high = [], False
                                                if edit_rat.strip():
                                                    for rat_item in edit_rat.split(';'):
                                                        rat_item = rat_item.strip()
                                                        if rat_item:
                                                            match = re.search(r'[Cc]hr\s*(\d+).*?[Zz]:\s*([\d.]+)', rat_item)
                                                            if match:
                                                                r_chr, r_z = int(match.group(1)), float(match.group(2))
                                                                msg, risk = analyze_rat(config, r_chr, r_z, edit_test_num)
                                                                if risk in ["POSITIVE", "HIGH"]: is_rat_high = True
                                                                analyzed_rats.append(f"Chr {r_chr} (Z:{r_z}) -> {msg}")
                                                                new_full_z[str(r_chr)] = r_z
                                                            else:
                                                                analyzed_rats.append(rat_item)

                                                all_risks = [t21_risk, t18_risk, t13_risk, sca_risk]
                                                is_positive = "POSITIVE" in all_risks
                                                is_high_risk = "HIGH" in all_risks or is_cnv_high or is_rat_high

                                                qc_stat, qc_msg, qc_advice = check_qc_metrics(config, edit_panel, edit_reads, edit_cff, edit_gc, edit_qs, edit_uniq, edit_err, is_positive or is_high_risk)

                                                final_summary = "NEGATIVE"
                                                if is_positive: final_summary = "POSITIVE DETECTED"
                                                elif is_high_risk: final_summary = "HIGH RISK (SEE ADVICE)"
                                                if qc_stat == "FAIL": final_summary = "INVALID (QC FAIL)"
                                            else:
                                                t21_res, t18_res, t13_res, sca_res = result_details['t21_res'], result_details['t18_res'], result_details['t13_res'], result_details['sca_res']
                                                analyzed_cnvs = cnv_list if isinstance(cnv_list, list) else []
                                                analyzed_rats = rat_list if isinstance(rat_list, list) else []
                                                qc_stat, qc_msg, qc_advice = result_details['qc_status'], result_details['qc_details'], result_details['qc_advice']
                                                final_summary = result_details['final_summary']

                                            update_data = {
                                                'panel_type': edit_panel, 'qc_status': qc_stat, 'qc_details': str(qc_msg) if recalc_results else qc_msg,
                                                'qc_advice': qc_advice, 'qc_metrics': new_qc_metrics, 't21_res': t21_res, 't18_res': t18_res, 't13_res': t13_res,
                                                'sca_res': sca_res, 'cnv_list': analyzed_cnvs, 'rat_list': analyzed_rats, 'full_z': new_full_z, 'final_summary': final_summary
                                            }

                                            success, message = update_result(result_id, update_data, st.session_state.user['id'])
                                            if success:
                                                st.success(f"✅ {message}")
                                                st.session_state.selected_result_id = None
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {message}")
                        else:
                            st.info("No test results found for this patient.")

                    # --- QC Override Tab ---
                    with detail_tabs[2]:
                        st.markdown("**Override QC status for validation purposes.**")

                        with get_db_connection() as conn:
                            qc_query = """
                                SELECT r.id, r.qc_status, r.qc_override, r.qc_override_reason,
                                       r.qc_override_at, u.full_name as override_by
                                FROM results r
                                LEFT JOIN users u ON r.qc_override_by = u.id
                                WHERE r.patient_id = ? ORDER BY r.created_at DESC
                            """
                            qc_results = pd.read_sql(qc_query, conn, params=(patient_id,))

                        if not qc_results.empty:
                            for _, qc_row in qc_results.iterrows():
                                result_id = qc_row['id']
                                original_status = qc_row['qc_status']
                                is_overridden = bool(qc_row.get('qc_override'))

                                st.markdown(f"**Result #{result_id}** - QC: `{original_status}`")

                                if is_overridden:
                                    st.success(f"✅ Overridden to PASS by {qc_row.get('override_by', 'Unknown')}")
                                    st.caption(f"Reason: {qc_row.get('qc_override_reason', 'N/A')}")
                                    if st.button(f"Remove Override", key=f"rm_override_{result_id}"):
                                        ok, msg = remove_qc_override(result_id, st.session_state.user['id'])
                                        if ok:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)
                                elif original_status in ['FAIL', 'WARNING']:
                                    with st.form(key=f"override_form_{result_id}"):
                                        override_reason = st.text_input("Override Reason (required)", placeholder="e.g., Clinical judgment")
                                        if st.form_submit_button("Override to PASS"):
                                            if override_reason.strip():
                                                ok, msg = override_qc_status(result_id, override_reason.strip(), st.session_state.user['id'])
                                                if ok:
                                                    st.success(msg)
                                                    st.rerun()
                                                else:
                                                    st.error(msg)
                                            else:
                                                st.error("Reason required")
                                else:
                                    st.info("QC already PASS")
                                st.divider()
                        else:
                            st.info("No results found.")

                    # --- Delete Tab ---
                    with detail_tabs[3]:
                        st.warning("**Danger Zone:** Permanently delete this patient and all test results.")

                        with get_db_connection() as conn:
                            result_count = pd.read_sql("SELECT COUNT(*) FROM results WHERE patient_id = ?", conn, params=(patient_id,)).iloc[0, 0]

                        st.error(f"This will delete **{result_count}** test result(s). This action cannot be undone.")

                        confirm_delete = st.checkbox(f"I confirm deletion of patient '{patient_details['mrn']}'")

                        if st.button("🗑️ Delete Permanently", type="primary", disabled=not confirm_delete):
                            ok, msg = delete_patient(patient_id, hard_delete=True)
                            if ok:
                                st.success(msg)
                                st.session_state.selected_patient_id = None
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.error("Patient not found.")
                    if st.button("Clear Selection"):
                        st.session_state.selected_patient_id = None
                        st.rerun()

        # ==================== TAB 2: EXPORT & TOOLS ====================
        with registry_tabs[1]:
            st.markdown("### Data Export")

            exp_col1, exp_col2 = st.columns(2)

            with exp_col1:
                st.markdown("**📥 Export Full Registry (CSV)**")
                with get_db_connection() as conn:
                    full_dump = pd.read_sql("""
                        SELECT * FROM results r
                        JOIN patients p ON p.id = r.patient_id
                    """, conn)

                st.download_button("📥 Download CSV", full_dump.to_csv(index=False), "nipt_registry.csv", "text/csv", use_container_width=True)
                st.caption(f"{len(full_dump)} records")

            with exp_col2:
                st.markdown("**📤 Export as JSON**")
                with get_db_connection() as conn:
                    json_df = pd.read_sql("""
                        SELECT r.id as report_id, r.created_at as report_date,
                               p.full_name, p.mrn_id, p.age, p.weight_kg, p.height_cm, p.bmi, p.weeks,
                               p.clinical_notes, r.panel_type, r.qc_status,
                               r.t21_res, r.t18_res, r.t13_res, r.sca_res, r.final_summary
                        FROM results r
                        JOIN patients p ON p.id = r.patient_id
                        ORDER BY r.id DESC
                    """, conn)

                json_records = []
                for _, row in json_df.iterrows():
                    record = {
                        'report_id': int(row['report_id']) if pd.notna(row['report_id']) else None,
                        'report_date': str(row['report_date']) if pd.notna(row['report_date']) else None,
                        'patient': {
                            'name': str(row['full_name']) if pd.notna(row['full_name']) else None,
                            'mrn': str(row['mrn_id']) if pd.notna(row['mrn_id']) else None,
                            'age': int(row['age']) if pd.notna(row['age']) else None,
                        },
                        'results': {
                            'trisomy_21': str(row['t21_res']) if pd.notna(row['t21_res']) else None,
                            'trisomy_18': str(row['t18_res']) if pd.notna(row['t18_res']) else None,
                            'trisomy_13': str(row['t13_res']) if pd.notna(row['t13_res']) else None,
                            'sca': str(row['sca_res']) if pd.notna(row['sca_res']) else None,
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

                st.download_button("📤 Download JSON", json.dumps(json_export, indent=2), "nipt_registry.json", "application/json", use_container_width=True)
                st.caption(f"{len(json_records)} records")

            st.divider()

            st.markdown("### Tools")

            tool_col1, tool_col2 = st.columns(2)

            with tool_col1:
                st.markdown("**📄 Generate PDF Report**")
                pdf_id = st.number_input("Report ID", min_value=1, value=1, key="tool_pdf_id")
                pdf_lang = st.selectbox("Language", ["English", "Francais"], key="tool_pdf_lang")
                lang_code = 'en' if pdf_lang == "English" else 'fr'

                if st.button("Generate PDF", use_container_width=True):
                    pdf_data = generate_pdf_report(pdf_id, lang=lang_code)
                    if pdf_data:
                        st.download_button("⬇️ Download PDF", pdf_data, f"Report_{pdf_id}_{lang_code.upper()}.pdf", "application/pdf", key="tool_pdf_download")
                    else:
                        st.error("Report not found")

            with tool_col2:
                st.markdown("**🗑️ Delete Record**")
                del_id = st.number_input("Report ID to Delete", min_value=1, value=1, key="tool_del_id")
                confirm_del = st.checkbox("Confirm deletion", key="tool_del_confirm")

                if st.button("Delete Record", type="secondary", disabled=not confirm_del, use_container_width=True):
                    ok, msg = delete_record(del_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
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

                # Check for existing patients and validate MRNs
                existing_mrns = []
                invalid_mrns = []
                config = load_config()
                allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)

                # Initialize duplicate handling choices in session state
                if 'pdf_duplicate_choices' not in st.session_state:
                    st.session_state.pdf_duplicate_choices = {}

                for mrn in patients.keys():
                    # Validate MRN format
                    is_valid, error_msg = validate_mrn(mrn, allow_alphanumeric=allow_alphanum)
                    if not is_valid:
                        invalid_mrns.append((mrn, error_msg))
                        st.error(f"🚫 MRN '{mrn}': {error_msg} - Will be SKIPPED during import.")
                        continue

                    # Check if patient exists
                    exists, existing_patient = check_duplicate_patient(mrn)
                    if exists:
                        existing_mrns.append((mrn, existing_patient))

                # Show duplicate handling options for each existing MRN
                if existing_mrns:
                    st.markdown("---")
                    st.markdown("### ⚠️ Duplicate MRN Handling")
                    st.info("The following MRNs already exist in the registry. Choose how to handle each:")

                    for mrn, existing_patient in existing_mrns:
                        with st.container():
                            st.markdown(f"**MRN: {mrn}** - Existing patient: {existing_patient['name']} ({existing_patient['result_count']} existing result(s))")

                            # Get current choice or default
                            choice_key = f"dup_choice_{mrn}"
                            new_mrn_key = f"new_mrn_{mrn}"

                            current_choice = st.session_state.pdf_duplicate_choices.get(mrn, {}).get('action', 'add_to_existing')

                            col_opt1, col_opt2 = st.columns(2)
                            with col_opt1:
                                add_to_existing = st.radio(
                                    f"Action for MRN {mrn}",
                                    options=["add_to_existing", "create_new"],
                                    format_func=lambda x: "Add as new test result to existing patient" if x == "add_to_existing" else "Create new patient with different MRN",
                                    key=choice_key,
                                    index=0 if current_choice == "add_to_existing" else 1,
                                    horizontal=True
                                )

                            # Show new MRN input if user chose to create new
                            if add_to_existing == "create_new":
                                with col_opt2:
                                    # Suggest next available MRN
                                    suggested_mrn = mrn
                                    suffix = 1
                                    while True:
                                        test_mrn = f"{mrn}_{suffix}"
                                        exists_test, _ = check_duplicate_patient(test_mrn)
                                        if not exists_test:
                                            suggested_mrn = test_mrn
                                            break
                                        suffix += 1
                                        if suffix > 100:
                                            break

                                    current_new_mrn = st.session_state.pdf_duplicate_choices.get(mrn, {}).get('new_mrn', suggested_mrn)
                                    new_mrn_input = st.text_input(
                                        f"New MRN for patient from {mrn}",
                                        value=current_new_mrn,
                                        key=new_mrn_key,
                                        help=f"Suggested: {suggested_mrn}"
                                    )

                                    # Validate new MRN
                                    if new_mrn_input:
                                        new_mrn_valid, new_mrn_err = validate_mrn(new_mrn_input, allow_alphanumeric=allow_alphanum)
                                        if not new_mrn_valid:
                                            st.error(f"Invalid MRN: {new_mrn_err}")
                                        else:
                                            dup_exists, _ = check_duplicate_patient(new_mrn_input)
                                            if dup_exists:
                                                st.warning(f"MRN '{new_mrn_input}' also exists. Choose a different MRN.")
                                            else:
                                                st.success(f"✓ MRN '{new_mrn_input}' is available")

                                    # Store choice
                                    st.session_state.pdf_duplicate_choices[mrn] = {
                                        'action': 'create_new',
                                        'new_mrn': new_mrn_input
                                    }
                            else:
                                # Store choice
                                st.session_state.pdf_duplicate_choices[mrn] = {
                                    'action': 'add_to_existing',
                                    'new_mrn': None
                                }

                            st.divider()

                    st.markdown("---")

                # Show patients grouped by MRN with editable fields using forms
                for mrn, records in patients.items():
                    # Skip invalid MRNs
                    if any(mrn == invalid_mrn[0] for invalid_mrn in invalid_mrns):
                        continue

                    is_existing = any(mrn == em[0] for em in existing_mrns)
                    dup_choice = st.session_state.pdf_duplicate_choices.get(mrn, {})

                    # Determine display MRN based on user choice
                    display_mrn = mrn
                    if is_existing and dup_choice.get('action') == 'create_new' and dup_choice.get('new_mrn'):
                        display_mrn = f"{mrn} → {dup_choice.get('new_mrn')}"

                    expander_title = f"📋 Patient: {display_mrn} - {records[0]['patient_name']} ({len(records)} file(s))"
                    if is_existing:
                        if dup_choice.get('action') == 'add_to_existing':
                            expander_title = f"➕ [ADD TO EXISTING] {expander_title}"
                        else:
                            expander_title = f"🆕 [NEW MRN] {expander_title}"

                    with st.expander(expander_title, expanded=True):
                        if is_existing:
                            st.info("Results will be added to the existing patient record with this MRN.")

                        for idx, record in enumerate(records, 1):
                            edit_key = f"{mrn}_{idx}"
                            st.markdown(f"**File {idx}: {record['source_file']}**")

                            # Use form to prevent crashes on edit
                            with st.form(key=f"form_{edit_key}"):
                                st.markdown("##### Patient Information")

                                # Get previously edited MRN if available, otherwise use original
                                prev_edit = st.session_state.get('pdf_edit_data', {}).get(edit_key, {})
                                current_mrn = prev_edit.get('mrn', mrn)

                                # MRN edit row
                                mrn_col1, mrn_col2 = st.columns([1, 3])
                                with mrn_col1:
                                    edit_mrn = st.text_input("MRN", value=current_mrn,
                                        help="You can modify the MRN here. Leave as-is to use the extracted value.")
                                with mrn_col2:
                                    if edit_mrn != mrn:
                                        st.info(f"📝 MRN will be changed from '{mrn}' to '{edit_mrn}'")

                                p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
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
                                with p_col5:
                                    # Test number selection (1st, 2nd, or 3rd test)
                                    current_test_num = safe_int(record.get('test_number'), 1)
                                    if current_test_num not in [1, 2, 3]:
                                        current_test_num = 1
                                    edit_test_number = st.selectbox("Test #", options=[1, 2, 3],
                                        format_func=lambda x: f"{'1st' if x == 1 else '2nd' if x == 2 else '3rd'} Test",
                                        index=current_test_num - 1,
                                        help="Select test iteration: 1st (initial), 2nd (re-library), or 3rd (final verification)")

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
                                        'mrn': edit_mrn,  # Store edited MRN
                                        'original_mrn': mrn,  # Keep track of original for reference
                                        'patient_name': edit_name,
                                        'age': edit_age,
                                        'weeks': edit_weeks,
                                        'panel': edit_panel,
                                        'test_number': edit_test_number,  # Store test number
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
                                    if edit_mrn != mrn:
                                        st.success(f"✅ Changes saved for {edit_name} (MRN changed to: {edit_mrn})")
                                    else:
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

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Confirm & Import All to Registry", type="primary"):
                        success, fail, skipped = 0, 0, 0
                        config = load_config()
                        edit_data = st.session_state.get('pdf_edit_data', {})

                        # Get duplicate handling choices
                        dup_choices = st.session_state.get('pdf_duplicate_choices', {})

                        for mrn, records in patients.items():
                            # Validate original MRN first
                            allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
                            is_valid, error_msg = validate_mrn(mrn, allow_alphanumeric=allow_alphanum)
                            if not is_valid:
                                skipped += len(records)
                                st.warning(f"⚠️ Skipped MRN '{mrn}' - {error_msg}")
                                continue

                            # Check user's choice for handling duplicate MRNs
                            dup_choice = dup_choices.get(mrn, {})
                            use_mrn = mrn
                            allow_dup = True  # Default: allow adding to existing patient

                            if dup_choice.get('action') == 'create_new':
                                # User wants to create new patient with different MRN
                                new_mrn = dup_choice.get('new_mrn')
                                if new_mrn:
                                    # Validate new MRN
                                    new_valid, new_err = validate_mrn(new_mrn, allow_alphanumeric=allow_alphanum)
                                    if not new_valid:
                                        skipped += len(records)
                                        st.warning(f"⚠️ Skipped MRN '{mrn}' - New MRN '{new_mrn}' invalid: {new_err}")
                                        continue
                                    # Check if new MRN also exists
                                    new_exists, _ = check_duplicate_patient(new_mrn)
                                    if new_exists:
                                        skipped += len(records)
                                        st.warning(f"⚠️ Skipped MRN '{mrn}' - New MRN '{new_mrn}' already exists")
                                        continue
                                    use_mrn = new_mrn
                                    allow_dup = False  # New patient, don't allow duplicate
                                else:
                                    skipped += len(records)
                                    st.warning(f"⚠️ Skipped MRN '{mrn}' - No new MRN specified")
                                    continue

                            for idx, original_data in enumerate(records, 1):
                                try:
                                    edit_key = f"{mrn}_{idx}"
                                    # Use edited data if available, otherwise use original
                                    data = edit_data.get(edit_key, original_data)

                                    # Check if user edited the MRN in the form
                                    edited_mrn = data.get('mrn', None)
                                    if edited_mrn and edited_mrn != mrn:
                                        # User changed MRN in form - validate and use it
                                        edited_valid, edited_err = validate_mrn(edited_mrn, allow_alphanumeric=allow_alphanum)
                                        if not edited_valid:
                                            st.warning(f"⚠️ Skipped record - Edited MRN '{edited_mrn}' invalid: {edited_err}")
                                            fail += 1
                                            continue
                                        # Check if edited MRN exists
                                        edited_exists, _ = check_duplicate_patient(edited_mrn)
                                        # Use edited MRN and set allow_dup based on whether it exists
                                        use_mrn = edited_mrn
                                        allow_dup = edited_exists  # If exists, add to existing; if not, create new

                                    # Get test number (default to 1 if not specified)
                                    test_number = safe_int(data.get('test_number'), 1)
                                    if test_number not in [1, 2, 3]:
                                        test_number = 1  # Default to 1 if invalid value

                                    # Get Z-scores
                                    z_scores = data.get('z_scores', {})
                                    z_21 = safe_float(z_scores.get(21, z_scores.get('21', 0.0)))
                                    z_18 = safe_float(z_scores.get(18, z_scores.get('18', 0.0)))
                                    z_13 = safe_float(z_scores.get(13, z_scores.get('13', 0.0)))
                                    z_xx = safe_float(z_scores.get('XX', 0.0))
                                    z_xy = safe_float(z_scores.get('XY', 0.0))

                                    # Analyze
                                    t21, _ = analyze_trisomy(config, z_21, "21", test_number)
                                    t18, _ = analyze_trisomy(config, z_18, "18", test_number)
                                    t13, _ = analyze_trisomy(config, z_13, "13", test_number)
                                    cff_val = safe_float(data.get('cff'), 10.0)
                                    sca, _ = analyze_sca(config, data.get('sca_type', 'XX'), z_xx, z_xy, cff_val, test_number)

                                    # Process CNVs and RATs
                                    analyzed_cnvs = []
                                    for cnv in data.get('cnv_findings', []):
                                        msg, _, _ = analyze_cnv(cnv['size'], cnv['ratio'], test_number, config)
                                        analyzed_cnvs.append(f"{cnv['size']}Mb ({cnv['ratio']}%) -> {msg}")

                                    analyzed_rats = []
                                    for rat in data.get('rat_findings', []):
                                        msg, _ = analyze_rat(config, rat['chr'], rat['z'], test_number)
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
                                        'id': use_mrn,  # Use the chosen MRN (original or new)
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

                                    # Use allow_dup based on user's choice for duplicate handling
                                    rid, msg = save_result(p_data, r_data, c_data, full_z, qc_metrics=qc_metrics, allow_duplicate=allow_dup, test_number=test_number)
                                    if rid:
                                        success += 1
                                    else:
                                        st.warning(f"⚠️ {data.get('patient_name', 'Unknown')}: {msg}")
                                        fail += 1

                                except Exception as e:
                                    st.error(f"Failed to import {data.get('patient_name', 'Unknown')}: {e}")
                                    fail += 1

                        result_msg = f"✅ Import Complete: {success} records imported"
                        if fail > 0:
                            result_msg += f", {fail} failed"
                        if skipped > 0:
                            result_msg += f", {skipped} skipped (invalid MRNs)"
                        st.success(result_msg)
                        log_audit("PDF_IMPORT", f"Imported {success} records, {fail} failed, {skipped} skipped (invalid MRNs)",
                                 st.session_state.user['id'])

                        # Clean up session state
                        for key in ['pdf_import_data', 'pdf_edit_data', 'pdf_import_errors', 'pdf_duplicate_choices']:
                            if key in st.session_state:
                                del st.session_state[key]

                with col2:
                    if st.button("❌ Cancel"):
                        for key in ['pdf_import_data', 'pdf_edit_data', 'pdf_import_errors', 'pdf_duplicate_choices']:
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
            'TestNumber': [1],
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

                        # Get test number (default to 1 if not specified)
                        test_number = int(row.get('TestNumber', 1))
                        if test_number not in [1, 2, 3]:
                            test_number = 1  # Default to 1 if invalid value

                        p_data = {
                            'name': row.get('Patient Name'), 'id': str(row.get('MRN')),
                            'age': row.get('Age'), 'weight': row.get('Weight'),
                            'height': row.get('Height'), 'bmi': 0,
                            'weeks': row.get('Weeks'), 'notes': ''
                        }

                        z_map = {i: row.get(f'Z-{i}', 0.0) for i in range(1, 23)}
                        z_map['XX'] = row.get('Z-XX', 0.0)
                        z_map['XY'] = row.get('Z-XY', 0.0)

                        t21, _ = analyze_trisomy(config, z_map[21], "21", test_number)
                        t18, _ = analyze_trisomy(config, z_map[18], "18", test_number)
                        t13, _ = analyze_trisomy(config, z_map[13], "13", test_number)
                        sca, _ = analyze_sca(config, row.get('SCA Type', 'XX'),
                                           z_map['XX'], z_map['XY'], row.get('Cff', 10), test_number)

                        rats = []
                        for ch, z in z_map.items():
                            if isinstance(ch, int) and ch not in [13, 18, 21]:
                                msg, _ = analyze_rat(config, ch, z, test_number)
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
                                   full_z=z_map, test_number=test_number)
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
                new_config = copy.deepcopy(config)
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

        st.subheader("Test-Specific Thresholds Configuration")
        st.markdown("Configure Z-score thresholds for 1st, 2nd, and 3rd tests across all analysis types.")

        with st.expander("🧬 Advanced Threshold Configuration", expanded=False):
            test_config_tabs = st.tabs(["Trisomy (T21/T18/T13)", "RAT Analysis", "SCA Analysis", "CNV Analysis"])

            # Get current TEST_SPECIFIC_THRESHOLDS from config
            test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', DEFAULT_CONFIG['TEST_SPECIFIC_THRESHOLDS'])

            # Tab 1: Trisomy Thresholds
            with test_config_tabs[0]:
                st.markdown("**Trisomy Z-Score Thresholds** (Chromosomes 21, 18, 13)")

                with st.form("trisomy_thresholds_form"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**1st Test**")
                        t1_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][1]['low']), key="t1_low")
                        t1_amb = st.number_input("Ambiguous Threshold", 0.0, 15.0,
                            value=float(test_thresholds['TRISOMY'][1]['ambiguous']), key="t1_amb")

                    with col2:
                        st.markdown("**2nd Test**")
                        t2_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][2]['low']), key="t2_low")
                        t2_med = st.number_input("Medium Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][2]['medium']), key="t2_med")
                        t2_high = st.number_input("High Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][2]['high']), key="t2_high")
                        t2_pos = st.number_input("Positive Threshold", 0.0, 15.0,
                            value=float(test_thresholds['TRISOMY'][2]['positive']), key="t2_pos")

                    with col3:
                        st.markdown("**3rd Test**")
                        t3_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][3]['low']), key="t3_low")
                        t3_med = st.number_input("Medium Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][3]['medium']), key="t3_med")
                        t3_high = st.number_input("High Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['TRISOMY'][3]['high']), key="t3_high")
                        t3_pos = st.number_input("Positive Threshold", 0.0, 15.0,
                            value=float(test_thresholds['TRISOMY'][3]['positive']), key="t3_pos")

                    if st.form_submit_button("💾 Save Trisomy Thresholds"):
                        new_config = copy.deepcopy(config)
                        if 'TEST_SPECIFIC_THRESHOLDS' not in new_config:
                            new_config['TEST_SPECIFIC_THRESHOLDS'] = copy.deepcopy(DEFAULT_CONFIG['TEST_SPECIFIC_THRESHOLDS'])
                        new_config['TEST_SPECIFIC_THRESHOLDS']['TRISOMY'] = {
                            1: {'low': t1_low, 'ambiguous': t1_amb},
                            2: {'low': t2_low, 'medium': t2_med, 'high': t2_high, 'positive': t2_pos},
                            3: {'low': t3_low, 'medium': t3_med, 'high': t3_high, 'positive': t3_pos}
                        }
                        if save_config(new_config):
                            st.success("✅ Trisomy thresholds saved")
                            log_audit("CONFIG_UPDATE", "Updated trisomy thresholds", st.session_state.user['id'])
                            st.rerun()

            # Tab 2: RAT Thresholds
            with test_config_tabs[1]:
                st.markdown("**RAT (Rare Autosomal Trisomy) Z-Score Thresholds**")

                with st.form("rat_thresholds_form"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**1st Test**")
                        r1_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['RAT'][1]['low']), key="r1_low")
                        r1_pos = st.number_input("Positive Threshold", 0.0, 15.0,
                            value=float(test_thresholds['RAT'][1]['positive']), key="r1_pos")

                    with col2:
                        st.markdown("**2nd Test**")
                        r2_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['RAT'][2]['low']), key="r2_low")
                        r2_pos = st.number_input("Positive Threshold", 0.0, 15.0,
                            value=float(test_thresholds['RAT'][2]['positive']), key="r2_pos")

                    with col3:
                        st.markdown("**3rd Test**")
                        r3_low = st.number_input("Low Risk Threshold", 0.0, 10.0,
                            value=float(test_thresholds['RAT'][3]['low']), key="r3_low")
                        r3_pos = st.number_input("Positive Threshold", 0.0, 15.0,
                            value=float(test_thresholds['RAT'][3]['positive']), key="r3_pos")

                    if st.form_submit_button("💾 Save RAT Thresholds"):
                        new_config = copy.deepcopy(config)
                        if 'TEST_SPECIFIC_THRESHOLDS' not in new_config:
                            new_config['TEST_SPECIFIC_THRESHOLDS'] = copy.deepcopy(DEFAULT_CONFIG['TEST_SPECIFIC_THRESHOLDS'])
                        new_config['TEST_SPECIFIC_THRESHOLDS']['RAT'] = {
                            1: {'low': r1_low, 'positive': r1_pos},
                            2: {'low': r2_low, 'positive': r2_pos},
                            3: {'low': r3_low, 'positive': r3_pos}
                        }
                        if save_config(new_config):
                            st.success("✅ RAT thresholds saved")
                            log_audit("CONFIG_UPDATE", "Updated RAT thresholds", st.session_state.user['id'])
                            st.rerun()

            # Tab 3: SCA Thresholds
            with test_config_tabs[2]:
                st.markdown("**SCA (Sex Chromosomal Aneuploidies) Z-Score Thresholds**")

                with st.form("sca_thresholds_form"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**1st Test**")
                        s1_xx = st.number_input("XX Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][1]['xx_threshold']), key="s1_xx")
                        s1_xy = st.number_input("XY Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][1]['xy_threshold']), key="s1_xy")

                    with col2:
                        st.markdown("**2nd Test**")
                        s2_xx = st.number_input("XX Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][2]['xx_threshold']), key="s2_xx")
                        s2_xy = st.number_input("XY Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][2]['xy_threshold']), key="s2_xy")

                    with col3:
                        st.markdown("**3rd Test**")
                        s3_xx = st.number_input("XX Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][3]['xx_threshold']), key="s3_xx")
                        s3_xy = st.number_input("XY Threshold", 0.0, 10.0,
                            value=float(test_thresholds['SCA'][3]['xy_threshold']), key="s3_xy")

                    if st.form_submit_button("💾 Save SCA Thresholds"):
                        new_config = copy.deepcopy(config)
                        if 'TEST_SPECIFIC_THRESHOLDS' not in new_config:
                            new_config['TEST_SPECIFIC_THRESHOLDS'] = copy.deepcopy(DEFAULT_CONFIG['TEST_SPECIFIC_THRESHOLDS'])
                        new_config['TEST_SPECIFIC_THRESHOLDS']['SCA'] = {
                            1: {'xx_threshold': s1_xx, 'xy_threshold': s1_xy},
                            2: {'xx_threshold': s2_xx, 'xy_threshold': s2_xy},
                            3: {'xx_threshold': s3_xx, 'xy_threshold': s3_xy}
                        }
                        if save_config(new_config):
                            st.success("✅ SCA thresholds saved")
                            log_audit("CONFIG_UPDATE", "Updated SCA thresholds", st.session_state.user['id'])
                            st.rerun()

            # Tab 4: CNV Thresholds
            with test_config_tabs[3]:
                st.markdown("**CNV (Copy Number Variation) Ratio Thresholds by Size**")
                st.caption("Thresholds are percentage values for abnormal ratio detection")

                with st.form("cnv_thresholds_form"):
                    st.markdown("**1st Test**")
                    c1a, c1b, c1c, c1d = st.columns(4)
                    c1_10 = c1a.number_input("≥10 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][1]['>= 10']), key="c1_10")
                    c1_7 = c1b.number_input(">7 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][1]['> 7']), key="c1_7")
                    c1_35 = c1c.number_input(">3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][1]['> 3.5']), key="c1_35")
                    c1_le = c1d.number_input("≤3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][1]['<= 3.5']), key="c1_le")

                    st.markdown("**2nd Test**")
                    c2a, c2b, c2c, c2d = st.columns(4)
                    c2_10 = c2a.number_input("≥10 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][2]['>= 10']), key="c2_10")
                    c2_7 = c2b.number_input(">7 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][2]['> 7']), key="c2_7")
                    c2_35 = c2c.number_input(">3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][2]['> 3.5']), key="c2_35")
                    c2_le = c2d.number_input("≤3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][2]['<= 3.5']), key="c2_le")

                    st.markdown("**3rd Test**")
                    c3a, c3b, c3c, c3d = st.columns(4)
                    c3_10 = c3a.number_input("≥10 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][3]['>= 10']), key="c3_10")
                    c3_7 = c3b.number_input(">7 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][3]['> 7']), key="c3_7")
                    c3_35 = c3c.number_input(">3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][3]['> 3.5']), key="c3_35")
                    c3_le = c3d.number_input("≤3.5 Mb (%)", 0.0, 20.0,
                        value=float(test_thresholds['CNV'][3]['<= 3.5']), key="c3_le")

                    if st.form_submit_button("💾 Save CNV Thresholds"):
                        new_config = copy.deepcopy(config)
                        if 'TEST_SPECIFIC_THRESHOLDS' not in new_config:
                            new_config['TEST_SPECIFIC_THRESHOLDS'] = copy.deepcopy(DEFAULT_CONFIG['TEST_SPECIFIC_THRESHOLDS'])
                        new_config['TEST_SPECIFIC_THRESHOLDS']['CNV'] = {
                            1: {'>= 10': c1_10, '> 7': c1_7, '> 3.5': c1_35, '<= 3.5': c1_le},
                            2: {'>= 10': c2_10, '> 7': c2_7, '> 3.5': c2_35, '<= 3.5': c2_le},
                            3: {'>= 10': c3_10, '> 7': c3_7, '> 3.5': c3_35, '<= 3.5': c3_le}
                        }
                        if save_config(new_config):
                            st.success("✅ CNV thresholds saved")
                            log_audit("CONFIG_UPDATE", "Updated CNV thresholds", st.session_state.user['id'])
                            st.rerun()

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
                new_config = copy.deepcopy(config)
                new_config['REPORT_LANGUAGE'] = language_options[selected_lang_display]
                if save_config(new_config):
                    st.success(f"✅ Report language set to {selected_lang_display}")
                    log_audit("CONFIG_UPDATE", f"Changed report language to {selected_lang_display}",
                             st.session_state.user['id'])
                    st.rerun()
                else:
                    st.error("Failed to save language preference")

        st.divider()

        st.subheader("Patient Data Management")

        st.markdown("**MRN Validation Settings**")
        st.markdown("""
        Configure how Medical Record Numbers (MRNs) are validated in the system.
        - **Numerical Only** (Recommended): Only digits allowed (e.g., 12345, 00123)
        - **Alphanumeric**: Allows letters, numbers, hyphens, and underscores (e.g., P-12345, MRN_00123)
        """)

        allow_alphanum_current = config.get('ALLOW_ALPHANUMERIC_MRN', False)
        allow_alphanum = st.checkbox(
            "Allow Alphanumeric MRNs",
            value=allow_alphanum_current,
            help="Enable if your facility uses alphanumeric MRNs. Note: Numerical-only is recommended for consistency."
        )

        if allow_alphanum != allow_alphanum_current:
            if st.button("💾 Save MRN Validation Setting"):
                new_config = copy.deepcopy(config)
                new_config['ALLOW_ALPHANUMERIC_MRN'] = allow_alphanum
                if save_config(new_config):
                    mode_text = "alphanumeric" if allow_alphanum else "numerical only"
                    st.success(f"✅ MRN validation set to {mode_text}")
                    log_audit("CONFIG_UPDATE", f"Changed MRN validation to {mode_text}",
                             st.session_state.user['id'])
                    st.rerun()
                else:
                    st.error("Failed to save MRN validation setting")

        st.markdown("---")

        st.markdown("**Registry Sorting Settings**")
        st.markdown("""
        Choose how patients are sorted in the registry by default:
        - **By ID**: Chronological order (order patients were added to system)
        - **By MRN**: Sorted by Medical Record Number
        """)

        default_sort_current = config.get('DEFAULT_SORT', 'id')
        default_sort = st.radio(
            "Default Sort Order",
            options=["id", "mrn"],
            index=0 if default_sort_current == 'id' else 1,
            format_func=lambda x: "By ID (Chronological)" if x == 'id' else "By MRN",
            help="This sets the default sort order for patient lists in the registry"
        )

        if default_sort != default_sort_current:
            if st.button("💾 Save Sort Order Setting"):
                new_config = copy.deepcopy(config)
                new_config['DEFAULT_SORT'] = default_sort
                if save_config(new_config):
                    sort_text = "ID (Chronological)" if default_sort == 'id' else "MRN"
                    st.success(f"✅ Default sort order set to {sort_text}")
                    log_audit("CONFIG_UPDATE", f"Changed default sort to {sort_text}",
                             st.session_state.user['id'])
                    st.rerun()
                else:
                    st.error("Failed to save sort order setting")

        st.markdown("---")

        st.info("""
        ℹ️ **Understanding Patient IDs vs MRNs:**

        - **Patient ID (Database ID)**: Automatically assigned, chronological, never reused. When a patient is deleted, their ID becomes a "ghost" ID.
        - **MRN (Medical Record Number)**: Your facility's patient identifier. Can be reused if a patient is deleted and recreated.
        - **Results**: Multiple test results can be linked to the same MRN (same patient, different tests over time).
        """)

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
