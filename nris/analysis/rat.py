"""
Rare Autosomal Trisomy (RAT) analysis functions for NRIS.
"""

from typing import Dict, Tuple


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
