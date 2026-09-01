"""Application status workflow.

This module owns every write to ``MobilityApplication.status``.  Services
never assign the column directly: they call :func:`transition`, which
validates the move against the permitted workflow (BR-26) and records an
``ApplicationStatusHistory`` row so the lifecycle stays auditable.

The permitted moves follow the workflow in the requirements document,
with one addition: rejecting a Learning Agreement returns the application
to ``CREATED`` so the student can revise the mapping and upload a new
version (requirements document, section 5).
"""

from ..models import ApplicationStatus, ApplicationStatusHistory
from ..errors import AppError

PERMITTED_TRANSITIONS = {
    ApplicationStatus.CREATED: {
        ApplicationStatus.WAITING_LA_APPROVAL,
    },
    ApplicationStatus.WAITING_LA_APPROVAL: {
        # Coordinator rejected the agreement; the student revises it.
        ApplicationStatus.CREATED,
        # Office completes the pre-departure check on the approved agreement.
        ApplicationStatus.PRE_DEPARTURE_COMPLETED,
        # A modification approved mid-mobility resumes the mobility rather
        # than repeating the pre-departure phase.  Only reachable for an
        # application that already completed it, which ``has_reached``
        # decides, so this does not let a new application skip a phase.
        ApplicationStatus.MOBILITY_IN_PROGRESS,
    },
    ApplicationStatus.PRE_DEPARTURE_COMPLETED: {
        ApplicationStatus.MOBILITY_IN_PROGRESS,
    },
    ApplicationStatus.MOBILITY_IN_PROGRESS: {
        # A modification is a new Learning Agreement version, so it sends
        # the application back for approval without losing the mobility.
        ApplicationStatus.WAITING_LA_APPROVAL,
        ApplicationStatus.UNDER_EXAM_RECOGNITION,
    },
    ApplicationStatus.UNDER_EXAM_RECOGNITION: {
        ApplicationStatus.CLOSED,
    },
    ApplicationStatus.CLOSED: set(),
}


def record_initial(application) -> None:
    """Record the opening history row for a newly created application.

    ``old_status`` is null here: this is the only row in an application's
    history with no predecessor.
    """
    application.status_history.append(
        ApplicationStatusHistory(
            old_status=None,
            new_status=application.status,
        )
    )


def transition(application, new_status: ApplicationStatus) -> None:
    """Move an application to ``new_status`` and record the change.

    Raises ``AppError("INVALID_TRANSITION")`` when the move is not part of
    the permitted workflow.  History rows are appended through the
    relationship so the foreign key resolves on flush, which keeps a
    transition made in the same transaction as the insert working.
    """
    old_status = application.status

    if new_status not in PERMITTED_TRANSITIONS[old_status]:
        raise AppError("INVALID_TRANSITION")

    application.status = new_status

    application.status_history.append(
        ApplicationStatusHistory(
            old_status=old_status,
            new_status=new_status,
        )
    )


def has_reached(application, status: ApplicationStatus) -> bool:
    """Whether the application has ever been in ``status``.

    Read from the recorded history rather than the current status, so a
    phase stays "done" after the application moves on.  This is what
    separates an initial Learning Agreement approval from a modification
    approved during an ongoing mobility.
    """
    if application.status is status:
        return True

    return any(entry.new_status is status for entry in application.status_history)


def guard_not_closed(application) -> None:
    """Reject any change to a closed application (BR-09)."""
    if application.status is ApplicationStatus.CLOSED:
        raise AppError("APPLICATION_CLOSED")


def guard_status(application, *expected: ApplicationStatus) -> None:
    """Require the application to currently be in one of ``expected``."""
    if application.status not in expected:
        raise AppError("INVALID_STATUS")
