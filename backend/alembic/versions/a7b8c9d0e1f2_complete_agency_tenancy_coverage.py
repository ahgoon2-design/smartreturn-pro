"""Complete agency tenancy coverage.

Revision ID: a7b8c9d0e1f2
Revises: f0a1b2c3d456
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f0a1b2c3d456"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CLIENT_SCOPED_TABLES = (
    "client_units",
    "client_warehouse_settings",
    "return_judgment_warehouse_routes",
    "products",
    "product_barcodes",
    "return_external_outbound_batches",
    "return_processing_attachments",
)


def _add_agency_column(table_name: str) -> None:
    op.add_column(table_name, sa.Column("agency_id", sa.Integer(), nullable=True))
    op.create_foreign_key(f"fk_{table_name}_agency_id", table_name, "agencies", ["agency_id"], ["id"])


def _backfill_from_client(connection, table_name: str, client_column: str = "client_id") -> None:
    connection.execute(
        sa.text(
            f"""
            update {table_name}
               set agency_id = clients.agency_id
              from clients
             where {table_name}.{client_column} = clients.id
               and {table_name}.agency_id is null
            """
        )
    )


def upgrade() -> None:
    connection = op.get_bind()

    for table_name in CLIENT_SCOPED_TABLES:
        _add_agency_column(table_name)
        _backfill_from_client(connection, table_name)

    op.add_column("auth_login_logs", sa.Column("agency_id", sa.Integer(), nullable=True))
    op.add_column("auth_login_logs", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_auth_login_logs_agency_id", "auth_login_logs", "agencies", ["agency_id"], ["id"])
    op.create_foreign_key("fk_auth_login_logs_client_id", "auth_login_logs", "clients", ["client_id"], ["id"])
    connection.execute(
        sa.text(
            """
            update auth_login_logs
               set agency_id = users.agency_id,
                   client_id = users.client_id
              from users
             where auth_login_logs.user_id = users.id
               and (auth_login_logs.agency_id is null or auth_login_logs.client_id is null)
            """
        )
    )

    op.create_index("ix_client_units_agency_client", "client_units", ["agency_id", "client_id"], unique=False)
    op.create_index(
        "ix_client_warehouse_settings_agency_client",
        "client_warehouse_settings",
        ["agency_id", "client_id"],
        unique=False,
    )
    op.create_index(
        "ix_return_judgment_routes_agency_client",
        "return_judgment_warehouse_routes",
        ["agency_id", "client_id"],
        unique=False,
    )
    op.create_index("ix_products_agency_client", "products", ["agency_id", "client_id"], unique=False)
    op.create_index("ix_product_barcodes_agency_client", "product_barcodes", ["agency_id", "client_id"], unique=False)
    op.create_index(
        "ix_return_external_outbound_batches_agency_client_created",
        "return_external_outbound_batches",
        ["agency_id", "client_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_return_processing_attachments_agency_client",
        "return_processing_attachments",
        ["agency_id", "client_id"],
        unique=False,
    )
    op.create_index("ix_auth_login_logs_agency_created", "auth_login_logs", ["agency_id", "created_at"], unique=False)
    op.create_index("ix_auth_login_logs_client_created", "auth_login_logs", ["client_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_login_logs_client_created", table_name="auth_login_logs")
    op.drop_index("ix_auth_login_logs_agency_created", table_name="auth_login_logs")
    op.drop_index("ix_return_processing_attachments_agency_client", table_name="return_processing_attachments")
    op.drop_index(
        "ix_return_external_outbound_batches_agency_client_created",
        table_name="return_external_outbound_batches",
    )
    op.drop_index("ix_product_barcodes_agency_client", table_name="product_barcodes")
    op.drop_index("ix_products_agency_client", table_name="products")
    op.drop_index("ix_return_judgment_routes_agency_client", table_name="return_judgment_warehouse_routes")
    op.drop_index("ix_client_warehouse_settings_agency_client", table_name="client_warehouse_settings")
    op.drop_index("ix_client_units_agency_client", table_name="client_units")

    op.drop_constraint("fk_auth_login_logs_client_id", "auth_login_logs", type_="foreignkey")
    op.drop_constraint("fk_auth_login_logs_agency_id", "auth_login_logs", type_="foreignkey")
    op.drop_column("auth_login_logs", "client_id")
    op.drop_column("auth_login_logs", "agency_id")

    for table_name in reversed(CLIENT_SCOPED_TABLES):
        op.drop_constraint(f"fk_{table_name}_agency_id", table_name, type_="foreignkey")
        op.drop_column(table_name, "agency_id")
