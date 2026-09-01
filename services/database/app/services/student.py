"""Student service: the application lifecycle from the student's side.

Covers FR-03, FR-04, FR-05, FR-07 and FR-09.  Every lookup goes through
the repository's student-scoped queries, so an application belonging to
someone else is simply not found (BR-04).

Proposing a modification is not a separate operation here: a revised
course mapping is a new Learning Agreement version, so
:func:`upload_learning_agreement` serves both the first submission and
every later revision.  That is what makes an approved modification become
the current mapping (BR-13) and a rejected one leave the previous mapping
standing (BR-14) without moving any rows.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

from .. import repositories as repo
from ..database import db
from ..errors import AppError
from ..models import (
    ApplicationStatus,
    CourseMapping,
    ExamResult,
    LearningAgreement,
    MobilityApplication,
    MobilityPeriod,
    RecognitionStatus,
    TranscriptOfRecords,
    UserRole,
)
from ..storage import save_upload
from ._parsing import parse_date, parse_json_field
from ._workflow import guard_not_closed, guard_status, record_initial, transition

REQUIRED_CREATE_FIELDS = (
    "academic_year",
    "host_institution_id",
    "expected_mobility_period",
    "coordinator_id",
)

MAPPING_TEXT_FIELDS = (
    "home_course_code",
    "home_course_name",
    "foreign_course_code",
    "foreign_course_name",
)

MAPPING_CREDIT_FIELDS = (
    "home_course_credits",
    "foreign_course_credits",
)


def _require_application(application_id, student_id) -> MobilityApplication:
    application = repo.get_student_application(application_id, student_id)

    if application is None:
        raise AppError("APPLICATION_NOT_FOUND")

    return application


def _validate_academic_year(value) -> str:
    """Format ``YYYY/YYYY`` with consecutive years (BR-07).

    The database CHECK enforces the shape but cannot express "the second
    year is the first plus one", so that half is enforced here.
    """
    text = str(value)
    first, separator, second = text.partition("/")

    if separator != "/" or not (first.isdigit() and second.isdigit()):
        raise AppError("INVALID_ACADEMIC_YEAR")

    if len(first) != 4 or len(second) != 4 or int(second) != int(first) + 1:
        raise AppError("INVALID_ACADEMIC_YEAR")

    return text


def _validate_period(value) -> MobilityPeriod:
    """First semester, second semester, or full year (BR-08)."""
    if isinstance(value, MobilityPeriod):
        return value

    try:
        return MobilityPeriod(str(value))
    except ValueError:
        raise AppError("INVALID_PERIOD")


def _validate_institution(institution_id):
    institution = repo.get_institution(institution_id)

    if institution is None:
        raise AppError("INSTITUTION_NOT_FOUND")

    if not institution.is_active:
        raise AppError("INSTITUTION_INACTIVE")

    return institution


def _validate_coordinator(coordinator_id):
    """Exactly one assigned academic coordinator (BR-03)."""
    coordinator = repo.get_user(coordinator_id)

    if coordinator is None:
        raise AppError("COORDINATOR_NOT_FOUND")

    if coordinator.user_role is not UserRole.COORDINATOR:
        raise AppError("INVALID_COORDINATOR")

    return coordinator


def _validate_credits(value):
    """Credits must be present and positive (BR-11)."""
    try:
        credits = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise AppError("INVALID_COURSE_MAPPING")

    if credits <= 0:
        raise AppError("INVALID_COURSE_MAPPING")

    return credits


def _build_course_mappings(raw_mappings) -> list[CourseMapping]:
    """Validate and build the proposed mappings for one agreement (FR-04)."""
    mappings = parse_json_field(raw_mappings, [])

    if not isinstance(mappings, list) or not mappings:
        raise AppError("MISSING_COURSE_MAPPINGS")

    built = []
    seen_pairs = set()

    for entry in mappings:
        if not isinstance(entry, dict):
            raise AppError("INVALID_COURSE_MAPPING")

        values = {}

        for field in MAPPING_TEXT_FIELDS:
            text = (entry.get(field) or "").strip()

            if not text:
                raise AppError("INVALID_COURSE_MAPPING")

            values[field] = text

        for field in MAPPING_CREDIT_FIELDS:
            values[field] = _validate_credits(entry.get(field))

        # The database enforces this per agreement version; checking here
        # turns a duplicate into a clear error instead of an IntegrityError.
        pair = (values["home_course_code"], values["foreign_course_code"])

        if pair in seen_pairs:
            raise AppError("DUPLICATE_COURSE_MAPPING")

        seen_pairs.add(pair)
        built.append(CourseMapping(**values))

    return built


def create_application(student_id, data: dict) -> MobilityApplication:
    """Create an application in ``created`` (FR-03)."""
    missing = [field for field in REQUIRED_CREATE_FIELDS if not data.get(field)]

    if missing:
        raise AppError("MISSING_FIELDS")

    academic_year = _validate_academic_year(data["academic_year"])
    period = _validate_period(data["expected_mobility_period"])
    institution = _validate_institution(data["host_institution_id"])
    coordinator = _validate_coordinator(data["coordinator_id"])

    application = MobilityApplication(
        student_id=student_id,
        academic_year=academic_year,
        expected_mobility_period=period,
        host_institution_id=institution.institution_id,
        coordinator_id=coordinator.user_id,
        optional_note=data.get("optional_note"),
        status=ApplicationStatus.CREATED,
    )

    record_initial(application)
    db.session.add(application)
    db.session.flush()

    return application


def list_applications(student_id) -> list[MobilityApplication]:
    return repo.list_student_applications(student_id)


def get_application(application_id, student_id) -> MobilityApplication:
    return _require_application(application_id, student_id)


def update_application(application_id, student_id, updates: dict) -> MobilityApplication:
    """Revise application details while it is still a draft."""
    application = _require_application(application_id, student_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.CREATED)

    if "academic_year" in updates:
        application.academic_year = _validate_academic_year(updates["academic_year"])

    if "expected_mobility_period" in updates:
        application.expected_mobility_period = _validate_period(
            updates["expected_mobility_period"]
        )

    if "host_institution_id" in updates:
        application.host_institution_id = _validate_institution(
            updates["host_institution_id"]
        ).institution_id

    if "coordinator_id" in updates:
        application.coordinator_id = _validate_coordinator(
            updates["coordinator_id"]
        ).user_id

    if "optional_note" in updates:
        application.optional_note = updates["optional_note"]

    db.session.flush()

    return application


def delete_application(application_id, student_id) -> None:
    """Withdraw a draft.  Once submitted, an application is a record."""
    application = _require_application(application_id, student_id)
    guard_status(application, ApplicationStatus.CREATED)

    db.session.delete(application)
    db.session.flush()


def upload_learning_agreement(
    application_id,
    student_id,
    file,
    course_mappings,
) -> MobilityApplication:
    """Submit a Learning Agreement version with its mappings (FR-05).

    Serves the first submission, a resubmission after rejection, and a
    modification proposed during the mobility.  Each call adds the next
    version (BR-16) and sends the application back for approval.
    """
    application = _require_application(application_id, student_id)
    guard_not_closed(application)

    # Checked before the status guard: a version awaiting a decision is the
    # usual reason a second upload is refused, and saying so is more use to
    # the student than reporting the status it put the application in (BR-12).
    if repo.has_pending_learning_agreement(application):
        raise AppError("PENDING_LA_EXISTS")

    guard_status(
        application,
        ApplicationStatus.CREATED,
        ApplicationStatus.MOBILITY_IN_PROGRESS,
    )

    if file is None:
        raise AppError("MISSING_FILE")

    # Validate before writing the file, so a rejected submission does not
    # leave an orphan upload on disk.
    mappings = _build_course_mappings(course_mappings)
    _, stored_path = save_upload(file)

    agreement = LearningAgreement(
        version_number=repo.next_learning_agreement_version(application),
        file_path=stored_path,
    )
    agreement.course_mappings = mappings

    application.learning_agreements.append(agreement)
    transition(application, ApplicationStatus.WAITING_LA_APPROVAL)
    db.session.flush()

    return application


def set_mobility_dates(
    application_id,
    student_id,
    arrival_date=None,
    departure_date=None,
) -> MobilityApplication:
    """Record actual arrival and departure at the host institution (FR-07).

    Recording the arrival is what starts the mobility: the office signs
    off the pre-departure check, and the student then reports having
    arrived, which moves the application to ``mobility_in_progress``.
    """
    application = _require_application(application_id, student_id)
    guard_not_closed(application)
    guard_status(
        application,
        ApplicationStatus.PRE_DEPARTURE_COMPLETED,
        ApplicationStatus.MOBILITY_IN_PROGRESS,
    )

    arrival = parse_date(arrival_date)
    departure = parse_date(departure_date)

    if arrival is not None:
        application.actual_arrival_date = arrival

    if departure is not None:
        application.actual_departure_date = departure

    # Checked here as well as by the database so the caller gets a clear
    # error rather than an integrity failure (BR-21).
    if application.actual_departure_date is not None:
        if application.actual_arrival_date is None:
            raise AppError("INVALID_DATES")

        if application.actual_departure_date < application.actual_arrival_date:
            raise AppError("INVALID_DATES")

    if (
        application.status is ApplicationStatus.PRE_DEPARTURE_COMPLETED
        and application.actual_arrival_date is not None
    ):
        transition(application, ApplicationStatus.MOBILITY_IN_PROGRESS)

    db.session.flush()

    return application


def upload_transcript(application_id, student_id, file) -> MobilityApplication:
    """Upload the Transcript of Records, opening recognition (FR-09).

    Recognition cannot begin before this happens (BR-23), which is why the
    application only reaches ``under_exam_recognition`` here.
    """
    application = _require_application(application_id, student_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.MOBILITY_IN_PROGRESS)

    if file is None:
        raise AppError("MISSING_FILE")

    _, stored_path = save_upload(file)

    if application.transcript is None:
        application.transcript = TranscriptOfRecords(file_path=stored_path)
    else:
        application.transcript.file_path = stored_path

    transition(application, ApplicationStatus.UNDER_EXAM_RECOGNITION)
    db.session.flush()

    return application


def _validate_exam_date(application, exam_date: date) -> None:
    """An exam falls within the mobility, when both dates are known (BR-22)."""
    arrival = application.actual_arrival_date
    departure = application.actual_departure_date

    if arrival is None or departure is None:
        return

    if exam_date < arrival or exam_date > departure:
        raise AppError("EXAM_DATE_OUT_OF_RANGE")


def record_exam_results(application_id, student_id, results) -> MobilityApplication:
    """Record grade and passing date for foreign exams (FR-09).

    Each result attaches to a mapping in the currently approved agreement
    (BR-24).  A result already decided by the coordinator is left alone.
    """
    application = _require_application(application_id, student_id)
    guard_not_closed(application)
    guard_status(application, ApplicationStatus.UNDER_EXAM_RECOGNITION)

    entries = parse_json_field(results, [])

    if not isinstance(entries, list) or not entries:
        raise AppError("MISSING_EXAM_RESULTS")

    current = repo.current_approved_learning_agreement(application)

    if current is None:
        raise AppError("NO_APPROVED_LA")

    by_mapping_id = {
        mapping.mapping_id: mapping for mapping in current.course_mappings
    }

    for entry in entries:
        if not isinstance(entry, dict):
            raise AppError("INVALID_EXAM_RESULT")

        mapping = by_mapping_id.get(entry.get("mapping_id"))

        if mapping is None:
            raise AppError("MAPPING_NOT_IN_CURRENT_LA")

        grade = (entry.get("foreign_grade") or "").strip()

        if not grade:
            raise AppError("INVALID_EXAM_RESULT")

        exam_date = parse_date(entry.get("exam_date"))

        if exam_date is None:
            raise AppError("INVALID_EXAM_RESULT")

        _validate_exam_date(application, exam_date)

        existing = mapping.exam_result

        if existing is None:
            mapping.exam_result = ExamResult(
                foreign_grade=grade,
                exam_date=exam_date,
                recognition_status=RecognitionStatus.PENDING,
            )
        else:
            if existing.recognition_status is not RecognitionStatus.PENDING:
                raise AppError("RESULT_ALREADY_DECIDED")

            existing.foreign_grade = grade
            existing.exam_date = exam_date

    db.session.flush()

    return application
