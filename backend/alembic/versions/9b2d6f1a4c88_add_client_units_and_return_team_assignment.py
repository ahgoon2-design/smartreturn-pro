"""add client units and return team assignment

Revision ID: 9b2d6f1a4c88
Revises: 7f3a8d2c5b91
Create Date: 2026-06-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9b2d6f1a4c88"
down_revision: str | Sequence[str] | None = "7f3a8d2c5b91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("unit_code", sa.String(length=80), nullable=False),
        sa.Column("unit_name", sa.String(length=255), nullable=False),
        sa.Column("unit_type", sa.String(length=50), nullable=True),
        sa.Column("default_warehouse_id", sa.Integer(), nullable=True),
        sa.Column("return_warehouse_id", sa.Integer(), nullable=True),
        sa.Column("active_yn", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["default_warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["return_warehouse_id"], ["warehouses.id"]),
        sa.UniqueConstraint("client_id", "unit_code", name="uq_client_units_client_unit_code"),
    )
    op.create_index("ix_client_units_client_active", "client_units", ["client_id", "active_yn"], unique=False)
    op.create_index("ix_client_units_default_warehouse", "client_units", ["default_warehouse_id"], unique=False)
    op.create_index("ix_client_units_return_warehouse", "client_units", ["return_warehouse_id"], unique=False)

    op.add_column("return_intake_batches", sa.Column("client_unit_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_batches_client_unit_id",
        "return_intake_batches",
        "client_units",
        ["client_unit_id"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_batches_client_unit",
        "return_intake_batches",
        ["client_id", "client_unit_id"],
        unique=False,
    )

    op.add_column("return_intake_rows", sa.Column("client_unit_id", sa.Integer(), nullable=True))
    op.add_column(
        "return_intake_rows",
        sa.Column("team_assign_status", sa.String(length=50), server_default="NOT_REQUIRED", nullable=False),
    )
    op.add_column("return_intake_rows", sa.Column("client_unit_assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("return_intake_rows", sa.Column("client_unit_assigned_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_rows_client_unit_id",
        "return_intake_rows",
        "client_units",
        ["client_unit_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_return_intake_rows_client_unit_assigned_by",
        "return_intake_rows",
        "users",
        ["client_unit_assigned_by"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_client_unit",
        "return_intake_rows",
        ["client_id", "client_unit_id"],
        unique=False,
    )
    op.create_index(
        "ix_return_intake_rows_team_assignment",
        "return_intake_rows",
        ["client_id", "team_assign_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_team_assignment", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_client_unit", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_client_unit_assigned_by", "return_intake_rows", type_="foreignkey")
    op.drop_constraint("fk_return_intake_rows_client_unit_id", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "client_unit_assigned_by")
    op.drop_column("return_intake_rows", "client_unit_assigned_at")
    op.drop_column("return_intake_rows", "team_assign_status")
    op.drop_column("return_intake_rows", "client_unit_id")

    op.drop_index("ix_return_intake_batches_client_unit", table_name="return_intake_batches")
    op.drop_constraint("fk_return_intake_batches_client_unit_id", "return_intake_batches", type_="foreignkey")
    op.drop_column("return_intake_batches", "client_unit_id")

    op.drop_index("ix_client_units_return_warehouse", table_name="client_units")
    op.drop_index("ix_client_units_default_warehouse", table_name="client_units")
    op.drop_index("ix_client_units_client_active", table_name="client_units")
    op.drop_table("client_units")
