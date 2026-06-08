from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.import_job import ImportJob, ImportJobFile, ImportJobRow, ImportMappingProfile, ImportValidationError
from app.models.master import Client, Product, ProductBarcode, Warehouse


TEST_PASSWORD = "DummyPass123!"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):
    return compiler.visit_JSON(_type, **kwargs)


def _create_tables(engine) -> None:
    for table in (
        Client.__table__,
        Warehouse.__table__,
        Product.__table__,
        ProductBarcode.__table__,
        ImportJob.__table__,
        ImportJobFile.__table__,
        ImportJobRow.__table__,
        ImportValidationError.__table__,
        ImportMappingProfile.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
    ):
        table.create(bind=engine)


def _create_client(db: Session, code: str = "CLIENT_IMPORT") -> Client:
    client = Client(client_code=code, client_name=f"{code} Name", active_yn=True)
    db.add(client)
    db.commit()
    return client


def _create_user(db: Session, login_id: str) -> User:
    role = Role(role_code="INTERNAL_ADMIN", role_name="INTERNAL_ADMIN", role_type="INTERNAL", active_yn=True)
    db.add(role)
    db.flush()
    user = User(
        login_id=login_id,
        user_name=f"{login_id} user",
        password_hash=hash_password(TEST_PASSWORD),
        active_yn=True,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    for permission_code in ("IMPORT_VIEW", "IMPORT_MANAGE"):
        permission = Permission(permission_code=permission_code, permission_name=permission_code, active_yn=True)
        db.add(permission)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_import_job(client: TestClient, headers: dict[str, str], client_id: int) -> int:
    response = client.post(
        "/api/import-jobs",
        headers=headers,
        json={
            "import_type": "PRODUCT_MASTER",
            "source_type": "PASTE",
            "requested_client_id": client_id,
            "source_name": "pytest-product-master",
        },
    )
    assert response.status_code == 200
    return int(response.json()["data"]["job_id"])


def _save_rows(client: TestClient, headers: dict[str, str], job_id: int, rows: list[dict]) -> None:
    response = client.post(
        f"/api/import-jobs/{job_id}/rows/paste",
        headers=headers,
        json={
            "replace_existing": False,
            "rows": [
                {
                    "row_no": index + 1,
                    "raw_json": row,
                    "source_row_key": f"row-{index + 1}",
                }
                for index, row in enumerate(rows)
            ],
        },
    )
    assert response.status_code == 200


def _client_with_db() -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()

    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), db
    finally:
        app.dependency_overrides.clear()
        db.close()
        engine.dispose()


def test_product_master_fields_and_template_are_available():
    for client, db in _client_with_db():
        _create_client(db)
        _create_user(db, "import_mapper_fields_admin")
        headers = _login(client, "import_mapper_fields_admin")

        source_response = client.get("/api/import-jobs/source-types", headers=headers)
        assert source_response.status_code == 200
        assert "PRODUCT_MASTER" in source_response.json()["data"]["import_types"]
        assert "CSV_FILE" in source_response.json()["data"]["source_types"]

        fields_response = client.get("/api/import-jobs/source-types/PRODUCT_MASTER/fields", headers=headers)
        assert fields_response.status_code == 200
        field_names = {item["field_name"] for item in fields_response.json()["data"]["fields"]}
        assert {"product_code", "product_name", "primary_barcode", "carton_barcode"}.issubset(field_names)

        template_response = client.get("/api/import-jobs/templates/PRODUCT_MASTER", headers=headers)
        assert template_response.status_code == 200
        assert "상품코드" in template_response.text


def test_product_master_auto_map_validate_confirm_and_profile_reuse():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_admin")
        headers = _login(client, "import_mapper_admin")
        rows = [
            {
                "상품코드": "PM-A001",
                "상품명": "자동매핑 상품",
                "대표바코드": "880000000001",
                "추가바코드": "880000000002",
                "카톤바코드": "1880000000001",
                "카톤입수": "12",
                "사용여부": "사용",
                "메모": "테스트",
            }
        ]
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(client, headers, job_id, rows)

        map_response = client.post(
            f"/api/import-jobs/{job_id}/auto-map",
            headers=headers,
            json={"save_profile": True, "profile_name": "상품 기본 매핑"},
        )
        assert map_response.status_code == 200
        mapping_data = map_response.json()["data"]
        assert mapping_data["applied_mapping"]["상품코드"] == "product_code"
        assert mapping_data["mapped_rows"] == 1
        assert db.query(ImportMappingProfile).count() == 1

        row_response = client.get(f"/api/import-jobs/{job_id}/rows", headers=headers)
        assert row_response.status_code == 200
        assert row_response.json()["data"]["items"][0]["row_no"] == 1
        assert row_response.json()["data"]["items"][0]["normalized_json"]["product_code"] == "PM-A001"

        validate_response = client.post(f"/api/import-jobs/{job_id}/validate", headers=headers, json={"force": False})
        assert validate_response.status_code == 200
        assert validate_response.json()["data"]["status"] == "VALIDATED"

        confirm_response = client.post(f"/api/import-jobs/{job_id}/confirm", headers=headers)
        assert confirm_response.status_code == 200
        assert confirm_response.json()["data"]["status"] == "APPLIED"
        product = db.query(Product).filter(Product.client_id == client_row.id, Product.product_code == "PM-A001").one()
        assert product.product_name == "자동매핑 상품"
        assert product.barcode == "880000000001"
        assert db.query(ProductBarcode).filter(ProductBarcode.product_id == product.id).count() == 3

        second_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            second_job_id,
            [
                {
                    "상품코드": "PM-A002",
                    "상품명": "프로필 재사용 상품",
                    "대표바코드": "880000000003",
                    "추가바코드": "",
                    "카톤바코드": "",
                    "카톤입수": "",
                    "사용여부": "사용",
                    "메모": "",
                }
            ],
        )
        second_map_response = client.post(f"/api/import-jobs/{second_job_id}/auto-map", headers=headers, json={})
        assert second_map_response.status_code == 200
        assert any(item["status"] == "PROFILE" for item in second_map_response.json()["data"]["suggestions"])


def test_product_master_error_rows_block_confirm():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_error_admin")
        headers = _login(client, "import_mapper_error_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [
                {
                    "상품코드": "PM-E001",
                    "대표바코드": "880000000011",
                }
            ],
        )
        client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})

        validate_response = client.post(f"/api/import-jobs/{job_id}/validate", headers=headers, json={"force": False})
        assert validate_response.status_code == 200
        assert validate_response.json()["data"]["status"] == "HAS_ERRORS"

        confirm_response = client.post(f"/api/import-jobs/{job_id}/confirm", headers=headers)
        assert confirm_response.status_code == 400
        assert confirm_response.json()["result_code"] == "IMPORT_JOB_CONFIRM_HAS_ERRORS"
