"""Tests for the coordinator service (FR-05, FR-10)."""

from datetime import date

import pytest

from app.errors import AppError
from app.models import ApplicationStatus, ApprovalStatus, RecognitionStatus
from app.services import coordinator as coordinator_service
from app.services import student as student_service
from app.services._workflow import transition


@pytest.fixture
def submitted(actors, application_data, course_mappings, upload, session):
    """An application with version 1 awaiting the coordinator's decision."""
    application = student_service.create_application(
        actors["student"].user_id,
        application_data,
    )
    student_service.upload_learning_agreement(
        application.application_id,
        actors["student"].user_id,
        upload(),
        course_mappings,
    )
    session.flush()

    return application


def advance_to_mobility(application):
    """The office-owned part of the workflow, which lands in the next stage."""
    transition(application, ApplicationStatus.PRE_DEPARTURE_COMPLETED)
    transition(application, ApplicationStatus.MOBILITY_IN_PROGRESS)


class TestScoping:
    def test_another_coordinator_cannot_see_the_application(self, submitted, actors, session):
        """BR-05: decisions are scoped to the assigned coordinator."""
        from app.models import UserAccount, UserRole

        stranger = UserAccount(
            email="stranger@example.com",
            password_hash="hash",
            first_name="Ida",
            last_name="Neri",
            user_role=UserRole.COORDINATOR,
        )
        session.add(stranger)
        session.flush()

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_learning_agreement(
                submitted.application_id,
                stranger.user_id,
                "approved",
            )

        assert raised.value.code == "APPLICATION_NOT_FOUND"

    def test_listing_returns_only_assigned_applications(self, submitted, actors):
        assigned = coordinator_service.list_applications(actors["coordinator"].user_id)

        assert [a.application_id for a in assigned] == [submitted.application_id]
        assert coordinator_service.list_applications(actors["student"].user_id) == []


class TestEvaluateLearningAgreement:
    def test_approval_records_the_decision_and_waits_for_the_office(
        self, submitted, actors
    ):
        """BR-18: an approved decision carries a date, and no reason."""
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "approved",
        )

        agreement = submitted.learning_agreements[0]
        assert agreement.approval_status is ApprovalStatus.APPROVED
        assert agreement.decision_date == date.today()
        assert agreement.rejection_reason is None
        # The office, not the coordinator, completes the pre-departure check.
        assert submitted.status is ApplicationStatus.WAITING_LA_APPROVAL

    def test_rejection_returns_the_application_to_the_student(self, submitted, actors):
        """BR-19: a rejection carries a non-empty reason."""
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "rejected",
            "Credits do not balance",
        )

        agreement = submitted.learning_agreements[0]
        assert agreement.approval_status is ApprovalStatus.REJECTED
        assert agreement.decision_date == date.today()
        assert agreement.rejection_reason == "Credits do not balance"
        assert submitted.status is ApplicationStatus.CREATED

    @pytest.mark.parametrize("reason", [None, "", "   "])
    def test_rejection_without_a_reason_is_refused(self, submitted, actors, reason):
        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_learning_agreement(
                submitted.application_id,
                actors["coordinator"].user_id,
                "rejected",
                reason,
            )

        assert raised.value.code == "REASON_REQUIRED"

    def test_unknown_decision_is_refused(self, submitted, actors):
        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_learning_agreement(
                submitted.application_id,
                actors["coordinator"].user_id,
                "maybe",
            )

        assert raised.value.code == "INVALID_DECISION"

    def test_cannot_decide_twice(self, submitted, actors):
        """A decided agreement is no longer pending, so there is nothing to decide.

        The application stays in ``waiting_la_approval`` after approval —
        it is now waiting on the office — so it is the absence of a pending
        version, not the status, that refuses a second decision.
        """
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "approved",
        )

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_learning_agreement(
                submitted.application_id,
                actors["coordinator"].user_id,
                "rejected",
                "changed my mind",
            )

        assert raised.value.code == "NO_PENDING_LA"

    def test_cannot_decide_a_draft(self, actors, application_data):
        """Nothing to decide before the student submits an agreement."""
        application = student_service.create_application(
            actors["student"].user_id,
            application_data,
        )

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_learning_agreement(
                application.application_id,
                actors["coordinator"].user_id,
                "approved",
            )

        assert raised.value.code == "INVALID_STATUS"

    def test_decides_the_latest_version_after_a_resubmission(
        self, submitted, actors, course_mappings, upload, session
    ):
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "rejected",
            "Missing signature",
        )
        student_service.upload_learning_agreement(
            submitted.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )
        session.flush()

        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "approved",
        )

        by_version = {a.version_number: a for a in submitted.learning_agreements}
        assert by_version[1].approval_status is ApprovalStatus.REJECTED
        assert by_version[2].approval_status is ApprovalStatus.APPROVED


