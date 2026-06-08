"""Add import mapping profiles.

Revision ID: b6c7d8e9f012
Revises: a4c1e8d2f0b5
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b6c7d8e9f012"
down_revision: str | Sequence[str] | None = "a4c1e8d2f0b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_mapping_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("import_type", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("profile_name", sa.String(length=120), nullable=False),
        sa.Column("header_signature", sa.String(length=500), nullable=False),
        sa.Column("mapping_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active_yn", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id",
            "import_type",
            "source_type",
            "profile_name",
            name="uq_import_mapping_profiles_client_type_name",
        ),
    )
    op.create_index(
        "ix_import_mapping_profiles_client_type",
        "import_mapping_profiles",
        ["client_id", "import_type", "source_type"],
        unique=False,
    )
    op.create_index(
        "ix_import_mapping_profiles_signature",
        "import_mapping_profiles",
        ["header_signature"],
        unique=False,
    )
    op.create_index(
        "ix_import_mapping_profiles_active",
        "import_mapping_profiles",
        ["active_yn"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_import_mapping_profiles_active", table_name="import_mapping_profiles")
    op.drop_index("ix_import_mapping_profiles_signature", table_name="import_mapping_profiles")
    op.drop_index("ix_import_mapping_profiles_client_type", table_name="import_mapping_profiles")
    op.drop_table("import_mapping_profiles")
