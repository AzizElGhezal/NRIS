"""
UI component rendering functions for NRIS.

This module provides reusable UI components for rendering patient information
cards and test result cards in the Streamlit interface.

Dependencies:
    - streamlit (optional): For rendering UI components
    - json: For parsing JSON data

Example:
    >>> from nris.ui.components import render_patient_info_card
    >>> record = {'full_name': 'John Doe', 'mrn_id': '12345', ...}
    >>> render_patient_info_card(record)
"""

import json
import html as html_module
from typing import Dict, Any, Optional, Union

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None  # type: ignore

from ..analysis.qc import get_reportable_status


def escape_html(val: Any) -> str:
    """Safely escape a value for HTML display.

    Args:
        val: Any value to escape. Will be converted to string.

    Returns:
        HTML-escaped string, or 'N/A' if value is None.

    Example:
        >>> escape_html('<script>alert("xss")</script>')
        '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
        >>> escape_html(None)
        'N/A'
    """
    if val is None:
        return 'N/A'
    return html_module.escape(str(val))


def parse_z_scores(full_z: Union[str, Dict, None]) -> Dict[str, Any]:
    """Parse Z-score data from various formats.

    Args:
        full_z: Z-score data as JSON string, dict, or None.

    Returns:
        Dictionary with Z-scores, empty dict if parsing fails.

    Example:
        >>> parse_z_scores('{"21": 1.5, "18": 0.8}')
        {'21': 1.5, '18': 0.8}
        >>> parse_z_scores(None)
        {}
    """
    if full_z is None:
        return {}

    if isinstance(full_z, dict):
        return full_z

    if isinstance(full_z, str):
        if not full_z or full_z == '{}':
            return {}
        try:
            return json.loads(full_z)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {}

    return {}


def format_z_score(z_value: Any) -> str:
    """Format a Z-score value for display.

    Args:
        z_value: Z-score value (float, int, string, or None).

    Returns:
        Formatted string with 2 decimal places, or 'N/A' if invalid.

    Example:
        >>> format_z_score(1.234)
        '1.23'
        >>> format_z_score('N/A')
        'N/A'
    """
    if z_value is None or z_value == 'N/A':
        return 'N/A'
    try:
        return f"{float(z_value):.2f}"
    except (ValueError, TypeError):
        return 'N/A'


def get_status_colors(summary: str, qc_status: str) -> tuple:
    """Determine display colors based on result status.

    Args:
        summary: Final summary string (e.g., 'NEGATIVE', 'POSITIVE DETECTED').
        qc_status: QC status string (e.g., 'PASS', 'FAIL', 'WARNING').

    Returns:
        Tuple of (border_color, background_color, status_emoji).

    Example:
        >>> get_status_colors('NEGATIVE', 'PASS')
        ('#27AE60', '#EAFAF1', '🟢')
    """
    summary_upper = summary.upper()
    qc_upper = qc_status.upper()

    if 'POSITIVE' in summary_upper:
        return "#E74C3C", "#FDEDEC", "🔴"
    elif 'FAIL' in qc_upper or 'INVALID' in summary_upper:
        return "#E74C3C", "#FDEDEC", "⚠️"
    elif 'WARNING' in qc_upper or 'HIGH RISK' in summary_upper:
        return "#F39C12", "#FEF9E7", "🟠"
    else:
        return "#27AE60", "#EAFAF1", "🟢"


def get_qc_color(qc_status: str) -> str:
    """Get color code for QC status display.

    Args:
        qc_status: QC status string.

    Returns:
        Hex color code for the status.
    """
    status = qc_status.upper()
    if status == 'PASS':
        return '#27AE60'
    elif status == 'FAIL':
        return '#E74C3C'
    return '#F39C12'


def get_summary_color(summary: str) -> str:
    """Get background color for summary display.

    Args:
        summary: Final summary string.

    Returns:
        Hex color code for the summary background.
    """
    summary_upper = summary.upper()
    if 'NEGATIVE' in summary_upper:
        return '#27AE60'
    elif 'POSITIVE' in summary_upper or 'INVALID' in summary_upper:
        return '#E74C3C'
    return '#F39C12'


