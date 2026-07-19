"""Lecturer service: evaluate learning agreements, modifications, scores.

Faithful port of lecturerServices.ts.  Operates only on applications
where the lecturer is the referent (enforced by the repository scope).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app import repositories as repo
from app.db.models import Application, ExamMapping, LearningAgreement
from app.errors import AppError


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def list_applications(db: AsyncSession, lecturer_id: uuid.UUID) -> list[Application]:
    return await repo.list_lecturer_applications(db, lecturer_id)


async def get_by_id(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID) -> Application:
    app = await repo.get_lecturer_application(db, app_id, lecturer_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    return app


async def download_la(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID, index: int) -> LearningAgreement:
    app = await repo.get_lecturer_application(db, app_id, lecturer_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if index < 0 or index >= len(app.learning_agreements):
        raise AppError("NO_LA_FOUND")
    return app.learning_agreements[index]


async def evaluate_la(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID, status: str, reason: str | None) -> Application:
    app = await repo.get_lecturer_application(db, app_id, lecturer_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if status not in ("approved", "rejected"):
        raise AppError("INVALID_STATUS")

    pending = [la for la in app.learning_agreements if la.status == "pending"]
    if not pending:
        raise AppError("NO_PENDING_LA")

    latest = pending[-1]
    latest.status = status
    latest.decision_date = _now()
    if reason:
        latest.reason = reason

    app.status = "preDepartureDone" if status == "approved" else "needs modifications"
    await db.flush()
    return app


async def evaluate_modification(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID, status: str, mod_id: str, reason: str | None) -> Application:
    app = await repo.get_lecturer_application(db, app_id, lecturer_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if status not in ("approved", "rejected"):
        raise AppError("INVALID_STATUS")

    mod = next((m for m in app.modifications if str(m.id) == str(mod_id)), None)
    if not mod:
        raise AppError("NO_MODIFICATIONS")
    if mod.status != "pending":
        raise AppError("INVALID_STATUS")

    mod.status = status
    mod.decision_date = _now()
    if reason:
        mod.reason = reason

    # The trailing pending LA is resolved along with the modification.
    pending_la = next((la for la in reversed(app.learning_agreements) if la.status == "pending"), None)

    if status == "approved":
        # Replace the live exam mappings with the proposed diff snapshot.
        # Delete the old rows and flush before inserting the new ones so the
        # (application_id, position) unique constraint is not violated
        # mid-flush by reusing the same positions.
        new_mappings = [
            ExamMapping(
                position=i,
                foreign_teaching_code=d.foreign_teaching_code,
                foreign_course_name=d.foreign_course_name,
                foreign_credits=d.foreign_credits,
                local_course_code=d.local_course_code,
                local_course_name=d.local_course_name,
                local_credits=d.local_credits,
            )
            for i, d in enumerate(mod.exam_mappings)
        ]
        app.exam_mappings = []
        await db.flush()
        app.exam_mappings = new_mappings
        if pending_la:
            pending_la.status = "approved"
            pending_la.decision_date = _now()
    else:
        if pending_la:
            pending_la.status = "rejected"
            pending_la.decision_date = _now()
            if reason:
                pending_la.reason = reason

    app.status = "inProgress"
    await db.flush()
    return app


async def approve_score(db: AsyncSession, app_id: str, lecturer_id: uuid.UUID, score_index: int) -> Application:
    app = await repo.get_lecturer_application(db, app_id, lecturer_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if score_index < 0 or score_index >= len(app.exam_scores):
        raise AppError("EXAM_SCORE_NOT_FOUND")

    score = app.exam_scores[score_index]
    if score.status != "pending":
        raise AppError("INVALID_STATUS")

    score.status = "approved"
    score.approved_by = lecturer_id
    score.approved_at = _now()
    await db.flush()
    return app
