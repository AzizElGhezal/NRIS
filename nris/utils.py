"""
Utility functions for NRIS.
"""

import re
from typing import Tuple, Dict


def validate_mrn(mrn: str, allow_alphanumeric: bool = False) -> Tuple[bool, str]:
    """Validate MRN format for clinical use.

    Args:
        mrn: The MRN string to validate
        allow_alphanumeric: If True, allows letters, digits, hyphens, and underscores
                          If False (default), only allows digits (strict numerical mode)

    Returns:
        (is_valid, error_message)

    Note: For clinical systems, numerical MRNs are recommended to avoid confusion.
          Leading zeros are preserved (e.g., "00123" is different from "123").
    """
    if not mrn or not mrn.strip():
        return False, "MRN cannot be empty"

    mrn = mrn.strip()

    if len(mrn) > 50:
        return False, "MRN too long (max 50 characters)"

    if allow_alphanumeric:
        # Allow alphanumeric MRNs for backward compatibility
        # Format: letters, digits, hyphens, underscores only
        if not all(c.isalnum() or c in '-_' for c in mrn):
            return False, "MRN can only contain letters, digits, hyphens, and underscores"
    else:
        # Strict numerical mode (default for clinical consistency)
        if not mrn.isdigit():
            return False, "MRN must be numerical (digits only). Use 'Allow Alphanumeric MRNs' in Settings if needed."

    return True, ""


def get_maternal_age_risk(age: int) -> Dict[str, float]:
    """Calculate maternal age-based prior risk for common aneuploidies.

    Based on published maternal age-specific risk data (Hook EB, 1981 and updated studies).

    Args:
        age: Maternal age in years

    Returns:
        Dictionary with risk values for T21, T18, T13
    """
    age_risk_table = {
        20: {'T21': 1/1441, 'T18': 1/10000, 'T13': 1/14300},
        25: {'T21': 1/1383, 'T18': 1/8300, 'T13': 1/12500},
        30: {'T21': 1/959, 'T18': 1/5900, 'T13': 1/9100},
        32: {'T21': 1/659, 'T18': 1/4500, 'T13': 1/7100},
        34: {'T21': 1/446, 'T18': 1/3300, 'T13': 1/5200},
        35: {'T21': 1/356, 'T18': 1/2700, 'T13': 1/4200},
        36: {'T21': 1/280, 'T18': 1/2200, 'T13': 1/3400},
        37: {'T21': 1/218, 'T18': 1/1800, 'T13': 1/2700},
        38: {'T21': 1/167, 'T18': 1/1400, 'T13': 1/2100},
        39: {'T21': 1/128, 'T18': 1/1100, 'T13': 1/1700},
        40: {'T21': 1/97, 'T18': 1/860, 'T13': 1/1300},
        41: {'T21': 1/73, 'T18': 1/670, 'T13': 1/1000},
        42: {'T21': 1/55, 'T18': 1/530, 'T13': 1/800},
        43: {'T21': 1/41, 'T18': 1/410, 'T13': 1/630},
        44: {'T21': 1/30, 'T18': 1/320, 'T13': 1/490},
        45: {'T21': 1/23, 'T18': 1/250, 'T13': 1/380},
    }

    if age < 20:
        return age_risk_table[20]
    elif age >= 45:
        return age_risk_table[45]

    # Linear interpolation for ages between table values
    sorted_ages = sorted(age_risk_table.keys())
    for i, table_age in enumerate(sorted_ages):
        if age <= table_age:
            if age == table_age:
                return age_risk_table[table_age]
            prev_age = sorted_ages[i-1] if i > 0 else table_age
            next_age = table_age
            ratio = (age - prev_age) / (next_age - prev_age) if next_age != prev_age else 0
            prev_risks = age_risk_table.get(prev_age, age_risk_table[20])
            next_risks = age_risk_table.get(next_age, age_risk_table[45])
            return {
                'T21': prev_risks['T21'] + (next_risks['T21'] - prev_risks['T21']) * ratio,
                'T18': prev_risks['T18'] + (next_risks['T18'] - prev_risks['T18']) * ratio,
                'T13': prev_risks['T13'] + (next_risks['T13'] - prev_risks['T13']) * ratio,
            }

    return age_risk_table[45]


def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float."""
    try:
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default


def safe_int(value: str, default: int = 0) -> int:
    """Safely convert string to int."""
    try:
        cleaned = re.sub(r'[^\d\-]', '', str(value))
        return int(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default
