"""Tests for the student service (FR-03, FR-04, FR-05, FR-07, FR-09)."""

from datetime import date

import pytest

from app.errors import AppError
from app.models import ApplicationStatus, ApprovalStatus, RecognitionStatus
from app.services import student as student_service


def create(actors, application_data, **overrides):
    return student_service.create_application(
        actors["student"].user_id,
        {**application_data, **overrides},
    )


def approve_latest_agreement(application):
    """Stand in for the coordinator, which arrives in the next stage."""
    agreement = max(
        application.learning_agreements,
        key=lambda item: item.version_number,
    )
    agreement.approval_status = ApprovalStatus.APPROVED
    agreement.decision_date = date.today()

    return agreement


def advance_to_mobility(application):
    """Walk the office-owned part of the workflow, not yet implemented."""
    from app.services._workflow import transition

    transition(application, ApplicationStatus.PRE_DEPARTURE_COMPLETED)
    transition(application, ApplicationStatus.MOBILITY_IN_PROGRESS)


class TestCreateApplication:
    def test_creates_in_created_status_with_history(self, actors, application_data):
        application = create(actors, application_data)

        assert application.application_id is not None
        assert application.status is ApplicationStatus.CREATED
        assert [(row.old_status, row.new_status) for row in application.status_history] == [
            (None, ApplicationStatus.CREATED)
        ]

    def test_rejects_missing_fields(self, actors, application_data):
        del application_data["academic_year"]

        with pytest.raises(AppError) as raised:
            create(actors, application_data)

        assert raised.value.code == "MISSING_FIELDS"

    @pytest.mark.parametrize(
        "academic_year",
        ["2025/2027", "2025-2026", "25/26", "2025/2025", "not a year"],
    )
    def test_rejects_non_consecutive_or_malformed_year(
        self, actors, application_data, academic_year
    ):
        """BR-07: the second year must be the first plus one."""
        with pytest.raises(AppError) as raised:
            create(actors, application_data, academic_year=academic_year)

        assert raised.value.code == "INVALID_ACADEMIC_YEAR"

    def test_rejects_unknown_period(self, actors, application_data):
        with pytest.raises(AppError) as raised:
            create(actors, application_data, expected_mobility_period="summer")

        assert raised.value.code == "INVALID_PERIOD"

    def test_rejects_inactive_institution(self, actors, application_data, session):
        actors["institution"].is_active = False
        session.flush()

        with pytest.raises(AppError) as raised:
            create(actors, application_data)

        assert raised.value.code == "INSTITUTION_INACTIVE"

    def test_rejects_coordinator_who_is_not_a_coordinator(self, actors, application_data):
        """BR-03: the assigned coordinator must hold that role."""
        with pytest.raises(AppError) as raised:
            create(actors, application_data, coordinator_id=actors["other_student"].user_id)

        assert raised.value.code == "INVALID_COORDINATOR"


class TestOwnership:
    def test_another_student_cannot_read_the_application(self, actors, application_data):
        """BR-04: applications are scoped to their owner."""
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.get_application(
                application.application_id,
                actors["other_student"].user_id,
            )

        assert raised.value.code == "APPLICATION_NOT_FOUND"

    def test_another_student_cannot_update_the_application(self, actors, application_data):
        application = create(actors, application_data)

        with pytest.raises(AppError):
            student_service.update_application(
                application.application_id,
                actors["other_student"].user_id,
                {"optional_note": "injected"},
            )

    def test_listing_only_returns_own_applications(self, actors, application_data):
        create(actors, application_data)

        assert student_service.list_applications(actors["student"].user_id)
        assert student_service.list_applications(actors["other_student"].user_id) == []


class TestUpdateAndDelete:
    def test_updates_while_draft(self, actors, application_data):
        application = create(actors, application_data)

        updated = student_service.update_application(
            application.application_id,
            actors["student"].user_id,
            {"optional_note": "Erasmus+", "academic_year": "2026/2027"},
        )

        assert updated.optional_note == "Erasmus+"
        assert updated.academic_year == "2026/2027"

    def test_cannot_update_once_submitted(
        self, actors, application_data, course_mappings, upload
    ):
        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        with pytest.raises(AppError) as raised:
            student_service.update_application(
                application.application_id,
                actors["student"].user_id,
                {"optional_note": "too late"},
            )

        assert raised.value.code == "INVALID_STATUS"

    def test_deletes_a_draft(self, actors, application_data, session):
        application = create(actors, application_data)
        application_id = application.application_id

        student_service.delete_application(application_id, actors["student"].user_id)

        assert student_service.list_applications(actors["student"].user_id) == []


