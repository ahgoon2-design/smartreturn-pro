"""Add agency tenancy layer.

Revision ID: 2c3d4e5f6a70
Revises: 1b2c3d4e5f60
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "2c3d4e5f6a70"
down_revision: str | Sequence[str] | None = "1b2c3d4e5f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_AGENCY_CODE = "DEFAULT_DIRECT"


def _default_agency_id(connection) -> int:
    row = connection.execute(
        sa.text("select id from agencies where agency_code = :agency_code"),
        {"agency_code": DEFAULT_AGENCY_CODE},
    ).first()
    if row is not None:
        return int(row[0])
    row = connection.execute(
        sa.text(
            """
            insert into agencies (agency_code, agency_name, agency_type, active_yn, remarks)
            values (:agency_code, :agency_name, :agency_type, true, :remarks)
            returning id
            """
        ),
        {
            "agency_code": DEFAULT_AGENCY_CODE,
            "agency_name": "본사 직영",
            "agency_type": "DIRECT",
            "remarks": "기존 고객사/운영 데이터를 묶는 기본 agency입니다.",
        },
    ).first()
    return int(row[0])


def upgrade() -> None:
    op.create_table(
        "agencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agency_code", sa.String(length=80), nullable=False),
        sa.Column("agency_name", sa.String(length=255), nullable=False),
        sa.Column("agency_type", sa.String(length=80), nullable=True),
        sa.Column("active_yn", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agency_code"),
    )
    op.create_index("ix_agencies_active_yn", "agencies", ["active_yn"], unique=False)
    op.create_index("ix_agencies_agency_name", "agencies", ["agency_name"], unique=False)

    connection = op.get_bind()
    default_agency_id = _default_agency_id(connection)

    op.add_column("clients", sa.Column("agency_id", sa.Integer(), nullable=True))
    op.create_index("ix_clients_agency_id", "clients", ["agency_id"], unique=False)
    op.create_foreign_key("fk_clients_agency_id", "clients", "agencies", ["agency_id"], ["id"])
    connection.execute(sa.text("update clients set agency_id = :agency_id where agency_id is null"), {"agency_id": default_agency_id})

    op.add_column("users", sa.Column("agency_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_agency_id", "users", ["agency_id"], unique=False)
    op.create_foreign_key("fk_users_agency_id", "users", "agencies", ["agency_id"], ["id"])
    connection.execute(
        sa.text(
            """
            update users
               set agency_id = clients.agency_id
              from clients
             where users.client_id = clients.id
               and users.agency_id is null
            """
        )
    )
    connection.execute(sa.text("update users set agency_id = :agency_id where agency_id is null"), {"agency_id": default_agency_id})

    connection.execute(
        sa.text(
            """
            insert into roles (role_code, role_name, role_type, active_yn)
            values ('AGENCY_ADMIN', '대리점 관리자', 'AGENCY', true)
            on conflict (role_code) do update
                set role_name = excluded.role_name,
                    role_type = excluded.role_type,
                    active_yn = true
            """
        )
    )

    client_tables = {
        "return_intake_batches": "client_id",
        "return_intake_rows": "client_id",
        "channel_accounts": "client_id",
        "channel_return_candidates": "client_id",
        "product_channel_mappings": "client_id",
        "inventory_events": "client_id",
        "current_inventory": "client_id",
        "import_jobs": "requested_client_id",
        "import_job_rows": "client_id",
    }
    for table_name, client_column in client_tables.items():
        op.add_column(table_name, sa.Column("agency_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table_name}_agency_id", table_name, "agencies", ["agency_id"], ["id"])
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
        connection.execute(
            sa.text(f"update {table_name} set agency_id = :agency_id where agency_id is null"),
            {"agency_id": default_agency_id},
        )

    account_tables = ("channel_sync_jobs", "channel_raw_events")
    for table_name in account_tables:
        op.add_column(table_name, sa.Column("agency_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table_name}_agency_id", table_name, "agencies", ["agency_id"], ["id"])
        connection.execute(
            sa.text(
                f"""
                update {table_name}
                   set agency_id = channel_accounts.agency_id
                  from channel_accounts
                 where {table_name}.channel_account_id = channel_accounts.id
                   and {table_name}.agency_id is null
                """
            )
        )
        connection.execute(
            sa.text(f"update {table_name} set agency_id = :agency_id where agency_id is null"),
            {"agency_id": default_agency_id},
        )

    op.create_index("ix_return_intake_batches_agency_client_created", "return_intake_batches", ["agency_id", "client_id", "created_at"], unique=False)
    op.create_index("ix_return_intake_rows_agency_tracking", "return_intake_rows", ["agency_id", "client_id", "return_tracking_no"], unique=False)
    op.create_index("ix_return_intake_rows_agency_status_created", "return_intake_rows", ["agency_id", "client_id", "status", "created_at"], unique=False)
    op.create_index("ix_channel_accounts_agency_client", "channel_accounts", ["agency_id", "client_id"], unique=False)
    op.create_index("ix_channel_sync_jobs_agency_created", "channel_sync_jobs", ["agency_id", "created_at"], unique=False)
    op.create_index("ix_channel_raw_events_agency_collected", "channel_raw_events", ["agency_id", "collected_at"], unique=False)
    op.create_index("ix_channel_return_candidates_agency_status", "channel_return_candidates", ["agency_id", "client_id", "match_status", "created_at"], unique=False)
    op.create_index("ix_product_channel_mappings_agency_channel", "product_channel_mappings", ["agency_id", "client_id", "channel_type"], unique=False)
    op.create_index("ix_inventory_events_agency_client_created", "inventory_events", ["agency_id", "client_id", "created_at"], unique=False)
    op.create_index("ix_current_inventory_agency_scope", "current_inventory", ["agency_id", "client_id", "warehouse_id", "product_id"], unique=False)
    op.create_index("ix_import_jobs_agency_client_type_created", "import_jobs", ["agency_id", "requested_client_id", "source_type", "created_at"], unique=False)
    op.create_index("ix_import_job_rows_agency_client_created", "import_job_rows", ["agency_id", "client_id", "created_at"], unique=False)


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_import_job_rows_agency_client_created", "import_job_rows"),
        ("ix_import_jobs_agency_client_type_created", "import_jobs"),
        ("ix_current_inventory_agency_scope", "current_inventory"),
        ("ix_inventory_events_agency_client_created", "inventory_events"),
        ("ix_product_channel_mappings_agency_channel", "product_channel_mappings"),
        ("ix_channel_return_candidates_agency_status", "channel_return_candidates"),
        ("ix_channel_raw_events_agency_collected", "channel_raw_events"),
        ("ix_channel_sync_jobs_agency_created", "channel_sync_jobs"),
        ("ix_channel_accounts_agency_client", "channel_accounts"),
        ("ix_return_intake_rows_agency_status_created", "return_intake_rows"),
        ("ix_return_intake_rows_agency_tracking", "return_intake_rows"),
        ("ix_return_intake_batches_agency_client_created", "return_intake_batches"),
    ):
        op.drop_index(index_name, table_name=table_name)

    for table_name in (
        "channel_raw_events",
        "channel_sync_jobs",
        "import_job_rows",
        "import_jobs",
        "current_inventory",
        "inventory_events",
        "product_channel_mappings",
        "channel_return_candidates",
        "channel_accounts",
        "return_intake_rows",
        "return_intake_batches",
    ):
        op.drop_constraint(f"fk_{table_name}_agency_id", table_name, type_="foreignkey")
        op.drop_column(table_name, "agency_id")

    op.drop_constraint("fk_users_agency_id", "users", type_="foreignkey")
    op.drop_index("ix_users_agency_id", table_name="users")
    op.drop_column("users", "agency_id")

    op.drop_constraint("fk_clients_agency_id", "clients", type_="foreignkey")
    op.drop_index("ix_clients_agency_id", table_name="clients")
    op.drop_column("clients", "agency_id")

    op.drop_index("ix_agencies_agency_name", table_name="agencies")
    op.drop_index("ix_agencies_active_yn", table_name="agencies")
    op.drop_table("agencies")
