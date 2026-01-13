# NRIS - NIPT Result Interpretation Software

**Version 2.4 Enhanced Edition**
*Advanced Clinical Genetics Dashboard with Bilingual Support, Enhanced Security & Reliability*

---

## Overview

NRIS (NIPT Result Interpretation Software) is a comprehensive web-based clinical genetics dashboard designed for managing and interpreting Non-Invasive Prenatal Testing (NIPT) results. This enhanced edition provides healthcare professionals with powerful tools for patient management, quality control analysis, clinical interpretation, and automated reporting.

### Key Features

- **User Authentication & Role-Based Access Control**
  - Secure login system with SHA256 password hashing and unique salts
  - Role-based permissions (Admin, Geneticist, Technician)
  - Account lockout protection after failed login attempts
  - Session timeout for security (60 minutes of inactivity)
  - Forced password change on first login
  - Strong password requirements (8+ chars, uppercase, lowercase, numbers)

- **Patient Management**
  - Complete patient demographics and clinical history
  - MRN (Medical Record Number) tracking with uniqueness enforcement
  - BMI calculations and gestational age tracking
  - Soft delete functionality with automatic MRN release for reuse
  - Patient data restoration capability
  - Orphaned patient cleanup utility (soft-deleted and active orphans)
  - Smart handling of patients with 0 results (automatic replacement)

- **NIPT Result Analysis**
  - Multiple panel types (Basic, Standard, Plus, Pro)
  - Quality control metrics validation
  - Automated trisomy risk assessment (T13, T18, T21)
  - Sex chromosome aneuploidy (SCA) detection
  - Rare autosomal trisomy (RAT) analysis
  - Fetal sex determination
  - **Reportable Status**: Clear Yes/No indicator for whether results should be reported
    - Yes: Screen Positive or Screen Negative results ready for reporting
    - No: Re-library, Resample, QC Fail, or Ambiguous results requiring further processing

- **PDF Import (Enhanced)**
  - Comprehensive data extraction from PDF reports
  - File validation (size, type, format verification)
  - Extraction confidence scoring (HIGH/MEDIUM/LOW)
  - Detailed error handling and logging
  - Support for various report formats
  - Batch processing with progress tracking

- **Advanced Analytics & Visualizations**
  - Interactive dashboards with Plotly
  - QC metrics trending and statistics
  - Result distribution analysis
  - Panel utilization reports
  - Cached analytics for better performance

- **Bilingual PDF Reporting (NEW in v2.2)**
  - Professional clinical reports in **English** and **French**
  - Language selection per report or default preference
  - Complete translation of all clinical content
  - Localized recommendations and disclaimers

- **Automated PDF Reporting**
  - Professional clinical reports with customizable headers
  - QC metrics summary and interpretation
  - Clinical recommendations based on thresholds
  - Digital signatures and timestamps

- **Audit Trail & Compliance**
  - Complete user activity logging
  - Result modification tracking
  - Login/logout tracking
  - Failed login attempt logging
  - Export capabilities for compliance reviews

- **Data Protection & Easy Launch**
  - Automatic database backups on startup (keeps last 10)
  - SQLite WAL mode for crash resilience
  - Database integrity verification
  - Desktop shortcut creator for one-click access
  - Auto browser open - no manual link copying

---

## What's New in v2.4

### Enhanced Analysis Report Display
- **Comprehensive Post-Analysis View**: After saving and analyzing a sample, the results are now displayed in a well-structured, professional format
- Complete patient demographics (name, MRN, age, gestational weeks)
- QC metrics display with all sequencing parameters (Reads, Cff, GC, QS, Unique %, Error %)
- Trisomy results with Z-scores in metric cards showing status at a glance
- Sex chromosome analysis with Z-XX and Z-XY values
- CNV and RAT findings clearly organized
- Color-coded final result banner with reportable status indicator

### Registry Improvements
- **French PDF Quick Access**: Quick actions in Browse & Search now include a language selector (EN/FR) for instant PDF generation
- **Patient Selection Feedback**: Clear success messages guide users to the Patient Details tab after selecting a patient
- **Multi-Result PDF Buttons**: Each test result in Patient Details has dedicated English and French PDF download buttons
- **Selection Banner**: Patient Details tab shows a prominent banner when a patient is already selected

