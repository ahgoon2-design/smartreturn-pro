"""Add import mapping decisions.

Revision ID: c7d8e9f0a123
Revises: b6c7d8e9f012
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c7d8e9f0a123"
down_revision: str | Sequence[str] | None = "b6c7d8e9f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_mapping_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("import_type", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_channel", sa.String(length=80), nullable=True),
        sa.Column("original_header", sa.String(length=255), nullable=False),
        sa.Column("normalized_header", sa.String(length=255), nullable=False),
        sa.Column("canonical_field", sa.String(length=100), nullable=True),
        sa.Column("decision_type", sa.String(length=50), nullable=False),
        sa.Column("confidence_before", sa.Float(), nullable=True),
        sa.Column("confidence_after", sa.Float(), nullable=True),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("header_signature", sa.String(length=500), nullable=True),
        sa.Column("file_signature", sa.String(length=255), nullable=True),
        sa.Column("sample_value_hash", sa.String(length=128), nullable=True),
        sa.Column("source_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["import_mapping_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_mapping_decisions_client_type",
        "import_mapping_decisions",
        ["client_id", "import_type", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_import_mapping_decisions_header",
        "import_mapping_decisions",
        ["normalized_header"],
        unique=False,
    )
    op.create_index(
        "ix_import_mapping_decisions_field",
        "import_mapping_decisions",
        ["canonical_field"],
        unique=False,
    )
    op.create_index(
        "ix_import_mapping_decisions_type",
        "import_mapping_decisions",
        ["decision_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_import_mapping_decisions_type", table_name="import_mapping_decisions")
    op.drop_index("ix_import_mapping_decisions_field", table_name="import_mapping_decisions")
    op.drop_index("ix_import_mapping_decisions_header", table_name="import_mapping_decisions")
    op.drop_index("ix_import_mapping_decisions_client_type", table_name="import_mapping_decisions")
    op.drop_table("import_mapping_decisions")
