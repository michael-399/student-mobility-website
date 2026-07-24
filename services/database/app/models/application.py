"""SQLAlchemy models for mobility applications and their status history."""
import enum

from ..database import db

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
        db.Enum(MobilityPeriod,
                name="mobility_period"),
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
