"""Authentication service: register + login.

Mirrors the legacy authServices.  Note: two bugs in the original are
fixed here (see README): the register route was unreachable due to a
missing leading slash, and the login controller compared against a
mis-spelled "INVALID CRFEDENTIALS" so wrong-password logins never
returned their intended 400 — here invalid credentials correctly raise
``INVALID_CREDENTIALS``.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app import repositories as repo
from app.core.security import hash_password, verify_password
from app.db.models import User
from app.errors import AppError

VALID_ROLES = {"student", "lecturer", "office"}


async def register(db: AsyncSession, email: str, password: str, name: str, role: str) -> User:
    if not email or not password or not name or not role:
        raise AppError("ALL_FIELDS_REQUIRED")
    if role not in VALID_ROLES:
        raise AppError("INVALID_ROLE")
    if await repo.find_user_by_email(db, email):
        raise AppError("EMAIL_IN_USE")

    user = User(email=email, password_hash=hash_password(password), name=name, role=role)
    db.add(user)
    await db.flush()
    return user


async def login(db: AsyncSession, email: str, password: str) -> User:
    user = await repo.find_user_by_email(db, email)
    if not user:
        raise AppError("NO_USER_WITH_THIS_EMAIL")
    if not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS")
    return user
