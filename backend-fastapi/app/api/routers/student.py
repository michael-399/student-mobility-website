"""Student application routes.

All routes require the "student" role.  Response shape matches the legacy
API: host institution and referent lecturer are populated; the student id
stays an id string.  File uploads are multipart; downloads stream the
original file.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.errors import AppError
from app.http import HttpError, translate
from app.schemas import DatesBody
from app.serializers import serialize_application
from app.services import student as svc
from app.storage import save_upload

router = APIRouter(prefix="/student/applications", tags=["student"])

NOT_FOUND = "Application is not found"


def _s(app) -> dict:
    return serialize_application(app, populate_institution=True, populate_lecturer=True)


@router.post("", status_code=201)
async def create(
    student=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
    academicYear: str | None = Form(None),
    hostInstitutionId: str | None = Form(None),
    expectedPeriod: str | None = Form(None),
    referentLecturerId: str | None = Form(None),
    examMappings: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    saved = await save_upload(file) if file else None
    data = {
        "academicYear": academicYear,
        "hostInstitutionId": hostInstitutionId,
        "expectedPeriod": expectedPeriod,
        "referentLecturerId": referentLecturerId,
        "examMappings": examMappings,
    }
    try:
        app = await svc.create(db, data, saved, student.id)
    except AppError as e:
        raise translate(
            e,
            {
                "MISSING_FIELDS": (400, "Missing required fields"),
                "MISSING_FILE": (400, "Learning Agreement file is required"),
            },
            (500, "Failed to create application"),
        )
    return _s(app)


@router.get("")
async def list_applications(student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    apps = await svc.list_applications(db, student.id)
    return [_s(a) for a in apps]


@router.get("/{app_id}")
async def get_by_id(app_id: str, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.get_by_id(db, app_id, student.id)
    except AppError as e:
        raise translate(e, {"APPLICATION_NOT_FOUND": (404, NOT_FOUND)}, (500, "Failed to get application"))
    return _s(app)


@router.patch("/{app_id}")
async def update(app_id: str, body: dict = Body(default={}), student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.update_application(db, app_id, student.id, body)
    except AppError as e:
        raise translate(
            e, {"NOT_EDITABLE": (404, "Only created applications can be edited")}, (500, "Failed to update application")
        )
    return _s(app)


@router.delete("/{app_id}")
async def remove(app_id: str, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        await svc.delete_application(db, app_id, student.id)
    except AppError as e:
        raise translate(e, {"APPLICATION_NOT_FOUND": (404, NOT_FOUND)}, (500, "Failed to delete application"))
    return {"message": "Application deleted"}


@router.patch("/{app_id}/cancel")
async def cancel(app_id: str, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.cancel_application(db, app_id, student.id)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, NOT_FOUND), "CANNOT_CANCEL": (400, "Application cannot be canceled")},
            (500, "Failed to cancel application"),
        )
    return _s(app)


@router.patch("/{app_id}/ready-for-transcript")
async def ready_for_transcript(app_id: str, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.ready_for_transcript(db, app_id, student.id)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, NOT_FOUND), "INVALID_STATUS": (400, "Application must be in mobility progress")},
            (500, "Failed to update application"),
        )
    return _s(app)


@router.post("/{app_id}/learning-agreement")
async def upload_learning_agreement(
    app_id: str,
    student=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
    file: UploadFile | None = File(None),
):
    saved = await save_upload(file) if file else None
    try:
        app = await svc.upload_la(db, app_id, student.id, saved)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, NOT_FOUND),
                "MISSING_FILE": (400, "Learning Agreement file is required"),
                "PENDING_LA_EXISTS": (400, "A Learning Agreement is already pending evaluation"),
            },
            (500, "Failed to upload learning agreement"),
        )
    return _s(app)


@router.get("/{app_id}/learning-agreement/{index}/download")
async def download_la(app_id: str, index: int, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        la = await svc.download_la(db, app_id, student.id, index)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, NOT_FOUND), "NO_LA_FOUND": (404, "Learning Agreement is not found")},
            (500, "Failed to download learning agreement"),
        )
    return FileResponse(la.file_path, filename=la.file_name)


@router.patch("/{app_id}/dates")
async def set_dates(app_id: str, body: DatesBody, student=Depends(require_role("student")), db: AsyncSession = Depends(get_db)):
    try:
        app = await svc.set_dates(db, app_id, student.id, body.actualArrivalDate, body.actualDepartureDate)
    except AppError as e:
        raise translate(
            e,
            {"APPLICATION_NOT_FOUND": (404, "Application not found"), "INVALID_STATUS": (400, "Application is not in mobility phase")},
            (500, "Failed to set dates"),
        )
    return _s(app)


@router.post("/{app_id}/modifications")
async def propose_modification(
    app_id: str,
    student=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
    description: str | None = Form(None),
    examMappingDiff: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    saved = await save_upload(file) if file else None
    try:
        app = await svc.propose_modification(db, app_id, student.id, description, examMappingDiff, saved)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "INVALID_STATUS": (400, "Application is not in mobility phase"),
                "MISSING_FILE": (400, "Learning Agreement file is required"),
            },
            (500, "Failed to propose modification"),
        )
    return _s(app)


@router.post("/{app_id}/transcript")
async def upload_transcript(
    app_id: str,
    student=Depends(require_role("student")),
    db: AsyncSession = Depends(get_db),
    examScores: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    saved = await save_upload(file) if file else None
    try:
        app = await svc.upload_transcript(db, app_id, student.id, saved, examScores)
    except AppError as e:
        raise translate(
            e,
            {
                "APPLICATION_NOT_FOUND": (404, "Application not found"),
                "INVALID_STATUS": (400, "Application is not in mobility phase"),
                "MISSING_FILE": (400, "Transcript required"),
            },
            (500, "Failed to upload transcript"),
        )
    return _s(app)
