"""Tests for the HTTP surface: authorisation, serialisation, status codes.

These drive the app through the test client, so they cover the pieces
that only exist for a real request -- role checks, the transaction
boundary, and the JSON shape -- rather than re-testing service rules
already covered by the service suites.
"""

import io
import json

import pytest

from app.database import db
from app.models import Institution, MobilityApplication, UserAccount, UserRole
from app.security import hash_password

PASSWORD = "password"


@pytest.fixture
def people(session):
    """One account per role, plus an institution to apply to."""
    accounts = {
        "student": ("routes_student@example.com", UserRole.STUDENT),
        "other_student": ("routes_other@example.com", UserRole.STUDENT),
        "coordinator": ("routes_coordinator@example.com", UserRole.COORDINATOR),
        "office": ("routes_office@example.com", UserRole.OFFICE_STAFF),
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

    institution = Institution(
        name="Routes University",
        country="Portugal",
        city="Porto",
    )
    session.add(institution)
    session.commit()

    created["institution"] = institution
    user_ids = [u.user_id for k, u in created.items() if k != "institution"]
    institution_id = institution.institution_id

    yield created

    # These rows were committed by the request boundary, so they must be
    # removed explicitly.  Applications reference users and institutions
    # with ON DELETE RESTRICT, so they go first; their own children fall
    # away through ON DELETE CASCADE.
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

    assert response.status_code == 200, response.get_json()

    return client


@pytest.fixture
def student(app, people):
    return sign_in(app, people["student"].email)


@pytest.fixture
def other_student(app, people):
    return sign_in(app, people["other_student"].email)


@pytest.fixture
def coordinator(app, people):
    return sign_in(app, people["coordinator"].email)


@pytest.fixture
def office(app, people):
    return sign_in(app, people["office"].email)


@pytest.fixture
def anonymous(app):
    return app.test_client()


def application_payload(people):
    return {
        "academic_year": "2025/2026",
        "host_institution_id": people["institution"].institution_id,
        "expected_mobility_period": "full_year",
        "coordinator_id": people["coordinator"].user_id,
    }


def upload_payload(mappings=None):
    return {
        "file": (io.BytesIO(b"%PDF-1.4 test"), "agreement.pdf"),
        "course_mappings": json.dumps(
            mappings
            or [
                {
                    "home_course_code": "CT0001",
                    "home_course_name": "Algorithms",
                    "home_course_credits": 6,
                    "foreign_course_code": "PT0001",
                    "foreign_course_name": "Algoritmos",
                    "foreign_course_credits": 6,
                }
            ]
        ),
    }


@pytest.fixture
def created_application(student, people):
    response = student.post("/api/student/applications", json=application_payload(people))

    assert response.status_code == 201

    return response.get_json()["application"]


class TestAuthorisation:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/student/applications"),
            ("get", "/api/coordinator/applications"),
            ("get", "/api/office/applications"),
            ("get", "/api/reference/institutions"),
        ],
    )
    def test_anonymous_is_refused(self, anonymous, method, path):
        assert getattr(anonymous, method)(path).status_code == 401

    def test_a_student_cannot_reach_coordinator_endpoints(self, student):
        assert student.get("/api/coordinator/applications").status_code == 403

    def test_a_student_cannot_reach_office_endpoints(self, student):
        assert student.get("/api/office/applications").status_code == 403

    def test_a_coordinator_cannot_reach_student_endpoints(self, coordinator):
        assert coordinator.get("/api/student/applications").status_code == 403

    def test_an_office_user_cannot_reach_coordinator_endpoints(self, office):
        assert office.get("/api/coordinator/applications").status_code == 403

    def test_every_role_may_read_reference_data(self, student, coordinator, office):
        for client in (student, coordinator, office):
            assert client.get("/api/reference/institutions").status_code == 200
            assert client.get("/api/reference/coordinators").status_code == 200


