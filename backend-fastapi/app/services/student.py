"""Student service: the full application lifecycle.

Faithful port of studentServices.ts — same validations, same status
transitions, same error codes.  Multi-table writes (create, propose
modification, upload transcript) happen inside the request's single
transaction, preserving the atomicity the Mongo document write had.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app import repositories as repo
from app.db.models import Application, ExamMapping, ExamScore, LearningAgreement, Modification, ModificationExamMapping
from app.errors import AppError
from app.services._parsing import parse_json_field

EDITABLE_FIELDS = {
    "academicYear": "academic_year",
    "hostInstitutionId": "host_institution_id",
    "expectedPeriod": "expected_period",
    "referentLecturerId": "referent_lecturer_id",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_uuid(value):
    """Coerce a client-supplied id string to UUID (columns are UUID typed)."""
    if isinstance(value, uuid.UUID) or value is None:
        return value
    return uuid.UUID(str(value))


def _coerce_date(value):
    """Coerce an ISO date/datetime string (as sent in JSON) to datetime.

    Mirrors Mongoose casting a string into a Date field; empty/invalid
    values become None instead of raising.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _mapping_kwargs(d: dict) -> dict:
    return {
        "foreign_teaching_code": d.get("foreignTeachingCode"),
        "foreign_course_name": d.get("foreignCourseName"),
        "foreign_credits": d.get("foreignCredits"),
        "local_course_code": d.get("localCourseCode"),
        "local_course_name": d.get("localCourseName"),
        "local_credits": d.get("localCredits"),
    }


async def create(db: AsyncSession, data: dict, file, student_id: uuid.UUID) -> Application:
    if not (data.get("academicYear") and data.get("hostInstitutionId") and data.get("expectedPeriod") and data.get("referentLecturerId")):
        raise AppError("MISSING_FIELDS")
    if not file:
        raise AppError("MISSING_FILE")

    file_name, file_path = file
    mappings = parse_json_field(data.get("examMappings"), [])

    app = Application(
        student_id=student_id,
        academic_year=data["academicYear"],
        host_institution_id=_to_uuid(data["hostInstitutionId"]),
        expected_period=data["expectedPeriod"],
        referent_lecturer_id=_to_uuid(data["referentLecturerId"]),
        status="awaitingLA",
    )
    app.exam_mappings = [ExamMapping(position=i, **_mapping_kwargs(m)) for i, m in enumerate(mappings)]
    app.learning_agreements = [
        LearningAgreement(position=0, file_name=file_name, file_path=file_path, upload_date=_now(), status="pending")
    ]
    db.add(app)
    await db.flush()
    # Re-load fully populated, mirroring getPopulatedById.
    return await repo.get_student_application(db, str(app.id), student_id)


async def list_applications(db: AsyncSession, student_id: uuid.UUID) -> list[Application]:
    return await repo.list_student_applications(db, student_id)


async def get_by_id(db: AsyncSession, app_id: str, student_id: uuid.UUID) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    return app


async def update_application(db: AsyncSession, app_id: str, student_id: uuid.UUID, updates: dict) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app or app.status != "created":
        raise AppError("NOT_EDITABLE")

    for json_key, attr in EDITABLE_FIELDS.items():
        if updates.get(json_key) is not None:
            value = _to_uuid(updates[json_key]) if attr.endswith("_id") else updates[json_key]
            setattr(app, attr, value)
    if updates.get("examMappings") is not None:
        mappings = parse_json_field(updates.get("examMappings"), [])
        new_mappings = [ExamMapping(position=i, **_mapping_kwargs(m)) for i, m in enumerate(mappings)]
        app.exam_mappings = []
        await db.flush()
        app.exam_mappings = new_mappings

    await db.flush()
    return app


async def delete_application(db: AsyncSession, app_id: str, student_id: uuid.UUID) -> None:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    await db.delete(app)
    await db.flush()


async def upload_la(db: AsyncSession, app_id: str, student_id: uuid.UUID, file) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not file:
        raise AppError("MISSING_FILE")
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if any(la.status == "pending" for la in app.learning_agreements):
        raise AppError("PENDING_LA_EXISTS")

    file_name, file_path = file
    app.learning_agreements.append(
        LearningAgreement(
            position=len(app.learning_agreements),
            file_name=file_name,
            file_path=file_path,
            upload_date=_now(),
            status="pending",
        )
    )
    if app.status in ("created", "needs modifications"):
        app.status = "awaitingLA"
    await db.flush()
    return app


async def download_la(db: AsyncSession, app_id: str, student_id: uuid.UUID, index: int) -> LearningAgreement:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if index < 0 or index >= len(app.learning_agreements):
        raise AppError("NO_LA_FOUND")
    return app.learning_agreements[index]


async def set_dates(db: AsyncSession, app_id: str, student_id: uuid.UUID, arrival, departure) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status != "inProgress":
        raise AppError("INVALID_STATUS")
    if arrival:
        app.actual_arrival_date = arrival
    if departure:
        app.actual_departure_date = departure
    await db.flush()
    return app


async def propose_modification(db: AsyncSession, app_id: str, student_id: uuid.UUID, description, exam_mapping_diff, file) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status != "inProgress":
        raise AppError("INVALID_STATUS")
    if not file:
        raise AppError("MISSING_FILE")

    file_name, file_path = file
    diff = parse_json_field(exam_mapping_diff, [])

    mod = Modification(
        position=len(app.modifications),
        description=description,
        new_la_file_name=file_name,
        new_la_file_path=file_path,
        status="pending",
        created_at=_now(),
    )
    mod.exam_mappings = [ModificationExamMapping(position=i, **_mapping_kwargs(m)) for i, m in enumerate(diff)]
    app.modifications.append(mod)

    app.learning_agreements.append(
        LearningAgreement(
            position=len(app.learning_agreements),
            file_name=file_name,
            file_path=file_path,
            upload_date=_now(),
            status="pending",
        )
    )
    app.status = "needs modifications"
    await db.flush()
    return app


async def cancel_application(db: AsyncSession, app_id: str, student_id: uuid.UUID) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status in ("closed", "canceled"):
        raise AppError("CANNOT_CANCEL")
    app.status = "canceled"
    await db.flush()
    return app


async def ready_for_transcript(db: AsyncSession, app_id: str, student_id: uuid.UUID) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if app.status != "inProgress":
        raise AppError("INVALID_STATUS")
    app.status = "torUploaded"
    await db.flush()
    return app


async def upload_transcript(db: AsyncSession, app_id: str, student_id: uuid.UUID, file, exam_scores) -> Application:
    app = await repo.get_student_application(db, app_id, student_id)
    if not app:
        raise AppError("APPLICATION_NOT_FOUND")
    if not file:
        raise AppError("MISSING_FILE")
    if app.status != "torUploaded":
        raise AppError("INVALID_STATUS")

    file_name, file_path = file
    app.transcript_file_name = file_name
    app.transcript_file_path = file_path
    app.transcript_upload_date = _now()

    parsed = parse_json_field(exam_scores, None)
    if parsed:
        new_scores = [
            ExamScore(
                position=i,
                exam_mapping_index=s.get("examMappingIndex"),
                score=s.get("score"),
                exam_date=_coerce_date(s.get("examDate")),
                status="pending",
            )
            for i, s in enumerate(parsed)
        ]
        # Clear any existing scores first (re-upload) to avoid a unique
        # (application_id, position) collision mid-flush.
        app.exam_scores = []
        await db.flush()
        app.exam_scores = new_scores
    await db.flush()
    return app
