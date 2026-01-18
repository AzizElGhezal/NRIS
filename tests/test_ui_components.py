"""
Unit tests for UI component helper functions.

Note: These tests focus on the pure functions that don't require Streamlit.
The render functions are tested for their logic, not their Streamlit output.
"""

import pytest
import json

from nris.ui.components import (
    escape_html,
    parse_z_scores,
    format_z_score,
    get_status_colors,
    get_qc_color,
    get_summary_color,
)


class TestEscapeHtml:
    """Test cases for HTML escaping function."""

    def test_normal_string(self):
        """Normal strings should pass through."""
        assert escape_html("John Doe") == "John Doe"

    def test_none_value(self):
        """None should return 'N/A'."""
        assert escape_html(None) == "N/A"

    def test_html_tags_escaped(self):
        """HTML tags should be escaped."""
        result = escape_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_quotes_escaped(self):
        """Quotes should be escaped."""
        result = escape_html('Test "quoted" text')
        assert "&quot;" in result

    def test_ampersand_escaped(self):
        """Ampersands should be escaped."""
        result = escape_html("A & B")
        assert "&amp;" in result

    def test_numeric_value(self):
        """Numeric values should be converted to string."""
        assert escape_html(12345) == "12345"
        assert escape_html(3.14) == "3.14"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert escape_html("") == ""

    def test_special_characters(self):
        """Special characters should be handled."""
        result = escape_html("<>&\"'")
        assert "<" not in result
        assert ">" not in result


class TestParseZScores:
    """Test cases for Z-score parsing function."""

    def test_valid_json_string(self):
        """Valid JSON string should be parsed."""
        result = parse_z_scores('{"21": 1.5, "18": 0.8, "13": -0.2}')
        assert result == {"21": 1.5, "18": 0.8, "13": -0.2}

    def test_dict_input(self):
        """Dict input should be returned as-is."""
        data = {"21": 1.5, "18": 0.8}
        result = parse_z_scores(data)
        assert result == data

    def test_none_input(self):
        """None should return empty dict."""
        assert parse_z_scores(None) == {}

    def test_empty_string(self):
        """Empty string should return empty dict."""
        assert parse_z_scores("") == {}

    def test_empty_json_object(self):
        """Empty JSON object string should return empty dict."""
        assert parse_z_scores("{}") == {}

    def test_invalid_json(self):
        """Invalid JSON should return empty dict."""
        assert parse_z_scores("not valid json") == {}
        assert parse_z_scores("{invalid}") == {}

    def test_json_with_integer_keys(self):
        """JSON with integer keys should be parsed."""
        result = parse_z_scores('{"21": 1.5}')
        assert "21" in result

    def test_nested_json(self):
        """Nested JSON should be parsed correctly."""
        result = parse_z_scores('{"21": 1.5, "extra": {"nested": true}}')
        assert result["21"] == 1.5


class TestFormatZScore:
    """Test cases for Z-score formatting function."""

    def test_float_value(self):
        """Float should be formatted to 2 decimal places."""
        assert format_z_score(1.234) == "1.23"
        assert format_z_score(1.235) == "1.24"  # Rounding

    def test_integer_value(self):
        """Integer should be formatted with decimal places."""
        assert format_z_score(2) == "2.00"

    def test_negative_value(self):
        """Negative values should be formatted correctly."""
        assert format_z_score(-1.5) == "-1.50"

    def test_none_value(self):
        """None should return 'N/A'."""
        assert format_z_score(None) == "N/A"

    def test_na_string(self):
        """'N/A' string should return 'N/A'."""
        assert format_z_score("N/A") == "N/A"

    def test_string_number(self):
        """String number should be converted and formatted."""
        assert format_z_score("1.5") == "1.50"

    def test_invalid_string(self):
        """Invalid string should return 'N/A'."""
        assert format_z_score("not a number") == "N/A"

    def test_zero_value(self):
        """Zero should be formatted correctly."""
        assert format_z_score(0) == "0.00"

    def test_large_value(self):
        """Large values should be formatted."""
        assert format_z_score(100.123) == "100.12"


class TestGetStatusColors:
    """Test cases for status color determination."""

    def test_positive_result(self):
        """Positive result should return red colors."""
        border, bg, emoji = get_status_colors("POSITIVE DETECTED", "PASS")
        assert border == "#E74C3C"
        assert emoji == "🔴"

    def test_negative_pass(self):
        """Negative with PASS QC should return green colors."""
        border, bg, emoji = get_status_colors("NEGATIVE", "PASS")
        assert border == "#27AE60"
        assert emoji == "🟢"

    def test_qc_fail(self):
        """QC FAIL should return red colors."""
        border, bg, emoji = get_status_colors("NEGATIVE", "FAIL")
        assert border == "#E74C3C"
        assert emoji == "⚠️"

    def test_invalid_summary(self):
        """INVALID summary should return red colors."""
        border, bg, emoji = get_status_colors("INVALID (QC FAIL)", "PASS")
        assert border == "#E74C3C"

    def test_high_risk(self):
        """HIGH RISK should return orange colors."""
        border, bg, emoji = get_status_colors("HIGH RISK (SEE ADVICE)", "PASS")
        assert border == "#F39C12"
        assert emoji == "🟠"

    def test_warning_qc(self):
        """QC WARNING should return orange colors."""
        border, bg, emoji = get_status_colors("NEGATIVE", "WARNING")
        assert border == "#F39C12"
        assert emoji == "🟠"

    def test_case_insensitive(self):
        """Status matching should be case-insensitive."""
        border1, _, _ = get_status_colors("positive", "pass")
        border2, _, _ = get_status_colors("POSITIVE", "PASS")
        assert border1 == border2


class TestGetQCColor:
    """Test cases for QC color function."""

    def test_pass_color(self):
        """PASS should return green."""
        assert get_qc_color("PASS") == "#27AE60"

    def test_fail_color(self):
        """FAIL should return red."""
        assert get_qc_color("FAIL") == "#E74C3C"

    def test_warning_color(self):
        """WARNING should return orange."""
        assert get_qc_color("WARNING") == "#F39C12"

    def test_unknown_status(self):
        """Unknown status should return orange (default)."""
        assert get_qc_color("UNKNOWN") == "#F39C12"

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert get_qc_color("pass") == "#27AE60"
        assert get_qc_color("Pass") == "#27AE60"


class TestGetSummaryColor:
    """Test cases for summary color function."""

    def test_negative_color(self):
        """NEGATIVE should return green."""
        assert get_summary_color("NEGATIVE") == "#27AE60"

    def test_positive_color(self):
        """POSITIVE should return red."""
        assert get_summary_color("POSITIVE DETECTED") == "#E74C3C"

    def test_invalid_color(self):
        """INVALID should return red."""
        assert get_summary_color("INVALID (QC FAIL)") == "#E74C3C"

    def test_high_risk_color(self):
        """HIGH RISK should return orange."""
        assert get_summary_color("HIGH RISK (SEE ADVICE)") == "#F39C12"

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert get_summary_color("negative") == "#27AE60"