### User Experience Polish
- Improved navigation flow between Browse and Patient Details tabs
- Better visual feedback for all user actions
- Cleaner layout for multiple test results per patient

---

## What's New in v2.3

### Patient Info Cards
- Registry now displays individual patient info cards instead of tables for better data visualization
- Color-coded status indicators for quick result identification

### Multi-Anomaly Analytics
- Stats dashboard properly handles samples with multiple anomalies (T21+T18, etc.)
- Dedicated breakdown charts for complex cases

### Enhanced Analysis Features
- SCA analysis: Detailed sex chromosome anomaly tracking and visualization
- CNV/RAT tracking: Comprehensive copy number variant and rare autosomal trisomy statistics
- Test result cards with color-coded status indicators
- Improved pagination for large datasets

---

## What's New in v2.2

### Data Protection & Backup System
- **Automatic Backups**: Database is automatically backed up on every application startup
  - Backups stored in `backups/` folder with timestamps
  - System automatically keeps the last 10 backups (older ones are removed)
  - Uses SQLite's safe backup API for data integrity
- **Crash Resilience**: SQLite WAL (Write-Ahead Logging) mode enabled
  - Prevents database corruption if application closes unexpectedly
  - Better performance for frequent read/write operations
- **Database Integrity Checks**: Automatic verification on startup
  - Alerts if any integrity issues are detected
  - Manual integrity check available in Settings
- **Backup Management UI** (in Settings tab):
  - View all available backups with size and date
  - Create manual backups anytime
  - Restore from any backup (admin only)
  - Verify database integrity on demand

### Easy Launch Options
- **Desktop Shortcut Creator**: Run `create_desktop_shortcut.bat` once
  - Creates "NRIS - Patient Registry" shortcut on desktop
  - No need to navigate to folders or copy links
  - Choose between normal or silent (minimized console) mode
- **Auto Browser Open**: Browser automatically opens when server is ready
  - No more copying localhost links manually
- **Silent Mode**: Run with minimized console window for cleaner desktop
  - Use `start_NRIS_silent.vbs` directly, or choose option 2 in shortcut creator

### Bilingual PDF Reports
- **Full French Language Support**: Generate PDF reports in both English and French
  - All clinical content fully translated including:
    - Section headers and labels
    - QC assessment terminology
    - Trisomy and SCA result descriptions
    - Clinical recommendations
    - Limitations and disclaimers
    - Authorization section
- **Language Selection Options**:
  - Set default language in Settings tab
  - Choose language per report in Analysis and Registry tabs
  - Reports include language suffix in filename (e.g., `Report_123_FR.pdf`)

### Improved User Interface for Technicians
- **Helpful Tooltips**: Added explanatory tooltips throughout the Analysis tab
  - Patient information fields with guidance
  - Sequencing metrics with reference ranges
  - Z-score thresholds and interpretation help
  - SCA type explanations
- **Visual Guidance**: Added captions showing risk thresholds at a glance
- **Streamlined Workflow**: Improved form layout and labeling

### Report Settings
- New "Report Settings" section in Settings tab
- Persistent language preference saved to configuration
- Audit logging for language preference changes

---

## What's New in v2.1

### Clinical Workflow Improvements
- **Reportable Status**: Replaced "Risk Category" with clear "Reportable" indicator (Yes/No)
  - Yes = Result ready to report (Screen Positive or Screen Negative)
  - No = Requires further action (Re-library, Resample, QC Fail, Ambiguous)
  - Displayed in Analysis results, Registry, and PDF reports
  - Color-coded: Red for positive results, Yellow for non-reportable
- **MRN Reuse for Deleted Patients**: When patients are deleted, their MRN is immediately available for new patients
- **Orphan Patient Handling**: Patients with 0 results are automatically detected and can be replaced during import
- **Improved Duplicate Detection**: Clear distinction between patients with results (skip) vs orphans (replace)

### Security Enhancements
- **Password Complexity**: Passwords must now contain 8+ characters with uppercase, lowercase, and numbers
- **Account Lockout**: Accounts lock for 15 minutes after 5 failed login attempts
- **Session Timeout**: Automatic logout after 60 minutes of inactivity
- **Forced Password Change**: Default admin account requires password change on first login
- **Enhanced Audit Logging**: All security events are logged

