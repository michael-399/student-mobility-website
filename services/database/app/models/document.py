"""SQLAlchemy models for Learning Agreements and Transcripts of Records."""
from ..database import db 

class TranscriptOfRecords(db.Model):
    __tablename__ = "transcript_of_records"

    transcript_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    application_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "mobility_application.application_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
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
    application = db.relationship(
        "MobilityApplication",
        back_populates="transcript"
    )