class TestModificationDuringMobility:
    @pytest.fixture
    def in_mobility(self, submitted, actors, session):
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "approved",
        )
        advance_to_mobility(submitted)
        session.flush()

        return submitted

    def test_approved_modification_resumes_the_mobility(
        self, in_mobility, actors, course_mappings, upload, session
    ):
        """The pre-departure phase is behind it, so approval returns there."""
        revised = [dict(course_mappings[0], foreign_course_code="ES0002")]
        student_service.upload_learning_agreement(
            in_mobility.application_id,
            actors["student"].user_id,
            upload(),
            revised,
        )
        session.flush()
        assert in_mobility.status is ApplicationStatus.WAITING_LA_APPROVAL

        coordinator_service.evaluate_learning_agreement(
            in_mobility.application_id,
            actors["coordinator"].user_id,
            "approved",
        )

        assert in_mobility.status is ApplicationStatus.MOBILITY_IN_PROGRESS

    def test_approved_modification_becomes_the_current_mapping(
        self, in_mobility, actors, course_mappings, upload, session
    ):
        """BR-13: the approved revision is the mapping now in force."""
        from app import repositories as repo

        revised = [dict(course_mappings[0], foreign_course_code="ES0002")]
        student_service.upload_learning_agreement(
            in_mobility.application_id,
            actors["student"].user_id,
            upload(),
            revised,
        )
        session.flush()
        coordinator_service.evaluate_learning_agreement(
            in_mobility.application_id,
            actors["coordinator"].user_id,
            "approved",
        )

        current = repo.current_approved_learning_agreement(in_mobility)
        assert current.version_number == 2
        assert current.course_mappings[0].foreign_course_code == "ES0002"

    def test_rejected_modification_leaves_the_previous_mapping_in_force(
        self, in_mobility, actors, course_mappings, upload, session
    ):
        """BR-14: rejection does not replace the approved mapping."""
        from app import repositories as repo

        revised = [dict(course_mappings[0], foreign_course_code="ES0002")]
        student_service.upload_learning_agreement(
            in_mobility.application_id,
            actors["student"].user_id,
            upload(),
            revised,
        )
        session.flush()

        coordinator_service.evaluate_learning_agreement(
            in_mobility.application_id,
            actors["coordinator"].user_id,
            "rejected",
            "Course not offered this term",
        )

        current = repo.current_approved_learning_agreement(in_mobility)
        assert current.version_number == 1
        assert current.course_mappings[0].foreign_course_code == "ES0001"


class TestEvaluateExamResult:
    @pytest.fixture
    def with_result(self, submitted, actors, upload, session):
        coordinator_service.evaluate_learning_agreement(
            submitted.application_id,
            actors["coordinator"].user_id,
            "approved",
        )
        advance_to_mobility(submitted)
        student_service.set_mobility_dates(
            submitted.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
            departure_date="2026-06-20",
        )
        student_service.upload_transcript(
            submitted.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )
        mapping = submitted.learning_agreements[0].course_mappings[0]
        student_service.record_exam_results(
            submitted.application_id,
            actors["student"].user_id,
            [
                {
                    "mapping_id": mapping.mapping_id,
                    "foreign_grade": "8",
                    "exam_date": "2026-03-01",
                }
            ],
        )
        session.flush()

        return submitted, mapping.exam_result

    def test_approves_a_result(self, with_result, actors):
        _, result = with_result

        decided = coordinator_service.evaluate_exam_result(
            result.result_id,
            actors["coordinator"].user_id,
            "approved",
        )

        assert decided.recognition_status is RecognitionStatus.APPROVED
        assert decided.decision_date == date.today()
        assert decided.rejection_reason is None

    def test_rejects_a_result_with_a_reason(self, with_result, actors):
        _, result = with_result

        decided = coordinator_service.evaluate_exam_result(
            result.result_id,
            actors["coordinator"].user_id,
            "rejected",
            "Grade not recognised",
        )

        assert decided.recognition_status is RecognitionStatus.REJECTED
        assert decided.rejection_reason == "Grade not recognised"

    def test_rejection_without_a_reason_is_refused(self, with_result, actors):
        _, result = with_result

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_exam_result(
                result.result_id,
                actors["coordinator"].user_id,
                "rejected",
            )

        assert raised.value.code == "REASON_REQUIRED"

    def test_cannot_decide_twice(self, with_result, actors):
        _, result = with_result
        coordinator_service.evaluate_exam_result(
            result.result_id,
            actors["coordinator"].user_id,
            "approved",
        )

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_exam_result(
                result.result_id,
                actors["coordinator"].user_id,
                "rejected",
                "second thoughts",
            )

        assert raised.value.code == "RESULT_ALREADY_DECIDED"

    def test_another_coordinator_cannot_decide(self, with_result, actors, session):
        from app.models import UserAccount, UserRole

        _, result = with_result
        stranger = UserAccount(
            email="stranger2@example.com",
            password_hash="hash",
            first_name="Ugo",
            last_name="Gallo",
            user_role=UserRole.COORDINATOR,
        )
        session.add(stranger)
        session.flush()

        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_exam_result(
                result.result_id,
                stranger.user_id,
                "approved",
            )

        assert raised.value.code == "EXAM_RESULT_NOT_FOUND"

    def test_unknown_result_is_refused(self, with_result, actors):
        with pytest.raises(AppError) as raised:
            coordinator_service.evaluate_exam_result(
                999999,
                actors["coordinator"].user_id,
                "approved",
            )

        assert raised.value.code == "EXAM_RESULT_NOT_FOUND"
