"""create p0 core tables

Revision ID: 974b73ce4bc9
Revises: 
Create Date: 2026-05-27 09:02:58.621584
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql

revision: str = '974b73ce4bc9'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # P0 기반 테이블 생성.
    op.create_table('clients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_code', sa.String(length=80), nullable=False),
    sa.Column('client_name', sa.String(length=255), nullable=False),
    sa.Column('business_no', sa.String(length=50), nullable=True),
    sa.Column('contact_name', sa.String(length=100), nullable=True),
    sa.Column('contact_phone', sa.String(length=50), nullable=True),
    sa.Column('contact_email', sa.String(length=255), nullable=True),
    sa.Column('use_oms', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('use_wms', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('use_returns', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('use_settlement', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_code')
    )
    op.create_index('ix_clients_active_yn', 'clients', ['active_yn'], unique=False)
    op.create_index('ix_clients_client_name', 'clients', ['client_name'], unique=False)
    op.create_table('common_code_groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('group_code', sa.String(length=80), nullable=False),
    sa.Column('group_name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_code')
    )
    op.create_index('ix_common_code_groups_active_yn', 'common_code_groups', ['active_yn'], unique=False)
    op.create_table('permissions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('permission_code', sa.String(length=80), nullable=False),
    sa.Column('permission_name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('permission_code')
    )
    op.create_index('ix_permissions_active_yn', 'permissions', ['active_yn'], unique=False)
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('role_code', sa.String(length=80), nullable=False),
    sa.Column('role_name', sa.String(length=100), nullable=False),
    sa.Column('role_type', sa.String(length=50), nullable=False),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('role_code')
    )
    op.create_index('ix_roles_active_yn', 'roles', ['active_yn'], unique=False)
    op.create_index('ix_roles_role_type', 'roles', ['role_type'], unique=False)
    op.create_table('warehouses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('warehouse_code', sa.String(length=80), nullable=False),
    sa.Column('warehouse_name', sa.String(length=255), nullable=False),
    sa.Column('warehouse_type', sa.String(length=50), nullable=True),
    sa.Column('address', sa.String(length=500), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('warehouse_code')
    )
    op.create_index('ix_warehouses_active_yn', 'warehouses', ['active_yn'], unique=False)
    op.create_index('ix_warehouses_warehouse_type', 'warehouses', ['warehouse_type'], unique=False)
    op.create_table('client_warehouse_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('usage_type', sa.String(length=80), nullable=False),
    sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id', 'warehouse_id', 'usage_type', name='uq_client_warehouse_usage')
    )
    op.create_index('ix_client_warehouse_settings_client_id', 'client_warehouse_settings', ['client_id'], unique=False)
    op.create_index('ix_client_warehouse_settings_client_usage', 'client_warehouse_settings', ['client_id', 'usage_type'], unique=False)
    op.create_index('ix_client_warehouse_settings_warehouse_id', 'client_warehouse_settings', ['warehouse_id'], unique=False)
    op.create_table('common_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.Column('code_value', sa.String(length=80), nullable=False),
    sa.Column('code_name', sa.String(length=100), nullable=False),
    sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('system_yn', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('locked_yn', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['common_code_groups.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'code_value', name='uq_common_codes_group_value')
    )
    op.create_index('ix_common_codes_group_active', 'common_codes', ['group_id', 'active_yn'], unique=False)
    op.create_index('ix_common_codes_sort_order', 'common_codes', ['sort_order'], unique=False)
    op.create_table('locations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('location_code', sa.String(length=80), nullable=False),
    sa.Column('location_name', sa.String(length=255), nullable=False),
    sa.Column('location_type', sa.String(length=50), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('warehouse_id', 'location_code', name='uq_locations_warehouse_code')
    )
    op.create_index('ix_locations_active_yn', 'locations', ['active_yn'], unique=False)
    op.create_index('ix_locations_warehouse_id', 'locations', ['warehouse_id'], unique=False)
    op.create_table('products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('product_code', sa.String(length=80), nullable=False),
    sa.Column('product_name', sa.String(length=255), nullable=False),
    sa.Column('barcode', sa.String(length=100), nullable=True),
    sa.Column('specification', sa.String(length=255), nullable=True),
    sa.Column('unit_name', sa.String(length=50), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id', 'product_code', name='uq_products_client_product_code')
    )
    op.create_index('ix_products_client_active', 'products', ['client_id', 'active_yn'], unique=False)
    op.create_index('ix_products_client_barcode', 'products', ['client_id', 'barcode'], unique=False)
    op.create_index('ix_products_client_product_name', 'products', ['client_id', 'product_name'], unique=False)
    op.create_table('role_permissions',
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('permission_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permissions_role_permission')
    )
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'], unique=False)
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('login_id', sa.String(length=80), nullable=False),
    sa.Column('user_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('default_warehouse_id', sa.Integer(), nullable=True),
    sa.Column('must_change_password', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['default_warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('login_id')
    )
    op.create_index('ix_users_active_yn', 'users', ['active_yn'], unique=False)
    op.create_index('ix_users_client_id', 'users', ['client_id'], unique=False)
    op.create_table('auth_login_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('login_id', sa.String(length=80), nullable=False),
    sa.Column('result', sa.String(length=50), nullable=False),
    sa.Column('failure_reason', sa.String(length=255), nullable=True),
    sa.Column('ip_address', sa.String(length=80), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_auth_login_logs_login_created', 'auth_login_logs', ['login_id', 'created_at'], unique=False)
    op.create_index('ix_auth_login_logs_result_created', 'auth_login_logs', ['result', 'created_at'], unique=False)
    op.create_index('ix_auth_login_logs_user_created', 'auth_login_logs', ['user_id', 'created_at'], unique=False)
    op.create_table('current_inventory',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('location_id', sa.Integer(), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('stock_status', sa.String(length=50), nullable=False),
    sa.Column('qty_on_hand', sa.Integer(), server_default='0', nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id', 'warehouse_id', 'location_id', 'product_id', 'stock_status', name='uq_current_inventory_scope')
    )
    op.create_index('ix_current_inventory_client_product', 'current_inventory', ['client_id', 'product_id'], unique=False)
    op.create_index('ix_current_inventory_stock_scope', 'current_inventory', ['client_id', 'warehouse_id', 'product_id', 'stock_status'], unique=False)
    op.create_index('ix_current_inventory_warehouse_product', 'current_inventory', ['warehouse_id', 'product_id'], unique=False)
    op.create_table('import_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('import_type', sa.String(length=80), nullable=False),
    sa.Column('source_type', sa.String(length=80), nullable=False),
    sa.Column('source_name', sa.String(length=255), nullable=True),
    sa.Column('requested_client_id', sa.Integer(), nullable=True),
    sa.Column('requested_warehouse_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('total_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('parsed_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('valid_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('invalid_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('inserted_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('updated_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('skipped_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_rows', sa.Integer(), server_default='0', nullable=False),
    sa.Column('progress_percent', sa.Integer(), server_default='0', nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=True),
    sa.Column('worksheet_name', sa.String(length=255), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['requested_client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['requested_warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_import_jobs_requested_client_created', 'import_jobs', ['requested_client_id', 'created_at'], unique=False)
    op.create_index('ix_import_jobs_status_created', 'import_jobs', ['status', 'created_at'], unique=False)
    op.create_index('ix_import_jobs_type_created', 'import_jobs', ['import_type', 'created_at'], unique=False)
    op.create_table('inventory_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_no', sa.String(length=80), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('location_id', sa.Integer(), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('product_code', sa.String(length=80), nullable=True),
    sa.Column('stock_status', sa.String(length=50), nullable=False),
    sa.Column('event_type', sa.String(length=80), nullable=False),
    sa.Column('qty_delta', sa.Integer(), nullable=False),
    sa.Column('source_type', sa.String(length=80), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('source_line_id', sa.Integer(), nullable=True),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    sa.Column('reverse_event_id', sa.Integer(), nullable=True),
    sa.Column('event_reason', sa.String(length=255), nullable=True),
    sa.Column('memo', sa.Text(), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['reverse_event_id'], ['inventory_events.id'], ),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_no', name='uq_inventory_events_event_no'),
    sa.UniqueConstraint('idempotency_key', name='uq_inventory_events_idempotency_key')
    )
    op.create_index('ix_inventory_events_client_product_created', 'inventory_events', ['client_id', 'product_id', 'created_at'], unique=False)
    op.create_index('ix_inventory_events_reverse_event_id', 'inventory_events', ['reverse_event_id'], unique=False)
    op.create_index('ix_inventory_events_source', 'inventory_events', ['source_type', 'source_id'], unique=False)
    op.create_index('ix_inventory_events_stock_scope', 'inventory_events', ['client_id', 'warehouse_id', 'product_id', 'stock_status'], unique=False)
    op.create_table('product_barcodes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('barcode', sa.String(length=100), nullable=False),
    sa.Column('barcode_norm', sa.String(length=100), nullable=False),
    sa.Column('barcode_type', sa.String(length=50), nullable=False),
    sa.Column('unit_qty', sa.Integer(), server_default='1', nullable=False),
    sa.Column('active_yn', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('remarks', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('unit_qty >= 1', name='ck_product_barcodes_unit_qty_positive'),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id', 'barcode_norm', name='uq_product_barcodes_client_barcode_norm')
    )
    op.create_index('ix_product_barcodes_client_active', 'product_barcodes', ['client_id', 'active_yn'], unique=False)
    op.create_index('ix_product_barcodes_client_product', 'product_barcodes', ['client_id', 'product_id'], unique=False)
    op.create_index('ix_product_barcodes_client_type', 'product_barcodes', ['client_id', 'barcode_type'], unique=False)
    op.create_table('user_roles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'role_id'),
    sa.UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role')
    )
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_table('import_job_files',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('stored_file_name', sa.String(length=255), nullable=True),
    sa.Column('relative_path', sa.String(length=500), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=True),
    sa.Column('size_bytes', sa.Integer(), nullable=True),
    sa.Column('uploaded_by', sa.Integer(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['import_jobs.id'], ),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_import_job_files_job_id', 'import_job_files', ['job_id'], unique=False)
    op.create_index('ix_import_job_files_uploaded_at', 'import_job_files', ['uploaded_at'], unique=False)
    op.create_table('import_job_rows',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('row_no', sa.Integer(), nullable=False),
    sa.Column('source_row_key', sa.String(length=255), nullable=True),
    sa.Column('row_hash', sa.String(length=128), nullable=True),
    sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('normalized_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('validation_status', sa.String(length=50), nullable=False),
    sa.Column('validation_message', sa.Text(), nullable=True),
    sa.Column('target_action', sa.String(length=50), nullable=True),
    sa.Column('target_table', sa.String(length=100), nullable=True),
    sa.Column('target_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
    sa.ForeignKeyConstraint(['job_id'], ['import_jobs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('job_id', 'row_no', name='uq_import_job_rows_job_row_no')
    )
    op.create_index('ix_import_job_rows_job_row_no', 'import_job_rows', ['job_id', 'row_no'], unique=False)
    op.create_index('ix_import_job_rows_job_validation', 'import_job_rows', ['job_id', 'validation_status'], unique=False)
    op.create_index('ix_import_job_rows_row_hash', 'import_job_rows', ['row_hash'], unique=False)
    op.create_index('ix_import_job_rows_source_row_key', 'import_job_rows', ['source_row_key'], unique=False)
    op.create_table('import_validation_errors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('row_id', sa.Integer(), nullable=True),
    sa.Column('row_no', sa.Integer(), nullable=True),
    sa.Column('field_name', sa.String(length=100), nullable=True),
    sa.Column('raw_value', sa.Text(), nullable=True),
    sa.Column('error_code', sa.String(length=80), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=False),
    sa.Column('severity', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['import_jobs.id'], ),
    sa.ForeignKeyConstraint(['row_id'], ['import_job_rows.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_import_validation_errors_job_id', 'import_validation_errors', ['job_id'], unique=False)
    op.create_index('ix_import_validation_errors_job_severity', 'import_validation_errors', ['job_id', 'severity'], unique=False)
    op.create_index('ix_import_validation_errors_row_id', 'import_validation_errors', ['row_id'], unique=False)
    op.create_index('ix_import_validation_errors_row_no', 'import_validation_errors', ['row_no'], unique=False)
    # P0 기반 테이블 생성 끝.


def downgrade() -> None:
    # 이번 기준선 migration은 DROP 금지 원칙에 따라 downgrade에서 테이블을 삭제하지 않는다.
    pass
