"""Student endpoints (FR-03, FR-04, FR-05, FR-07, FR-09).

Every view is behind ``role_required(UserRole.STUDENT)`` and passes the
signed-in user's id to the service, which scopes the lookup to their own
applications (BR-04).  Domain errors propagate to the handler registered
in ``app.http``; the transaction is committed by the boundary in
``create_app``.
"""

from flask import Blueprint, request

from ..models import UserRole
from ..serializers import serialize_application, serialize_application_detail
from ..services import documents
from ..services import student as student_service
from ._helpers import (
    COURSE_MAPPINGS_FIELD,
    current_user_id,
    json_body,
    send_stored_file,
    uploaded_file,
)
from .decorators import role_required

student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.get("/applications")
@role_required(UserRole.STUDENT)
def list_applications():
    applications = student_service.list_applications(current_user_id())

    return {
        "applications": [serialize_application(a) for a in applications]
    }, 200


@student_bp.post("/applications")
@role_required(UserRole.STUDENT)
def create_application():
    application = student_service.create_application(current_user_id(), json_body())

    return {"application": serialize_application_detail(application)}, 201


@student_bp.get("/applications/<application_id>")
@role_required(UserRole.STUDENT)
def get_application(application_id):
    application = student_service.get_application(application_id, current_user_id())

    return {"application": serialize_application_detail(application)}, 200


@student_bp.patch("/applications/<application_id>")
@role_required(UserRole.STUDENT)
def update_application(application_id):
    application = student_service.update_application(
        application_id,
        current_user_id(),
        json_body(),
    )

    return {"application": serialize_application_detail(application)}, 200


@student_bp.delete("/applications/<application_id>")
@role_required(UserRole.STUDENT)
def delete_application(application_id):
    student_service.delete_application(application_id, current_user_id())

    return "", 204


@student_bp.post("/applications/<application_id>/learning-agreements")
@role_required(UserRole.STUDENT)
def upload_learning_agreement(application_id):
    """Submit the next agreement version with its course mappings.

    Multipart: the signed agreement as ``file``, and the mappings as a
    JSON array in ``course_mappings``.
    """
    application = student_service.upload_learning_agreement(
        application_id,
        current_user_id(),
        uploaded_file(),
        request.form.get(COURSE_MAPPINGS_FIELD),
    )

    return {"application": serialize_application_detail(application)}, 201


@student_bp.get(
    "/applications/<application_id>/learning-agreements/<version_number>/file"
)
@role_required(UserRole.STUDENT)
def download_learning_agreement(application_id, version_number):
    application = student_service.get_application(application_id, current_user_id())
    agreement = documents.learning_agreement(application, version_number)

    return send_stored_file(
        agreement.file_path,
        documents.learning_agreement_filename(agreement),
    )


@student_bp.get("/applications/<application_id>/transcript/file")
@role_required(UserRole.STUDENT)
def download_transcript(application_id):
    application = student_service.get_application(application_id, current_user_id())
    transcript = documents.transcript(application)

    return send_stored_file(
        transcript.file_path,
        documents.transcript_filename(application),
    )


@student_bp.patch("/applications/<application_id>/mobility-dates")
@role_required(UserRole.STUDENT)
def set_mobility_dates(application_id):
    body = json_body()
    application = student_service.set_mobility_dates(
        application_id,
        current_user_id(),
        arrival_date=body.get("actual_arrival_date"),
        departure_date=body.get("actual_departure_date"),
    )

    return {"application": serialize_application_detail(application)}, 200


@student_bp.post("/applications/<application_id>/transcript")
@role_required(UserRole.STUDENT)
def upload_transcript(application_id):
    application = student_service.upload_transcript(
        application_id,
        current_user_id(),
        uploaded_file(),
    )

    return {"application": serialize_application_detail(application)}, 201


@student_bp.put("/applications/<application_id>/exam-results")
@role_required(UserRole.STUDENT)
def record_exam_results(application_id):
    application = student_service.record_exam_results(
        application_id,
        current_user_id(),
        json_body().get("exam_results"),
    )

    return {"application": serialize_application_detail(application)}, 200
