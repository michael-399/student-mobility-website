"""Overseas office endpoints (FR-02, FR-06, FR-11).

The office sees every application (FR-01), so nothing here is scoped to
an owner; the role check is the authorisation.
"""

from flask import Blueprint, request

from ..models import UserRole
from ..serializers import (
    serialize_application,
    serialize_application_detail,
    serialize_institution,
)
from ..services import documents
from ..services import office as office_service
from ._helpers import json_body, send_stored_file
from .decorators import role_required

office_bp = Blueprint("office", __name__, url_prefix="/office")


@office_bp.get("/applications")
@role_required(UserRole.OFFICE_STAFF)
def list_applications():
    applications = office_service.list_applications(request.args.get("status"))

    return {
        "applications": [serialize_application(a) for a in applications]
    }, 200


@office_bp.get("/applications/<application_id>")
@role_required(UserRole.OFFICE_STAFF)
def get_application(application_id):
    application = office_service.get_application(application_id)

    return {"application": serialize_application_detail(application)}, 200


@office_bp.get(
    "/applications/<application_id>/learning-agreements/<version_number>/file"
)
@role_required(UserRole.OFFICE_STAFF)
def download_learning_agreement(application_id, version_number):
    application = office_service.get_application(application_id)
    agreement = documents.learning_agreement(application, version_number)

    return send_stored_file(
        agreement.file_path,
        documents.learning_agreement_filename(agreement),
    )


@office_bp.get("/applications/<application_id>/transcript/file")
@role_required(UserRole.OFFICE_STAFF)
def download_transcript(application_id):
    application = office_service.get_application(application_id)
    transcript = documents.transcript(application)

    return send_stored_file(
        transcript.file_path,
        documents.transcript_filename(application),
    )


@office_bp.post("/applications/<application_id>/pre-departure")
@role_required(UserRole.OFFICE_STAFF)
def complete_pre_departure(application_id):
    application = office_service.complete_pre_departure(application_id)

    return {"application": serialize_application_detail(application)}, 200


@office_bp.post("/applications/<application_id>/close")
@role_required(UserRole.OFFICE_STAFF)
def close_application(application_id):
    application = office_service.close_application(application_id)

    return {"application": serialize_application_detail(application)}, 200


@office_bp.get("/institutions")
@role_required(UserRole.OFFICE_STAFF)
def list_institutions():
    """Every institution, including retired ones with ``?include_inactive=true``."""
    include_inactive = request.args.get("include_inactive", "").lower() in (
        "1",
        "true",
        "yes",
    )
    institutions = office_service.list_institutions(active_only=not include_inactive)

    return {
        "institutions": [serialize_institution(i) for i in institutions]
    }, 200


@office_bp.post("/institutions")
@role_required(UserRole.OFFICE_STAFF)
def create_institution():
    institution = office_service.create_institution(json_body())

    return {"institution": serialize_institution(institution)}, 201


@office_bp.patch("/institutions/<institution_id>")
@role_required(UserRole.OFFICE_STAFF)
def update_institution(institution_id):
    institution = office_service.update_institution(institution_id, json_body())

    return {"institution": serialize_institution(institution)}, 200


@office_bp.post("/institutions/<institution_id>/deactivate")
@role_required(UserRole.OFFICE_STAFF)
def deactivate_institution(institution_id):
    institution = office_service.deactivate_institution(institution_id)

    return {"institution": serialize_institution(institution)}, 200


@office_bp.post("/institutions/<institution_id>/reactivate")
@role_required(UserRole.OFFICE_STAFF)
def reactivate_institution(institution_id):
    institution = office_service.reactivate_institution(institution_id)

    return {"institution": serialize_institution(institution)}, 200
