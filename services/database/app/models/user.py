import enum

from ..database import db


class UserRole(enum.Enum):
    STUDENT = "student"
    COORDINATOR = "coordinator"
    OFFICE_STAFF = "office_staff"


class UserAccount(db.Model):
    __tablename__ = "user_account"

    user_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    password_hash = db.Column(
        db.Text,
        nullable=False,
    )

    first_name = db.Column(
        db.String(50),
        nullable=False,
    )

    last_name = db.Column(
        db.String(50),
        nullable=False,
    )

    user_role = db.Column(
        db.Enum(UserRole, name="user_role"),
        nullable=False,
    )

    student_applications = db.relationship(
        "MobilityApplication",
        foreign_keys="MobilityApplication.student_id",
        back_populates="student",
    )

    coordinated_applications = db.relationship(
        "MobilityApplication",
        foreign_keys="MobilityApplication.coordinator_id",
        back_populates="academic_coordinator",
    )
