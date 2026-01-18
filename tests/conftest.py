"""
Pytest configuration and fixtures for NRIS tests.
"""

import pytest
import tempfile
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nris.config import DEFAULT_CONFIG


@pytest.fixture
def config():
    """Provide default configuration for tests."""
    return DEFAULT_CONFIG.copy()


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_patient():
    """Provide sample patient data."""
    return {
        'id': '12345',
        'name': 'Jane Doe',
        'age': 35,
        'weight': 65.0,
        'height': 165,
        'bmi': 23.9,
        'weeks': 12,
        'notes': 'Test patient'
    }


@pytest.fixture
def sample_z_scores():
    """Provide sample Z-scores for testing."""
    return {
        21: 0.5,
        18: 0.3,
        13: 0.2,
        'XX': 0.1,
        'XY': -0.5,
    }


@pytest.fixture
def sample_qc_metrics():
    """Provide sample QC metrics for testing."""
    return {
        'reads': 10.5,
        'cff': 8.5,
        'gc': 40.0,
        'qs': 0.5,
        'unique_rate': 75.0,
        'error_rate': 0.3,
    }
