"""Data-access helpers (repository layer).

Query functions over the mobility application aggregate.  Ownership
scoping lives here rather than in the services: a student may only reach
their own applications (BR-04) and a coordinator only those assigned to
them (BR-05), so the scoped lookups simply return ``None`` for anything
outside the caller's reach and the service turns that into a not-found
error.  Office staff see every application (FR-01).
"""

from .database import db
from .models import (
    ApprovalStatus,
    ExamResult,
    Institution,
    LearningAgreement,
    MobilityApplication,
    UserAccount,
    UserRole,
)


def _to_id(value) -> int | None:
    """Coerce a path/body identifier to int; ``None`` when it is not one."""
    if isinstance(value, bool):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_student_application(application_id, student_id) -> MobilityApplication | None:
    identifier = _to_id(application_id)

    if identifier is None:
        return None

    return db.session.execute(
        db.select(MobilityApplication).where(
            MobilityApplication.application_id == identifier,
            MobilityApplication.student_id == student_id,
        )
    ).scalar_one_or_none()


def list_student_applications(student_id) -> list[MobilityApplication]:
    return list(
        db.session.execute(
            db.select(MobilityApplication)
            .where(MobilityApplication.student_id == student_id)
            .order_by(MobilityApplication.application_id.desc())
        ).scalars()
    )


def get_coordinator_application(application_id, coordinator_id) -> MobilityApplication | None:
    identifier = _to_id(application_id)

    if identifier is None:
        return None

    return db.session.execute(
        db.select(MobilityApplication).where(
            MobilityApplication.application_id == identifier,
            MobilityApplication.coordinator_id == coordinator_id,
        )
    ).scalar_one_or_none()


def list_coordinator_applications(coordinator_id) -> list[MobilityApplication]:
    return list(
        db.session.execute(
            db.select(MobilityApplication)
            .where(MobilityApplication.coordinator_id == coordinator_id)
            .order_by(MobilityApplication.application_id.desc())
        ).scalars()
    )


def get_application(application_id) -> MobilityApplication | None:
    identifier = _to_id(application_id)

    if identifier is None:
        return None

    return db.session.get(MobilityApplication, identifier)


def list_applications(status=None) -> list[MobilityApplication]:
    statement = db.select(MobilityApplication).order_by(
        MobilityApplication.application_id.desc()
    )

    if status is not None:
        statement = statement.where(MobilityApplication.status == status)

    return list(db.session.execute(statement).scalars())


def latest_learning_agreement(application) -> LearningAgreement | None:
    """The most recently uploaded Learning Agreement version, if any."""
    if not application.learning_agreements:
        return None

    return max(
        application.learning_agreements,
        key=lambda agreement: agreement.version_number,
    )


def current_approved_learning_agreement(application) -> LearningAgreement | None:
    """The highest approved version: the mapping currently in force.

    An approved modification is simply a later approved version, so this
    is what makes BR-13 and BR-14 hold without moving any rows around.
    """
    approved = [
        agreement
        for agreement in application.learning_agreements
        if agreement.approval_status is ApprovalStatus.APPROVED
    ]

    if not approved:
        return None

    return max(approved, key=lambda agreement: agreement.version_number)


def has_pending_learning_agreement(application) -> bool:
    return any(
        agreement.approval_status is ApprovalStatus.PENDING
        for agreement in application.learning_agreements
    )


def next_learning_agreement_version(application) -> int:
    """Version numbers are unique within an application (BR-16)."""
    latest = latest_learning_agreement(application)

    return 1 if latest is None else latest.version_number + 1


def get_exam_result(result_id) -> ExamResult | None:
    identifier = _to_id(result_id)

    if identifier is None:
        return None

    return db.session.get(ExamResult, identifier)


def list_institutions(active_only: bool = True) -> list[Institution]:
    statement = db.select(Institution).order_by(Institution.name.asc())

    if active_only:
        statement = statement.where(Institution.is_active.is_(True))

    return list(db.session.execute(statement).scalars())


def get_institution(institution_id) -> Institution | None:
    identifier = _to_id(institution_id)

    if identifier is None:
        return None

    return db.session.get(Institution, identifier)


def list_coordinators() -> list[UserAccount]:
    return list(
        db.session.execute(
            db.select(UserAccount)
            .where(UserAccount.user_role == UserRole.COORDINATOR)
            .order_by(UserAccount.last_name.asc())
        ).scalars()
    )


def get_user(user_id) -> UserAccount | None:
    identifier = _to_id(user_id)

    if identifier is None:
        return None

    return db.session.get(UserAccount, identifier)


def find_user_by_email(email: str) -> UserAccount | None:
    return db.session.execute(
        db.select(UserAccount).where(UserAccount.email == email)
    ).scalar_one_or_none()
