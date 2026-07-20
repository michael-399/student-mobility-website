"""SQLAlchemy models for mobility applications and their status history."""
from ..database import db

class MobilityApplication(db.Model):
    __tablename__ = "mobility_application"

    application_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    academic_year = db.Column(
        db.Date,
        nullable=False,
    )

    host_institution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "Institution.institution_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    host_institution = db.relationship(
        "Institution",
        back_populates="applications",
    )