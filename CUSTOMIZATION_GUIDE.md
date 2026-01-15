# NRIS Customization Guide

**Version 2.4**

---

## Overview

This guide covers customizing NRIS for your laboratory's needs:
- PDF import patterns for different report formats
- Clinical parameter configuration
- Data encryption options
- Backup procedures

### Key Files

| File | Purpose |
|------|---------|
| `NRIS_Enhanced.py` | Main application |
| `nris_config.json` | Custom configuration |
| `nipt_registry_v2.db` | SQLite database |

---

## PDF Import Customization

The system uses regex patterns to extract data from PDFs. To support new report formats, add patterns to `extract_data_from_pdf()` in `NRIS_Enhanced.py`.

### Adding a Pattern

Find the relevant pattern list and add your format:

```python
# Example: Adding support for "File No." as MRN
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'File\s+No\.[:\s]+([A-Za-z0-9\-]+)',  # Add new pattern
]
```

### Common Pattern Locations

| Field | Search for |
|-------|------------|
| Patient name | `name_patterns` |
| MRN/ID | `mrn_patterns` |
| Age | `age_patterns` |
| Z-scores | `z21_patterns`, `z18_patterns`, `z13_patterns` |

### Scanned PDFs

For image-based PDFs, install OCR support:
```bash
pip install pytesseract pillow pdf2image
```

---

## Configuration

### Method 1: Settings Tab (Recommended)

Log in as admin and modify values in **Settings** tab. Changes save automatically to `nris_config.json`.

### Method 2: Edit Config File

Edit `nris_config.json` directly:

```json
{
  "QC_THRESHOLDS": {
    "MIN_CFF": 3.5,
    "GC_RANGE": [37.0, 44.0],
    "MIN_UNIQ_RATE": 68.0,
    "MAX_ERROR_RATE": 1.0
  },
  "CLINICAL_THRESHOLDS": {
    "TRISOMY_LOW": 2.58,
    "TRISOMY_AMBIGUOUS": 6.0,
    "SCA_THRESHOLD": 4.5
  },
  "REPORT_LANGUAGE": "en"
}
```

Restart the application after editing.

---

## Data Encryption

NRIS does not encrypt data by default. Options for adding encryption:

| Approach | Description |
|----------|-------------|
| Column-level | Encrypt sensitive fields (name, MRN) using `cryptography` library |
| SQLCipher | Full database encryption via SQLCipher extension |
| Disk encryption | OS-level encryption (BitLocker, FileVault, LUKS) |

For column-level encryption:
```bash
pip install cryptography
```

Store encryption keys in environment variables, not in code.

---

## Backup

### Files to Back Up

- `nipt_registry_v2.db` - Database
- `nris_config.json` - Configuration
- `backups/` - Automatic backups

### Quick Backup

```bash
tar czf nris_backup_$(date +%Y%m%d).tar.gz nipt_registry_v2.db nris_config.json backups/
```

### Restore

```bash
tar xzf nris_backup_20260114.tar.gz
streamlit run NRIS_Enhanced.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No data extracted from PDF | Check if PDF is text-based (not scanned); add regex patterns for your format |
| Config not applied | Verify JSON syntax; restart application |
| Decryption failed | Check `NRIS_MASTER_KEY` environment variable |
| Slow after encryption | Use column-level encryption only for sensitive fields |

### Debug Logging

Add to `NRIS_Enhanced.py`:
```python
import logging
logging.basicConfig(filename='nris_debug.log', level=logging.DEBUG)
```

---

## Common Regex Patterns

```python
r'MRN[:\s]+(\d{7})'              # Medical record number
r'(\d{2}/\d{2}/\d{4})'           # Date DD/MM/YYYY
r'Z[:\s]*=?\s*(-?\d+\.?\d+)'     # Z-score
r'(\d+\.?\d*)\s*%'               # Percentage
r'Age[:\s]+(\d+)'                # Age
```

Test patterns at [regex101.com](https://regex101.com).

---

**Version 2.4** | Laboratory internal use only
