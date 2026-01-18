"""
Authentication and security functions for NRIS.
"""

import hashlib
import secrets
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_TIMEOUT_MINUTES = 60


def hash_password(password: str) -> str:
    """Hash password with salt using SHA256."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, hash_str: str) -> bool:
    """Verify password against hash."""
    try:
        salt, pwd_hash = hash_str.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password meets complexity requirements.

    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, ""


def authenticate_user(username: str, password: str, db_connection_func, log_audit_func) -> Optional[Dict]:
    """Authenticate user with account lockout protection.

    Args:
        username: Username to authenticate
        password: Password to verify
        db_connection_func: Function to get database connection
        log_audit_func: Function to log audit events

    Returns:
        User dict if successful, error dict if locked, None if failed
    """
    try:
        with db_connection_func() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, username, password_hash, full_name, role,
                       must_change_password, failed_login_attempts, locked_until
                FROM users WHERE username = ?
            """, (username,))
            row = c.fetchone()

            if not row:
                log_audit_func("LOGIN_FAILED", f"Unknown username: {username}", None)
                return None

            user_id, _, pwd_hash, full_name, role, must_change_pwd, failed_attempts, locked_until = row

            # Check if account is locked
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    remaining = (lock_time - datetime.now()).seconds // 60
                    log_audit_func("LOGIN_BLOCKED", f"Account locked for user {username}", user_id)
                    return {'error': f'Account locked. Try again in {remaining + 1} minutes.'}
                else:
                    # Lockout expired, reset
                    c.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,))

            if verify_password(password, pwd_hash):
                # Successful login - reset failed attempts
                c.execute("""
                    UPDATE users SET last_login = ?, failed_login_attempts = 0, locked_until = NULL
                    WHERE id = ?
                """, (datetime.now().isoformat(), user_id))
                conn.commit()
                log_audit_func("LOGIN", f"User {username} logged in", user_id)
                return {
                    'id': user_id,
                    'username': username,
                    'name': full_name,
                    'role': role,
                    'must_change_password': bool(must_change_pwd)
                }
            else:
                # Failed login
                new_attempts = (failed_attempts or 0) + 1
                if new_attempts >= MAX_LOGIN_ATTEMPTS:
                    lock_until = (datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)).isoformat()
                    c.execute("""
                        UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?
                    """, (new_attempts, lock_until, user_id))
                    log_audit_func("ACCOUNT_LOCKED", f"Account locked after {MAX_LOGIN_ATTEMPTS} failed attempts", user_id)
                else:
                    c.execute("UPDATE users SET failed_login_attempts = ? WHERE id = ?", (new_attempts, user_id))
                    log_audit_func("LOGIN_FAILED", f"Invalid password for {username} (attempt {new_attempts})", user_id)
                conn.commit()
    except Exception:
        pass
    return None


def check_session_timeout(last_activity: datetime) -> Tuple[bool, datetime]:
    """Check if the session has timed out.

    Args:
        last_activity: Datetime of last user activity

    Returns:
        Tuple of (is_valid, new_last_activity)
    """
    elapsed = (datetime.now() - last_activity).total_seconds() / 60
    if elapsed > SESSION_TIMEOUT_MINUTES:
        return False, last_activity
    return True, datetime.now()
