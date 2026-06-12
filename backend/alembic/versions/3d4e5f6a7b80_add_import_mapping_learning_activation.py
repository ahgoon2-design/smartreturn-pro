"""Add import mapping learning activation controls.

Revision ID: 3d4e5f6a7b80
Revises: 2c3d4e5f6a70, a7b8c9d0e1f2
Create Date: 2026-06-12
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "3d4e5f6a7b80"
down_revision: str | Sequence[str] | None = ("2c3d4e5f6a70", "a7b8c9d0e1f2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("import_mapping_profiles", sa.Column("deactivated_by", sa.Integer(), nullable=True))
    op.add_column("import_mapping_profiles", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("import_mapping_profiles", sa.Column("deactivate_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_import_mapping_profiles_deactivated_by_users",
        "import_mapping_profiles",
        "users",
        ["deactivated_by"],
        ["id"],
    )

    op.add_column(
        "import_mapping_decisions",
        sa.Column("active_yn", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column("import_mapping_decisions", sa.Column("deactivated_by", sa.Integer(), nullable=True))
    op.add_column("import_mapping_decisions", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("import_mapping_decisions", sa.Column("deactivate_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_import_mapping_decisions_deactivated_by_users",
        "import_mapping_decisions",
        "users",
        ["deactivated_by"],
        ["id"],
    )
    op.create_index(
        "ix_import_mapping_decisions_active",
        "import_mapping_decisions",
        ["active_yn"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_import_mapping_decisions_active", table_name="import_mapping_decisions")
    op.drop_constraint(
        "fk_import_mapping_decisions_deactivated_by_users",
        "import_mapping_decisions",
        type_="foreignkey",
    )
    op.drop_column("import_mapping_decisions", "deactivate_reason")
    op.drop_column("import_mapping_decisions", "deactivated_at")
    op.drop_column("import_mapping_decisions", "deactivated_by")
    op.drop_column("import_mapping_decisions", "active_yn")

    op.drop_constraint(
        "fk_import_mapping_profiles_deactivated_by_users",
        "import_mapping_profiles",
        type_="foreignkey",
    )
    op.drop_column("import_mapping_profiles", "deactivate_reason")
    op.drop_column("import_mapping_profiles", "deactivated_at")
    op.drop_column("import_mapping_profiles", "deactivated_by")
