"""
UI component rendering functions for NRIS.
"""

import json
import html as html_module
from typing import Dict

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from ..analysis.qc import get_reportable_status


def render_patient_info_card(record: Dict, show_full_details: bool = False, card_key: str = ""):
    """Render a styled patient information card.

    Args:
        record: Dictionary containing patient/result data
        show_full_details: Whether to show all details or a compact view
        card_key: Unique key for interactive elements
    """
    if not STREAMLIT_AVAILABLE:
        return

    def esc(val):
        return html_module.escape(str(val)) if val is not None else 'N/A'

    summary = str(record.get('final_summary', '')).upper()
    qc_status = str(record.get('qc_status', 'PASS')).upper()

    if 'POSITIVE' in summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_emoji = "🔴"
    elif 'FAIL' in qc_status or 'INVALID' in summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_emoji = "⚠️"
    elif 'WARNING' in qc_status or 'HIGH RISK' in summary:
        border_color = "#F39C12"
        bg_color = "#FEF9E7"
        status_emoji = "🟠"
    else:
        border_color = "#27AE60"
        bg_color = "#EAFAF1"
        status_emoji = "🟢"

    full_z = record.get('full_z_json', '{}')
    if isinstance(full_z, str):
        try:
            z_data = json.loads(full_z) if full_z and full_z != '{}' else {}
        except:
            z_data = {}
    else:
        z_data = full_z or {}

    z21 = z_data.get('21', z_data.get(21, 'N/A'))
    z18 = z_data.get('18', z_data.get(18, 'N/A'))
    z13 = z_data.get('13', z_data.get(13, 'N/A'))

    z21_str = f"{float(z21):.2f}" if z21 != 'N/A' and z21 is not None else 'N/A'
    z18_str = f"{float(z18):.2f}" if z18 != 'N/A' and z18 is not None else 'N/A'
    z13_str = f"{float(z13):.2f}" if z13 != 'N/A' and z13 is not None else 'N/A'

    full_name = esc(record.get('full_name', 'Unknown'))
    record_id = esc(record.get('id', 'N/A'))
    created_at = record.get('created_at', 'N/A')
    created_at_str = esc(created_at[:16]) if created_at and len(str(created_at)) >= 16 else esc(created_at)
    mrn_id = esc(record.get('mrn_id', 'N/A'))
    panel_type = esc(record.get('panel_type', 'N/A'))
    final_summary_str = esc(record.get('final_summary', 'N/A'))

    qc_override = bool(record.get('qc_override', 0))
    effective_qc = 'PASS' if qc_override else qc_status
    qc_color = '#27AE60' if effective_qc == 'PASS' else '#E74C3C' if effective_qc == 'FAIL' else '#F39C12'
    summary_bg = '#27AE60' if 'NEGATIVE' in summary else '#E74C3C' if 'POSITIVE' in summary or 'INVALID' in summary else '#F39C12'

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


def render_test_result_card(result: Dict, show_actions: bool = False, card_key: str = ""):
    """Render a styled test result card.

    Args:
        result: Dictionary containing test result data
        show_actions: Whether to show action buttons
        card_key: Unique key for interactive elements
    """
    if not STREAMLIT_AVAILABLE:
        return

    def esc(val):
        return html_module.escape(str(val)) if val is not None else 'N/A'

    qc_status = str(result.get('qc_status', 'PASS')).upper()
    qc_override = bool(result.get('qc_override', 0))
    final_summary = str(result.get('final_summary', '')).upper()

    effective_qc = 'PASS' if qc_override else qc_status

    if 'POSITIVE' in final_summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_icon = "🔴"
    elif 'FAIL' in effective_qc or 'INVALID' in final_summary:
        border_color = "#E74C3C"
        bg_color = "#FDEDEC"
        status_icon = "⚠️"
    elif 'WARNING' in effective_qc or 'HIGH RISK' in final_summary:
        border_color = "#F39C12"
        bg_color = "#FEF9E7"
        status_icon = "🟠"
    else:
        border_color = "#27AE60"
        bg_color = "#EAFAF1"
        status_icon = "🟢"

    created_at = result.get('created_at', 'N/A')
    if isinstance(created_at, str) and len(created_at) > 16:
        created_at = created_at[:16]
    created_at_str = esc(created_at)

    result_id = esc(result.get('id', 'N/A'))
    panel_type = esc(result.get('panel_type', 'N/A'))
    test_number = result.get('test_number', 1)
    test_label = f"{'1st' if test_number == 1 else '2nd' if test_number == 2 else '3rd'} Test"
    final_summary_str = esc(result.get('final_summary', 'N/A'))

    qc_color = '#27AE60' if effective_qc == 'PASS' else '#E74C3C' if effective_qc == 'FAIL' else '#F39C12'
    summary_bg = '#27AE60' if 'NEGATIVE' in final_summary else '#E74C3C' if 'POSITIVE' in final_summary else '#F39C12'
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
