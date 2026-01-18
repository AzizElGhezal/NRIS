# NRIS Customization Guide

**Version 2.4**

---

## Overview

This guide covers customizing NRIS for your laboratory's needs:
- Data encryption and security
- Database migrations
- Performance optimization
- PDF import patterns

### Key Files

| File | Purpose |
|------|---------|
| `NRIS_Enhanced.py` | Main application |
| `nris/` | Modular package |
| `nris_config.json` | Custom configuration |

---

## Data Encryption

NRIS provides a pluggable encryption framework. Choose your preferred backend:

### Option 1: Fernet Encryption (Built-in)

```python
from nris.encryption import get_encryptor, generate_key

# Generate and save key securely
key = generate_key()
print(f"Save this key: {key}")

# Use encryption
enc = get_encryptor('fernet', key=key)
encrypted = enc.encrypt("patient name")
decrypted = enc.decrypt(encrypted)
```

### Option 2: Field-Level Encryption

```python
from nris.encryption import FieldEncryptor, FernetEncryption

encryptor = FieldEncryptor(
    FernetEncryption(key),
    encrypted_fields={'full_name', 'mrn_id', 'clinical_notes'}
)
encrypted_patient = encryptor.encrypt_dict(patient_data)
```

### Option 3: Custom Backend

```python
from nris.encryption import register_backend

class MyEncryption:
    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...
    def is_encrypted(self, data: str) -> bool: ...

register_backend('custom', MyEncryption)
```

Store keys in environment variables: `export NRIS_ENCRYPTION_KEY="your-key"`

---

## Database Migrations

Safe schema updates with version tracking:

```python
from nris.migrations import MigrationManager

manager = MigrationManager()
manager.migrate()  # Apply pending migrations

# Check status
status = manager.get_status()
print(f"Version: {status['current_version']}")
print(f"Pending: {status['pending_count']}")

# Rollback if needed
manager.rollback(steps=1)
```

### Custom Migrations

```python
from nris.migrations import Migration, MigrationManager

manager = MigrationManager()
manager.register(Migration(
    version="100",
    description="Add custom column",
    up=["ALTER TABLE patients ADD COLUMN custom_field TEXT"],
    down=[]
))
manager.migrate()
```

---

## Performance Caching

Improve analytics performance with built-in caching:

```python
from nris.cache import cached, get_cache

# Decorator for automatic caching
@cached(ttl=300, persist=True)
def compute_statistics():
    # Expensive computation
    return stats

# Manual cache operations
cache = get_cache()
cache.set('key', data, ttl=600, persist=True)
data = cache.get('key')
cache.invalidate_pattern('analytics_')
```

Cache is two-tier: in-memory LRU + SQLite persistence.

---

## Configuration

### Settings Tab (Recommended)

Log in as admin, modify values in **Settings** tab. Saves to `nris_config.json`.

### Direct Edit

```json
{
  "QC_THRESHOLDS": {
    "MIN_CFF": 3.5,
    "GC_RANGE": [37.0, 44.0]
  },
  "CLINICAL_THRESHOLDS": {
    "TRISOMY_LOW": 2.58,
    "SCA_THRESHOLD": 4.5
  },
  "REPORT_LANGUAGE": "en"
}
```

---

## PDF Import Patterns

Add patterns to `nris/pdf/extraction.py`:

```python
mrn_patterns = [
    r'(?:MRN|Medical\s+Record)[:\s]+([A-Za-z0-9\-]+)',
    r'File\s+No\.[:\s]+([A-Za-z0-9\-]+)',  # New format
]
```

| Field | Variable |
|-------|----------|
| Patient name | `name_patterns` |
| MRN/ID | `mrn_patterns` |
| Z-scores | `z21_patterns` |

---

## Backup

### Programmatic Backup

```python
from nris.backup import create_backup, list_backups, restore_backup

create_backup("manual")
backups = list_backups()
restore_backup(backups[0]['path'])
```

### Files to Back Up

- `nipt_registry_v2.db` - Database
- `nris_config.json` - Configuration

---

## Type Checking

Run mypy for type validation:

```bash
pip install mypy
mypy nris/
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Migration failed | Check `manager.get_status()` for details |
| Cache not working | Verify `_analytics_cache` table exists |
| Encryption error | Check key format (base64, 32 bytes) |
| Type errors | Run `mypy nris/` for diagnostics |

---

**Version 2.4** | Laboratory internal use only
