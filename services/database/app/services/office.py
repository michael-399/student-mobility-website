"""Office service: partner institutions, pre-departure check, closure.

Covers FR-02, FR-06 and FR-11.  Office staff see every application
(FR-01), so nothing here is scoped to an owner; the role check belongs to
the route.

The office owns the two administrative gates of the lifecycle.  It signs
off the pre-departure check once the coordinator has approved a Learning
Agreement (BR-20), and it closes the application once the transcript is
in and every submitted exam has been decided (BR-25).  What happens in
between — arriving, revising the agreement, uploading results — belongs
to the student and the coordinator.
"""

from .. import repositories as repo
from ..database import db
from ..errors import AppError
from ..models import (
    ApplicationStatus,
    Institution,
    MobilityApplication,
    RecognitionStatus,
)
from ._workflow import guard_not_closed, guard_status, transition

REQUIRED_INSTITUTION_FIELDS = ("name", "country", "city")


def _require_application(application_id) -> MobilityApplication:
    application = repo.get_application(application_id)

    if application is None:
        raise AppError("APPLICATION_NOT_FOUND")

    return application


def list_applications(status=None) -> list[MobilityApplication]:
    """Every application, optionally filtered by status (FR-01)."""
    if status is not None and not isinstance(status, ApplicationStatus):
        try:
            status = ApplicationStatus(str(status))
        except ValueError:
            raise AppError("INVALID_STATUS_FILTER")

    return repo.list_applications(status)


def get_application(application_id) -> MobilityApplication:
    return _require_application(application_id)


def complete_pre_departure(application_id) -> MobilityApplication:
    """Sign off the pre-departure check (FR-06).

    Requires an approved Learning Agreement (BR-20) carrying at least one
    course mapping (FR-04).  The mobility itself starts when the student
    reports arriving at the host institution.
    """
    application = _require_application(application_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.WAITING_LA_APPROVAL)

    approved = repo.current_approved_learning_agreement(application)

    if approved is None:
        raise AppError("NO_APPROVED_LA")

    if not approved.course_mappings:
        raise AppError("MISSING_COURSE_MAPPINGS")

    transition(application, ApplicationStatus.PRE_DEPARTURE_COMPLETED)
    db.session.flush()

    return application


def close_application(application_id) -> MobilityApplication:
    """Close an application once recognition is complete (FR-11).

    Requires the Transcript of Records and a decision on every exam the
    student submitted (BR-25).  A rejected recognition is a decision, so
    it does not hold closure open; only a pending one does.
    """
    application = _require_application(application_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.UNDER_EXAM_RECOGNITION)

    if application.transcript is None:
        raise AppError("MISSING_TRANSCRIPT")

    approved = repo.current_approved_learning_agreement(application)

    if approved is None:
        raise AppError("NO_APPROVED_LA")

    results = [
        mapping.exam_result
        for mapping in approved.course_mappings
        if mapping.exam_result is not None
    ]

    if not results:
        raise AppError("MISSING_EXAM_RESULTS")

    if any(
        result.recognition_status is RecognitionStatus.PENDING for result in results
    ):
        raise AppError("PENDING_EXAM_RESULTS")

    transition(application, ApplicationStatus.CLOSED)
    db.session.flush()

    return application


def list_institutions(active_only: bool = True) -> list[Institution]:
    return repo.list_institutions(active_only=active_only)


def create_institution(data: dict) -> Institution:
    """Add a partner institution to the predefined list (FR-02)."""
    missing = [
        field for field in REQUIRED_INSTITUTION_FIELDS if not (data.get(field) or "").strip()
    ]

    if missing:
        raise AppError("MISSING_FIELDS")

    institution = Institution(
        name=data["name"].strip(),
        country=data["country"].strip(),
        city=data["city"].strip(),
        contact_email=(data.get("contact_email") or None),
    )

    db.session.add(institution)
    db.session.flush()

    return institution


def update_institution(institution_id, updates: dict) -> Institution:
    institution = repo.get_institution(institution_id)

    if institution is None:
        raise AppError("INSTITUTION_NOT_FOUND")

    for field in REQUIRED_INSTITUTION_FIELDS:
        if field in updates:
            value = (updates[field] or "").strip()

            if not value:
                raise AppError("MISSING_FIELDS")

            setattr(institution, field, value)

    if "contact_email" in updates:
        institution.contact_email = updates["contact_email"] or None

    db.session.flush()

    return institution


def deactivate_institution(institution_id) -> Institution:
    """Retire an institution without deleting it.

    Applications reference institutions with ``ON DELETE RESTRICT``, and
    past applications must keep pointing at the institution they were made
    for, so a retired partner is deactivated and simply stops appearing in
    the list students choose from.
    """
    institution = repo.get_institution(institution_id)

    if institution is None:
        raise AppError("INSTITUTION_NOT_FOUND")

    institution.is_active = False
    db.session.flush()

    return institution


def reactivate_institution(institution_id) -> Institution:
    institution = repo.get_institution(institution_id)

    if institution is None:
        raise AppError("INSTITUTION_NOT_FOUND")

    institution.is_active = True
    db.session.flush()

    return institution
