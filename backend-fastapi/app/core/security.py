"""Security helpers: password hashing (bcrypt) and JWT issue/verify.

Uses the same bcrypt scheme and JWT payload shape (``{"id": <user id>}``,
HS256, 24h expiry) as the original Express backend, so the auth contract
consumed by the Angular frontend is unchanged.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(raw: str) -> str:
    """Hash a plaintext password with bcrypt (cost 10, matching the seed)."""
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(raw: str, hashed: str) -> bool:
    """Return True if the plaintext password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: str) -> str:
    """Sign a JWT carrying the user id, valid for JWT_EXPIRES_HOURS."""
    payload = {
        "id": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT; raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
