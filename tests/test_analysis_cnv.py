"""
Unit tests for CNV (Copy Number Variation) analysis functions.
"""

import pytest
from nris.analysis.cnv import analyze_cnv
from nris.config import DEFAULT_CONFIG


class TestAnalyzeCNV:
    """Test cases for analyze_cnv function."""

    @pytest.fixture
    def config(self):
        return DEFAULT_CONFIG.copy()

    def test_large_cnv_low_ratio_first_test(self, config):
        """Large CNV with ratio below threshold should be low risk."""
        result, threshold, risk = analyze_cnv(size=15.0, ratio=4.0, test_number=1, config=config)
        assert risk == "LOW"
        assert threshold == 6.0  # >= 10 Mb threshold

    def test_large_cnv_high_ratio_first_test(self, config):
        """Large CNV with high ratio should be high risk on first test."""
        result, threshold, risk = analyze_cnv(size=15.0, ratio=7.0, test_number=1, config=config)
        assert risk == "HIGH"
        assert "Re-library" in result

    def test_medium_cnv_threshold(self, config):
        """Medium CNV (7-10 Mb) should use 8.0 threshold."""
        result, threshold, risk = analyze_cnv(size=8.5, ratio=5.0, test_number=1, config=config)
        assert threshold == 8.0

    def test_small_medium_cnv_threshold(self, config):
        """Small-medium CNV (3.5-7 Mb) should use 10.0 threshold."""
        result, threshold, risk = analyze_cnv(size=5.0, ratio=7.0, test_number=1, config=config)
        assert threshold == 10.0

    def test_small_cnv_threshold(self, config):
        """Small CNV (<= 3.5 Mb) should use 12.0 threshold."""
        result, threshold, risk = analyze_cnv(size=2.0, ratio=8.0, test_number=1, config=config)
        assert threshold == 12.0

    def test_second_test_positive(self, config):
        """Second test with ratio at threshold should be positive."""
        result, threshold, risk = analyze_cnv(size=12.0, ratio=6.5, test_number=2, config=config)
        assert risk == "POSITIVE"
        assert "2nd test" in result

    def test_second_test_high_risk(self, config):
        """Second test with ratio below threshold should be high risk."""
        result, threshold, risk = analyze_cnv(size=12.0, ratio=4.0, test_number=2, config=config)
        assert risk == "HIGH"
        assert "Resample" in result

    def test_third_test_label(self, config):
        """Third test should be labeled correctly."""
        result, threshold, risk = analyze_cnv(size=12.0, ratio=8.0, test_number=3, config=config)
        assert risk == "POSITIVE"
        assert "3rd test" in result

    def test_boundary_size_10(self, config):
        """CNV exactly at 10 Mb should use >= 10 threshold."""
        result, threshold, risk = analyze_cnv(size=10.0, ratio=5.0, test_number=1, config=config)
        assert threshold == 6.0

    def test_boundary_size_7(self, config):
        """CNV at 7.0 Mb should use > 7 threshold."""
        result, threshold, risk = analyze_cnv(size=7.0, ratio=6.0, test_number=1, config=config)
        # Size 7.0 is not > 7, so should use > 3.5 threshold
        assert threshold == 10.0

    def test_boundary_size_3_5(self, config):
        """CNV at 3.5 Mb should use <= 3.5 threshold."""
        result, threshold, risk = analyze_cnv(size=3.5, ratio=10.0, test_number=1, config=config)
        assert threshold == 12.0

    def test_without_config(self):
        """Should work without config (use defaults)."""
        result, threshold, risk = analyze_cnv(size=15.0, ratio=4.0, test_number=1, config=None)
        assert threshold == 6.0
        assert risk == "LOW"

    def test_ratio_display_in_result(self, config):
        """Result should include ratio value when positive."""
        result, threshold, risk = analyze_cnv(size=12.0, ratio=7.5, test_number=2, config=config)
        assert "7.5%" in result or "7.5" in result
