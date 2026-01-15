# NRIS - NIPT Result Interpretation Software

**Version 2.4**

A clinical genetics dashboard for managing and interpreting Non-Invasive Prenatal Testing (NIPT) results.

---

## Features

- **User Authentication** - Role-based access control (Admin, Geneticist, Technician)
- **Patient Management** - Demographics, MRN tracking, BMI and gestational age
- **NIPT Analysis** - Multiple panels, QC validation, trisomy risk assessment, SCA detection, RAT analysis
- **PDF Import** - Extract data from PDF reports with confidence scoring
- **Bilingual Reports** - Generate clinical PDF reports in English or French
- **Analytics** - Interactive dashboards, QC trends, result distributions
- **Data Protection** - Automatic backups, crash resilience, integrity verification
- **Audit Trail** - Complete activity logging for compliance

---

## Quick Start

### Windows (Recommended)

1. Clone or download this repository
2. Double-click `start_NRIS_v2.bat`
3. Browser opens automatically to `http://localhost:8501`

Optional: Run `create_desktop_shortcut.bat` for one-click access.

### Manual Installation

```bash
git clone https://github.com/AzizElGhezal/NRIS.git
cd NRIS
python -m venv venv_NRIS_v2
# Windows: venv_NRIS_v2\Scripts\activate
# macOS/Linux: source venv_NRIS_v2/bin/activate
pip install -r requirements_NRIS_v2.txt
streamlit run NRIS_Enhanced.py
```

---

## Default Login

```
Username: admin
Password: admin123
```

You must change the password on first login (8+ chars, uppercase, lowercase, number).

---

## Configuration

QC and clinical thresholds can be customized in the Settings tab:

| Setting | Default |
|---------|---------|
| CFF Minimum | 3.5% |
| GC Content | 37-44% |
| Unique Read Rate | 68%+ |
| Trisomy Low Risk | <2.58 |
| Trisomy High Risk | >6.0 |

---

## Author

**Aziz El Ghezal**

## Disclaimer

This software assists healthcare professionals in interpreting NIPT results. Clinical decisions should be made by qualified medical professionals. This tool does not replace professional medical judgment.
