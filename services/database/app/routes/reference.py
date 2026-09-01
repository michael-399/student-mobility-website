"""Reference data endpoints.

Available to any signed-in user: a student filling in an application
needs both lists, and the other roles need them to render the same
values back.  Managing institutions is a separate, office-only concern
under ``/office/institutions``.
"""

from flask import Blueprint

from ..serializers import serialize_institution, serialize_user
from ..services import reference as reference_service
from .decorators import login_required

reference_bp = Blueprint("reference", __name__, url_prefix="/reference")


@reference_bp.get("/institutions")
@login_required
def list_institutions():
    institutions = reference_service.list_institutions()

    return {
        "institutions": [serialize_institution(i) for i in institutions]
    }, 200


@reference_bp.get("/coordinators")
@login_required
def list_coordinators():
    coordinators = reference_service.list_coordinators()

    return {
        "coordinators": [serialize_user(c) for c in coordinators]
    }, 200
