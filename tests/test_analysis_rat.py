"""
Unit tests for RAT (Rare Autosomal Trisomy) analysis functions.
"""

import pytest
from nris.analysis.rat import analyze_rat
from nris.config import DEFAULT_CONFIG


class TestAnalyzeRAT:
    """Test cases for analyze_rat function."""

    @pytest.fixture
    def config(self):
        return DEFAULT_CONFIG.copy()

    def test_low_risk_first_test(self, config):
        """Z-score below 4.5 should be low risk on first test."""
        result, risk = analyze_rat(config, chrom=7, z_score=3.0, test_number=1)
        assert risk == "LOW"
        assert "Low Risk" in result

    def test_ambiguous_first_test(self, config):
        """Z-score between 4.5 and 8.0 should be ambiguous on first test."""
        result, risk = analyze_rat(config, chrom=7, z_score=6.0, test_number=1)
        assert risk == "HIGH"
        assert "Ambiguous" in result
        assert "Re-library" in result

    def test_positive_first_test(self, config):
        """Z-score >= 8.0 should be positive on first test."""
        result, risk = analyze_rat(config, chrom=7, z_score=9.0, test_number=1)
        assert risk == "POSITIVE"
        assert "POSITIVE" in result

    def test_negative_second_test(self, config):
        """Z-score <= 4.5 should be negative on second test."""
        result, risk = analyze_rat(config, chrom=16, z_score=3.5, test_number=2)
        assert risk == "LOW"
        assert "Negative" in result
        assert "2nd test" in result

    def test_high_risk_second_test(self, config):
        """Z-score between thresholds should be high risk on second test."""
        result, risk = analyze_rat(config, chrom=16, z_score=6.0, test_number=2)
        assert risk == "HIGH"
        assert "High Risk" in result
        assert "Resample" in result

    def test_positive_second_test(self, config):
        """Z-score >= 8.0 should be positive on second test."""
        result, risk = analyze_rat(config, chrom=16, z_score=9.5, test_number=2)
        assert risk == "POSITIVE"
        assert "POSITIVE" in result
        assert "2nd test" in result

    def test_third_test_label(self, config):
        """Third test should be labeled correctly."""
        result, risk = analyze_rat(config, chrom=22, z_score=9.0, test_number=3)
        assert risk == "POSITIVE"
        assert "3rd test" in result

    def test_boundary_low_threshold(self, config):
        """Z-score exactly at 4.5 should be low risk on first test."""
        result, risk = analyze_rat(config, chrom=7, z_score=4.5, test_number=1)
        # At exactly 4.5, it's not > 4.5, so should be low risk
        assert risk == "LOW"

    def test_boundary_high_threshold(self, config):
        """Z-score exactly at 8.0 should be positive on first test."""
        result, risk = analyze_rat(config, chrom=7, z_score=8.0, test_number=1)
        assert risk == "POSITIVE"

    def test_different_chromosomes(self, config):
        """Function should work with different chromosome numbers."""
        for chrom in [2, 7, 9, 15, 16, 22]:
            result, risk = analyze_rat(config, chrom=chrom, z_score=1.0, test_number=1)
            assert risk == "LOW"

    def test_negative_z_score(self, config):
        """Negative Z-score should be low risk."""
        result, risk = analyze_rat(config, chrom=7, z_score=-2.0, test_number=1)
        assert risk == "LOW"

    def test_very_high_z_score(self, config):
        """Very high Z-score should be positive."""
        result, risk = analyze_rat(config, chrom=7, z_score=20.0, test_number=1)
        assert risk == "POSITIVE"
