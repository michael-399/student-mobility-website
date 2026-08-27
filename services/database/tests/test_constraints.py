import pytest
from sqlalchemy.exc import IntegrityError
from datetime import date
from app import create_app
from app.database import db
from app.models import (
    Institution,
    UserAccount,
    UserRole,
    MobilityApplication,
    MobilityPeriod,
    LearningAgreement,
    CourseMapping,
    ApprovalStatus,
    ExamResult,
    RecognitionStatus,
)


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True

    return app


@pytest.fixture
def clean_database(app):
    with app.app_context():
        yield

        db.session.rollback()


@pytest.fixture
def sample_application(app):
    with app.app_context():
        student = UserAccount(
            user_id=1001,
            email="student@test.com",
            password_hash="test-hash",
            first_name="Test",
            last_name="Student",
            user_role=UserRole.STUDENT,
        )

        coordinator = UserAccount(
            user_id=1002,
            email="coordinator@test.com",
            password_hash="test-hash",
            first_name="Test",
            last_name="Coordinator",
            user_role=UserRole.COORDINATOR,
        )

        institution = Institution(
            institution_id=1001,
            name="Test University",
            country="Canada",
            city="Regina",
        )

        db.session.add_all([
            student,
            coordinator,
            institution,
        ])

        db.session.flush()

        application = MobilityApplication(
            application_id=1001,
            academic_year="2026/2027",
            expected_mobility_period=MobilityPeriod.FIRST_SEMESTER,
            host_institution_id=institution.institution_id,
            coordinator_id=coordinator.user_id,
            student_id=student.user_id,
        )

        db.session.add(application)
        db.session.flush()

        learning_agreement = LearningAgreement(
            application_id=application.application_id,
            version_number=1,
            file_path="tests/files/test_la.pdf",
            approval_status=ApprovalStatus.PENDING,
        )

        db.session.add(learning_agreement)
        db.session.flush()

        yield {
            "student": student,
            "coordinator": coordinator,
            "institution": institution,
            "application": application,
            "learning_agreement": learning_agreement,
        }

        db.session.rollback()


def test_reject_negative_course_credits(sample_application):
    application = sample_application["application"]

    mapping = CourseMapping(
        mapping_id=1001,
        application_id=application.application_id,
        version_number=1,
        home_course_code="DB101",
        home_course_name="Databases",
        foreign_course_code="CS500",
        foreign_course_name="Database Systems",
        home_course_credits=-6,
        foreign_course_credits=3,
    )

    db.session.add(mapping)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()

def test_reject_departure_before_arrival(sample_application):
    application = sample_application["application"]

    application.actual_arrival_date = date(2027, 2, 10)
    application.actual_departure_date = date(2027, 2, 5)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()

def test_reject_learning_agreement_without_reason(sample_application):
    learning_agreement = sample_application["learning_agreement"]

    learning_agreement.approval_status = ApprovalStatus.REJECTED
    learning_agreement.decision_date = date(2027, 1, 15)
    learning_agreement.rejection_reason = None

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()


def test_reject_duplicate_course_mapping(sample_application):
    application = sample_application["application"]

    first_mapping = CourseMapping(
        mapping_id=2001,
        application_id=application.application_id,
        version_number=1,
        home_course_code="DB101",
        home_course_name="Databases",
        foreign_course_code="CS500",
        foreign_course_name="Database Systems",
        home_course_credits=6,
        foreign_course_credits=3,
    )

    second_mapping = CourseMapping(
        mapping_id=2002,
        application_id=application.application_id,
        version_number=1,
        home_course_code="DB101",
        home_course_name="Databases",
        foreign_course_code="CS500",
        foreign_course_name="Database Systems",
        home_course_credits=6,
        foreign_course_credits=3,
    )

    db.session.add(first_mapping)
    db.session.flush()

    db.session.add(second_mapping)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()


def test_reject_exam_result_without_reason(sample_application):
    application = sample_application["application"]

    mapping = CourseMapping(
        mapping_id=3001,
        application_id=application.application_id,
        version_number=1,
        home_course_code="DB201",
        home_course_name="Advanced Databases",
        foreign_course_code="CS600",
        foreign_course_name="Advanced Database Systems",
        home_course_credits=6,
        foreign_course_credits=3,
    )

    db.session.add(mapping)
    db.session.flush()

    exam_result = ExamResult(
        result_id=3001,
        mapping_id=mapping.mapping_id,
        foreign_grade="A",
        exam_date=date(2027, 3, 20),
        recognition_status=RecognitionStatus.REJECTED,
        decision_date=date(2027, 4, 10),
        rejection_reason=None,
    )

    db.session.add(exam_result)

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()


def test_reject_invalid_academic_year(sample_application):
    application = sample_application["application"]

    application.academic_year = "2026-2027"

    with pytest.raises(IntegrityError):
        db.session.flush()

    db.session.rollback()


def test_accept_valid_course_mapping(sample_application):
    application = sample_application["application"]

    mapping = CourseMapping(
        mapping_id=4001,
        application_id=application.application_id,
        version_number=1,
        home_course_code="DB301",
        home_course_name="Database Systems",
        foreign_course_code="CS700",
        foreign_course_name="Advanced Database Systems",
        home_course_credits=6,
        foreign_course_credits=3,
    )

    db.session.add(mapping)
    db.session.flush()

    assert mapping.mapping_id == 4001

    db.session.rollback()