class TestStudentApplications:
    def test_creates_and_persists(self, student, people, created_application):
        """The transaction boundary commits, so a second request sees it."""
        listed = student.get("/api/student/applications").get_json()["applications"]

        assert created_application["application_id"] in [
            a["application_id"] for a in listed
        ]
        assert created_application["status"] == "created"

    def test_response_shape_is_serialised(self, created_application):
        assert created_application["host_institution"]["name"] == "Routes University"
        assert created_application["academic_coordinator"]["role"] == "coordinator"
        assert created_application["student"]["role"] == "student"
        # Dates are ISO strings, not RFC 822.
        assert created_application["actual_arrival_date"] is None
        assert created_application["status_history"][0]["new_status"] == "created"

    def test_another_student_gets_a_404(self, other_student, created_application):
        """Scoped lookups do not disclose that the application exists."""
        response = other_student.get(
            f"/api/student/applications/{created_application['application_id']}"
        )

        assert response.status_code == 404
        assert response.get_json()["code"] == "APPLICATION_NOT_FOUND"

    def test_a_domain_error_maps_to_its_status(self, student, people):
        payload = {**application_payload(people), "academic_year": "2025/2027"}

        response = student.post("/api/student/applications", json=payload)

        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_ACADEMIC_YEAR"

    def test_a_failed_create_leaves_nothing_behind(self, student, people):
        before = len(student.get("/api/student/applications").get_json()["applications"])

        student.post(
            "/api/student/applications",
            json={**application_payload(people), "academic_year": "nope"},
        )

        after = len(student.get("/api/student/applications").get_json()["applications"])
        assert after == before

    def test_updates_a_draft(self, student, created_application):
        response = student.patch(
            f"/api/student/applications/{created_application['application_id']}",
            json={"optional_note": "Erasmus+"},
        )

        assert response.status_code == 200
        assert response.get_json()["application"]["optional_note"] == "Erasmus+"

    def test_deletes_a_draft(self, student, created_application):
        application_id = created_application["application_id"]

        assert student.delete(f"/api/student/applications/{application_id}").status_code == 204
        assert student.get(f"/api/student/applications/{application_id}").status_code == 404

    def test_missing_body_becomes_a_domain_error(self, student):
        response = student.post("/api/student/applications")

        assert response.status_code == 400
        assert response.get_json()["code"] == "MISSING_FIELDS"


class TestLearningAgreementUpload:
    def test_uploads_a_version(self, student, created_application):
        response = student.post(
            f"/api/student/applications/{created_application['application_id']}"
            "/learning-agreements",
            data=upload_payload(),
            content_type="multipart/form-data",
        )

        assert response.status_code == 201

        application = response.get_json()["application"]
        assert application["status"] == "waiting_la_approval"

        agreement = application["learning_agreements"][0]
        assert agreement["version_number"] == 1
        assert agreement["approval_status"] == "pending"
        assert agreement["course_mappings"][0]["home_course_credits"] == 6.0
        # Server-side storage paths are never exposed.
        assert "file_path" not in agreement

    def test_a_missing_file_is_refused(self, student, created_application):
        response = student.post(
            f"/api/student/applications/{created_application['application_id']}"
            "/learning-agreements",
            data={"course_mappings": json.dumps([])},
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        assert response.get_json()["code"] in ("MISSING_FILE", "MISSING_COURSE_MAPPINGS")


class TestFullWorkflowOverHttp:
    def test_the_lifecycle_runs_end_to_end(
        self, student, coordinator, office, created_application
    ):
        application_id = created_application["application_id"]

        # Student submits the agreement.
        student.post(
            f"/api/student/applications/{application_id}/learning-agreements",
            data=upload_payload(),
            content_type="multipart/form-data",
        )

        # Coordinator approves it.
        decision = coordinator.post(
            f"/api/coordinator/applications/{application_id}/learning-agreement/decision",
            json={"decision": "approved"},
        )
        assert decision.status_code == 200

        # Office signs off the pre-departure check.
        signed_off = office.post(f"/api/office/applications/{application_id}/pre-departure")
        assert signed_off.status_code == 200
        assert signed_off.get_json()["application"]["status"] == "pre_departure_completed"

        # Student arrives, which starts the mobility.
        arrived = student.patch(
            f"/api/student/applications/{application_id}/mobility-dates",
            json={
                "actual_arrival_date": "2026-01-10",
                "actual_departure_date": "2026-06-20",
            },
        )
        assert arrived.get_json()["application"]["status"] == "mobility_in_progress"

        # Transcript opens recognition.
        transcript = student.post(
            f"/api/student/applications/{application_id}/transcript",
            data={"file": (io.BytesIO(b"%PDF tor"), "transcript.pdf")},
            content_type="multipart/form-data",
        )
        assert transcript.status_code == 201

        application = transcript.get_json()["application"]
        assert application["status"] == "under_exam_recognition"
        assert application["transcript"] is not None

        mapping_id = application["learning_agreements"][0]["course_mappings"][0][
            "mapping_id"
        ]

        # Student records a grade.
        recorded = student.put(
            f"/api/student/applications/{application_id}/exam-results",
            json={
                "exam_results": [
                    {
                        "mapping_id": mapping_id,
                        "foreign_grade": "8",
                        "exam_date": "2026-03-01",
                    }
                ]
            },
        )
        assert recorded.status_code == 200

        result = recorded.get_json()["application"]["learning_agreements"][0][
            "course_mappings"
        ][0]["exam_result"]
        assert result["recognition_status"] == "pending"

        # Closing is refused while the recognition is pending.
        too_early = office.post(f"/api/office/applications/{application_id}/close")
        assert too_early.status_code == 409
        assert too_early.get_json()["code"] == "PENDING_EXAM_RESULTS"

        # Coordinator decides it.
        decided = coordinator.post(
            f"/api/coordinator/exam-results/{result['result_id']}/decision",
            json={"decision": "approved"},
        )
        assert decided.status_code == 200
        assert decided.get_json()["exam_result"]["recognition_status"] == "approved"

        # Office closes it.
        closed = office.post(f"/api/office/applications/{application_id}/close")
        assert closed.status_code == 200
        assert closed.get_json()["application"]["status"] == "closed"

        # A closed application is frozen.
        frozen = student.patch(
            f"/api/student/applications/{application_id}/mobility-dates",
            json={"actual_departure_date": "2026-07-01"},
        )
        assert frozen.status_code == 409
        assert frozen.get_json()["code"] == "APPLICATION_CLOSED"


class TestOfficeInstitutions:
    def test_creates_and_lists(self, office):
        created = office.post(
            "/api/office/institutions",
            json={"name": "New Partner", "country": "Norway", "city": "Bergen"},
        )

        assert created.status_code == 201

        institution = created.get_json()["institution"]
        assert institution["is_active"] is True

        office.post(f"/api/office/institutions/{institution['institution_id']}/deactivate")

        active = office.get("/api/office/institutions").get_json()["institutions"]
        assert institution["institution_id"] not in [
            i["institution_id"] for i in active
        ]

        everything = office.get(
            "/api/office/institutions?include_inactive=true"
        ).get_json()["institutions"]
        assert institution["institution_id"] in [
            i["institution_id"] for i in everything
        ]

        # Committed by the boundary, so remove it explicitly.
        db.session.execute(
            db.delete(Institution).where(
                Institution.institution_id == institution["institution_id"]
            )
        )
        db.session.commit()

    def test_rejects_an_unknown_status_filter(self, office):
        response = office.get("/api/office/applications?status=in_orbit")

        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_STATUS_FILTER"

    def test_unknown_institution_is_a_404(self, office):
        response = office.patch("/api/office/institutions/999999", json={"city": "Nowhere"})

        assert response.status_code == 404


class TestCoordinatorDecisions:
    def test_rejection_requires_a_reason(self, student, coordinator, created_application):
        application_id = created_application["application_id"]
        student.post(
            f"/api/student/applications/{application_id}/learning-agreements",
            data=upload_payload(),
            content_type="multipart/form-data",
        )

        response = coordinator.post(
            f"/api/coordinator/applications/{application_id}/learning-agreement/decision",
            json={"decision": "rejected"},
        )

        assert response.status_code == 400
        assert response.get_json()["code"] == "REASON_REQUIRED"

    def test_rejection_returns_the_application_to_the_student(
        self, student, coordinator, created_application
    ):
        application_id = created_application["application_id"]
        student.post(
            f"/api/student/applications/{application_id}/learning-agreements",
            data=upload_payload(),
            content_type="multipart/form-data",
        )

        response = coordinator.post(
            f"/api/coordinator/applications/{application_id}/learning-agreement/decision",
            json={"decision": "rejected", "reason": "Credits do not balance"},
        )

        application = response.get_json()["application"]
        assert application["status"] == "created"
        assert application["learning_agreements"][0]["approval_status"] == "rejected"
        assert (
            application["learning_agreements"][0]["rejection_reason"]
            == "Credits do not balance"
        )

    def test_another_coordinator_gets_a_404(
        self, student, coordinator, created_application, people, app, session
    ):
        application_id = created_application["application_id"]
        student.post(
            f"/api/student/applications/{application_id}/learning-agreements",
            data=upload_payload(),
            content_type="multipart/form-data",
        )

        stranger = UserAccount(
            email="routes_stranger@example.com",
            password_hash=hash_password(PASSWORD),
            first_name="Stranger",
            last_name="Tester",
            user_role=UserRole.COORDINATOR,
        )
        session.add(stranger)
        session.commit()

        try:
            client = sign_in(app, stranger.email)
            response = client.post(
                f"/api/coordinator/applications/{application_id}"
                "/learning-agreement/decision",
                json={"decision": "approved"},
            )

            assert response.status_code == 404
        finally:
            session.rollback()
            session.delete(stranger)
            session.commit()
