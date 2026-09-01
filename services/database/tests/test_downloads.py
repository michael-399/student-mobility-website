"""Tests for document downloads and cross-origin access."""

import io
import json
import os

import pytest

from app.database import db
from app.models import Institution, MobilityApplication, UserAccount, UserRole
from app.security import hash_password

PASSWORD = "password"


@pytest.fixture
def people(session):
    accounts = {
        "student": ("dl_student@example.com", UserRole.STUDENT),
        "other_student": ("dl_other@example.com", UserRole.STUDENT),
        "coordinator": ("dl_coordinator@example.com", UserRole.COORDINATOR),
        "office": ("dl_office@example.com", UserRole.OFFICE_STAFF),
    }

    created = {}

    for key, (email, role) in accounts.items():
        user = UserAccount(
            email=email,
            password_hash=hash_password(PASSWORD),
            first_name=key.title(),
            last_name="Tester",
            user_role=role,
        )
        session.add(user)
        created[key] = user

    institution = Institution(name="Download U", country="Ireland", city="Cork")
    session.add(institution)
    session.commit()

    created["institution"] = institution
    user_ids = [u.user_id for k, u in created.items() if k != "institution"]
    institution_id = institution.institution_id

    yield created

    session.rollback()
    session.execute(
        db.delete(MobilityApplication).where(
            MobilityApplication.student_id.in_(user_ids)
        )
    )
    session.execute(db.delete(UserAccount).where(UserAccount.user_id.in_(user_ids)))
    session.execute(
        db.delete(Institution).where(Institution.institution_id == institution_id)
    )
    session.commit()


def sign_in(app, email):
    client = app.test_client()
    response = client.post("/api/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200

    return client


@pytest.fixture
def submitted(app, people):
    """An application with one uploaded agreement, plus signed-in clients."""
    student = sign_in(app, people["student"].email)

    created = student.post(
        "/api/student/applications",
        json={
            "academic_year": "2025/2026",
            "host_institution_id": people["institution"].institution_id,
            "expected_mobility_period": "full_year",
            "coordinator_id": people["coordinator"].user_id,
        },
    )
    application_id = created.get_json()["application"]["application_id"]

    student.post(
        f"/api/student/applications/{application_id}/learning-agreements",
        data={
            "file": (io.BytesIO(b"%PDF-1.4 agreement bytes"), "signed.pdf"),
            "course_mappings": json.dumps(
                [
                    {
                        "home_course_code": "CT1",
                        "home_course_name": "Algorithms",
                        "home_course_credits": 6,
                        "foreign_course_code": "IE1",
                        "foreign_course_name": "Algorithms",
                        "foreign_course_credits": 6,
                    }
                ]
            ),
        },
        content_type="multipart/form-data",
    )

    return {
        "application_id": application_id,
        "student": student,
        "coordinator": sign_in(app, people["coordinator"].email),
        "office": sign_in(app, people["office"].email),
        "other_student": sign_in(app, people["other_student"].email),
    }


class TestLearningAgreementDownload:
    def test_the_owner_downloads_it(self, submitted):
        response = submitted["student"].get(
            f"/api/student/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 200
        assert response.data == b"%PDF-1.4 agreement bytes"
        assert "learning-agreement-v1.pdf" in response.headers["Content-Disposition"]
        assert "attachment" in response.headers["Content-Disposition"]

    def test_the_assigned_coordinator_downloads_it(self, submitted):
        response = submitted["coordinator"].get(
            f"/api/coordinator/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 200
        assert response.data == b"%PDF-1.4 agreement bytes"

    def test_the_office_downloads_it(self, submitted):
        response = submitted["office"].get(
            f"/api/office/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 200

    def test_another_student_cannot(self, submitted):
        """Downloads carry the same scoping as reading the application."""
        response = submitted["other_student"].get(
            f"/api/student/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 404
        assert response.get_json()["code"] == "APPLICATION_NOT_FOUND"

    def test_anonymous_cannot(self, app, submitted):
        response = app.test_client().get(
            f"/api/student/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 401

    @pytest.mark.parametrize("version", ["2", "0", "-1", "abc"])
    def test_an_unknown_version_is_a_404(self, submitted, version):
        response = submitted["student"].get(
            f"/api/student/applications/{submitted['application_id']}"
            f"/learning-agreements/{version}/file"
        )

        assert response.status_code == 404
        assert response.get_json()["code"] == "LEARNING_AGREEMENT_NOT_FOUND"

    def test_a_row_without_its_file_is_a_404_not_a_crash(self, submitted, app):
        """A restored backup or a lost volume must not produce a 500."""
        with app.app_context():
            application = db.session.get(
                MobilityApplication, submitted["application_id"]
            )
            os.remove(application.learning_agreements[0].file_path)

        response = submitted["student"].get(
            f"/api/student/applications/{submitted['application_id']}"
            "/learning-agreements/1/file"
        )

        assert response.status_code == 404
        assert response.get_json()["code"] == "FILE_MISSING_FROM_STORAGE"


class TestTranscriptDownload:
    def test_missing_transcript_is_a_404(self, submitted):
        response = submitted["student"].get(
            f"/api/student/applications/{submitted['application_id']}/transcript/file"
        )

        assert response.status_code == 404
        assert response.get_json()["code"] == "TRANSCRIPT_NOT_FOUND"

    def test_downloads_after_upload(self, submitted):
        application_id = submitted["application_id"]
        student = submitted["student"]

        submitted["coordinator"].post(
            f"/api/coordinator/applications/{application_id}/learning-agreement/decision",
            json={"decision": "approved"},
        )
        submitted["office"].post(f"/api/office/applications/{application_id}/pre-departure")
        student.patch(
            f"/api/student/applications/{application_id}/mobility-dates",
            json={"actual_arrival_date": "2026-01-10"},
        )
        student.post(
            f"/api/student/applications/{application_id}/transcript",
            data={"file": (io.BytesIO(b"%PDF transcript bytes"), "tor.pdf")},
            content_type="multipart/form-data",
        )

        response = student.get(
            f"/api/student/applications/{application_id}/transcript/file"
        )

        assert response.status_code == 200
        assert response.data == b"%PDF transcript bytes"
        assert (
            f"transcript-of-records-{application_id}.pdf"
            in response.headers["Content-Disposition"]
        )


class TestCors:
    def test_a_configured_origin_is_allowed_with_credentials(self, app, people):
        client = app.test_client()

        response = client.post(
            "/api/login",
            json={"email": people["student"].email, "password": PASSWORD},
            headers={"Origin": "http://localhost:4200"},
        )

        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:4200"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

    def test_an_unlisted_origin_gets_no_grant(self, app, people):
        client = app.test_client()

        response = client.post(
            "/api/login",
            json={"email": people["student"].email, "password": PASSWORD},
            headers={"Origin": "http://evil.example"},
        )

        assert "Access-Control-Allow-Origin" not in response.headers

    def test_credentialed_responses_never_use_a_wildcard(self, app, people):
        """Browsers reject "*" on a credentialed request."""
        client = app.test_client()

        response = client.post(
            "/api/login",
            json={"email": people["student"].email, "password": PASSWORD},
            headers={"Origin": "http://localhost:4200"},
        )

        assert response.headers.get("Access-Control-Allow-Origin") != "*"


class TestSessionCookie:
    def test_the_cookie_is_http_only(self, app, people):
        client = app.test_client()

        response = client.post(
            "/api/login",
            json={"email": people["student"].email, "password": PASSWORD},
        )

        cookie = response.headers["Set-Cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie
