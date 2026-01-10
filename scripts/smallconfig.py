# config.py
# ---------------------------------------------------------
# NIPT Analysis Configuration
# ---------------------------------------------------------

# QUALITY CONTROL (QC) THRESHOLDS
QC_RULES = {
    # Fetal Fraction (Cff) must be between 3.5% and 50% 
    'MIN_CFF_PERCENT': 3.5,
    'MAX_CFF_PERCENT': 50.0,

    # GC Content Ratio must be between 37% and 44% 
    'GC_RATIO_MIN': 37.0,
    'GC_RATIO_MAX': 44.0,

    # Quality Score (QS) Hard Limits 
    # If a sample is negative, QS must be < 2.0.
    # If a sample is positive, QS must be < 1.7.
    'HARD_QS_LIMIT_NEGATIVE': 2.0,
    'HARD_QS_LIMIT_POSITIVE': 1.7
}

# TRISOMY Z-SCORE RISK RANGES (Chr 21, 18, 13) 
# Z-scores determine if we report Low Risk, Ambiguous, or High Risk.
Z_SCORE_CUTOFFS = {
    'LOW_RISK': 2.58,        # Below this is Negative
    'AMBIGUOUS_LOW': 3.0,    # Between 2.58 and 3.0 is "Low Risk but Ambiguous"
    'AMBIGUOUS_HIGH': 4.0,   # Between 3.0 and 4.0 is "High Risk but Ambiguous"
    'HIGH_RISK': 6.0         # Above 6.0 is Positive
}

# SEQUENCING DEPTH THRESHOLDS
# Minimum Unique Reads required (in Millions) 
UNIQ_READS_MIN = {
    'Basic': 5,
    'Standard': 7,
    'Plus': 12,
    'Pro': 20
}
