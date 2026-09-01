"""Tests for the request-level wiring: transactions and error responses.

These exercise the app through the test client rather than calling
services directly, because the behaviour under test only exists for a
real request.
"""

import pytest
from flask import jsonify

from app.errors import AppError
from app.database import db
from app.models import Institution, UserAccount, UserRole
from app.security import hash_password
from app.services import office as office_service


@pytest.fixture
def wired(app):
    """Routes that exercise the boundary, registered on the real app."""

    @app.post("/testing/create-institution")
    def create_institution():
        institution = office_service.create_institution(
            {"name": "Committed U", "country": "Italy", "city": "Venice"}
        )

        return jsonify({"institution_id": institution.institution_id}), 201

    @app.post("/testing/create-then-fail")
    def create_then_fail():
        office_service.create_institution(
            {"name": "Rolled Back U", "country": "Italy", "city": "Padua"}
        )
        raise AppError("INVALID_STATUS")

    @app.post("/testing/create-then-crash")
    def create_then_crash():
        office_service.create_institution(
            {"name": "Crashed U", "country": "Italy", "city": "Verona"}
        )
        raise RuntimeError("unexpected")

    return app


def institution_exists(name):
    return db.session.execute(
        db.select(Institution).where(Institution.name == name)
    ).scalar_one_or_none() is not None


class TestTransactionBoundary:
    def test_a_successful_request_commits(self, wired):
        client = wired.test_client()

        response = client.post("/testing/create-institution")
        assert response.status_code == 201

        with wired.app_context():
            assert institution_exists("Committed U")

            # Clean up: this one really was committed.
            db.session.execute(
                db.delete(Institution).where(Institution.name == "Committed U")
            )
            db.session.commit()

    def test_a_domain_error_rolls_the_request_back(self, wired):
        """Nothing written before the refusal survives."""
        client = wired.test_client()

        response = client.post("/testing/create-then-fail")
        assert response.status_code == 409

        with wired.app_context():
            assert not institution_exists("Rolled Back U")

    def test_an_unexpected_error_rolls_the_request_back(self, wired):
        client = wired.test_client()

        with pytest.raises(RuntimeError):
            client.post("/testing/create-then-crash")

        with wired.app_context():
            assert not institution_exists("Crashed U")


class TestErrorResponses:
    @pytest.fixture
    def client(self, wired):
        @wired.post("/testing/raise/<code>")
        def raise_code(code):
            raise AppError(code)

        return wired.test_client()

    @pytest.mark.parametrize(
        "code,status",
        [
            ("APPLICATION_NOT_FOUND", 404),
            ("EXAM_RESULT_NOT_FOUND", 404),
            ("INSTITUTION_NOT_FOUND", 404),
            ("APPLICATION_CLOSED", 409),
            ("INVALID_STATUS", 409),
            ("PENDING_LA_EXISTS", 409),
            ("PENDING_EXAM_RESULTS", 409),
            ("MISSING_FIELDS", 400),
            ("INVALID_ACADEMIC_YEAR", 400),
            ("REASON_REQUIRED", 400),
        ],
    )
    def test_codes_map_to_their_status(self, client, code, status):
        response = client.post(f"/testing/raise/{code}")

        assert response.status_code == status
        assert response.get_json()["code"] == code
        assert response.get_json()["error"]

    def test_an_unmapped_code_falls_back_to_bad_request(self, client):
        response = client.post("/testing/raise/SOMETHING_NEW")

        assert response.status_code == 400
        assert response.get_json()["code"] == "SOMETHING_NEW"

    def test_every_raised_code_is_mapped(self):
        """No service can raise a code the translation layer forgot."""
        import pathlib
        import re

        from app.http import ERROR_RESPONSES

        source = pathlib.Path(__file__).resolve().parents[1] / "app"
        raised = set()

        for path in source.rglob("*.py"):
            raised |= set(re.findall(r'AppError\("([A-Z_]+)"\)', path.read_text()))

        assert raised - set(ERROR_RESPONSES) == set()


class TestSeededLogin:
    def test_seeded_credentials_work(self, app, session):
        """The seed's accounts can actually log in."""
        user = UserAccount(
            email="seedcheck@example.com",
            password_hash=hash_password("password"),
            first_name="Seed",
            last_name="Check",
            user_role=UserRole.STUDENT,
        )
        session.add(user)
        session.commit()

        try:
            client = app.test_client()
            response = client.post(
                "/api/login",
                json={"email": "seedcheck@example.com", "password": "password"},
            )

            assert response.status_code == 200
            assert response.get_json()["user"]["role"] == "student"
        finally:
            session.execute(
                db.delete(UserAccount).where(
                    UserAccount.email == "seedcheck@example.com"
                )
            )
            session.commit()
