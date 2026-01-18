"""
Unit tests for QC (Quality Control) analysis functions.
"""

import pytest
from nris.analysis.qc import validate_inputs, check_qc_metrics, get_reportable_status
from nris.config import DEFAULT_CONFIG


class TestValidateInputs:
    """Test cases for validate_inputs function."""

    def test_valid_inputs(self):
        """Valid inputs should return empty error list."""
        errors = validate_inputs(reads=10.0, cff=8.0, gc=40.0, age=30)
        assert errors == []

    def test_invalid_reads_negative(self):
        """Negative reads should be invalid."""
        errors = validate_inputs(reads=-1.0, cff=8.0, gc=40.0, age=30)
        assert len(errors) == 1
        assert "Reads" in errors[0]

    def test_invalid_reads_too_high(self):
        """Reads > 100 should be invalid."""
        errors = validate_inputs(reads=150.0, cff=8.0, gc=40.0, age=30)
        assert len(errors) == 1

    def test_invalid_cff_negative(self):
        """Negative CFF should be invalid."""
        errors = validate_inputs(reads=10.0, cff=-1.0, gc=40.0, age=30)
        assert len(errors) == 1
        assert "Cff" in errors[0]

    def test_invalid_cff_too_high(self):
        """CFF > 50 should be invalid."""
        errors = validate_inputs(reads=10.0, cff=55.0, gc=40.0, age=30)
        assert len(errors) == 1

    def test_invalid_gc_negative(self):
        """Negative GC should be invalid."""
        errors = validate_inputs(reads=10.0, cff=8.0, gc=-5.0, age=30)
        assert len(errors) == 1
        assert "GC" in errors[0]

    def test_invalid_gc_too_high(self):
        """GC > 100 should be invalid."""
        errors = validate_inputs(reads=10.0, cff=8.0, gc=105.0, age=30)
        assert len(errors) == 1

    def test_invalid_age_too_young(self):
        """Age < 15 should be invalid."""
        errors = validate_inputs(reads=10.0, cff=8.0, gc=40.0, age=14)
        assert len(errors) == 1
        assert "Age" in errors[0]

    def test_invalid_age_too_old(self):
        """Age > 60 should be invalid."""
        errors = validate_inputs(reads=10.0, cff=8.0, gc=40.0, age=65)
        assert len(errors) == 1

    def test_multiple_invalid_inputs(self):
        """Multiple invalid inputs should return multiple errors."""
        errors = validate_inputs(reads=-1.0, cff=-1.0, gc=-1.0, age=10)
        assert len(errors) == 4


class TestCheckQCMetrics:
    """Test cases for check_qc_metrics function."""

    @pytest.fixture
    def config(self):
        return DEFAULT_CONFIG.copy()

    def test_all_pass(self, config):
        """All metrics within range should PASS."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=40.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "PASS"
        assert issues == []
        assert advice == "None"

    def test_low_reads_fail(self, config):
        """Low reads should FAIL."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=3.0, cff=8.0, gc=40.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"
        assert any("HARD" in i and "Reads" in i for i in issues)
        assert "Resequencing" in advice

    def test_low_cff_fail(self, config):
        """Low CFF should FAIL."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=2.0, gc=40.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"
        assert any("HARD" in i and "Cff" in i for i in issues)
        assert "Resample" in advice

    def test_high_cff_fail(self, config):
        """CFF > 50 should FAIL."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=55.0, gc=40.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"

    def test_gc_out_of_range_fail(self, config):
        """GC out of range should FAIL."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=30.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"
        assert any("GC" in i for i in issues)

    def test_high_qs_negative_fail(self, config):
        """High QS with negative result should FAIL."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=40.0,
            qs=2.0, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"
        assert any("QS" in i for i in issues)

    def test_high_qs_positive_fail(self, config):
        """High QS with positive result uses different threshold."""
        # QS_LIMIT_POS is 2.0, so qs=2.0 should fail
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=40.0,
            qs=2.0, uniq=75.0, error=0.3, is_positive=True
        )
        assert status == "FAIL"

    def test_low_unique_rate_warning(self, config):
        """Low unique rate should be WARNING (soft fail)."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=40.0,
            qs=0.5, uniq=60.0, error=0.3, is_positive=False
        )
        assert status == "WARNING"
        assert any("SOFT" in i and "UniqueRate" in i for i in issues)

    def test_high_error_rate_warning(self, config):
        """High error rate should be WARNING (soft fail)."""
        status, issues, advice = check_qc_metrics(
            config, panel="NIPT Standard", reads=10.0, cff=8.0, gc=40.0,
            qs=0.5, uniq=75.0, error=2.0, is_positive=False
        )
        assert status == "WARNING"
        assert any("SOFT" in i and "ErrorRate" in i for i in issues)

    def test_panel_specific_read_limits(self, config):
        """Different panels should have different read limits."""
        # NIPT Pro requires 20M reads
        status, issues, _ = check_qc_metrics(
            config, panel="NIPT Pro", reads=15.0, cff=8.0, gc=40.0,
            qs=0.5, uniq=75.0, error=0.3, is_positive=False
        )
        assert status == "FAIL"
        assert any("Reads" in i for i in issues)


class TestGetReportableStatus:
    """Test cases for get_reportable_status function."""

    def test_positive_reportable(self):
        """POSITIVE result should be reportable."""
        status, reason = get_reportable_status("POSITIVE", "PASS", False)
        assert status == "Yes"
        assert "Positive" in reason

    def test_low_risk_reportable(self):
        """Low Risk result should be reportable."""
        status, reason = get_reportable_status("Low Risk", "PASS", False)
        assert status == "Yes"
        assert "Negative" in reason

    def test_negative_reportable(self):
        """Negative result should be reportable."""
        status, reason = get_reportable_status("Negative (2nd test)", "PASS", False)
        assert status == "Yes"

    def test_re_library_not_reportable(self):
        """Re-library result should NOT be reportable."""
        status, reason = get_reportable_status("High Risk -> Re-library", "PASS", False)
        assert status == "No"
        assert "Re-library" in reason

    def test_resample_not_reportable(self):
        """Resample result should NOT be reportable."""
        status, reason = get_reportable_status("High Risk -> Resample", "PASS", False)
        assert status == "No"
        assert "Resample" in reason

    def test_ambiguous_not_reportable(self):
        """Ambiguous result should NOT be reportable."""
        status, reason = get_reportable_status("Ambiguous XO", "PASS", False)
        assert status == "No"
        assert "Ambiguous" in reason

    def test_qc_fail_not_reportable(self):
        """QC FAIL should NOT be reportable."""
        status, reason = get_reportable_status("Low Risk", "FAIL", False)
        assert status == "No"
        assert "QC" in reason

    def test_qc_fail_with_override_reportable(self):
        """QC FAIL with override should be reportable."""
        status, reason = get_reportable_status("Low Risk", "FAIL", True)
        assert status == "Yes"

    def test_invalid_not_reportable(self):
        """INVALID result should NOT be reportable."""
        status, reason = get_reportable_status("INVALID (Cff < 3.5%)", "PASS", False)
        assert status == "No"
        assert "Invalid" in reason

    def test_invalid_with_override_reportable(self):
        """INVALID with override should be reportable."""
        status, reason = get_reportable_status("INVALID (Cff < 3.5%)", "PASS", True)
        assert status == "Yes"
