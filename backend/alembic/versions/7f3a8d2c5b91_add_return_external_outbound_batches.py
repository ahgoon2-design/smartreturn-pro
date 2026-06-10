"""add return external outbound batches

Revision ID: 7f3a8d2c5b91
Revises: 6e2a9c4d1f03
Create Date: 2026-06-05 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7f3a8d2c5b91"
down_revision: str | Sequence[str] | None = "6e2a9c4d1f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "return_external_outbound_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("batch_no", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="CONFIRMED", nullable=False),
        sa.Column(
            "target_type",
            sa.String(length=80),
            server_default="NON_GOOD_EXTERNAL_OUTBOUND",
            nullable=False,
        ),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("confirmed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.UniqueConstraint("batch_no", name="uq_return_external_outbound_batches_batch_no"),
    )
    op.create_index(
        "ix_return_external_outbound_batches_client_created",
        "return_external_outbound_batches",
        ["client_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_return_external_outbound_batches_status_created",
        "return_external_outbound_batches",
        ["status", "created_at"],
        unique=False,
    )
    op.add_column(
        "return_intake_rows",
        sa.Column("external_outbound_batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_return_intake_rows_external_outbound_batch_id",
        "return_intake_rows",
        "return_external_outbound_batches",
        ["external_outbound_batch_id"],
        ["id"],
    )
    op.create_index(
        "ix_return_intake_rows_external_outbound_batch",
        "return_intake_rows",
        ["external_outbound_batch_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_return_intake_rows_external_outbound_batch", table_name="return_intake_rows")
    op.drop_constraint(
        "fk_return_intake_rows_external_outbound_batch_id",
        "return_intake_rows",
        type_="foreignkey",
    )
    op.drop_column("return_intake_rows", "external_outbound_batch_id")
    op.drop_index(
        "ix_return_external_outbound_batches_status_created",
        table_name="return_external_outbound_batches",
    )
    op.drop_index(
        "ix_return_external_outbound_batches_client_created",
        table_name="return_external_outbound_batches",
    )
    op.drop_table("return_external_outbound_batches")
