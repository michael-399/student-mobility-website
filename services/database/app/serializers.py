"""Response serialisers.

Services return SQLAlchemy models; routes return JSON.  This module owns
that conversion, so the shape of the API is described in one place rather
than scattered across route handlers.

Two deliberate choices:

* Dates and decimals are converted explicitly.  Flask would render a
  ``date`` as an RFC 822 string and refuse a ``Decimal`` outright, so
  every one is turned into an ISO string or a float here.
* Stored file paths are never exposed.  They are server-side locations,
  and a Learning Agreement or transcript always has one, so its presence
  carries no information the client cannot already infer.
"""


def _date(value):
    return value.isoformat() if value is not None else None


def _credits(value):
    return float(value) if value is not None else None


def serialize_user(user) -> dict | None:
    if user is None:
        return None

    return {
        "user_id": user.user_id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.user_role.value,
    }


def serialize_institution(institution) -> dict | None:
    if institution is None:
        return None

    return {
        "institution_id": institution.institution_id,
        "name": institution.name,
        "country": institution.country,
        "city": institution.city,
        "contact_email": institution.contact_email,
        "is_active": institution.is_active,
    }


def serialize_exam_result(result) -> dict | None:
    if result is None:
        return None

    return {
        "result_id": result.result_id,
        "mapping_id": result.mapping_id,
        "foreign_grade": result.foreign_grade,
        "exam_date": _date(result.exam_date),
        "recognition_status": result.recognition_status.value,
        "decision_date": _date(result.decision_date),
        "rejection_reason": result.rejection_reason,
    }


def serialize_course_mapping(mapping) -> dict:
    return {
        "mapping_id": mapping.mapping_id,
        "home_course_code": mapping.home_course_code,
        "home_course_name": mapping.home_course_name,
        "home_course_credits": _credits(mapping.home_course_credits),
        "foreign_course_code": mapping.foreign_course_code,
        "foreign_course_name": mapping.foreign_course_name,
        "foreign_course_credits": _credits(mapping.foreign_course_credits),
        "exam_result": serialize_exam_result(mapping.exam_result),
    }


def serialize_learning_agreement(agreement) -> dict:
    return {
        "version_number": agreement.version_number,
        "uploaded_at": _date(agreement.uploaded_at),
        "approval_status": agreement.approval_status.value,
        "decision_date": _date(agreement.decision_date),
        "rejection_reason": agreement.rejection_reason,
        "course_mappings": [
            serialize_course_mapping(mapping) for mapping in agreement.course_mappings
        ],
    }


def serialize_transcript(transcript) -> dict | None:
    if transcript is None:
        return None

    return {
        "transcript_id": transcript.transcript_id,
        "uploaded_at": _date(transcript.uploaded_at),
    }


def serialize_status_change(entry) -> dict:
    return {
        "old_status": entry.old_status.value if entry.old_status else None,
        "new_status": entry.new_status.value,
        "changed_at": _date(entry.changed_at),
    }


def serialize_application(application) -> dict:
    """The summary form, used for lists."""
    return {
        "application_id": application.application_id,
        "academic_year": application.academic_year,
        "optional_note": application.optional_note,
        "expected_mobility_period": application.expected_mobility_period.value,
        "status": application.status.value,
        "student": serialize_user(application.student),
        "academic_coordinator": serialize_user(application.academic_coordinator),
        "host_institution": serialize_institution(application.host_institution),
        "actual_arrival_date": _date(application.actual_arrival_date),
        "actual_departure_date": _date(application.actual_departure_date),
    }


def serialize_application_detail(application) -> dict:
    """The full aggregate: agreements, mappings, results, history."""
    agreements = sorted(
        application.learning_agreements,
        key=lambda agreement: agreement.version_number,
    )

    return {
        **serialize_application(application),
        "learning_agreements": [
            serialize_learning_agreement(agreement) for agreement in agreements
        ],
        "transcript": serialize_transcript(application.transcript),
        "status_history": [
            serialize_status_change(entry) for entry in application.status_history
        ],
    }
