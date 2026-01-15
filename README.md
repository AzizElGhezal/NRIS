# NRIS - NIPT Result Interpretation Software

![Version](https://img.shields.io/badge/version-2.4-blue) ![Python](https://img.shields.io/badge/python-3.8+-green) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

A clinical genetics dashboard for Non-Invasive Prenatal Testing (NIPT) result management, quality control, and reporting. Designed for genetics laboratories and prenatal diagnosis centers.

## Features

**Analysis & Detection**
- Trisomy screening (T21, T18, T13) with Z-score interpretation
- Sex chromosome aneuploidy (SCA) detection
- Rare autosomal trisomy (RAT) and copy number variation (CNV) analysis
- Multi-panel support (Basic, Standard, Plus, Pro) with test-specific thresholds

**Clinical Workflow**
- Patient registry with demographics and test history
- Automatic PDF data extraction with confidence scoring
- Batch import for high-throughput processing
- Bilingual PDF reports (English/French)

**Quality & Compliance**
- Multi-metric QC validation (CFF, GC content, read rates)
- Role-based access (Admin, Geneticist, Technician)
- Complete audit trail for regulatory compliance
- Automatic backups with integrity verification

## Requirements

- Python 3.8+
- Dependencies: Streamlit, Pandas, Plotly, ReportLab, PyPDF2

## Quick Start

**Windows:** Double-click `start_NRIS_v2.bat` — browser opens automatically.

**Manual Installation:**
```bash
git clone https://github.com/AzizElGhezal/NRIS.git
cd NRIS
python -m venv venv_NRIS_v2
source venv_NRIS_v2/bin/activate  # Windows: venv_NRIS_v2\Scripts\activate
pip install -r requirements_NRIS_v2.txt
streamlit run NRIS_Enhanced.py
```

**Default login:** `admin` / `admin123` (password change required on first login)

## Configuration

All thresholds are configurable via the **Settings** tab without code changes:

| Category | Parameters |
|----------|------------|
| QC Thresholds | CFF range, GC content, unique read rate, error rate |
| Clinical Thresholds | Trisomy risk cutoffs, SCA thresholds, CNV size limits |
| Report Settings | Default language, MRN format validation |

For advanced customization (PDF patterns, encryption, branding), see [CUSTOMIZATION_GUIDE.md](CUSTOMIZATION_GUIDE.md).

## Documentation

- **[CUSTOMIZATION_GUIDE.md](CUSTOMIZATION_GUIDE.md)** - PDF patterns, encryption options, report customization

## Author

**Aziz El Ghezal**

## Disclaimer

For clinical decision support only. Results must be interpreted by qualified healthcare professionals. Does not replace professional medical judgment.
