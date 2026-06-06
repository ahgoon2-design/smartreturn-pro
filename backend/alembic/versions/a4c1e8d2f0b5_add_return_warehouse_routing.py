"""add return warehouse routing

Revision ID: a4c1e8d2f0b5
Revises: 9b2d6f1a4c88
Create Date: 2026-06-06 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a4c1e8d2f0b5"
down_revision: str | Sequence[str] | None = "9b2d6f1a4c88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "return_judgment_warehouse_routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("client_unit_id", sa.Integer(), nullable=True),
        sa.Column("judgment_code", sa.String(length=80), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("active_yn", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["client_unit_id"], ["client_units.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.UniqueConstraint(
            "client_id",
            "client_unit_id",
            "judgment_code",
            "warehouse_id",
            name="uq_return_judgment_warehouse_route",
        ),
    )
    op.create_index(
        "ix_return_judgment_routes_client_judgment",
        "return_judgment_warehouse_routes",
        ["client_id", "judgment_code", "active_yn"],
        unique=False,
    )
    op.create_index(
        "ix_return_judgment_routes_client_unit",
        "return_judgment_warehouse_routes",
        ["client_id", "client_unit_id", "active_yn"],
        unique=False,
    )
    op.create_index(
        "ix_return_judgment_routes_warehouse",
        "return_judgment_warehouse_routes",
        ["warehouse_id"],
        unique=False,
    )

    op.add_column("return_intake_rows", sa.Column("recommended_warehouse_id", sa.Integer(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("final_warehouse_id", sa.Integer(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("warehouse_route_id", sa.Integer(), nullable=True))
    op.add_column("return_intake_rows", sa.Column("warehouse_override_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_return_intake_rows_recommended_warehouse_id",
        "return_intake_rows",
        "warehouses",
        ["recommended_warehouse_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_return_intake_rows_final_warehouse_id",
        "return_intake_rows",
        "warehouses",
        ["final_warehouse_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_return_intake_rows_warehouse_route_id",
        "return_intake_rows",
        "return_judgment_warehouse_routes",
        ["warehouse_route_id"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_recommended_warehouse",
        "return_intake_rows",
        ["recommended_warehouse_id"],
        unique=False,
    )
    op.create_index(
        "ix_return_intake_rows_final_warehouse",
        "return_intake_rows",
        ["final_warehouse_id"],
        unique=False,
    )
    op.create_index(
        "ix_return_intake_rows_warehouse_route",
        "return_intake_rows",
        ["warehouse_route_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_warehouse_route", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_final_warehouse", table_name="return_intake_rows")
    op.drop_index("ix_return_intake_rows_recommended_warehouse", table_name="return_intake_rows")
    op.drop_constraint("fk_return_intake_rows_warehouse_route_id", "return_intake_rows", type_="foreignkey")
    op.drop_constraint("fk_return_intake_rows_final_warehouse_id", "return_intake_rows", type_="foreignkey")
    op.drop_constraint("fk_return_intake_rows_recommended_warehouse_id", "return_intake_rows", type_="foreignkey")
    op.drop_column("return_intake_rows", "warehouse_override_reason")
    op.drop_column("return_intake_rows", "warehouse_route_id")
    op.drop_column("return_intake_rows", "final_warehouse_id")
    op.drop_column("return_intake_rows", "recommended_warehouse_id")

    op.drop_index("ix_return_judgment_routes_warehouse", table_name="return_judgment_warehouse_routes")
    op.drop_index("ix_return_judgment_routes_client_unit", table_name="return_judgment_warehouse_routes")
    op.drop_index("ix_return_judgment_routes_client_judgment", table_name="return_judgment_warehouse_routes")
    op.drop_table("return_judgment_warehouse_routes")
