"""
Integration tests for database module.
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import datetime
from unittest.mock import patch

from nris.database import (
    get_db_connection,
    init_database,
    log_audit,
    get_patient_details,
    get_result_details,
    check_duplicate_patient,
    delete_patient,
    delete_record,
    save_result,
    override_qc_status,
    get_qc_override_info,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_file = tmp_path / "test_nris.db"
    with patch('nris.database.DB_FILE', str(db_file)), \
         patch('nris.config.DB_FILE', str(db_file)):
        init_database()
        yield str(db_file)


@pytest.fixture
def db_with_data(temp_db):
    """Create a database with sample data."""
    with patch('nris.database.DB_FILE', temp_db), \
         patch('nris.config.DB_FILE', temp_db):

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Add a test patient
        cursor.execute("""
            INSERT INTO patients (mrn_id, full_name, age, weight_kg, height_cm, bmi, weeks, clinical_notes, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("12345", "John Doe", 35, 70.0, 170, 24.2, 12, "Test notes", datetime.now().isoformat(), 1))
        patient_id = cursor.lastrowid

        # Add a test result
        cursor.execute("""
            INSERT INTO results (patient_id, panel_type, qc_status, qc_details, qc_advice, qc_metrics_json,
                                t21_res, t18_res, t13_res, sca_res, cnv_json, rat_json, full_z_json,
                                final_summary, created_at, created_by, test_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, "NIPT Standard", "PASS", "All metrics pass", "No issues", "{}",
              "Low Risk", "Low Risk", "Low Risk", "XX (Female)", "[]", "[]",
              '{"21": 1.0, "18": 0.5, "13": -0.2}', "NEGATIVE", datetime.now().isoformat(), 1, 1))
        result_id = cursor.lastrowid

        conn.commit()
        conn.close()

        yield {
            'db_file': temp_db,
            'patient_id': patient_id,
            'result_id': result_id
        }


class TestInitDatabase:
    """Test cases for database initialization."""

    def test_creates_tables(self, tmp_path):
        """Should create all required tables."""
        db_file = tmp_path / "test.db"

        with patch('nris.database.DB_FILE', str(db_file)), \
             patch('nris.config.DB_FILE', str(db_file)):
            init_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            assert 'users' in tables
            assert 'patients' in tables
            assert 'results' in tables
            assert 'audit_log' in tables

            conn.close()

    def test_creates_default_admin(self, tmp_path):
        """Should create default admin user."""
        db_file = tmp_path / "test.db"

        with patch('nris.database.DB_FILE', str(db_file)), \
             patch('nris.config.DB_FILE', str(db_file)):
            init_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT username, role FROM users WHERE username = 'admin'")
            admin = cursor.fetchone()

            assert admin is not None
            assert admin[0] == 'admin'
            assert admin[1] == 'admin'

            conn.close()

    def test_creates_indexes(self, tmp_path):
        """Should create performance indexes."""
        db_file = tmp_path / "test.db"

        with patch('nris.database.DB_FILE', str(db_file)), \
             patch('nris.config.DB_FILE', str(db_file)):
            init_database()

            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}

            assert 'idx_patients_mrn' in indexes
            assert 'idx_results_patient_id' in indexes

            conn.close()


class TestLogAudit:
    """Test cases for audit logging."""

    def test_logs_action(self, temp_db):
        """Should log audit actions."""
        with patch('nris.database.DB_FILE', temp_db), \
             patch('nris.config.DB_FILE', temp_db):

            log_audit("TEST_ACTION", "Test details", user_id=1)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT action, details FROM audit_log ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "TEST_ACTION"
            assert row[1] == "Test details"

    def test_handles_none_user(self, temp_db):
        """Should handle None user_id."""
        with patch('nris.database.DB_FILE', temp_db), \
             patch('nris.config.DB_FILE', temp_db):

            log_audit("TEST_ACTION", "Test details", user_id=None)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM audit_log ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            assert row[0] is None

    def test_truncates_long_details(self, temp_db):
        """Should truncate very long details."""
        with patch('nris.database.DB_FILE', temp_db), \
             patch('nris.config.DB_FILE', temp_db):

            long_details = "x" * 2000
            log_audit("TEST_ACTION", long_details, user_id=1)

            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute("SELECT details FROM audit_log ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            assert len(row[0]) <= 1000


class TestGetPatientDetails:
    """Test cases for retrieving patient details."""

    def test_returns_patient_data(self, db_with_data):
        """Should return patient details."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            patient = get_patient_details(db_with_data['patient_id'])

            assert patient is not None
            assert patient['name'] == "John Doe"
            assert patient['mrn'] == "12345"
            assert patient['age'] == 35

    def test_returns_none_for_invalid_id(self, db_with_data):
        """Should return None for nonexistent patient."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            patient = get_patient_details(99999)
            assert patient is None


class TestGetResultDetails:
    """Test cases for retrieving result details."""

    def test_returns_result_data(self, db_with_data):
        """Should return result details."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            result = get_result_details(db_with_data['result_id'])

            assert result is not None
            assert result['panel_type'] == "NIPT Standard"
            assert result['qc_status'] == "PASS"
            assert result['final_summary'] == "NEGATIVE"

    def test_parses_json_fields(self, db_with_data):
        """Should parse JSON fields correctly."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            result = get_result_details(db_with_data['result_id'])

            assert isinstance(result['full_z'], dict)
            assert result['full_z'].get('21') == 1.0

    def test_returns_none_for_invalid_id(self, db_with_data):
        """Should return None for nonexistent result."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            result = get_result_details(99999)
            assert result is None


class TestCheckDuplicatePatient:
    """Test cases for duplicate patient checking."""

    def test_finds_existing_patient(self, db_with_data):
        """Should find existing patient by MRN."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            exists, patient = check_duplicate_patient("12345")

            assert exists is True
            assert patient is not None
            assert patient['name'] == "John Doe"

    def test_returns_false_for_new_mrn(self, db_with_data):
        """Should return False for new MRN."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            exists, patient = check_duplicate_patient("99999")

            assert exists is False
            assert patient is None


class TestDeletePatient:
    """Test cases for patient deletion."""

    def test_deletes_patient_and_results(self, db_with_data):
        """Should delete patient and associated results."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = delete_patient(db_with_data['patient_id'], user_id=1)

            assert success is True

            # Verify patient is deleted
            patient = get_patient_details(db_with_data['patient_id'])
            assert patient is None

            # Verify result is deleted
            result = get_result_details(db_with_data['result_id'])
            assert result is None

    def test_returns_false_for_invalid_id(self, db_with_data):
        """Should return False for nonexistent patient."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = delete_patient(99999, user_id=1)

            assert success is False
            assert "not found" in msg.lower()


class TestDeleteRecord:
    """Test cases for result deletion."""

    def test_deletes_result(self, db_with_data):
        """Should delete result record."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = delete_record(db_with_data['result_id'], user_id=1)

            assert success is True

            # Verify result is deleted
            result = get_result_details(db_with_data['result_id'])
            assert result is None

            # Verify patient still exists
            patient = get_patient_details(db_with_data['patient_id'])
            assert patient is not None

    def test_returns_false_for_invalid_id(self, db_with_data):
        """Should return False for nonexistent result."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = delete_record(99999, user_id=1)

            assert success is False
            assert "not found" in msg.lower()


class TestSaveResult:
    """Test cases for saving results."""

    def test_saves_new_patient_and_result(self, temp_db):
        """Should save new patient and result."""
        with patch('nris.database.DB_FILE', temp_db), \
             patch('nris.config.DB_FILE', temp_db):

            patient = {
                'name': 'Jane Doe',
                'id': '67890',
                'age': 30,
                'weight': 65.0,
                'height': 165,
                'bmi': 23.9,
                'weeks': 14,
                'notes': 'Test'
            }
            results = {
                'panel': 'NIPT Standard',
                'qc_status': 'PASS',
                'qc_msgs': ['All pass'],
                'qc_advice': 'None'
            }
            clinical = {
                't21': 'Low Risk',
                't18': 'Low Risk',
                't13': 'Low Risk',
                'sca': 'XX (Female)',
                'cnv_list': [],
                'rat_list': [],
                'final': 'NEGATIVE'
            }

            result_id, msg = save_result(
                patient, results, clinical,
                full_z={'21': 0.5},
                qc_metrics={'cff': 10.0},
                test_number=1,
                user_id=1
            )

            assert result_id > 0
            assert msg == "Success"

    def test_adds_result_to_existing_patient(self, db_with_data):
        """Should add new result to existing patient."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            patient = {
                'name': 'John Doe',
                'id': '12345',  # Existing MRN
                'age': 35,
                'weight': 70.0,
                'height': 170,
                'bmi': 24.2,
                'weeks': 16,
                'notes': 'Follow-up test'
            }
            results = {
                'panel': 'NIPT Plus',
                'qc_status': 'PASS',
                'qc_msgs': ['All pass'],
                'qc_advice': 'None'
            }
            clinical = {
                't21': 'Low Risk',
                't18': 'Low Risk',
                't13': 'Low Risk',
                'sca': 'XX (Female)',
                'cnv_list': [],
                'rat_list': [],
                'final': 'NEGATIVE'
            }

            result_id, msg = save_result(
                patient, results, clinical,
                test_number=2,
                user_id=1
            )

            assert result_id > 0

            # Verify patient wasn't duplicated
            conn = sqlite3.connect(db_with_data['db_file'])
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM patients WHERE mrn_id = '12345'")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 1


class TestQCOverride:
    """Test cases for QC override functionality."""

    def test_overrides_qc_status(self, db_with_data):
        """Should override QC status."""
        # First, update the result to have a FAIL status
        conn = sqlite3.connect(db_with_data['db_file'])
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE results SET qc_status = 'FAIL', final_summary = 'INVALID (QC FAIL)' WHERE id = ?",
            (db_with_data['result_id'],)
        )
        conn.commit()
        conn.close()

        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = override_qc_status(
                db_with_data['result_id'],
                "Technician verified sample quality",
                user_id=1
            )

            assert success is True

            # Verify override is recorded
            override_info = get_qc_override_info(db_with_data['result_id'])
            assert override_info is not None
            assert override_info['is_overridden'] is True
            assert "verified" in override_info['reason']

    def test_returns_false_for_invalid_id(self, db_with_data):
        """Should return False for nonexistent result."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            success, msg = override_qc_status(99999, "Test reason", user_id=1)

            assert success is False
            assert "not found" in msg.lower()


class TestGetQCOverrideInfo:
    """Test cases for retrieving QC override info."""

    def test_returns_none_for_non_overridden(self, db_with_data):
        """Should return None for non-overridden results."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            info = get_qc_override_info(db_with_data['result_id'])
            assert info is None

    def test_returns_none_for_invalid_id(self, db_with_data):
        """Should return None for nonexistent result."""
        with patch('nris.database.DB_FILE', db_with_data['db_file']), \
             patch('nris.config.DB_FILE', db_with_data['db_file']):

            info = get_qc_override_info(99999)
            assert info is None
