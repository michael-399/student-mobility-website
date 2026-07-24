"""SQLAlchemy models for Learning Agreements and their course mappings."""

import enum

from ..database import db


class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LearningAgreement(db.Model):
    __tablename__ = "learning_agreement"

    application_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "mobility_application.application_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    version_number = db.Column(
        db.Integer,
        primary_key=True,
    )

    file_path = db.Column(
        db.Text,
        nullable=False,
    )

    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    approval_status = db.Column(
        db.Enum(
            ApprovalStatus,
            name="approval_status",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )

    decision_date = db.Column(
        db.Date,
        nullable=True,
    )

    rejection_reason = db.Column(
        db.Text,
        nullable=True,
    )

    application = db.relationship(
        "MobilityApplication",
        back_populates="learning_agreements",
    )

    course_mappings = db.relationship(
        "CourseMapping",
        back_populates="learning_agreement",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "version_number > 0",
            name="ck_learning_agreement_version_positive",
        ),
    )


class CourseMapping(db.Model):
    __tablename__ = "course_mapping"

    mapping_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    application_id = db.Column(
        db.BigInteger,
        nullable=False,
    )

    version_number = db.Column(
        db.Integer,
        nullable=False,
    )

    home_course_code = db.Column(
        db.String(50),
        nullable=False,
    )

    home_course_name = db.Column(
        db.String(255),
        nullable=False,
    )

    foreign_course_code = db.Column(
        db.String(50),
        nullable=False,
    )

    foreign_course_name = db.Column(
        db.String(255),
        nullable=False,
    )

    home_course_credits = db.Column(
        db.Numeric(4, 1),
        nullable=False,
    )

    foreign_course_credits = db.Column(
        db.Numeric(4, 1),
        nullable=False,
    )

    learning_agreement = db.relationship(
        "LearningAgreement",
        back_populates="course_mappings",
    )

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["application_id", "version_number"],
            [
                "learning_agreement.application_id",
                "learning_agreement.version_number",
            ],
            ondelete="CASCADE",
            name="fk_course_mapping_learning_agreement",
        ),
        db.CheckConstraint(
            "home_course_credits > 0",
            name="ck_course_mapping_home_credits_positive",
        ),
        db.CheckConstraint(
            "foreign_course_credits > 0",
            name="ck_course_mapping_foreign_credits_positive",
        ),
        db.UniqueConstraint(
            "application_id",
            "version_number",
            "home_course_code",
            "foreign_course_code",
            name="uq_course_mapping_plan_course_pair",
        ),
    )