class TestLearningAgreement:
    def test_first_upload_creates_version_one_and_awaits_approval(
        self, actors, application_data, course_mappings, upload
    ):
        application = create(actors, application_data)

        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        assert application.status is ApplicationStatus.WAITING_LA_APPROVAL
        assert len(application.learning_agreements) == 1

        agreement = application.learning_agreements[0]
        assert agreement.version_number == 1
        assert agreement.approval_status is ApprovalStatus.PENDING
        assert len(agreement.course_mappings) == 1
        assert agreement.course_mappings[0].home_course_code == "CT0001"

    def test_accepts_mappings_as_a_json_string(
        self, actors, application_data, course_mappings, upload
    ):
        """Mappings arrive as a JSON field alongside the multipart file."""
        import json

        application = create(actors, application_data)

        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            json.dumps(course_mappings),
        )

        assert len(application.learning_agreements[0].course_mappings) == 1

    def test_rejects_second_upload_while_one_is_pending(
        self, actors, application_data, course_mappings, upload
    ):
        """BR-12: the mapping is frozen while a version awaits a decision."""
        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                upload(),
                course_mappings,
            )

        assert raised.value.code == "PENDING_LA_EXISTS"

    def test_requires_a_file(self, actors, application_data, course_mappings):
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                None,
                course_mappings,
            )

        assert raised.value.code == "MISSING_FILE"

    def test_requires_at_least_one_mapping(self, actors, application_data, upload):
        """FR-04: an application carries one or more proposed mappings."""
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                upload(),
                [],
            )

        assert raised.value.code == "MISSING_COURSE_MAPPINGS"

    @pytest.mark.parametrize("credits", [0, -3])
    def test_rejects_non_positive_credits(
        self, actors, application_data, course_mappings, upload, credits
    ):
        """BR-11: credits must be positive."""
        course_mappings[0]["home_course_credits"] = credits
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                upload(),
                course_mappings,
            )

        assert raised.value.code == "INVALID_COURSE_MAPPING"

    def test_rejects_empty_course_name(
        self, actors, application_data, course_mappings, upload
    ):
        course_mappings[0]["foreign_course_name"] = "   "
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                upload(),
                course_mappings,
            )

        assert raised.value.code == "INVALID_COURSE_MAPPING"

    def test_rejects_duplicate_course_pair(
        self, actors, application_data, course_mappings, upload
    ):
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.upload_learning_agreement(
                application.application_id,
                actors["student"].user_id,
                upload(),
                course_mappings + course_mappings,
            )

        assert raised.value.code == "DUPLICATE_COURSE_MAPPING"

    def test_resubmission_after_rejection_adds_version_two(
        self, actors, application_data, course_mappings, upload, session
    ):
        """BR-16: version numbers are unique and increase within an application."""
        from app.services._workflow import transition

        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        # The coordinator rejects, which returns the draft to the student.
        agreement = application.learning_agreements[0]
        agreement.approval_status = ApprovalStatus.REJECTED
        agreement.decision_date = date.today()
        agreement.rejection_reason = "Credits do not balance"
        transition(application, ApplicationStatus.CREATED)
        session.flush()

        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        versions = sorted(a.version_number for a in application.learning_agreements)
        assert versions == [1, 2]
        assert application.status is ApplicationStatus.WAITING_LA_APPROVAL

    def test_modification_during_mobility_returns_for_approval(
        self, actors, application_data, course_mappings, upload, session
    ):
        """A mid-mobility revision is simply the next agreement version."""
        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )
        approve_latest_agreement(application)
        advance_to_mobility(application)
        session.flush()

        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )

        assert application.status is ApplicationStatus.WAITING_LA_APPROVAL
        assert len(application.learning_agreements) == 2


class TestMobilityDates:
    @pytest.fixture
    def in_mobility(self, actors, application_data, course_mappings, upload, session):
        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )
        approve_latest_agreement(application)
        advance_to_mobility(application)
        session.flush()

        return application

    def test_records_dates(self, in_mobility, actors):
        student_service.set_mobility_dates(
            in_mobility.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
            departure_date="2026-06-20",
        )

        assert in_mobility.actual_arrival_date == date(2026, 1, 10)
        assert in_mobility.actual_departure_date == date(2026, 6, 20)

    def test_rejects_departure_before_arrival(self, in_mobility, actors):
        """BR-21: departure cannot precede arrival."""
        with pytest.raises(AppError) as raised:
            student_service.set_mobility_dates(
                in_mobility.application_id,
                actors["student"].user_id,
                arrival_date="2026-06-20",
                departure_date="2026-01-10",
            )

        assert raised.value.code == "INVALID_DATES"

    def test_rejects_dates_before_mobility_starts(self, actors, application_data):
        application = create(actors, application_data)

        with pytest.raises(AppError) as raised:
            student_service.set_mobility_dates(
                application.application_id,
                actors["student"].user_id,
                arrival_date="2026-01-10",
            )

        assert raised.value.code == "INVALID_STATUS"


