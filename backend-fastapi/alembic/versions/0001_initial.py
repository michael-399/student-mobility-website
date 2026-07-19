"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _mapping_columns() -> list:
    return [
        sa.Column("foreign_teaching_code", sa.String(), nullable=False),
        sa.Column("foreign_course_name", sa.String(), nullable=False),
        sa.Column("foreign_credits", sa.Numeric(), nullable=False),
        sa.Column("local_course_code", sa.String(), nullable=False),
        sa.Column("local_course_name", sa.String(), nullable=False),
        sa.Column("local_credits", sa.Numeric(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
    )

    op.create_table(
        "institutions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
    )

    op.create_table(
        "applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("student_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("academic_year", sa.String(), nullable=False),
        sa.Column("host_institution_id", UUID, sa.ForeignKey("institutions.id"), nullable=False),
        sa.Column("expected_period", sa.String(), nullable=False),
        sa.Column("referent_lecturer_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("pre_departure_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pre_departure_completed_at", sa.DateTime(timezone=True)),
        sa.Column("pre_departure_completed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("actual_arrival_date", sa.DateTime(timezone=True)),
        sa.Column("actual_departure_date", sa.DateTime(timezone=True)),
        sa.Column("transcript_file_name", sa.String()),
        sa.Column("transcript_file_path", sa.String()),
        sa.Column("transcript_upload_date", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_applications_student_id", "applications", ["student_id"])
    op.create_index("ix_applications_referent_lecturer_id", "applications", ["referent_lecturer_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    op.create_table(
        "learning_agreements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision_date", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.String()),
        sa.UniqueConstraint("application_id", "position"),
    )
    op.create_index("ix_learning_agreements_application_id", "learning_agreements", ["application_id"])

    op.create_table(
        "exam_mappings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_mapping_columns(),
        sa.UniqueConstraint("application_id", "position"),
    )
    op.create_index("ix_exam_mappings_application_id", "exam_mappings", ["application_id"])

    op.create_table(
        "modifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("new_la_file_name", sa.String(), nullable=False),
        sa.Column("new_la_file_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision_date", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("application_id", "position"),
    )
    op.create_index("ix_modifications_application_id", "modifications", ["application_id"])

    op.create_table(
        "modification_exam_mappings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("modification_id", UUID, sa.ForeignKey("modifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *_mapping_columns(),
        sa.UniqueConstraint("modification_id", "position"),
    )
    op.create_index("ix_modification_exam_mappings_modification_id", "modification_exam_mappings", ["modification_id"])

    op.create_table(
        "exam_scores",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("exam_mapping_index", sa.Integer(), nullable=False),
        sa.Column("score", sa.String(), nullable=False),
        sa.Column("exam_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("application_id", "position"),
    )
    op.create_index("ix_exam_scores_application_id", "exam_scores", ["application_id"])


def downgrade() -> None:
    op.drop_table("exam_scores")
    op.drop_table("modification_exam_mappings")
    op.drop_table("modifications")
    op.drop_table("exam_mappings")
    op.drop_table("learning_agreements")
    op.drop_table("applications")
    op.drop_table("institutions")
    op.drop_table("users")
