"""Academic coordinator endpoints (FR-05, FR-10).

Scoped by the service to applications assigned to the signed-in
coordinator (BR-05).
"""

from flask import Blueprint

from ..models import UserRole
from ..serializers import (
    serialize_application,
    serialize_application_detail,
    serialize_exam_result,
)
from ..services import coordinator as coordinator_service
from ..services import documents
from ._helpers import current_user_id, json_body, send_stored_file
from .decorators import role_required

coordinator_bp = Blueprint("coordinator", __name__, url_prefix="/coordinator")


@coordinator_bp.get("/applications")
@role_required(UserRole.COORDINATOR)
def list_applications():
    applications = coordinator_service.list_applications(current_user_id())

    return {
        "applications": [serialize_application(a) for a in applications]
    }, 200


@coordinator_bp.get("/applications/<application_id>")
@role_required(UserRole.COORDINATOR)
def get_application(application_id):
    application = coordinator_service.get_application(application_id, current_user_id())

    return {"application": serialize_application_detail(application)}, 200


@coordinator_bp.get(
    "/applications/<application_id>/learning-agreements/<version_number>/file"
)
@role_required(UserRole.COORDINATOR)
def download_learning_agreement(application_id, version_number):
    """Read the agreement before deciding on it."""
    application = coordinator_service.get_application(application_id, current_user_id())
    agreement = documents.learning_agreement(application, version_number)

    return send_stored_file(
        agreement.file_path,
        documents.learning_agreement_filename(agreement),
    )


@coordinator_bp.get("/applications/<application_id>/transcript/file")
@role_required(UserRole.COORDINATOR)
def download_transcript(application_id):
    application = coordinator_service.get_application(application_id, current_user_id())
    transcript = documents.transcript(application)

    return send_stored_file(
        transcript.file_path,
        documents.transcript_filename(application),
    )


@coordinator_bp.post("/applications/<application_id>/learning-agreement/decision")
@role_required(UserRole.COORDINATOR)
def decide_learning_agreement(application_id):
    """Approve or reject the version awaiting a decision.

    Body: ``decision`` of "approved" or "rejected", plus ``reason``,
    which a rejection must carry (BR-19).
    """
    body = json_body()
    application = coordinator_service.evaluate_learning_agreement(
        application_id,
        current_user_id(),
        body.get("decision"),
        body.get("reason"),
    )

    return {"application": serialize_application_detail(application)}, 200


@coordinator_bp.post("/exam-results/<result_id>/decision")
@role_required(UserRole.COORDINATOR)
def decide_exam_result(result_id):
    body = json_body()
    result = coordinator_service.evaluate_exam_result(
        result_id,
        current_user_id(),
        body.get("decision"),
        body.get("reason"),
    )

    return {"exam_result": serialize_exam_result(result)}, 200
