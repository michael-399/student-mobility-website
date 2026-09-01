"""Shared fixtures for the service-layer tests.

Each test runs inside a transaction that is rolled back afterwards, so
tests neither see nor leave behind each other's rows.
"""

import io
import os

# Point at a database of the suite's own before anything reads the config,
# so a bare ``pytest`` cannot run against a development database.  An
# explicitly exported DATABASE_URL still wins.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/mobility_flask_test",
)

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.database import db  # noqa: E402
from app.models import Institution, UserAccount, UserRole  # noqa: E402


@pytest.fixture
def app(tmp_path):
    application = create_app()
    application.config["TESTING"] = True
    # Keep uploaded fixtures out of the working tree.
    application.config["UPLOAD_DIR"] = str(tmp_path / "uploads")

    yield application

    # Every test builds its own app, and each one carries its own
    # connection pool. Without this the pools accumulate across the suite
    # until Postgres refuses with "too many clients already" -- which only
    # shows up on a full run, not on a single file.
    with application.app_context():
        db.engine.dispose()


@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session

        db.session.rollback()


@pytest.fixture
def actors(session):
    """A student, their coordinator, a second student, and an institution."""
    student = UserAccount(
        email="student@example.com",
        password_hash="hash",
        first_name="Sara",
        last_name="Rossi",
        user_role=UserRole.STUDENT,
    )

    coordinator = UserAccount(
        email="coordinator@example.com",
        password_hash="hash",
        first_name="Marco",
        last_name="Bianchi",
        user_role=UserRole.COORDINATOR,
    )

    other_student = UserAccount(
        email="other@example.com",
        password_hash="hash",
        first_name="Luca",
        last_name="Verdi",
        user_role=UserRole.STUDENT,
    )

    institution = Institution(
        name="Partner University",
        country="Spain",
        city="Barcelona",
    )

    session.add_all([student, coordinator, other_student, institution])
    session.flush()

    return {
        "student": student,
        "coordinator": coordinator,
        "other_student": other_student,
        "institution": institution,
    }


@pytest.fixture
def application_data(actors):
    return {
        "academic_year": "2025/2026",
        "host_institution_id": actors["institution"].institution_id,
        "expected_mobility_period": "full_year",
        "coordinator_id": actors["coordinator"].user_id,
    }


@pytest.fixture
def course_mappings():
    return [
        {
            "home_course_code": "CT0001",
            "home_course_name": "Algorithms",
            "home_course_credits": 6,
            "foreign_course_code": "ES0001",
            "foreign_course_name": "Algoritmos",
            "foreign_course_credits": 6,
        }
    ]


@pytest.fixture
def upload():
    """A minimal file-like upload, as Werkzeug would hand to a service."""
    from werkzeug.datastructures import FileStorage

    def make(filename="learning-agreement.pdf"):
        return FileStorage(
            stream=io.BytesIO(b"%PDF-1.4 test"),
            filename=filename,
            content_type="application/pdf",
        )

    return make
