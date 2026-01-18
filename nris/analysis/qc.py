"""
Quality Control (QC) analysis functions for NRIS.
"""

from typing import Dict, List, Tuple


def validate_inputs(reads: float, cff: float, gc: float, age: int) -> List[str]:
    """Validate clinical inputs.

    Args:
        reads: Sequencing reads in millions
        cff: Cell-free fetal fraction percentage
        gc: GC content percentage
        age: Maternal age in years

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    if reads < 0 or reads > 100:
        errors.append("Reads must be 0-100M")
    if cff < 0 or cff > 50:
        errors.append("Cff must be 0-50%")
    if gc < 0 or gc > 100:
        errors.append("GC must be 0-100%")
    if age < 15 or age > 60:
        errors.append("Age must be 15-60")
    return errors


def check_qc_metrics(config: Dict, panel: str, reads: float, cff: float, gc: float,
                     qs: float, uniq: float, error: float, is_positive: bool) -> Tuple[str, List[str], str]:
    """Enhanced QC check with configurable thresholds.

    Args:
        config: Configuration dictionary with QC thresholds
        panel: Panel type name
        reads: Sequencing reads in millions
        cff: Cell-free fetal fraction percentage
        gc: GC content percentage
        qs: Quality score
        uniq: Unique read rate percentage
        error: Sequencing error rate percentage
        is_positive: Whether any result is positive

    Returns:
        Tuple of (status, issues_list, advice_string)
        - status: "PASS", "FAIL", or "WARNING"
        - issues_list: List of issue descriptions
        - advice_string: Recommended action
    """
    thresholds = config['QC_THRESHOLDS']
    issues, advice = [], []

    min_reads = config['PANEL_READ_LIMITS'].get(panel, 5)
    if reads < min_reads:
        issues.append(f"HARD: Reads {reads}M < {min_reads}M")
        advice.append("Resequencing")

    if cff < thresholds['MIN_CFF']:
        issues.append(f"HARD: Cff {cff}% < {thresholds['MIN_CFF']}%")
        advice.append("Resample")

    max_cff = thresholds.get('MAX_CFF', 50.0)
    if cff > max_cff:
        issues.append(f"HARD: Cff {cff}% > {max_cff}%")
        advice.append("Resample")

    gc_range = thresholds['GC_RANGE']
    if not (gc_range[0] <= gc <= gc_range[1]):
        issues.append(f"HARD: GC {gc}% out of range")
        advice.append("Re-library")

    qs_limit = thresholds['QS_LIMIT_POS'] if is_positive else thresholds['QS_LIMIT_NEG']
    if qs >= qs_limit:
        issues.append(f"HARD: QS {qs} >= {qs_limit}")
        advice.append("Re-library")

    if uniq < thresholds['MIN_UNIQ_RATE']:
        issues.append(f"SOFT: UniqueRate {uniq}% Low")
    if error > thresholds['MAX_ERROR_RATE']:
        issues.append(f"SOFT: ErrorRate {error}% High")

    status = "FAIL" if any("HARD" in i for i in issues) else ("WARNING" if issues else "PASS")
    advice_str = " / ".join(set(advice)) if advice else "None"

    return status, issues, advice_str


def get_reportable_status(result_text: str, qc_status: str = "PASS", qc_override: bool = False) -> Tuple[str, str]:
    """Determine if a result should be reported to the patient.

    Args:
        result_text: The result text (e.g., "Low Risk", "High Risk -> Re-library", "POSITIVE")
        qc_status: QC status (PASS, FAIL, WARNING)
        qc_override: Whether QC has been overridden by staff

    Returns:
        Tuple of (reportable_status, reason)
        - "Yes": Result should be reported (positive or negative/low risk)
        - "No": Result requires re-processing (re-library, resample, QC fail)
    """
    result_upper = str(result_text).upper()

    # QC Fail without override -> Not reportable
    if qc_status == "FAIL" and not qc_override:
        return "No", "QC Fail"

    # Check for conditions requiring re-processing
    if "RE-LIBRARY" in result_upper or "RELIBRARY" in result_upper:
        return "No", "Re-library required"
    if "RESAMPLE" in result_upper:
        return "No", "Resample required"
    if "AMBIGUOUS" in result_upper:
        return "No", "Ambiguous result"
    if "INVALID" in result_upper and not qc_override:
        return "No", "Invalid result"

    # POSITIVE or Low Risk -> Reportable
    if "POSITIVE" in result_upper:
        return "Yes", "Screen Positive"
    if "LOW" in result_upper or "NEGATIVE" in result_upper:
        return "Yes", "Screen Negative"

    # Default: assume reportable if none of the above conditions match
    return "Yes", "Result available"
