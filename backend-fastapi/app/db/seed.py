"""Idempotent database seeder.

Inserts the same demo users (password "password") and partner institutions
as the legacy backend, so the existing demo login flows work unchanged.
Runs on startup and is a no-op if any users already exist.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import Institution, User


async def seed(db: AsyncSession) -> None:
    existing = await db.scalar(select(func.count()).select_from(User))
    if existing:
        return

    pw = hash_password("password")
    db.add_all(
        [
            User(email="student@test.com", password_hash=pw, name="Alice Student", role="student"),
            User(email="student2@test.com", password_hash=pw, name="Bob Student", role="student"),
            User(email="lecturer@test.com", password_hash=pw, name="Dr. Smith", role="lecturer"),
            User(email="lecturer2@test.com", password_hash=pw, name="Prof. Jones", role="lecturer"),
            User(email="office@test.com", password_hash=pw, name="Office Admin", role="office"),
        ]
    )
    db.add_all(
        [
            Institution(name="University of Barcelona", country="Spain", city="Barcelona"),
            Institution(name="TU Berlin", country="Germany", city="Berlin"),
            Institution(name="Sorbonne University", country="France", city="Paris"),
            Institution(name="University of Oslo", country="Norway", city="Oslo"),
            Institution(name="University of Tokyo", country="Japan", city="Tokyo"),
            Institution(name="KU Leuven", country="Belgium", city="Leuven"),
            Institution(name="ETH Zurich", country="Switzerland", city="Zurich"),
            Institution(name="University College Dublin", country="Ireland", city="Dublin"),
        ]
    )
    await db.commit()
