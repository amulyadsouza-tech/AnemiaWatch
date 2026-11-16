import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError

from backend.app.core.config import settings

# Initialize Argon2id password hasher
ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    type=Type.ID
)

LEGACY_SALT = b"anemiawatch-salt-secure-hash"

def hash_password(password: str) -> str:
    """Hashes password with Argon2id."""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies password using Argon2id.
    Falls back to legacy PBKDF2 if user was registered before Argon2id migration.
    """
    if not hashed_password or not plain_password:
        return False
    
    # Check if Argon2 hash (starts with $argon2)
    if hashed_password.startswith("$argon2"):
        try:
            return ph.verify(hashed_password, plain_password)
        except (VerifyMismatchError, VerificationError):
            return False
        except Exception:
            return False
    else:
        # Legacy PBKDF2 HMAC-SHA256 check
        try:
            legacy_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), LEGACY_SALT, 100000).hex()
            return hmac.compare_digest(legacy_key, hashed_password)
        except Exception:
            return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates password strength:
    - Min 8 characters
    - At least one letter
    - At least one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, ""

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Creates short-lived JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def hash_token(raw_token: str) -> str:
    """Returns SHA-256 hash of a refresh token for safe storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def generate_refresh_token() -> tuple[str, str, datetime]:
    """
    Generates a secure random refresh token.
    Returns: (raw_token, token_hash, expires_at)
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at
