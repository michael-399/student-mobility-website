"""SQLAlchemy models for partner host institutions."""
from ..database import db 

class Institution(db.Model):
    __tablename__ = "Institution"

    institution_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    name = db.Column(
        db.String(255),
        nullable=False,
    )

    country = db.Column(
        db.String(100),
        nullable=False,
    )

    city = db.Column(
        db.String(100),
        nullable=False,
    )

    contact_email = db.Column(
        db.String(255),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "name",
            "country",
            "city",
            name="uq_host_institution_location",
        ),

    )

    applications = db.relationship(
        "MobilityApplication",
        back_populates="host_institution",
    )    
    

    