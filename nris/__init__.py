"""
NRIS - NIPT Result Interpretation Software.

A modular clinical genetics dashboard for NIPT analysis and reporting.

Modules:
    analysis: Trisomy, SCA, CNV, RAT analysis and QC validation
    pdf: PDF extraction and report generation
    ui: Streamlit UI components
    auth: Authentication and session management
    database: Database operations and CRUD
    backup: Backup and data protection
    encryption: Pluggable encryption framework
    migrations: Database schema migrations
    cache: Performance caching system
    config: Configuration management
    utils: Utility functions
"""

__version__ = "2.4.1"
__author__ = "AzizElGhezal"

# Core modules
from . import config
from . import auth
from . import database
from . import backup
from . import utils

# New feature modules
from . import encryption
from . import migrations
from . import cache

# Sub-packages
from . import analysis
from . import pdf
from . import ui

__all__ = [
    "__version__",
    "__author__",
    "config",
    "auth",
    "database",
    "backup",
    "utils",
    "encryption",
    "migrations",
    "cache",
    "analysis",
    "pdf",
    "ui",
]
