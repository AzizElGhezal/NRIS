"""
Database operations for NRIS.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from .config import DB_FILE
from .auth import hash_password


def get_db_connection():
    """Get database connection with foreign keys and WAL mode enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def init_database() -> None:
    """Initialize database with all tables and indexes."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
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
                is_deleted INTEGER DEFAULT 0,
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
                test_number INTEGER DEFAULT 1,
                qc_override INTEGER DEFAULT 0,
                qc_override_by INTEGER,
                qc_override_reason TEXT,
                qc_override_at TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')

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

        # Create indexes
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
                pass

        # Create default admin user if none exists
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            admin_hash = hash_password("admin123")
            c.execute("""
                INSERT INTO users (username, password_hash, full_name, role, created_at, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin", admin_hash, "System Administrator", "admin", datetime.now().isoformat(), 1))


def log_audit(action: str, details: str, user_id: Optional[int] = None) -> None:
    """Log user actions for compliance."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            safe_details = str(details)[:1000] if details else ""
            c.execute("""
                INSERT INTO audit_log (user_id, action, details, timestamp, ip_address)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, safe_details, datetime.now().isoformat(), "local"))
            conn.commit()
    except Exception:
        pass


def get_patient_details(patient_id: int) -> Optional[Dict]:
    """Get full patient details."""
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


def get_result_details(result_id: int) -> Optional[Dict]:
    """Get full result details."""
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
                    'test_number': row[16] if row[16] is not None else 1
                }
    except Exception:
        pass
    return None


def check_duplicate_patient(mrn: str) -> Tuple[bool, Optional[Dict]]:
    """Check if a patient with this MRN already exists."""
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


def delete_patient(patient_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
    """Delete a patient and all associated results."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            c.execute("SELECT mrn_id, full_name FROM patients WHERE id = ?", (patient_id,))
            patient = c.fetchone()
            if not patient:
                return False, "Patient not found"

            mrn, name = patient

            c.execute("SELECT COUNT(*) FROM results WHERE patient_id = ?", (patient_id,))
            result_count = c.fetchone()[0]

            c.execute("DELETE FROM results WHERE patient_id = ?", (patient_id,))
            c.execute("DELETE FROM patients WHERE id = ?", (patient_id,))

            conn.commit()
            log_audit("DELETE_PATIENT",
                     f"Deleted patient {mrn} ({name}) and {result_count} results. ID {patient_id} now ghost.",
                     user_id)
            return True, f"Deleted patient {mrn} and {result_count} associated results"

    except Exception as e:
        return False, f"Delete failed: {str(e)}"


def delete_record(report_id: int, user_id: Optional[int] = None) -> Tuple[bool, str]:
    """Delete a result record."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT patient_id FROM results WHERE id = ?", (report_id,))
            row = c.fetchone()
            if not row:
                return False, "Result not found"

            c.execute("DELETE FROM results WHERE id = ?", (report_id,))
            conn.commit()
            log_audit("DELETE_RESULT", f"Deleted result {report_id}", user_id)
            return True, f"Deleted result {report_id}"
    except Exception as e:
        return False, str(e)


def save_result(patient: Dict, results: Dict, clinical: Dict, full_z: Optional[Dict] = None,
                qc_metrics: Optional[Dict] = None, allow_duplicate: bool = True,
                test_number: int = 1, user_id: int = None) -> Tuple[int, str]:
    """Save analysis result to database."""
    from .utils import validate_mrn
    from .config import load_config

    conn = None
    try:
        config = load_config()
        allow_alphanum = config.get('ALLOW_ALPHANUMERIC_MRN', False)
        is_valid, error_msg = validate_mrn(patient['id'], allow_alphanumeric=allow_alphanum)
        if not is_valid:
            return 0, f"Invalid MRN: {error_msg}"

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("BEGIN TRANSACTION")

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
            c.execute("""
                INSERT INTO patients
                (mrn_id, full_name, age, weight_kg, height_cm, bmi, weeks, clinical_notes, created_at, created_by, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                patient['id'], patient['name'], patient['age'], patient['weight'],
                patient['height'], patient['bmi'], patient['weeks'], patient['notes'],
                datetime.now().isoformat(), user_id
            ))
            patient_db_id = c.lastrowid

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
            datetime.now().isoformat(), user_id, test_number
        ))
        result_id = c.lastrowid

        conn.commit()
        log_audit("SAVE_RESULT", f"Created result {result_id} for patient {patient['id']} (Test #{test_number})", user_id)
        return result_id, "Success"
    except Exception as e:
        if conn:
            conn.rollback()
        return 0, str(e)
    finally:
        if conn:
            conn.close()


def override_qc_status(result_id: int, reason: str, user_id: int) -> Tuple[bool, str]:
    """Override QC status to PASS for a result."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            c.execute("""
                SELECT t21_res, t18_res, t13_res, sca_res, cnv_json, rat_json, final_summary
                FROM results WHERE id = ?
            """, (result_id,))
            row = c.fetchone()
            if not row:
                return False, "Result not found"

            t21_res, t18_res, t13_res, sca_res, cnv_json, rat_json, old_summary = row

            all_results = [str(t21_res), str(t18_res), str(t13_res), str(sca_res)]
            is_positive = any('POSITIVE' in r.upper() for r in all_results)
            is_high_risk = any('HIGH' in r.upper() or 'RE-LIBRARY' in r.upper() or 'RESAMPLE' in r.upper() for r in all_results)

            try:
                cnvs = json.loads(cnv_json) if cnv_json else []
                rats = json.loads(rat_json) if rat_json else []
                if cnvs or rats:
                    is_high_risk = True
            except Exception:
                pass

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
