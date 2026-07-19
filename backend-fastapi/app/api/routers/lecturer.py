"""Lecturer application routes.

All routes require the "lecturer" role.  Response shape matches the legacy
API: student and host institution are populated; the referent lecturer id
stays an id string.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.errors import AppError
from app.http import translate
from app.schemas import EvaluateBody
from app.serializers import serialize_application
from app.services import lecturer as svc

router = APIRouter(prefix="/lecturer/applications", tags=["lecturer"])


def _s(app) -> dict:
    return serialize_application(app, populate_student=True, populate_institution=True)


@router.get("")
async def list_applications(lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)):
    apps = await svc.list_applications(db, lect.id)
    return [_s(a) for a in apps]


@router.get("/{app_id}")
async def get_by_id(app_id: str, lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.get_by_id(db, app_id, lect.id)
    except AppError as e:
        raise translate(e, {"APPLICATION_NOT_FOUND": (404, "Application is not found")}, (500, "Failed to get application"))
    return _s(app)


@router.get("/{app_id}/learning-agreement/{index}/download")
async def download_la(app_id: str, index: int, lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)):
    try:
        la = await svc.download_la(db, app_id, lect.id, index)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, "Application is not found"), "NO_LA_FOUND": (404, "Learning Agreement is not found")},
            (500, "Failed to download learning agreement"),
        )
    return FileResponse(la.file_path, filename=la.file_name)


@router.patch("/{app_id}/learning-agreement/evaluate")
async def evaluate_la(app_id: str, body: EvaluateBody, lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.evaluate_la(db, app_id, lect.id, body.status, body.reason)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "NO_PENDING_LA": (400, "No pending Learning Agreement"),
                "INVALID_STATUS": (400, "Status must be 'approved' or 'rejected'"),
            },
            (500, "Failed to evaluate learning agreement"),
        )
    return _s(app)


@router.patch("/{app_id}/modifications/{mod_id}/evaluate")
async def evaluate_modification(
    app_id: str, mod_id: str, body: EvaluateBody, lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)
):
    try:
        app = await svc.evaluate_modification(db, app_id, lect.id, body.status, mod_id, body.reason)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "INVALID_STATUS": (404, "Status must be 'approved' or 'rejected'"),
                "NO_MODIFICATIONS": (404, "Modification not found"),
            },
            (500, "Failed to evaluate modification"),
        )
    return _s(app)


@router.patch("/{app_id}/transcript/scores/{score_index}")
async def approve_score(app_id: str, score_index: int, lect=Depends(require_role("lecturer")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.approve_score(db, app_id, lect.id, score_index)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "INVALID_STATUS": (404, "Status must be 'approved' or 'rejected'"),
                "EXAM_SCORE_NOT_FOUND": (404, "Exam score is not found"),
            },
            (500, "Failed to approve score"),
        )
    return _s(app)
