"""Office service: pre-departure completion and application closure.

Faithful port of officeServices.ts.  The office can see and act on every
application (no owner scope).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app import repositories as repo
from app.db.models import Application, LearningAgreement
from app.errors import AppError


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def list_applications(db: AsyncSession, status: str | None) -> list[Application]:
    return await repo.list_applications(db, status)


async def get_by_id(db: AsyncSession, app_id: str) -> Application:
    app = await repo.get_application(db, app_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    return app


async def download_la(db: AsyncSession, app_id: str, index: int) -> LearningAgreement:
    app = await repo.get_application(db, app_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if index < 0 or index >= len(app.learning_agreements):
        raise AppError("NO_LA_FOUND")
    return app.learning_agreements[index]


async def complete_predeparture(db: AsyncSession, app_id: str, user_id: uuid.UUID) -> Application:
    app = await repo.get_application(db, app_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status != "preDepartureDone":
        raise AppError("LA_MUST_BE_APPROVED_BEFORE")

    has_approved_la = any(la.status == "approved" for la in app.learning_agreements)
    if not has_approved_la:
        raise AppError("NO_LA")
    if not app.exam_mappings:
        raise AppError("APPLICATION_MUST_HAVE_EXAM_MAPPINGS")

    app.pre_departure_completed = True
    app.pre_departure_completed_at = _now()
    app.pre_departure_completed_by = user_id
    app.status = "inProgress"
    await db.flush()
    return app


async def close_application(db: AsyncSession, app_id: str, user_id: uuid.UUID) -> Application:
    app = await repo.get_application(db, app_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status != "torUploaded":
        raise AppError("TOR_MUST_BE_UPLOADED")
    if not app.transcript_file_name:
        raise AppError("TOR_NOT_FOUND")
    if not app.exam_scores:
        raise AppError("NO_EXAM_SCORES")
    if any(s.status == "pending" for s in app.exam_scores):
        raise AppError("SCORES_NOT_CLOSED")

    app.status = "closed"
    app.closed_at = _now()
    app.closed_by = user_id
    await db.flush()
    return app
