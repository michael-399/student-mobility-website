"""Tests for the office service (FR-02, FR-06, FR-11)."""

import pytest

from app.errors import AppError
from app.models import ApplicationStatus, RecognitionStatus
from app.services import coordinator as coordinator_service
from app.services import office as office_service
from app.services import student as student_service


@pytest.fixture
def approved(actors, application_data, course_mappings, upload, session):
    """An application whose agreement the coordinator has approved."""
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
    coordinator_service.evaluate_learning_agreement(
        application.application_id,
        actors["coordinator"].user_id,
        "approved",
    )
    session.flush()

    return application


@pytest.fixture
def in_recognition(approved, actors, upload, session):
    """An application with the transcript and one pending exam result."""
    office_service.complete_pre_departure(approved.application_id)
    student_service.set_mobility_dates(
        approved.application_id,
        actors["student"].user_id,
        arrival_date="2026-01-10",
        departure_date="2026-06-20",
    )
    student_service.upload_transcript(
        approved.application_id,
        actors["student"].user_id,
        upload("transcript.pdf"),
    )
    mapping = approved.learning_agreements[0].course_mappings[0]
    student_service.record_exam_results(
        approved.application_id,
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

    return approved, mapping


class TestVisibility:
    def test_office_sees_every_application(self, approved, actors, application_data):
        """FR-01: the office is not scoped to an owner."""
        other = student_service.create_application(
            actors["other_student"].user_id,
            application_data,
        )

        visible = {a.application_id for a in office_service.list_applications()}

        assert {approved.application_id, other.application_id} <= visible

    def test_filters_by_status(self, approved, actors, application_data):
        student_service.create_application(actors["student"].user_id, application_data)

        drafts = office_service.list_applications(ApplicationStatus.CREATED)
        waiting = office_service.list_applications("waiting_la_approval")

        assert all(a.status is ApplicationStatus.CREATED for a in drafts)
        assert approved.application_id in {a.application_id for a in waiting}

    def test_rejects_an_unknown_status_filter(self, approved):
        with pytest.raises(AppError) as raised:
            office_service.list_applications("in_orbit")

        assert raised.value.code == "INVALID_STATUS_FILTER"


class TestPreDeparture:
    def test_signs_off_an_approved_agreement(self, approved):
        office_service.complete_pre_departure(approved.application_id)

        assert approved.status is ApplicationStatus.PRE_DEPARTURE_COMPLETED

    def test_refuses_without_an_approved_agreement(
        self, actors, application_data, course_mappings, upload, session
    ):
        """BR-20: no pre-departure sign-off without an approved agreement."""
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

        with pytest.raises(AppError) as raised:
            office_service.complete_pre_departure(application.application_id)

        assert raised.value.code == "NO_APPROVED_LA"

    def test_refuses_on_a_draft(self, actors, application_data):
        application = student_service.create_application(
            actors["student"].user_id,
            application_data,
        )

        with pytest.raises(AppError) as raised:
            office_service.complete_pre_departure(application.application_id)

        assert raised.value.code == "INVALID_STATUS"

    def test_cannot_sign_off_twice(self, approved):
        office_service.complete_pre_departure(approved.application_id)

        with pytest.raises(AppError) as raised:
            office_service.complete_pre_departure(approved.application_id)

        assert raised.value.code == "INVALID_STATUS"

    def test_arrival_starts_the_mobility(self, approved, actors):
        """FR-07: the student reports arriving, which begins the mobility."""
        office_service.complete_pre_departure(approved.application_id)

        student_service.set_mobility_dates(
            approved.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
        )

        assert approved.status is ApplicationStatus.MOBILITY_IN_PROGRESS

    def test_pre_departure_alone_does_not_start_the_mobility(self, approved):
        office_service.complete_pre_departure(approved.application_id)

        assert approved.status is ApplicationStatus.PRE_DEPARTURE_COMPLETED


class TestClosure:
    def test_closes_once_every_result_is_decided(self, in_recognition, actors):
        application, mapping = in_recognition
        coordinator_service.evaluate_exam_result(
            mapping.exam_result.result_id,
            actors["coordinator"].user_id,
            "approved",
        )

        office_service.close_application(application.application_id)

        assert application.status is ApplicationStatus.CLOSED

    def test_refuses_while_a_result_is_pending(self, in_recognition):
        """BR-25: a pending recognition holds closure open."""
        application, mapping = in_recognition

        assert mapping.exam_result.recognition_status is RecognitionStatus.PENDING

        with pytest.raises(AppError) as raised:
            office_service.close_application(application.application_id)

        assert raised.value.code == "PENDING_EXAM_RESULTS"

    def test_a_rejected_recognition_does_not_hold_closure_open(
        self, in_recognition, actors
    ):
        application, mapping = in_recognition
        coordinator_service.evaluate_exam_result(
            mapping.exam_result.result_id,
            actors["coordinator"].user_id,
            "rejected",
            "Grade not recognised",
        )

        office_service.close_application(application.application_id)

        assert application.status is ApplicationStatus.CLOSED

    def test_refuses_before_recognition_opens(self, approved, actors):
        office_service.complete_pre_departure(approved.application_id)
        student_service.set_mobility_dates(
            approved.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
        )

        with pytest.raises(AppError) as raised:
            office_service.close_application(approved.application_id)

        assert raised.value.code == "INVALID_STATUS"

    def test_refuses_with_no_results_submitted(self, approved, actors, upload, session):
        office_service.complete_pre_departure(approved.application_id)
        student_service.set_mobility_dates(
            approved.application_id,
            actors["student"].user_id,
            arrival_date="2026-01-10",
        )
        student_service.upload_transcript(
            approved.application_id,
            actors["student"].user_id,
            upload("transcript.pdf"),
        )
        session.flush()

        with pytest.raises(AppError) as raised:
            office_service.close_application(approved.application_id)

        assert raised.value.code == "MISSING_EXAM_RESULTS"

    def test_a_closed_application_is_frozen(self, in_recognition, actors, session):
        """BR-09: a closed application shall not be modified."""
        application, mapping = in_recognition
        coordinator_service.evaluate_exam_result(
            mapping.exam_result.result_id,
            actors["coordinator"].user_id,
            "approved",
        )
        office_service.close_application(application.application_id)
        session.flush()

        with pytest.raises(AppError) as raised:
            student_service.set_mobility_dates(
                application.application_id,
                actors["student"].user_id,
                departure_date="2026-07-01",
            )

        assert raised.value.code == "APPLICATION_CLOSED"

        with pytest.raises(AppError) as second:
            office_service.close_application(application.application_id)

        assert second.value.code == "APPLICATION_CLOSED"


class TestInstitutions:
    def test_creates_an_institution(self, session):
        institution = office_service.create_institution(
            {
                "name": "Nordic University",
                "country": "Sweden",
                "city": "Uppsala",
                "contact_email": "mobility@nordic.example",
            }
        )

        assert institution.institution_id is not None
        assert institution.is_active is True

    @pytest.mark.parametrize("field", ["name", "country", "city"])
    def test_requires_name_country_and_city(self, session, field):
        """FR-02: each institution has at least a name, country, and city."""
        data = {"name": "N", "country": "C", "city": "T"}
        data[field] = "   "

        with pytest.raises(AppError) as raised:
            office_service.create_institution(data)

        assert raised.value.code == "MISSING_FIELDS"

    def test_updates_an_institution(self, actors):
        updated = office_service.update_institution(
            actors["institution"].institution_id,
            {"city": "Madrid"},
        )

        assert updated.city == "Madrid"

    def test_deactivation_hides_it_from_the_list(self, actors):
        institution_id = actors["institution"].institution_id

        office_service.deactivate_institution(institution_id)

        active = {i.institution_id for i in office_service.list_institutions()}
        everything = {
            i.institution_id
            for i in office_service.list_institutions(active_only=False)
        }

        assert institution_id not in active
        assert institution_id in everything

    def test_a_deactivated_institution_cannot_be_chosen(
        self, actors, application_data
    ):
        office_service.deactivate_institution(actors["institution"].institution_id)

        with pytest.raises(AppError) as raised:
            student_service.create_application(
                actors["student"].user_id,
                application_data,
            )

        assert raised.value.code == "INSTITUTION_INACTIVE"

    def test_deactivation_keeps_existing_applications_intact(self, approved, actors):
        """Past applications keep pointing at the institution they were made for."""
        office_service.deactivate_institution(actors["institution"].institution_id)

        assert approved.host_institution_id == actors["institution"].institution_id
        assert office_service.get_application(approved.application_id) is approved

    def test_reactivates_an_institution(self, actors):
        institution_id = actors["institution"].institution_id
        office_service.deactivate_institution(institution_id)

        office_service.reactivate_institution(institution_id)

        active = {i.institution_id for i in office_service.list_institutions()}
        assert institution_id in active

    def test_unknown_institution_is_refused(self, session):
        with pytest.raises(AppError) as raised:
            office_service.update_institution(999999, {"city": "Nowhere"})

        assert raised.value.code == "INSTITUTION_NOT_FOUND"
