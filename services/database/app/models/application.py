"""SQLAlchemy models for mobility applications and their status history."""
import enum

from ..database import db
class ApplicationStatus(enum.Enum):
    CREATED = "created"
    WAITING_LA_APPROVAL = "waiting_la_approval"
    PRE_DEPARTURE_COMPLETED = "pre_departure_completed"
    MOBILITY_IN_PROGRESS = "mobility_in_progress"
    UNDER_EXAM_RECOGNITION = "under_exam_recognition"
    CLOSED = "closed"
class MobilityPeriod(enum.Enum):
    FIRST_SEMESTER = "first_semester"
    SECOND_SEMESTER = "second_semester"
    FULL_YEAR = "full_year"


class MobilityApplication(db.Model):
    __tablename__ = "mobility_application"

    application_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    academic_year = db.Column(
        db.String(9),
        nullable=False,
    )
    optional_note = db.Column(
        db.String(500),
        nullable=True,
    )

    expected_mobility_period = db.Column(
        db.Enum(
            MobilityPeriod,
            name="mobility_period",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
    )

    host_institution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "institution.institution_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    status = db.Column(
        db.Enum(ApplicationStatus,
                name="application_status",
                values_callable=lambda enum_class: [
                    member.value for member in enum_class 
                ],
            ),
            nullable=False,
            default=ApplicationStatus.CREATED,
            server_default="created",
    )

    host_institution = db.relationship(
        "Institution",
        back_populates="applications",
    )

    coordinator_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "user_account.user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    academic_coordinator = db.relationship(
        "UserAccount",
        foreign_keys=[coordinator_id],
        back_populates="coordinated_applications",
    )

    student_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "user_account.user_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    student = db.relationship(
        "UserAccount",
        foreign_keys=[student_id],
        back_populates="student_applications",
    )

    learning_agreements = db.relationship(
        "LearningAgreement",
        back_populates="application",
        cascade="all, delete-orphan",
    )

    transcript = db.relationship(
        "TranscriptOfRecords",
        back_populates="application",
        cascade="all, delete-orphan",
        uselist=False,
    )

    actual_arrival_date = db.Column(
        db.Date,
        nullable=True,
    )

    actual_departure_date = db.Column(
        db.Date,
        nullable=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            (
                "actual_departure_date IS NULL "
                "OR (actual_arrival_date IS NOT NULL "
                "AND actual_departure_date >= actual_arrival_date)"
            ),
            name="ck_mobility_application_actual_dates",
        ),
    )