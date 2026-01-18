"""
Trisomy analysis functions for NRIS.
"""

from typing import Dict, Tuple
import pandas as pd


def analyze_trisomy(config: Dict, z_score: float, chrom: str, test_number: int = 1) -> Tuple[str, str]:
    """Analyze trisomy risk based on Z-score.

    Args:
        config: Configuration dictionary with clinical thresholds
        z_score: Z-score value for the chromosome
        chrom: Chromosome identifier (e.g., "21", "18", "13")
        test_number: 1 for first test, 2 for second test, 3 for third test

    Returns:
        Tuple of (result_text, risk_level)
        - result_text: Human-readable result description
        - risk_level: One of "LOW", "HIGH", "POSITIVE", "UNKNOWN"
    """
    if pd.isna(z_score):
        return "Invalid Data", "UNKNOWN"

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