def render_patient_info_card(
    record: Dict[str, Any],
    show_full_details: bool = False,
    card_key: str = ""
) -> None:
    """Render a styled patient information card.

    Displays patient demographics, QC status, and test summary in a
    color-coded card format. Colors indicate result severity:
    - Green: Negative/Normal
    - Orange: Warning/High Risk
    - Red: Positive/Failed

    Args:
        record: Dictionary containing patient/result data with keys:
            - full_name: Patient's full name
            - mrn_id: Medical Record Number
            - id: Result ID
            - created_at: Timestamp string
            - panel_type: Test panel type
            - qc_status: QC status (PASS/FAIL/WARNING)
            - qc_override: Whether QC was overridden
            - final_summary: Final result summary
            - full_z_json: Z-scores as JSON string or dict
        show_full_details: Whether to show expanded details (unused currently).
        card_key: Unique key for interactive elements (unused currently).

    Returns:
        None. Renders card directly to Streamlit.

    Note:
        This function does nothing if Streamlit is not available.
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return

    summary = str(record.get('final_summary', '')).upper()
    qc_status = str(record.get('qc_status', 'PASS')).upper()

    border_color, bg_color, status_emoji = get_status_colors(summary, qc_status)

    z_data = parse_z_scores(record.get('full_z_json', '{}'))

    z21 = z_data.get('21', z_data.get(21, 'N/A'))
    z18 = z_data.get('18', z_data.get(18, 'N/A'))
    z13 = z_data.get('13', z_data.get(13, 'N/A'))

    z21_str = format_z_score(z21)
    z18_str = format_z_score(z18)
    z13_str = format_z_score(z13)

    full_name = escape_html(record.get('full_name', 'Unknown'))
    record_id = escape_html(record.get('id', 'N/A'))
    created_at = record.get('created_at', 'N/A')
    created_at_str = escape_html(created_at[:16]) if created_at and len(str(created_at)) >= 16 else escape_html(created_at)
    mrn_id = escape_html(record.get('mrn_id', 'N/A'))
    panel_type = escape_html(record.get('panel_type', 'N/A'))
    final_summary_str = escape_html(record.get('final_summary', 'N/A'))

    qc_override = bool(record.get('qc_override', 0))
    effective_qc = 'PASS' if qc_override else qc_status
    qc_color = get_qc_color(effective_qc)
    summary_bg = get_summary_color(summary)

    card_html = f'''
    <div style="border: 2px solid {border_color}; border-radius: 12px; padding: 16px; margin: 10px 0; background-color: {bg_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
                <span style="font-size: 1.3em; font-weight: bold; color: #2C3E50;">{status_emoji} {full_name}</span>
                <span style="background: #3498DB; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; margin-left: 10px;">ID #{record_id}</span>
            </div>
            <div style="text-align: right; color: #7F8C8D; font-size: 0.9em;">{created_at_str}</div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">MRN</div>
                <div style="font-weight: 600; color: #2C3E50;">{mrn_id}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">Panel</div>
                <div style="font-weight: 600; color: #2C3E50;">{panel_type}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 6px;">
                <div style="font-size: 0.8em; color: #7F8C8D;">QC Status</div>
                <div style="font-weight: 600; color: {qc_color};">{effective_qc}</div>
            </div>
        </div>
        <div style="margin-top: 12px; padding: 10px; background: {summary_bg}; border-radius: 6px; text-align: center;">
            <span style="color: white; font-weight: 700; font-size: 1.1em;">{final_summary_str}</span>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)


def render_test_result_card(
    result: Dict[str, Any],
    show_actions: bool = False,
    card_key: str = ""
) -> None:
    """Render a styled test result card.

    Displays a compact result card with QC status and final summary.
    Used for showing individual test results in lists.

    Args:
        result: Dictionary containing test result data with keys:
            - id: Result ID
            - created_at: Timestamp string
            - panel_type: Test panel type
            - test_number: Test iteration (1, 2, or 3)
            - qc_status: QC status (PASS/FAIL/WARNING)
            - qc_override: Whether QC was overridden
            - final_summary: Final result summary
        show_actions: Whether to show action buttons (unused currently).
        card_key: Unique key for interactive elements (unused currently).

    Returns:
        None. Renders card directly to Streamlit.

    Note:
        This function does nothing if Streamlit is not available.
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return

    qc_status = str(result.get('qc_status', 'PASS')).upper()
    qc_override = bool(result.get('qc_override', 0))
    final_summary = str(result.get('final_summary', '')).upper()

    effective_qc = 'PASS' if qc_override else qc_status

    border_color, bg_color, status_icon = get_status_colors(final_summary, effective_qc)

    created_at = result.get('created_at', 'N/A')
    if isinstance(created_at, str) and len(created_at) > 16:
        created_at = created_at[:16]
    created_at_str = escape_html(created_at)

    result_id = escape_html(result.get('id', 'N/A'))
    panel_type = escape_html(result.get('panel_type', 'N/A'))
    test_number = result.get('test_number', 1)
    test_label = f"{'1st' if test_number == 1 else '2nd' if test_number == 2 else '3rd'} Test"
    final_summary_str = escape_html(result.get('final_summary', 'N/A'))

    qc_color = get_qc_color(effective_qc)
    summary_bg = get_summary_color(final_summary)
    test_color = '#3498DB' if test_number == 1 else '#E67E22' if test_number == 2 else '#E74C3C'

    card_html = f'''
    <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 14px; margin: 8px 0; background-color: {bg_color};">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div>
                <span style="font-weight: bold; font-size: 1.1em;">{status_icon} Result #{result_id}</span>
                <span style="background: #9B59B6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 8px;">{panel_type}</span>
                <span style="background: {test_color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin-left: 4px;">{test_label}</span>
            </div>
            <div style="color: #7F8C8D; font-size: 0.85em;">{created_at_str}</div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="background: white; padding: 6px 12px; border-radius: 4px;">
                <span style="font-size: 0.8em; color: #7F8C8D;">QC: </span>
                <span style="font-weight: 600; color: {qc_color};">{effective_qc}</span>
            </div>
            <div style="padding: 6px 12px; border-radius: 4px; background: {summary_bg}; color: white; font-weight: 600;">{final_summary_str}</div>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)
