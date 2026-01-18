"""
UI components package for NRIS.

This package provides reusable UI components for the Streamlit interface.
"""

from .components import (
    render_patient_info_card,
    render_test_result_card,
    escape_html,
    parse_z_scores,
    format_z_score,
    get_status_colors,
    get_qc_color,
    get_summary_color,
)

__all__ = [
    'render_patient_info_card',
    'render_test_result_card',
    'escape_html',
    'parse_z_scores',
    'format_z_score',
    'get_status_colors',
    'get_qc_color',
    'get_summary_color',
]
