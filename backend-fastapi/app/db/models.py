"""SQLAlchemy 2.0 models.

The original MongoDB schema stored the whole application aggregate as one
document with embedded arrays (learningAgreements, examMappings,
modifications, examScores).  Here those embedded arrays are normalised
into child tables.  Each child carries an explicit ``position`` integer
that reproduces the original array index, because the HTTP contract the
Angular frontend depends on addresses sub-documents by array position
(``/learning-agreement/:index``, ``/scores/:scoreIndex``).

Primary keys are UUIDs; they are serialised to JSON as ``_id`` so the
frontend (which treats ids as opaque strings) needs no changes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# ``Mapped[uuid.UUID]`` resolves to SQLAlchemy's generic Uuid type, which
# renders as a native ``uuid`` column on PostgreSQL (and CHAR elsewhere),
# so no dialect-specific import is needed.


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # "student" | "lecturer" | "office"
    role: Mapped[str] = mapped_column(String, nullable=False)


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = _uuid_pk()

    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String, nullable=False)
    host_institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False)
    # "first_semester" | "second_semester" | "entire_year"
    expected_period: Mapped[str] = mapped_column(String, nullable=False)
    referent_lecturer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="created", index=True)

    pre_departure_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pre_departure_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pre_departure_completed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    actual_arrival_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_departure_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # transcriptOfRecords (single optional object) flattened onto the row.
    transcript_file_name: Mapped[str | None] = mapped_column(String)
    transcript_file_path: Mapped[str | None] = mapped_column(String)
    transcript_upload_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))

    # Python-side defaults (not server_default) so async sessions never need
    # to re-fetch a DB-generated value after INSERT/UPDATE.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships (eager-loaded via selectin so they are available in async).
    student: Mapped[User] = relationship(foreign_keys=[student_id], lazy="selectin")
    referent_lecturer: Mapped[User] = relationship(foreign_keys=[referent_lecturer_id], lazy="selectin")
    host_institution: Mapped[Institution] = relationship(lazy="selectin")

    learning_agreements: Mapped[list[LearningAgreement]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="LearningAgreement.position",
        lazy="selectin",
    )
    exam_mappings: Mapped[list[ExamMapping]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ExamMapping.position",
        lazy="selectin",
    )
    modifications: Mapped[list[Modification]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Modification.position",
        lazy="selectin",
    )
    exam_scores: Mapped[list[ExamScore]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ExamScore.position",
        lazy="selectin",
    )


class LearningAgreement(Base):
    __tablename__ = "learning_agreements"
    __table_args__ = (UniqueConstraint("application_id", "position"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # "pending" | "approved" | "rejected"
    status: Mapped[str] = mapped_column(String, nullable=False)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String)

    application: Mapped[Application] = relationship(back_populates="learning_agreements")


class ExamMapping(Base):
    __tablename__ = "exam_mappings"
    __table_args__ = (UniqueConstraint("application_id", "position"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    foreign_teaching_code: Mapped[str] = mapped_column(String, nullable=False)
    foreign_course_name: Mapped[str] = mapped_column(String, nullable=False)
    foreign_credits: Mapped[float] = mapped_column(Numeric, nullable=False)
    local_course_code: Mapped[str] = mapped_column(String, nullable=False)
    local_course_name: Mapped[str] = mapped_column(String, nullable=False)
    local_credits: Mapped[float] = mapped_column(Numeric, nullable=False)

    application: Mapped[Application] = relationship(back_populates="exam_mappings")


class Modification(Base):
    __tablename__ = "modifications"
    __table_args__ = (UniqueConstraint("application_id", "position"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    description: Mapped[str] = mapped_column(String, nullable=False)
    new_la_file_name: Mapped[str] = mapped_column(String, nullable=False)
    new_la_file_path: Mapped[str] = mapped_column(String, nullable=False)
    # "pending" | "approved" | "rejected"
    status: Mapped[str] = mapped_column(String, nullable=False)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    application: Mapped[Application] = relationship(back_populates="modifications")
    # Snapshot of the proposed exam mappings (examMappingDiff).
    exam_mappings: Mapped[list[ModificationExamMapping]] = relationship(
        back_populates="modification",
        cascade="all, delete-orphan",
        order_by="ModificationExamMapping.position",
        lazy="selectin",
    )


class ModificationExamMapping(Base):
    __tablename__ = "modification_exam_mappings"
    __table_args__ = (UniqueConstraint("modification_id", "position"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    modification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modifications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    foreign_teaching_code: Mapped[str] = mapped_column(String, nullable=False)
    foreign_course_name: Mapped[str] = mapped_column(String, nullable=False)
    foreign_credits: Mapped[float] = mapped_column(Numeric, nullable=False)
    local_course_code: Mapped[str] = mapped_column(String, nullable=False)
    local_course_name: Mapped[str] = mapped_column(String, nullable=False)
    local_credits: Mapped[float] = mapped_column(Numeric, nullable=False)

    modification: Mapped[Modification] = relationship(back_populates="exam_mappings")


class ExamScore(Base):
    __tablename__ = "exam_scores"
    __table_args__ = (UniqueConstraint("application_id", "position"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    # Logical index into the application's exam_mappings (matches original field).
    exam_mapping_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Kept as text to match the original model (values like "28", "A", "Pass").
    score: Mapped[str] = mapped_column(String, nullable=False)
    exam_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # "pending" | "approved"
    status: Mapped[str] = mapped_column(String, nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped[Application] = relationship(back_populates="exam_scores")