### Data Integrity Improvements
- **Foreign Key Enforcement**: Database foreign key constraints now properly enforced
- **Soft Delete**: Deleted patients are marked rather than removed, preventing ghost records
- **MRN Release on Delete**: Soft-deleted patients have their MRN modified to free it for reuse
- **Transaction Support**: Import operations use database transactions to prevent partial saves
- **Enhanced Orphan Cleanup**: Two cleanup options - soft-deleted only or all orphans including active

### Performance Optimizations
- **Database Indexes**: Added indexes on frequently queried columns
- **Query Caching**: Analytics queries cached for 60 seconds
- **Optimized Queries**: Combined multiple queries into single efficient queries
- **Reduced Database Calls**: Minimized redundant database connections

### PDF Import Improvements
- **File Validation**: Size limits, type checking, and header verification
- **Better Error Handling**: Specific error messages for different failure types
- **Extraction Confidence**: Shows confidence level for extracted data
- **Missing Field Detection**: Reports which fields couldn't be extracted
- **Scanned PDF Detection**: Warns when PDF appears to be image-based
- **Smart Orphan Replacement**: Automatically replaces patients with 0 results instead of skipping

---

## Quick Start

### Prerequisites

- **Python 3.8 or higher** ([Download Python](https://www.python.org/downloads/))
- Windows, macOS, or Linux
- 4GB RAM minimum (8GB recommended)
- Modern web browser (Chrome, Firefox, Edge, Safari)

### Installation

#### Windows Users (Recommended)

1. **Download or clone this repository**
   ```bash
   git clone https://github.com/AzizElGhezal/NRIS.git
   cd NRIS
   ```

2. **Run the launcher**
   - Double-click `start_NRIS_v2.bat`
   - The launcher will automatically:
     - Check for Python installation
     - Create an isolated virtual environment
     - Install all dependencies
     - Launch the application
     - Open your browser automatically

3. **Access the application**
   - Your web browser will automatically open to `http://localhost:8501`

4. **(Optional) Create Desktop Shortcut for Easy Access**
   - Double-click `create_desktop_shortcut.bat`
   - Choose option 2 (Silent mode) for a cleaner experience
   - A shortcut "NRIS - Patient Registry" will appear on your desktop
   - From now on, just double-click the desktop shortcut to launch NRIS

#### Manual Installation (All Platforms)

1. **Clone the repository**
   ```bash
   git clone https://github.com/AzizElGhezal/NRIS.git
   cd NRIS
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv_NRIS_v2
   ```

3. **Activate the virtual environment**
   - Windows: `venv_NRIS_v2\Scripts\activate`
   - macOS/Linux: `source venv_NRIS_v2/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements_NRIS_v2.txt
   ```

5. **Launch the application**
   ```bash
   streamlit run NRIS_Enhanced.py
   ```

6. **Open your browser to** `http://localhost:8501`

---

## Default Login Credentials

```
Username: admin
Password: admin123
```

**IMPORTANT: You will be required to change the default password on first login!**

Password requirements:
- At least 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)

---

## Usage Guide

### First-Time Setup

1. **Create Desktop Shortcut** (optional but recommended)
   - Run `create_desktop_shortcut.bat` for easy future access
2. **Login** with default credentials
3. **Change Password** (required on first login)
4. **Configure QC Thresholds** in Settings (optional)
5. **Create User Accounts** for your team members
6. **Import Patient Data** or add patients manually

### Daily Workflow

1. **Add/Select Patient** from the Patient Management tab
2. **Enter NIPT Results** with QC metrics
3. **Review Automated Interpretation** and clinical recommendations
4. **Generate PDF Report** for clinical records
5. **Export Data** for analysis or compliance

### Analytics & Reporting

- **Dashboard Tab**: Real-time overview of recent results and statistics
- **Analytics Tab**: Detailed QC trends, result distribution, and panel usage
- **Audit Log Tab**: Complete activity tracking and compliance reporting
- **Export Features**: Excel, CSV, and JSON data export capabilities

### Admin Functions

- **User Management**: Create/manage user accounts
- **Database Maintenance**:
  - Clean up soft-deleted orphaned patients
  - Clean up ALL orphaned patients (including active ones with 0 results)
  - Frees up MRN IDs for reuse
- **Data Protection**:
  - View and manage automatic backups
  - Create manual backups
  - Restore from previous backups
  - Verify database integrity
- **Audit Log Review**: Monitor all system activity
- **Configuration**: Adjust QC and clinical thresholds

---

## Technical Specifications

### Technology Stack

- **Framework**: Streamlit 1.28+
- **Database**: SQLite3 with foreign key enforcement
- **Visualization**: Plotly 5.17+
- **Reporting**: ReportLab 4.0+
- **Data Processing**: Pandas 2.0+
- **PDF Handling**: PyPDF2 3.0+

### File Structure

```
NRIS/
├── NRIS_Enhanced.py           # Main application
├── start_NRIS_v2.bat          # Windows launcher (auto-opens browser)
├── start_NRIS_silent.vbs      # Silent launcher (minimized console)
├── create_desktop_shortcut.bat # Creates desktop shortcut for easy access
├── requirements_NRIS_v2.txt   # Python dependencies
├── README.md                  # This file
├── nipt_registry_v2.db        # Database (auto-created)
├── nris_config.json           # Configuration (auto-created)
└── backups/                   # Automatic backups (auto-created)
    └── nris_backup_*.db       # Timestamped database backups
```

### Database Schema

The application uses SQLite with the following main tables:
- **users**: User accounts and authentication
- **patients**: Patient demographics (with soft delete support)
- **results**: NIPT test results linked to patients
- **audit_log**: Comprehensive activity logging

Indexes are automatically created on:
- `patients(mrn_id)` - Fast patient lookup
- `results(patient_id)` - Fast result retrieval
- `results(created_at)` - Date-based queries
- `audit_log(timestamp)` - Audit log queries

### Dependencies

```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
reportlab>=4.0.0
openpyxl>=3.1.0
xlsxwriter>=3.1.0
PyPDF2>=3.0.0
```

---

## Configuration

### QC Thresholds

Default quality control thresholds can be customized in the Settings tab:

- **Cell-Free Fetal DNA (CFF)**: Minimum 3.5%
- **GC Content**: 37.0-44.0%
- **Unique Read Rate**: Minimum 68.0%
- **Error Rate**: Maximum 1.0%
- **Quality Score Limits**: Negative <1.7, Positive >2.0

### Clinical Interpretation Thresholds

- **Trisomy Low Risk**: <2.58
- **Trisomy Ambiguous**: 2.58-6.0
- **Trisomy High Risk**: >6.0
- **SCA Threshold**: >4.5
- **RAT Positive**: >8.0
- **RAT Ambiguous**: 4.5-8.0

### Panel Types

- **NIPT Basic**: 5M reads minimum
- **NIPT Standard**: 7M reads minimum
- **NIPT Plus**: 12M reads minimum
- **NIPT Pro**: 20M reads minimum

### Security Settings (Built-in)

- **Session Timeout**: 60 minutes
- **Account Lockout**: 5 failed attempts = 15 minute lockout
- **Password Requirements**: 8+ chars, mixed case, numbers

---

## Security & Compliance

### Security Features

- SHA256 password hashing with random salt
- Session-based authentication with timeout
- Role-based access control (RBAC)
- Account lockout protection
- Audit logging for all data modifications
- Secure database storage with parameterized queries
- Foreign key constraint enforcement

### Data Privacy

- Patient data stored locally in SQLite database
- No external data transmission
- HIPAA compliance considerations built-in
- Audit trail for regulatory compliance
- Soft delete preserves data integrity

### Data Protection & Backups

**Automatic Protection (Built-in)**
- Database is automatically backed up on every application startup
- Backups are stored in the `backups/` folder with timestamps
- System keeps the last 10 backups automatically
- SQLite WAL mode prevents corruption from unexpected shutdowns
- Database integrity is verified on each startup

**Manual Backup Options**
- Create manual backups anytime from Settings → Data Protection
- Restore from any backup (admin only) if needed
- Verify database integrity on demand

**For Additional Safety**
Periodically copy these files to an external location:
- `backups/` folder - Contains all automatic backups
- `nipt_registry_v2.db` - Current database
- `nris_config.json` - Custom configuration settings

---

## Troubleshooting

### Common Issues

**Application won't start**
- Ensure Python 3.8+ is installed and in PATH
- Try running `pip install -r requirements_NRIS_v2.txt` manually
- Check firewall settings for port 8501

**Database errors**
- Delete `nipt_registry_v2.db` to reset (warning: deletes all data)
- Ensure write permissions in the application directory

**Import errors**
- Verify all dependencies installed: `pip list`
- Update pip: `pip install --upgrade pip`
- Reinstall requirements: `pip install -r requirements_NRIS_v2.txt --force-reinstall`

**PDF extraction issues**
- Ensure PDFs are text-based (not scanned images)
- Check extraction confidence level for quality indicators
- Review missing fields list for problematic PDFs

**Account locked**
- Wait 15 minutes for automatic unlock
- Admin can reset via database if needed

**Session expired**
- Re-login after 60 minutes of inactivity
- This is a security feature

**Browser won't open**
- Manually navigate to `http://localhost:8501`
- Try a different browser
- Check if port 8501 is already in use

---

## Version History

### Version 2.4 (Current)
**Analysis Report**
- Comprehensive post-analysis display with patient info, QC metrics, results
- Color-coded trisomy and SCA results with Z-scores
- Reportable status indicator

**Registry**
- French/English PDF language selector in quick actions
- Multi-result PDF buttons per test result
- Clear navigation feedback and patient selection banners

**User Experience**
- Improved navigation flow between tabs
- Better visual feedback for all actions

### Version 2.3
**Display Improvements**
- Patient info cards in registry
- Multi-anomaly analytics support
- SCA tracking and visualization
- CNV/RAT statistics in analytics

### Version 2.2
**Data Protection**
- Automatic database backup on every startup
- SQLite WAL mode for crash resilience
- Database integrity verification on startup
- Backup management UI in Settings (view, create, restore)
- Automatic backup rotation (keeps last 10)

**Easy Launch**
- Desktop shortcut creator for one-click access
- Auto browser open when server is ready
- Silent mode option (minimized console)
- No more navigating to folders or copying links

**Bilingual Support**
- Full French language support for PDF reports
- Language selection in Analysis and Registry tabs
- Default language preference in Settings
- Complete translation of clinical content

**Technician Experience**
- Helpful tooltips on all input fields
- Visual guidance with threshold captions
- Improved form layout and labeling
- Streamlined analysis workflow

### Version 2.1
**Clinical Workflow**
- New "Reportable" status replaces confusing "Risk Category"
- Clear Yes/No indicator for whether results can be reported
- Color-coded results (Red=Positive, Yellow=Needs action)

**Patient Management**
- MRN reuse when patients are deleted
- Smart orphan patient detection and replacement
- Improved duplicate handling in batch import
- Enhanced cleanup utilities for orphaned records

**Security**
- Password complexity requirements (8+ chars, mixed case, numbers)
- Account lockout after 5 failed login attempts
- 60-minute session timeout for inactive users
- Forced password change on first login
- Enhanced audit logging

**Data Integrity**
- Database foreign key constraint enforcement
- Soft delete with automatic MRN release
- Transaction support for import operations
- Optimized database indexes

**Performance**
- Query caching for analytics (60 seconds)
- Combined and optimized database queries
- Reduced redundant database connections

**PDF Import**
- File validation (size, type, format)
- Extraction confidence scoring
- Smart orphan replacement during import
- Better error handling and reporting

### Version 2.0
- Added user authentication and role-based access control
- Implemented comprehensive audit logging
- Enhanced analytics dashboard with Plotly visualizations
- Added automated PDF report generation
- Improved QC validation and clinical interpretation
- Added configuration management system
- Enhanced data export capabilities (Excel, CSV, JSON)

---

## Author

**Aziz El Ghezal**

---

## License

This software is provided for clinical and research use. Please ensure compliance with local regulations regarding medical software and patient data handling.

---

## Support & Contributing

For issues, feature requests, or contributions:
- Open an issue on the GitHub repository
- Contact the development team
- Review the audit logs for troubleshooting

---

## Disclaimer

This software is designed to assist healthcare professionals in interpreting NIPT results. Clinical decisions should always be made by qualified medical professionals considering all available clinical information. This tool does not replace professional medical judgment.

---

**NRIS v2.4 Enhanced Edition** - Advancing Clinical Genetics Through Technology
