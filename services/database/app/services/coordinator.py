"""Coordinator service: academic decisions on an assigned application.

Covers FR-05 and FR-10.  Every lookup goes through the repository's
coordinator-scoped queries, so an application assigned to a colleague is
simply not found (BR-05).

Both decisions share the same shape, enforced by the database as a CHECK
constraint and validated here first so the caller gets a clear error
instead of an integrity failure: a pending decision carries no date and
no reason (BR-17), a decided one carries a date (BR-18), and a rejection
carries a non-empty reason (BR-19).
"""

from datetime import date

from .. import repositories as repo
from ..database import db
from ..errors import AppError
from ..models import (
    ApplicationStatus,
    ApprovalStatus,
    LearningAgreement,
    MobilityApplication,
    RecognitionStatus,
)
from ._workflow import guard_not_closed, guard_status, has_reached, transition

APPROVED = "approved"
REJECTED = "rejected"
DECISIONS = (APPROVED, REJECTED)


def _require_application(application_id, coordinator_id) -> MobilityApplication:
    application = repo.get_coordinator_application(application_id, coordinator_id)

    if application is None:
        raise AppError("APPLICATION_NOT_FOUND")

    return application


def _validate_decision(decision, reason) -> tuple[str, str | None]:
    """Normalise a decision and the reason that must accompany a rejection."""
    value = getattr(decision, "value", decision)

    if value not in DECISIONS:
        raise AppError("INVALID_DECISION")

    if value == REJECTED:
        text = (reason or "").strip()

        if not text:
            raise AppError("REASON_REQUIRED")

        return (REJECTED, text)

    return (APPROVED, None)


def list_applications(coordinator_id) -> list[MobilityApplication]:
    return repo.list_coordinator_applications(coordinator_id)


def get_application(application_id, coordinator_id) -> MobilityApplication:
    return _require_application(application_id, coordinator_id)


def evaluate_learning_agreement(
    application_id,
    coordinator_id,
    decision,
    reason=None,
) -> MobilityApplication:
    """Approve or reject the agreement awaiting a decision (FR-05).

    Approval of a first agreement leaves the application awaiting the
    office's pre-departure check; approval of a revision proposed during
    an ongoing mobility resumes that mobility instead, since the
    pre-departure phase is already behind it.  Rejection returns the
    application to the student, who revises the mapping and uploads the
    next version (requirements document, section 5).
    """
    application = _require_application(application_id, coordinator_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.WAITING_LA_APPROVAL)

    outcome, rejection_reason = _validate_decision(decision, reason)

    agreement = _pending_agreement(application)
    agreement.decision_date = date.today()

    if outcome == REJECTED:
        agreement.approval_status = ApprovalStatus.REJECTED
        agreement.rejection_reason = rejection_reason
        transition(application, ApplicationStatus.CREATED)
    else:
        agreement.approval_status = ApprovalStatus.APPROVED
        agreement.rejection_reason = None

        if has_reached(application, ApplicationStatus.PRE_DEPARTURE_COMPLETED):
            transition(application, ApplicationStatus.MOBILITY_IN_PROGRESS)

    db.session.flush()

    return application


def _pending_agreement(application) -> LearningAgreement:
    pending = [
        agreement
        for agreement in application.learning_agreements
        if agreement.approval_status is ApprovalStatus.PENDING
    ]

    if not pending:
        raise AppError("NO_PENDING_LA")

    return max(pending, key=lambda agreement: agreement.version_number)


def evaluate_exam_result(result_id, coordinator_id, decision, reason=None):
    """Approve or reject one proposed exam recognition (FR-10).

    Returns the decided result.  Only results attached to the agreement
    currently in force can be decided (BR-24): a mapping superseded by a
    later approved version is no longer part of the recognition.
    """
    result = repo.get_exam_result(result_id)

    if result is None:
        raise AppError("EXAM_RESULT_NOT_FOUND")

    mapping = result.course_mapping
    application = repo.get_coordinator_application(mapping.application_id, coordinator_id)

    if application is None:
        raise AppError("EXAM_RESULT_NOT_FOUND")

    guard_not_closed(application)
    guard_status(application, ApplicationStatus.UNDER_EXAM_RECOGNITION)

    current = repo.current_approved_learning_agreement(application)

    if current is None or mapping.version_number != current.version_number:
        raise AppError("MAPPING_NOT_IN_CURRENT_LA")

    if result.recognition_status is not RecognitionStatus.PENDING:
        raise AppError("RESULT_ALREADY_DECIDED")

    outcome, rejection_reason = _validate_decision(decision, reason)

    result.decision_date = date.today()

    if outcome == REJECTED:
        result.recognition_status = RecognitionStatus.REJECTED
        result.rejection_reason = rejection_reason
    else:
        result.recognition_status = RecognitionStatus.APPROVED
        result.rejection_reason = None

    db.session.flush()

    return result
