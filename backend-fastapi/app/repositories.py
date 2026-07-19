"""Data-access helpers (repository layer).

Thin query functions over the Application aggregate, mirroring the scoping
rules of the original repo classes: students see only their own
applications, lecturers see applications where they are the referent, and
the office sees everything.  Child collections are eager-loaded via the
model's ``selectin`` relationships, so a returned Application is fully
populated.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, Institution, User


def _to_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    """Coerce a path/id string to UUID; return None when it isn't valid."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def get_student_application(db: AsyncSession, app_id: str, student_id: uuid.UUID) -> Application | None:
    uid = _to_uuid(app_id)
    if uid is None:
        return None
    return await db.scalar(
        select(Application).where(Application.id == uid, Application.student_id == student_id)
    )


async def list_student_applications(db: AsyncSession, student_id: uuid.UUID) -> list[Application]:
    rows = await db.scalars(
        select(Application)
        .where(Application.student_id == student_id)
        .order_by(Application.created_at.desc())
    )
    return list(rows)


async def get_lecturer_application(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID) -> Application | None:
    uid = _to_uuid(app_id)
    if uid is None:
        return None
    return await db.scalar(
        select(Application).where(Application.id == uid, Application.referent_lecturer_id == lecturer_id)
    )


async def list_lecturer_applications(db: AsyncSession, lecturer_id: uuid.UUID) -> list[Application]:
    rows = await db.scalars(
        select(Application)
        .where(Application.referent_lecturer_id == lecturer_id)
        .order_by(Application.created_at.desc())
    )
    return list(rows)


async def get_application(db: AsyncSession, app_id: str) -> Application | None:
    uid = _to_uuid(app_id)
    if uid is None:
        return None
    return await db.scalar(select(Application).where(Application.id == uid))


async def list_applications(db: AsyncSession, status: str | None) -> list[Application]:
    stmt = select(Application).order_by(Application.created_at.desc())
    if status:
        stmt = stmt.where(Application.status == status)
    rows = await db.scalars(stmt)
    return list(rows)


async def list_institutions(db: AsyncSession) -> list[Institution]:
    rows = await db.scalars(select(Institution).order_by(Institution.name.asc()))
    return list(rows)


async def list_lecturers(db: AsyncSession) -> list[User]:
    rows = await db.scalars(select(User).where(User.role == "lecturer"))
    return list(rows)


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))
