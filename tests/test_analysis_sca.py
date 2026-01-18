"""
Unit tests for SCA (Sex Chromosome Aneuploidy) analysis functions.
"""

import pytest
from nris.analysis.sca import analyze_sca
from nris.config import DEFAULT_CONFIG


class TestAnalyzeSCA:
    """Test cases for analyze_sca function."""

    @pytest.fixture
    def config(self):
        return DEFAULT_CONFIG.copy()

    def test_normal_female_first_test(self, config):
        """XX with normal CFF should be negative female."""
        result, risk = analyze_sca(config, sca_type="XX", z_xx=0.5, z_xy=-0.5, cff=8.0, test_number=1)
        assert risk == "LOW"
        assert "Female" in result
        assert "Negative" in result

    def test_normal_male_first_test(self, config):
        """XY with normal CFF should be negative male."""
        result, risk = analyze_sca(config, sca_type="XY", z_xx=-0.5, z_xy=0.5, cff=8.0, test_number=1)
        assert risk == "LOW"
        assert "Male" in result
        assert "Negative" in result

    def test_low_cff_invalid(self, config):
        """Low CFF should return invalid."""
        result, risk = analyze_sca(config, sca_type="XX", z_xx=0.5, z_xy=-0.5, cff=2.0, test_number=1)
        assert risk == "INVALID"
        assert "Cff" in result

    def test_turner_xo_positive_high_z(self, config):
        """Turner XO with high Z-score should be positive."""
        result, risk = analyze_sca(config, sca_type="XO", z_xx=5.0, z_xy=-0.5, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "Turner" in result

    def test_turner_xo_ambiguous_low_z(self, config):
        """Turner XO with low Z-score should be ambiguous."""
        result, risk = analyze_sca(config, sca_type="XO", z_xx=3.0, z_xy=-0.5, cff=8.0, test_number=1)
        assert risk == "HIGH"
        assert "Ambiguous" in result
        assert "Re-library" in result

    def test_triple_x_positive(self, config):
        """Triple X with high Z-score should be positive."""
        result, risk = analyze_sca(config, sca_type="XXX", z_xx=5.5, z_xy=-0.5, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "Triple X" in result

    def test_triple_x_ambiguous(self, config):
        """Triple X with low Z-score should be ambiguous."""
        result, risk = analyze_sca(config, sca_type="XXX", z_xx=3.5, z_xy=-0.5, cff=8.0, test_number=1)
        assert risk == "HIGH"
        assert "Ambiguous" in result

    def test_klinefelter_xxy_positive(self, config):
        """Klinefelter XXY should always be positive."""
        result, risk = analyze_sca(config, sca_type="XXY", z_xx=0.5, z_xy=0.5, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "XXY" in result

    def test_xyy_positive(self, config):
        """XYY should always be positive."""
        result, risk = analyze_sca(config, sca_type="XYY", z_xx=-0.5, z_xy=1.5, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "XYY" in result

    def test_xxx_xy_mosaic_positive(self, config):
        """XXX+XY mosaicism should be positive."""
        result, risk = analyze_sca(config, sca_type="XXX+XY", z_xx=2.0, z_xy=2.0, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "XXX+XY" in result

    def test_xo_xy_mosaic_positive_high_z(self, config):
        """XO+XY with high Z-XY should be positive."""
        result, risk = analyze_sca(config, sca_type="XO+XY", z_xx=2.0, z_xy=7.0, cff=8.0, test_number=1)
        assert risk == "POSITIVE"
        assert "XO+XY" in result

    def test_xo_xy_mosaic_ambiguous_low_z(self, config):
        """XO+XY with low Z-XY should be ambiguous."""
        result, risk = analyze_sca(config, sca_type="XO+XY", z_xx=2.0, z_xy=4.0, cff=8.0, test_number=1)
        assert risk == "HIGH"
        assert "Ambiguous" in result

    def test_second_test_normal_female(self, config):
        """Second test XX should indicate test number."""
        result, risk = analyze_sca(config, sca_type="XX", z_xx=0.5, z_xy=-0.5, cff=8.0, test_number=2)
        assert risk == "LOW"
        assert "2nd test" in result

    def test_second_test_low_cff_message(self, config):
        """Second test with low CFF should have specific message."""
        result, risk = analyze_sca(config, sca_type="XX", z_xx=0.5, z_xy=-0.5, cff=2.0, test_number=2)
        assert risk == "INVALID"
        assert "previous result" in result.lower()

    def test_third_test_label(self, config):
        """Third test should be labeled correctly."""
        result, risk = analyze_sca(config, sca_type="XY", z_xx=-0.5, z_xy=0.5, cff=8.0, test_number=3)
        assert risk == "LOW"
        assert "3rd test" in result
