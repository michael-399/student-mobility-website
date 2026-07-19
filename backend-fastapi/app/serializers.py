"""Response serialisers.

These build plain dicts that reproduce, key-for-key, the JSON the legacy
Mongoose/Express backend returned — including the ``_id`` naming, the
nested "populated" objects, and the omission of unset optional fields
(Mongoose leaves ``undefined`` fields out of the response).

The ``populate_*`` flags reproduce the per-role ``.populate(...)`` calls:
  * student endpoints populate host institution + referent lecturer
  * lecturer endpoints populate student + host institution
  * office endpoints populate all three
Non-populated references serialise to their id string, exactly as an
un-populated Mongoose ObjectId would.
"""

from __future__ import annotations

from app.db.models import (
    Application,
    ExamMapping,
    ExamScore,
    Institution,
    LearningAgreement,
    Modification,
    ModificationExamMapping,
    User,
)


def serialize_user(u: User) -> dict:
    return {"_id": str(u.id), "name": u.name, "email": u.email}


def serialize_institution(i: Institution) -> dict:
    return {"_id": str(i.id), "name": i.name, "country": i.country, "city": i.city}


def serialize_mapping(m: ExamMapping | ModificationExamMapping) -> dict:
    return {
        "foreignTeachingCode": m.foreign_teaching_code,
        "foreignCourseName": m.foreign_course_name,
        "foreignCredits": float(m.foreign_credits),
        "localCourseCode": m.local_course_code,
        "localCourseName": m.local_course_name,
        "localCredits": float(m.local_credits),
    }


def serialize_learning_agreement(la: LearningAgreement) -> dict:
    d: dict = {
        "fileName": la.file_name,
        "filePath": la.file_path,
        "uploadDate": la.upload_date,
        "status": la.status,
    }
    if la.decision_date is not None:
        d["decisionDate"] = la.decision_date
    if la.reason is not None:
        d["reason"] = la.reason
    return d


def serialize_modification(mod: Modification) -> dict:
    d: dict = {
        "_id": str(mod.id),
        "description": mod.description,
        "examMappingDiff": [serialize_mapping(m) for m in mod.exam_mappings],
        "newLAFile": {"fileName": mod.new_la_file_name, "filePath": mod.new_la_file_path},
        "status": mod.status,
        "createdAt": mod.created_at,
    }
    if mod.decision_date is not None:
        d["decisionDate"] = mod.decision_date
    if mod.reason is not None:
        d["reason"] = mod.reason
    return d


def serialize_exam_score(s: ExamScore) -> dict:
    d: dict = {
        "examMappingIndex": s.exam_mapping_index,
        "score": s.score,
        "status": s.status,
    }
    if s.exam_date is not None:
        d["examDate"] = s.exam_date
    if s.approved_by is not None:
        d["approvedBy"] = str(s.approved_by)
    if s.approved_at is not None:
        d["approvedAt"] = s.approved_at
    return d


def serialize_application(
    app: Application,
    *,
    populate_student: bool = False,
    populate_lecturer: bool = False,
    populate_institution: bool = False,
) -> dict:
    d: dict = {
        "_id": str(app.id),
        "studentId": serialize_user(app.student) if populate_student else str(app.student_id),
        "academicYear": app.academic_year,
        "hostInstitutionId": (
            serialize_institution(app.host_institution)
            if populate_institution
            else str(app.host_institution_id)
        ),
        "expectedPeriod": app.expected_period,
        "referentLecturerId": (
            serialize_user(app.referent_lecturer) if populate_lecturer else str(app.referent_lecturer_id)
        ),
        "status": app.status,
        "learningAgreements": [serialize_learning_agreement(la) for la in app.learning_agreements],
        "examMappings": [serialize_mapping(m) for m in app.exam_mappings],
        "preDepartureCompleted": app.pre_departure_completed,
        "modifications": [serialize_modification(m) for m in app.modifications],
        "examScores": [serialize_exam_score(s) for s in app.exam_scores],
        "createdAt": app.created_at,
        "updatedAt": app.updated_at,
    }

    if app.pre_departure_completed_at is not None:
        d["preDepartureCompletedAt"] = app.pre_departure_completed_at
    if app.pre_departure_completed_by is not None:
        d["preDepartureCompletedBy"] = str(app.pre_departure_completed_by)
    if app.actual_arrival_date is not None:
        d["actualArrivalDate"] = app.actual_arrival_date
    if app.actual_departure_date is not None:
        d["actualDepartureDate"] = app.actual_departure_date
    if app.transcript_file_name is not None:
        d["transcriptOfRecords"] = {
            "fileName": app.transcript_file_name,
            "filePath": app.transcript_file_path,
            "uploadDate": app.transcript_upload_date,
        }
    if app.closed_at is not None:
        d["closedAt"] = app.closed_at
    if app.closed_by is not None:
        d["closedBy"] = str(app.closed_by)

    return d
