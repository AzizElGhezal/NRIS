"""
Sex Chromosome Aneuploidy (SCA) analysis functions for NRIS.
"""

from typing import Dict, Tuple


def analyze_sca(config: Dict, sca_type: str, z_xx: float, z_xy: float, cff: float, test_number: int = 1) -> Tuple[str, str]:
    """Enhanced SCA (Sex Chromosomal Aneuploidies) analysis.

    Args:
        config: Configuration dictionary with clinical thresholds
        sca_type: Type of SCA detected (XX, XY, XO, XXX, XXY, XYY, XXX+XY, XO+XY)
        z_xx: Z-score for XX
        z_xy: Z-score for XY
        cff: Cell-free fetal DNA concentration percentage
        test_number: 1 for first test, 2 for second test, 3 for third test

    Returns:
        Tuple of (result_text, risk_level)

    SCA decision logic:
    First test:
    - XX/XY: Report Negative
    - XYY/XXY/XXX+XY: Report Positive
    - XO: If Z-score(XX) >= 4.5, report XO; else re-library
    - XXX: If Z-score(XX) >= 4.5, report XXX; else re-library
    - XO+XY: If Z-score(XY) >= 6, report XO+XY; else re-library

    Second/Third test:
    - Low CFF (<3.5%): Do not refer to first result
    - When CFF >= 3.5%: More stringent interpretation
    """
    min_cff = config['QC_THRESHOLDS']['MIN_CFF']

    # Get test-specific thresholds if available, otherwise use defaults
    test_thresholds = config.get('TEST_SPECIFIC_THRESHOLDS', {}).get('SCA', {})
    t = test_thresholds.get(test_number, {'xx_threshold': 4.5, 'xy_threshold': 6.0})
    threshold = t['xx_threshold']
    xy_threshold = t['xy_threshold']

    # First test logic
    if test_number == 1:
        if cff < min_cff:
            return "INVALID (Cff < 3.5%) -> Resample", "INVALID"

        if sca_type == "XX":
            return "Negative (Female)", "LOW"
        if sca_type == "XY":
            return "Negative (Male)", "LOW"

        if sca_type == "XO":
            return ("POSITIVE (Turner XO)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XO -> Re-library", "HIGH")

        if sca_type == "XXX":
            return ("POSITIVE (Triple X)", "POSITIVE") if z_xx >= threshold else ("Ambiguous XXX -> Re-library", "HIGH")

        if sca_type == "XXX+XY":
            return "POSITIVE (XXX+XY)", "POSITIVE"

        if sca_type == "XO+XY":
            return ("POSITIVE (XO+XY)", "POSITIVE") if z_xy >= xy_threshold else ("Ambiguous XO+XY -> Re-library", "HIGH")

        if sca_type in ["XXY", "XYY"]:
            return f"POSITIVE ({sca_type})", "POSITIVE"

        return "Ambiguous SCA -> Re-library", "HIGH"

    # Second and third test logic (based on GeneMind documentation)
    else:
        test_label = "2nd test" if test_number == 2 else "3rd test"

        if cff < min_cff:
            return f"INVALID (Cff < 3.5%) -> Do not refer to previous result", "INVALID"

        # Normal karyotypes
        if sca_type == "XX":
            return f"Negative (Female, {test_label})", "LOW"
        if sca_type == "XY":
            return f"Negative (Male, {test_label})", "LOW"

        # Always positive SCAs
        if sca_type in ["XYY", "XXY", "XXX+XY"]:
            return f"POSITIVE ({sca_type}, {test_label})", "POSITIVE"

        # XO: Needs verification based on Z-score consistency
        if sca_type == "XO":
            if z_xx >= threshold:
                return f"POSITIVE (Turner XO, {test_label})", "POSITIVE"
            else:
                return f"XO (Z:{z_xx:.2f}) -> Resample for verification", "HIGH"

        # XXX: Needs verification based on Z-score consistency
        if sca_type == "XXX":
            if z_xx >= threshold:
                return f"POSITIVE (Triple X, {test_label})", "POSITIVE"
            else:
                return f"XXX (Z:{z_xx:.2f}) -> Resample for verification", "HIGH"

        # XO+XY: Needs verification based on Z-score consistency
        if sca_type == "XO+XY":
            if z_xy >= xy_threshold:
                return f"POSITIVE (XO+XY, {test_label})", "POSITIVE"
            else:
                return f"XO+XY (Z:{z_xy:.2f}) -> Resample for verification", "HIGH"

        return f"Ambiguous SCA -> Resample for verification", "HIGH"
