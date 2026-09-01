"""Translation from domain errors to HTTP responses.

The service layer raises :class:`~app.errors.AppError` with a stable code
and knows nothing about HTTP.  This module owns the other half: which
status each code deserves and what to tell the caller.  Registering the
handler here means every route gets the same behaviour without repeating
a try/except, and a service can add a code without touching any route.

Responses keep the shape the existing auth routes already use --
``{"error": <message>}`` -- with the stable code alongside it so a client
can branch on something other than prose.
"""

from .errors import AppError

NOT_FOUND = 404
CONFLICT = 409
BAD_REQUEST = 400

# Anything absent from this map falls back to 400, which is the right
# default for a domain rule the caller violated.
ERROR_RESPONSES = {
    # The caller asked for something that is not theirs or does not exist.
    # Scoped lookups deliberately return "not found" rather than
    # "forbidden", so an application's existence is not disclosed to a
    # user who has no claim on it (BR-04, BR-05).
    "APPLICATION_NOT_FOUND": (NOT_FOUND, "Application not found"),
    "EXAM_RESULT_NOT_FOUND": (NOT_FOUND, "Exam result not found"),
    "INSTITUTION_NOT_FOUND": (NOT_FOUND, "Institution not found"),
    "COORDINATOR_NOT_FOUND": (NOT_FOUND, "Coordinator not found"),
    "LEARNING_AGREEMENT_NOT_FOUND": (NOT_FOUND, "Learning Agreement version not found"),
    "TRANSCRIPT_NOT_FOUND": (NOT_FOUND, "No Transcript of Records has been uploaded"),
    "FILE_MISSING_FROM_STORAGE": (NOT_FOUND, "The stored file is no longer available"),

    # The request is well formed but conflicts with the application's
    # current state.
    "APPLICATION_CLOSED": (CONFLICT, "A closed application cannot be modified"),
    "INVALID_STATUS": (CONFLICT, "Not allowed while the application is in this status"),
    "INVALID_TRANSITION": (CONFLICT, "That status change is not part of the workflow"),
    "PENDING_LA_EXISTS": (
        CONFLICT,
        "A Learning Agreement is already awaiting a decision",
    ),
    "NO_PENDING_LA": (CONFLICT, "No Learning Agreement is awaiting a decision"),
    "NO_APPROVED_LA": (CONFLICT, "No approved Learning Agreement"),
    "RESULT_ALREADY_DECIDED": (CONFLICT, "This exam result has already been decided"),
    "PENDING_EXAM_RESULTS": (
        CONFLICT,
        "Every submitted exam must be decided before closing",
    ),
    "MISSING_TRANSCRIPT": (CONFLICT, "No Transcript of Records has been uploaded"),
    "MISSING_EXAM_RESULTS": (CONFLICT, "No exam results have been submitted"),
    "MISSING_COURSE_MAPPINGS": (BAD_REQUEST, "At least one course mapping is required"),
    "INSTITUTION_INACTIVE": (CONFLICT, "This institution is no longer available"),
    "MAPPING_NOT_IN_CURRENT_LA": (
        CONFLICT,
        "That course mapping is not part of the current Learning Agreement",
    ),

    # The request itself is wrong.
    "MISSING_FIELDS": (BAD_REQUEST, "Required fields are missing"),
    "MISSING_FILE": (BAD_REQUEST, "A file is required"),
    "INVALID_ACADEMIC_YEAR": (
        BAD_REQUEST,
        "Academic year must be YYYY/YYYY with consecutive years",
    ),
    "INVALID_PERIOD": (
        BAD_REQUEST,
        "Mobility period must be first_semester, second_semester or full_year",
    ),
    "INVALID_COORDINATOR": (BAD_REQUEST, "That user is not an academic coordinator"),
    "INVALID_COURSE_MAPPING": (
        BAD_REQUEST,
        "Each course mapping needs codes, names and positive credits",
    ),
    "DUPLICATE_COURSE_MAPPING": (
        BAD_REQUEST,
        "The same course pair appears more than once",
    ),
    "INVALID_DATES": (BAD_REQUEST, "Departure cannot be earlier than arrival"),
    "EXAM_DATE_OUT_OF_RANGE": (
        BAD_REQUEST,
        "The exam date falls outside the mobility period",
    ),
    "INVALID_EXAM_RESULT": (BAD_REQUEST, "Each exam result needs a grade and a date"),
    "INVALID_DECISION": (BAD_REQUEST, "Decision must be approved or rejected"),
    "REASON_REQUIRED": (BAD_REQUEST, "A rejection must include a reason"),
    "INVALID_STATUS_FILTER": (BAD_REQUEST, "Unknown application status"),
}

DEFAULT_RESPONSE = (BAD_REQUEST, "The request could not be completed")


def describe(error: AppError) -> tuple[dict, int]:
    """Render a domain error as a JSON body and status code."""
    status, message = ERROR_RESPONSES.get(error.code, DEFAULT_RESPONSE)

    return ({"error": message, "code": error.code}, status)


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        return describe(error)
