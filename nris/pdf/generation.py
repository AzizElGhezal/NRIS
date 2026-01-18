"""
PDF report generation functions for NRIS.
"""

import io
import json
from datetime import datetime
from typing import Optional, Dict

try:
    import pandas as pd
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from ..config import load_config, get_translation
from ..database import get_db_connection
from ..utils import get_maternal_age_risk
from ..analysis.qc import get_reportable_status


def get_clinical_recommendation(result: str, test_type: str) -> str:
    """Generate clinical recommendation based on test result.

    Args:
        result: Result text (e.g., "POSITIVE", "Low Risk")
        test_type: Type of test (T21, T18, T13, SCA, CNV, RAT)

    Returns:
        Clinical recommendation string
    """
    recommendations = {
        'POSITIVE': {
            'T21': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Genetic counseling should be offered.",
            'T18': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.",
            'T13': "Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.",
            'SCA': "Genetic counseling recommended. Confirmatory testing may be considered based on clinical judgment.",
            'CNV': "Detailed ultrasound recommended. Genetic counseling and possible confirmatory testing advised.",
            'RAT': "Genetic counseling recommended. Clinical correlation and possible confirmatory testing advised."
        },
        'HIGH': {
            'default': "Re-analysis recommended. If persistent, consider confirmatory diagnostic testing."
        },
        'LOW': {
            'default': "No additional testing indicated based on NIPT result alone. Standard prenatal care recommended."
        }
    }

    if 'POSITIVE' in result.upper():
        return recommendations['POSITIVE'].get(test_type, recommendations['POSITIVE'].get('default', ''))
    elif 'HIGH' in result.upper() or 'AMBIGUOUS' in result.upper():
        return recommendations['HIGH']['default']
    else:
        return recommendations['LOW']['default']


