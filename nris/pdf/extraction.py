"""
PDF data extraction functions for NRIS.
"""

import re
from typing import Dict, List, Optional, Tuple

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from ..utils import safe_float, safe_int

# PDF validation constants
MAX_PDF_SIZE_MB = 50
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
MIN_TEXT_LENGTH = 100


def validate_pdf_file(pdf_file, filename: str = "") -> Tuple[bool, str]:
    """Validate PDF file before processing.

    Args:
        pdf_file: File-like object containing PDF data
        filename: Original filename for extension checking

    Returns:
        (is_valid, error_message)
    """
    # Check file extension
    if filename:
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{ext}' not in ALLOWED_PDF_EXTENSIONS:
            return False, f"Invalid file type: .{ext}. Only PDF files are allowed."

    # Check file size
    try:
        pdf_file.seek(0, 2)
        size_bytes = pdf_file.tell()
        pdf_file.seek(0)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > MAX_PDF_SIZE_MB:
            return False, f"File too large: {size_mb:.1f}MB. Maximum allowed is {MAX_PDF_SIZE_MB}MB."
    except Exception:
        pass

    # Verify it's a valid PDF by checking header
    try:
        pdf_file.seek(0)
        header = pdf_file.read(8)
        pdf_file.seek(0)
        if isinstance(header, bytes):
            header = header.decode('latin-1', errors='ignore')
        if not header.startswith('%PDF'):
            return False, "Invalid PDF file: missing PDF header signature."
    except Exception:
        pass

    return True, ""


def extract_with_fallback(text: str, patterns: List[str], group: int = 1,
                          flags: int = re.IGNORECASE) -> Optional[str]:
    """Try multiple regex patterns and return first match."""
    for pattern in patterns:
        try:
            match = re.search(pattern, text, flags)
            if match:
                return match.group(group).strip()
        except (re.error, IndexError):
            continue
    return None


