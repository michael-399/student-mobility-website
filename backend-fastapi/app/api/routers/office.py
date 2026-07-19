"""Office application routes.

All routes require the "office" role.  The office can view/act on every
application; responses populate student, host institution and referent
lecturer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.errors import AppError
from app.http import translate
from app.serializers import serialize_application
from app.services import office as svc

router = APIRouter(prefix="/office/applications", tags=["office"])


def _s(app) -> dict:
    return serialize_application(app, populate_student=True, populate_institution=True, populate_lecturer=True)


@router.get("")
async def list_applications(
    status: str | None = Query(default=None), office=Depends(require_role("office")), db: AsyncSession = Depends(get_db)
):
    apps = await svc.list_applications(db, status)
    return [_s(a) for a in apps]


@router.get("/{app_id}")
async def get_by_id(app_id: str, office=Depends(require_role("office")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.get_by_id(db, app_id)
    except AppError as e:
        raise translate(e, {"APPLICATION_NOT_FOUND": (404, "Application not found")}, (500, "Failed to get application"))
    return _s(app)


@router.get("/{app_id}/learning-agreement/{index}/download")
async def download_la(app_id: str, index: int, office=Depends(require_role("office")), db: AsyncSession = Depends(get_db)):
    try:
        la = await svc.download_la(db, app_id, index)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, "Application is not found"), "NO_LA_FOUND": (404, "Learning Agreement is not found")},
            (500, "Failed to download learning agreement"),
        )
    return FileResponse(la.file_path, filename=la.file_name)


@router.patch("/{app_id}/pre-departure")
async def complete_pre_departure(app_id: str, office=Depends(require_role("office")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.complete_predeparture(db, app_id, office.id)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "LA_MUST_BE_APPROVED_BEFORE": (404, "Learning agreement must be approved before predeparture"),
                "NO_LA": (404, "Learning Agreement is not found"),
                "APPLICATION_MUST_HAVE_EXAM_MAPPINGS": (404, "Application must have exam mappings"),
            },
            (500, "Failed to complete pre-departure"),
        )
    return _s(app)


@router.patch("/{app_id}/close")
async def close_application(app_id: str, office=Depends(require_role("office")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.close_application(db, app_id, office.id)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "TOR_MUST_BE_UPLOADED": (404, "Transcript of Records is not uploaded"),
                "TOR_NOT_FOUND": (404, "Transcript of records is not found"),
                "SCORES_NOT_CLOSED": (400, "All exam scores must be approved by the lecturer before closing"),
                "NO_EXAM_SCORES": (400, "No exam scores have been submitted"),
            },
            (500, "Failed to close application"),
        )
    return _s(app)