def generate_pdf_report(report_id: int, lang: str = None) -> Optional[bytes]:
    """Generate comprehensive clinical PDF report.

    Args:
        report_id: The ID of the result to generate a report for
        lang: Language code ('en' for English, 'fr' for French)

    Returns:
        PDF bytes or None if generation fails
    """
    if not REPORTLAB_AVAILABLE:
        return None

    try:
        config = load_config()
        if lang is None:
            lang = config.get('REPORT_LANGUAGE', 'en')

        def t(key: str) -> str:
            return get_translation(key, lang)

        with get_db_connection() as conn:
            query = """
                SELECT r.id, p.full_name, p.mrn_id, p.age, p.weeks, r.created_at, p.clinical_notes,
                       r.panel_type, r.qc_status, r.qc_details, r.qc_advice, r.qc_metrics_json,
                       r.t21_res, r.t18_res, r.t13_res, r.sca_res,
                       r.cnv_json, r.rat_json, r.full_z_json, r.final_summary,
                       p.weight_kg, p.height_cm, p.bmi,
                       u.full_name as technician_name,
                       r.qc_override, r.qc_override_reason, r.qc_override_at,
                       ov_user.full_name as qc_override_by_name,
                       r.test_number
                FROM results r
                JOIN patients p ON p.id = r.patient_id
                LEFT JOIN users u ON u.id = r.created_by
                LEFT JOIN users ov_user ON ov_user.id = r.qc_override_by
                WHERE r.id = ?
            """
            df = pd.read_sql(query, conn, params=(report_id,))

        if df.empty:
            return None

        row = df.iloc[0]
        cnvs = json.loads(row['cnv_json']) if row['cnv_json'] else []
        rats = json.loads(row['rat_json']) if row['rat_json'] else []
        z_data = json.loads(row['full_z_json']) if row['full_z_json'] else {}
        qc_metrics = json.loads(row['qc_metrics_json']) if row.get('qc_metrics_json') else {}

        qc_override = bool(row.get('qc_override'))
        qc_override_reason = row.get('qc_override_reason', '')
        qc_override_by = row.get('qc_override_by_name', '')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.4*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16,
                                     textColor=colors.HexColor('#1a5276'), alignment=TA_CENTER,
                                     spaceAfter=6)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10,
                                        alignment=TA_CENTER, textColor=colors.HexColor('#566573'))
        section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=11,
                                       textColor=colors.HexColor('#2c3e50'), spaceBefore=10, spaceAfter=4)
        small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8,
                                     textColor=colors.HexColor('#7f8c8d'))
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8,
                                    leading=10, wordWrap='CJK')

        # Header
        story.append(Paragraph(t('lab_title'), title_style))
        story.append(Paragraph(t('report_title'), subtitle_style))
        story.append(Spacer(1, 0.15*inch))

        # Report metadata
        report_date = row['created_at'][:10] if row['created_at'] else datetime.now().strftime('%Y-%m-%d')
        test_num = row.get('test_number', 1)
        test_num_label = t('first_test') if test_num == 1 else (t('second_test') if test_num == 2 else t('third_test'))

        meta_data = [
            [t('report_id'), str(row['id']), t('report_date'), report_date],
            [t('panel_type'), row['panel_type'], t('test_number'), test_num_label],
        ]
        meta_table = Table(meta_data, colWidths=[1.1*inch, 2.2*inch, 1.1*inch, 2.1*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.1*inch))

        # Patient information
        story.append(Paragraph(t('patient_info'), section_style))
        bmi_val = row['bmi'] if row['bmi'] else (
            round(row['weight_kg'] / ((row['height_cm']/100)**2), 1)
            if row['weight_kg'] and row['height_cm'] and row['height_cm'] > 0 else 'N/A'
        )

        patient_data = [
            [t('name'), str(row['full_name']), t('mrn'), str(row['mrn_id'])],
            [t('maternal_age'), f"{row['age']} {t('years')}", t('gestational_age'), f"{row['weeks']} {t('weeks')}"],
        ]
        patient_table = Table(patient_data, colWidths=[1.1*inch, 2.2*inch, 1.1*inch, 2.1*inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 0.1*inch))

        # Results section
        story.append(Paragraph(t('aneuploidy_results'), section_style))

        z21 = z_data.get('21', z_data.get(21, 'N/A'))
        z18 = z_data.get('18', z_data.get(18, 'N/A'))
        z13 = z_data.get('13', z_data.get(13, 'N/A'))

        def fmt_z(z):
            return f"{z:.2f}" if isinstance(z, (int, float)) else str(z)

        effective_qc_status = 'PASS' if qc_override else (row['qc_status'] or 'PASS')
        t21_reportable, _ = get_reportable_status(str(row['t21_res']), effective_qc_status, qc_override)
        t18_reportable, _ = get_reportable_status(str(row['t18_res']), effective_qc_status, qc_override)
        t13_reportable, _ = get_reportable_status(str(row['t13_res']), effective_qc_status, qc_override)

        results_header = [[t('condition'), t('result'), t('z_score'), t('reportable')]]
        results_rows = [
            [t('trisomy_21'), str(row['t21_res']), fmt_z(z21), t21_reportable],
            [t('trisomy_18'), str(row['t18_res']), fmt_z(z18), t18_reportable],
            [t('trisomy_13'), str(row['t13_res']), fmt_z(z13), t13_reportable],
            [t('sca'), str(row['sca_res']), '-', '-'],
        ]

        results_data = results_header + results_rows
        results_table = Table(results_data, colWidths=[2*inch, 2*inch, 1*inch, 1.2*inch])
        results_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(results_table)
        story.append(Spacer(1, 0.1*inch))

        # Final interpretation
        story.append(Paragraph(t('final_interpretation'), section_style))
        final_summary = row['final_summary']
        final_color = colors.HexColor('#27ae60') if 'NEGATIVE' in str(final_summary).upper() else (
            colors.HexColor('#e74c3c') if 'POSITIVE' in str(final_summary).upper() else colors.HexColor('#f39c12'))

        final_cell_style = ParagraphStyle('FinalCell', parent=styles['Normal'], fontSize=12,
                                          leading=14, alignment=TA_CENTER, textColor=colors.whitesmoke,
                                          fontName='Helvetica-Bold')
        final_box = Table([[Paragraph(str(final_summary), final_cell_style)]], colWidths=[6.5*inch])
        final_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), final_color),
            ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ('TOPPADDING', (0, 0), (0, 0), 10),
        ]))
        story.append(final_box)
        story.append(Spacer(1, 0.1*inch))

        # Disclaimer
        story.append(Paragraph(t('limitations'), section_style))
        disclaimer_text = f"""
        <b>{t('important_info')}</b><br/>
        {t('disclaimer_1')}<br/>
        {t('disclaimer_2')}
        """
        story.append(Paragraph(disclaimer_text, small_style))
        story.append(Spacer(1, 0.15*inch))

        # Footer
        footer_text = f"{t('report_generated')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {t('version')}"
        story.append(Paragraph(footer_text, small_style))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        return None
