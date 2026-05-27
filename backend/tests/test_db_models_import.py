from app.db.base import Base
import app.models  # noqa: F401


P0_TABLES = {
    "auth_login_logs",
    "client_warehouse_settings",
    "clients",
    "common_code_groups",
    "common_codes",
    "current_inventory",
    "import_job_files",
    "import_job_rows",
    "import_jobs",
    "import_validation_errors",
    "inventory_events",
    "locations",
    "permissions",
    "product_barcodes",
    "products",
    "role_permissions",
    "roles",
    "user_roles",
    "users",
    "warehouses",
}

NON_P0_TABLES = {
    "return_expected_batches",
    "return_expected_rows",
    "return_receipts",
    "return_receipt_items",
    "inbound_tasks",
    "outbound_tasks",
    "settlement_headers",
}


def test_p0_models_are_registered_without_db_connection() -> None:
    table_names = set(Base.metadata.tables)

    assert P0_TABLES.issubset(table_names)
    assert table_names.isdisjoint(NON_P0_TABLES)