def extract_data_from_pdf(pdf_file, filename: str = "") -> Optional[Dict]:
    """Extract comprehensive patient and test data from PDF report.

    Args:
        pdf_file: File-like object containing PDF data
        filename: Original filename

    Returns:
        Dict with extracted data or None if extraction fails
    """
    if PyPDF2 is None:
        return None

    extraction_warnings = []

    # Validate PDF file first
    is_valid, error_msg = validate_pdf_file(pdf_file, filename)
    if not is_valid:
        extraction_warnings.append(error_msg)

    try:
        pdf_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        if len(pdf_reader.pages) == 0:
            return None

        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception:
                extraction_warnings.append(f"Could not extract text from page {page_num + 1}")

        if len(text.strip()) < MIN_TEXT_LENGTH:
            extraction_warnings.append("Low text content - possible scanned PDF")

        # Clean up text
        text = re.sub(r'\s+', ' ', text)

        # Initialize data structure
        data = {
            'source_file': filename,
            'patient_name': '',
            'mrn': '',
            'age': 0,
            'weight': 0.0,
            'height': 0,
            'bmi': 0.0,
            'weeks': 0,
            'panel': 'NIPT Standard',
            'reads': 0.0,
            'cff': 0.0,
            'gc': 0.0,
            'qs': 0.0,
            'unique_rate': 0.0,
            'error_rate': 0.0,
            'z_scores': {},
            'sca_type': 'XX',
            'cnv_findings': [],
            'rat_findings': [],
            'qc_status': '',
            'final_result': '',
            'notes': '',
            'extraction_confidence': 'HIGH'
        }

        # Extract patient name
        name_patterns = [
            r'(?:Patient|Patient\s+Name|Name)[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|ID|Age|DOB|Date|\||,|\n|$))',
            r'Full\s+Name[:\s]+([A-Za-z][A-Za-z\s\-\'\.]+?)(?:\s*(?:MRN|\n|$))',
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()
                name = re.sub(r'[\d\|\,]+$', '', name).strip()
                if len(name) > 2:
                    data['patient_name'] = name
                    break

        # Extract MRN
        mrn_patterns = [
            r'MRN[:\s#]+([A-Za-z0-9\-]+)',
            r'(?:Patient\s+)?ID[:\s#]+([A-Za-z0-9\-]{4,})',
            r'Sample\s+ID[:\s]+([A-Za-z0-9\-]+)',
        ]
        for pattern in mrn_patterns:
            mrn_match = re.search(pattern, text, re.IGNORECASE)
            if mrn_match:
                data['mrn'] = mrn_match.group(1).strip()
                break

        # Extract age
        age_patterns = [
            r'(?:Maternal\s+)?Age[:\s]+(\d{1,2})\s*(?:years?|yrs?|y)?(?:\s|,|\.|$)',
        ]
        for pattern in age_patterns:
            age_match = re.search(pattern, text, re.IGNORECASE)
            if age_match:
                age = int(age_match.group(1))
                if 15 <= age <= 60:
                    data['age'] = age
                    break

        # Extract weight
        weight_patterns = [
            r'Weight[:\s]+(\d+\.?\d*)\s*(?:kg|KG|kilograms?)',
        ]
        for pattern in weight_patterns:
            weight_match = re.search(pattern, text, re.IGNORECASE)
            if weight_match:
                weight = float(weight_match.group(1))
                if 30 <= weight <= 200:
                    data['weight'] = round(weight, 1)
                    break

        # Extract height
        height_patterns = [
            r'Height[:\s]+(\d{2,3})\s*(?:cm|CM|centimeters?)',
        ]
        for pattern in height_patterns:
            height_match = re.search(pattern, text, re.IGNORECASE)
            if height_match:
                height = int(height_match.group(1))
                if 100 <= height <= 220:
                    data['height'] = height
                    break

        # Calculate BMI if not present
        if not data['bmi'] and data['weight'] > 0 and data['height'] > 0:
            data['bmi'] = round(data['weight'] / ((data['height']/100)**2), 1)

        # Extract gestational weeks
        weeks_patterns = [
            r'(?:Gestational\s+Age|GA)[:\s]+(\d{1,2})\s*(?:\+\s*\d+)?(?:\s*weeks?|\s*wks?)?',
        ]
        for pattern in weeks_patterns:
            weeks_match = re.search(pattern, text, re.IGNORECASE)
            if weeks_match:
                weeks = int(weeks_match.group(1))
                if 9 <= weeks <= 42:
                    data['weeks'] = weeks
                    break

        # Extract sequencing reads
        reads_patterns = [
            r'(?:Total\s+)?Reads?[:\s]+(\d+\.?\d*)\s*(?:M|million)',
        ]
        for pattern in reads_patterns:
            reads_match = re.search(pattern, text, re.IGNORECASE)
            if reads_match:
                reads = float(reads_match.group(1))
                if reads > 100:
                    reads = reads / 1000000
                if 0.1 <= reads <= 100:
                    data['reads'] = round(reads, 2)
                    break

        # Extract fetal fraction
        cff_patterns = [
            r'(?:Cff|FF|Fetal\s+Fraction)[:\s]+(\d+\.?\d*)\s*%?',
        ]
        for pattern in cff_patterns:
            cff_match = re.search(pattern, text, re.IGNORECASE)
            if cff_match:
                cff = float(cff_match.group(1))
                if 0.5 <= cff <= 50:
                    data['cff'] = round(cff, 2)
                    break

        # Extract GC content
        gc_patterns = [
            r'GC\s*(?:Content)?[:\s]+(\d+\.?\d*)\s*%?',
        ]
        for pattern in gc_patterns:
            gc_match = re.search(pattern, text, re.IGNORECASE)
            if gc_match:
                gc = float(gc_match.group(1))
                if 20 <= gc <= 80:
                    data['gc'] = round(gc, 2)
                    break

        # Extract Z-scores for main trisomies
        def extract_z_score(patterns_list, search_text):
            all_matches = []
            for pattern in patterns_list:
                for match in re.finditer(pattern, search_text, re.IGNORECASE):
                    try:
                        z_val = float(match.group(1))
                        if -20 <= z_val <= 50:
                            all_matches.append((match.start(), z_val))
                    except (ValueError, IndexError):
                        continue
            if all_matches:
                all_matches.sort(key=lambda x: x[0])
                return round(all_matches[-1][1], 3)
            return None

        for chrom in [13, 18, 21]:
            z_patterns = [
                rf'(?:Trisomy\s*)?{chrom}[^)]*?\(Z[:\s]*(-?\d+\.?\d*)\)',
                rf'Z[-\s]?{chrom}\b[:\s]+(-?\d+\.?\d*)',
            ]
            z_val = extract_z_score(z_patterns, text)
            if z_val is not None:
                data['z_scores'][chrom] = z_val

        # Extract SCA Z-scores
        z_xx_patterns = [
            r'Z[-\s]?XX\b[:\s]*(-?\d+\.?\d*)',
        ]
        z_val = extract_z_score(z_xx_patterns, text)
        if z_val is not None:
            data['z_scores']['XX'] = z_val

        z_xy_patterns = [
            r'Z[-\s]?XY\b[:\s]*(-?\d+\.?\d*)',
        ]
        z_val = extract_z_score(z_xy_patterns, text)
        if z_val is not None:
            data['z_scores']['XY'] = z_val

        # Detect SCA type
        sca_patterns = [
            (r'XXX\+XY|XXX\s*\+\s*XY', 'XXX+XY'),
            (r'XO\+XY|XO\s*\+\s*XY', 'XO+XY'),
            (r'Turner|Monosomy\s+X|45[,\s]*X(?:O)?', 'XO'),
            (r'Triple\s+X|Trisomy\s+X|47[,\s]*XXX', 'XXX'),
            (r'Klinefelter|47[,\s]*XXY', 'XXY'),
            (r'47[,\s]*XYY', 'XYY'),
            (r'(?:Fetal\s+)?Sex[:\s]+Male|XY\s+(?:Male|detected)', 'XY'),
            (r'(?:Fetal\s+)?Sex[:\s]+Female|XX\s+(?:Female|detected)', 'XX'),
        ]
        for pattern, sca_type in sca_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                data['sca_type'] = sca_type
                break

        # Calculate extraction confidence
        critical_fields = {
            'patient_name': bool(data['patient_name']),
            'mrn': bool(data['mrn']),
            'age': data['age'] > 0,
            'weeks': data['weeks'] > 0,
            'cff': data['cff'] > 0,
            'z_scores': len(data['z_scores']) >= 3,
        }

        extracted_count = sum(critical_fields.values())
        if extracted_count >= 5:
            data['extraction_confidence'] = 'HIGH'
        elif extracted_count >= 3:
            data['extraction_confidence'] = 'MEDIUM'
        else:
            data['extraction_confidence'] = 'LOW'

        data['_extraction_warnings'] = extraction_warnings
        data['_extracted_count'] = extracted_count

        return data

    except Exception as e:
        return None


def parse_pdf_batch(pdf_files: List) -> Dict[str, List[Dict]]:
    """Parse multiple PDF files and group by patient MRN.

    Args:
        pdf_files: List of file-like objects

    Returns:
        Dictionary with 'patients' (grouped by MRN) and 'errors' lists
    """
    patients = {}
    errors = []

    for pdf_file in pdf_files:
        filename = pdf_file.name if hasattr(pdf_file, 'name') else 'unknown.pdf'
        data = extract_data_from_pdf(pdf_file, filename)

        if data:
            if data['mrn']:
                mrn = data['mrn']
                if mrn not in patients:
                    patients[mrn] = []
                patients[mrn].append(data)
            else:
                errors.append(f"No MRN found in {filename}")
        else:
            errors.append(f"Failed to extract data from {filename}")

    return {'patients': patients, 'errors': errors}
