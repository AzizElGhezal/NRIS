"""
Unit tests for trisomy analysis functions.
"""

import pytest
from nris.analysis.trisomy import analyze_trisomy
from nris.config import DEFAULT_CONFIG


class TestAnalyzeTrisomy:
    """Test cases for analyze_trisomy function."""

    @pytest.fixture
    def config(self):
        return DEFAULT_CONFIG.copy()

    def test_low_risk_z_score_first_test(self, config):
        """Z-score below 2.58 should be low risk on first test."""
        result, risk = analyze_trisomy(config, z_score=1.5, chrom="21", test_number=1)
        assert risk == "LOW"
        assert "Low Risk" in result

    def test_high_risk_z_score_first_test(self, config):
        """Z-score between 2.58 and 6.0 should be high risk on first test."""
        result, risk = analyze_trisomy(config, z_score=4.0, chrom="21", test_number=1)
        assert risk == "HIGH"
        assert "High Risk" in result
        assert "Re-library" in result

    def test_positive_z_score_first_test(self, config):
        """Z-score >= 6.0 should be positive on first test."""
        result, risk = analyze_trisomy(config, z_score=7.0, chrom="21", test_number=1)
        assert risk == "POSITIVE"
        assert "POSITIVE" in result

    def test_negative_second_test(self, config):
        """Z-score below threshold should be negative on second test."""
        result, risk = analyze_trisomy(config, z_score=2.0, chrom="21", test_number=2)
        assert risk == "LOW"
        assert "Negative" in result
        assert "2nd test" in result

    def test_positive_second_test(self, config):
        """Z-score >= 6.0 should be positive on second test."""
        result, risk = analyze_trisomy(config, z_score=8.0, chrom="18", test_number=2)
        assert risk == "POSITIVE"
        assert "POSITIVE" in result
        assert "2nd test" in result

    def test_high_risk_second_test(self, config):
        """Z-score in middle range should be high risk on second test."""
        result, risk = analyze_trisomy(config, z_score=3.5, chrom="13", test_number=2)
        assert risk == "HIGH"
        assert "High Risk" in result
        assert "Resample" in result

    def test_third_test_logic(self, config):
        """Third test should use same logic as second test."""
        result, risk = analyze_trisomy(config, z_score=7.5, chrom="21", test_number=3)
        assert risk == "POSITIVE"
        assert "3rd test" in result

    def test_invalid_z_score(self, config):
        """NaN z_score should return UNKNOWN."""
        import math
        result, risk = analyze_trisomy(config, z_score=float('nan'), chrom="21", test_number=1)
        assert risk == "UNKNOWN"
        assert "Invalid" in result

    def test_boundary_low_threshold(self, config):
        """Z-score exactly at low threshold (2.58) should be high risk."""
        result, risk = analyze_trisomy(config, z_score=2.58, chrom="21", test_number=1)
        # At exactly 2.58, should be high risk (>= comparison in real implementation)
        assert risk == "HIGH"

    def test_boundary_high_threshold(self, config):
        """Z-score exactly at 6.0 should be positive on first test."""
        result, risk = analyze_trisomy(config, z_score=6.0, chrom="21", test_number=1)
        assert risk == "POSITIVE"

    def test_negative_z_score(self, config):
        """Negative Z-score should be low risk."""
        result, risk = analyze_trisomy(config, z_score=-1.5, chrom="21", test_number=1)
        assert risk == "LOW"

    def test_very_high_z_score(self, config):
        """Very high Z-score should still be positive."""
        result, risk = analyze_trisomy(config, z_score=25.0, chrom="21", test_number=1)
        assert risk == "POSITIVE"
