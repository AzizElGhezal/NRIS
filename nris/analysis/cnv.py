"""
Copy Number Variation (CNV) analysis functions for NRIS.
"""

from typing import Dict, Tuple, Optional


def analyze_cnv(size: float, ratio: float, test_number: int = 1, config: Optional[Dict] = None) -> Tuple[str, float, str]:
    """CNV (Copy Number Variation) analysis.

    Args:
        size: Size of CNV in megabases (Mb)
        ratio: Abnormal ratio percentage
        test_number: 1 for first test, 2 for second test, 3 for third test
        config: Configuration dictionary (optional, for test-specific thresholds)

    Returns:
        Tuple of (result_text, threshold, risk_level)
    """
    # Get test-specific thresholds if available
    if config:
        test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('CNV', {})
        cnv_thresholds = test_thresholds.get(test_number, {
            '>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0
        })
    else:
        cnv_thresholds = {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0}

    # Determine threshold based on CNV size
    if size >= 10:
        threshold = cnv_thresholds.get('>= 10', 6.0)
    elif size > 7:
        threshold = cnv_thresholds.get('> 7', 8.0)
    elif size > 3.5:
        threshold = cnv_thresholds.get('> 3.5', 10.0)
    else:
        threshold = cnv_thresholds.get('<= 3.5', 12.0)

    # First test logic
    if test_number == 1:
        if ratio >= threshold:
            return f"High Risk -> Re-library", threshold, "HIGH"
        return "Low Risk", threshold, "LOW"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"
        if ratio >= threshold:
            return f"POSITIVE (Ratio:{ratio:.1f}%, {test_label})", threshold, "POSITIVE"
        else:
            return f"High Risk (Ratio:{ratio:.1f}%) -> Resample for verification", threshold, "HIGH"