class TestTranscriptAndResults:
    @pytest.fixture
    def in_mobility(self, actors, application_data, course_mappings, upload, session):
        application = create(actors, application_data)
        student_service.upload_learning_agreement(
            application.application_id,
            actors["student"].user_id,
            upload(),
            course_mappings,
        )
        approve_latest_agreement(application)
        advance_to_mobility(application)
        student_service.set_mobility_dates(
            application.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
            departure_date="2026-06-20",
        )
        session.flush()

        return application

    def test_transcript_opens_recognition(self, in_mobility, actors, upload):
        """BR-23: recognition begins only once the transcript exists."""
        student_service.upload_transcript(
            in_mobility.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )

        assert in_mobility.status is ApplicationStatus.UNDER_EXAM_RECOGNITION
        assert in_mobility.transcript is not None

    def test_results_cannot_be_recorded_before_the_transcript(self, in_mobility, actors):
        mapping = in_mobility.learning_agreements[0].course_mappings[0]

        with pytest.raises(AppError) as raised:
            student_service.record_exam_results(
                in_mobility.application_id,
                actors["student"].user_id,
                [{"mapping_id": mapping.mapping_id, "foreign_grade": "8", "exam_date": "2026-03-01"}],
            )

        assert raised.value.code == "INVALID_STATUS"

    def test_records_a_result_as_pending(self, in_mobility, actors, upload):
        student_service.upload_transcript(
            in_mobility.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )
        mapping = in_mobility.learning_agreements[0].course_mappings[0]

        student_service.record_exam_results(
            in_mobility.application_id,
            actors["student"].user_id,
            [{"mapping_id": mapping.mapping_id, "foreign_grade": "8", "exam_date": "2026-03-01"}],
        )

        assert mapping.exam_result.foreign_grade == "8"
        assert mapping.exam_result.exam_date == date(2026, 3, 1)
        assert mapping.exam_result.recognition_status is RecognitionStatus.PENDING

    def test_rejects_a_mapping_outside_the_current_agreement(
        self, in_mobility, actors, upload
    ):
        """BR-24: results attach to the mapping currently in force."""
        student_service.upload_transcript(
            in_mobility.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )

        with pytest.raises(AppError) as raised:
            student_service.record_exam_results(
                in_mobility.application_id,
                actors["student"].user_id,
                [{"mapping_id": 999999, "foreign_grade": "8", "exam_date": "2026-03-01"}],
            )

        assert raised.value.code == "MAPPING_NOT_IN_CURRENT_LA"

    def test_rejects_exam_date_outside_the_mobility(self, in_mobility, actors, upload):
        """BR-22: the passing date falls within the mobility period."""
        student_service.upload_transcript(
            in_mobility.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )
        mapping = in_mobility.learning_agreements[0].course_mappings[0]

        with pytest.raises(AppError) as raised:
            student_service.record_exam_results(
                in_mobility.application_id,
                actors["student"].user_id,
                [{"mapping_id": mapping.mapping_id, "foreign_grade": "8", "exam_date": "2027-01-01"}],
            )

        assert raised.value.code == "EXAM_DATE_OUT_OF_RANGE"

    def test_leaves_an_already_decided_result_alone(self, in_mobility, actors, upload, session):
        student_service.upload_transcript(
            in_mobility.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )
        mapping = in_mobility.learning_agreements[0].course_mappings[0]
        student_service.record_exam_results(
            in_mobility.application_id,
            actors["student"].user_id,
            [{"mapping_id": mapping.mapping_id, "foreign_grade": "8", "exam_date": "2026-03-01"}],
        )

        mapping.exam_result.recognition_status = RecognitionStatus.APPROVED
        mapping.exam_result.decision_date = date.today()
        session.flush()

        with pytest.raises(AppError) as raised:
            student_service.record_exam_results(
                in_mobility.application_id,
                actors["student"].user_id,
                [{"mapping_id": mapping.mapping_id, "foreign_grade": "30", "exam_date": "2026-03-01"}],
            )

        assert raised.value.code == "RESULT_ALREADY_DECIDED"
