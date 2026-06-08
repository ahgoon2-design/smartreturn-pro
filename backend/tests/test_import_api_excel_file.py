from collections.abc import Generator
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
import html

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.import_job import ImportJob, ImportJobFile, ImportJobRow, ImportValidationError
from app.models.master import Client, Warehouse


TEST_PASSWORD = "DummyPass123!"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):
    return compiler.visit_JSON(_type, **kwargs)


def _xlsx_bytes(headers: list[str], rows: list[list[object]], *, sheet_name: str = "Sheet1", leading_rows: list[list[object]] | None = None) -> bytes:
    def column_name(index: int) -> str:
        value = ""
        index += 1
        while index:
            index, remainder = divmod(index - 1, 26)
            value = chr(65 + remainder) + value
        return value

    def cell(ref: str, value: object) -> str:
        return (
            f'<c r="{ref}" t="inlineStr"><is><t>'
            f"{html.escape(str(value))}"
            f"</t></is></c>"
        )

    worksheet_rows = []
    all_rows = [*(leading_rows or []), headers, *rows]
    for row_index, row_values in enumerate(all_rows, start=1):
        cells = "".join(cell(f"{column_name(col_index)}{row_index}", value) for col_index, value in enumerate(row_values))
        worksheet_rows.append(f'<row r="{row_index}">{cells}</row>')

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        )
        zip_file.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        zip_file.writestr(
            "xl/workbook.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="{html.escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        zip_file.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        zip_file.writestr(
            "xl/worksheets/sheet1.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(worksheet_rows)}</sheetData>
</worksheet>""",
        )
    return buffer.getvalue()


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def _create_client(db: Session, code: str = "CLIENT_A") -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=True)
    db.add(row)
    db.commit()
    return row


def _create_user(
    db: Session,
    *,
    login_id: str,
    role_code: str,
    permissions: list[str] | None = None,
    client_id: int | None = None,
) -> User:
    role_type = "INTERNAL" if role_code in {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"} else "CLIENT"
    role = db.query(Role).filter(Role.role_code == role_code).one_or_none()
    if role is None:
        role = Role(role_code=role_code, role_name=role_code, role_type=role_type, active_yn=True)
        db.add(role)
        db.flush()

    user = User(
        login_id=login_id,
        user_name=f"{login_id} user",
        password_hash=hash_password(TEST_PASSWORD),
        client_id=client_id,
        active_yn=True,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))

    for permission_code in permissions or []:
        permission = db.query(Permission).filter(Permission.permission_code == permission_code).one_or_none()
        if permission is None:
            permission = Permission(permission_code=permission_code, permission_name=permission_code, active_yn=True)
            db.add(permission)
            db.flush()
        exists = (
            db.query(RolePermission)
            .filter(RolePermission.role_id == role.id, RolePermission.permission_id == permission.id)
            .one_or_none()
        )
        if exists is None:
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _admin_headers(client: TestClient, db: Session, login_id: str = "excel_admin") -> dict[str, str]:
    _create_user(
        db,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_MANAGE", "IMPORT_VIEW"],
    )
    return _login(client, login_id)


def _create_job(
    db: Session,
    *,
    import_type: str = "PRODUCT_MASTER",
    source_type: str = "EXCEL_FILE",
    status: str = "DRAFT",
    client_row: Client | None = None,
    created_by: User | None = None,
) -> ImportJob:
    client_row = client_row or _create_client(db)
    created_by = created_by or _create_user(
        db,
        login_id=f"excel_owner_{import_type.lower()}_{source_type.lower()}",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = ImportJob(
        import_type=import_type,
        source_type=source_type,
        source_name="excel source",
        requested_client_id=client_row.id,
        requested_warehouse_id=None,
        status=status,
        total_rows=0,
        parsed_rows=0,
        valid_rows=0,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=0,
        file_name=None,
        worksheet_name=None,
        message=None,
        raw_json=None,
        created_by=created_by.id,
    )
    db.add(job)
    db.commit()
    return job


def _upload(
    client: TestClient,
    job_id: int,
    headers: dict[str, str],
    content: bytes | None = None,
    file_name: str = "products.xlsx",
):
    content = content if content is not None else _xlsx_bytes(
        ["product_code", "product_name", "barcode"],
        [["P001", "Product", "B001"]],
    )
    return client.post(
        f"/api/import-jobs/{job_id}/files/excel",
        files={"file": (file_name, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Client.__table__,
        Warehouse.__table__,
        ImportJob.__table__,
        ImportJobFile.__table__,
        ImportJobRow.__table__,
        ImportValidationError.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
    ):
        table.create(bind=engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_excel_upload_requires_auth(client: TestClient, db_session: Session):
    job = _create_job(db_session)

    response = _upload(client, job.id, headers={})

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_excel_upload_saves_rows_and_preserves_excel_row_numbers(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_upload_admin")
    content = _xlsx_bytes(
        ["상품코드", "상품명", "바코드"],
        [["P001", "Product 1", "B001"], ["P002", "Product 2", "B002"]],
        sheet_name="Products",
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    body = response.json()
    assert body["result_code"] == "IMPORT_JOB_EXCEL_FILE_UPLOADED"
    assert body["data"]["status"] == "READY_TO_VALIDATE"
    assert body["data"]["saved_row_count"] == 2
    assert body["data"]["headers"] == ["상품코드", "상품명", "바코드"]
    assert body["data"]["mapped_headers"] == {
        "product_code": "상품코드",
        "product_name": "상품명",
        "primary_barcode": "바코드",
    }
    assert body["data"]["unmapped_headers"] == []
    assert body["data"]["worksheet_name"] == "Products"

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    rows = rows_response.json()["data"]["items"]
    assert [row["row_no"] for row in rows] == [2, 3]
    assert rows[0]["raw_json"]["상품코드"] == "P001"
    assert rows[0]["normalized_json"]["product_code"] == "P001"
    assert db_session.query(ImportJobFile).filter(ImportJobFile.job_id == job.id).count() == 1
    _assert_no_sensitive_values(body)


def test_excel_upload_skips_empty_and_noise_rows_without_errors(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_row_filter_admin")
    content = _xlsx_bytes(
        ["상품코드", "상품명", "대표바코드", "메모"],
        [
            ["", "", "", ""],
            ["-", "--", "없음", ""],
            ["합계", "", "", "주의사항"],
            ["", "", "", "메모만 있는 행"],
            ["P100", "실제 상품", "B100", ""],
        ],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["saved_row_count"] == 1
    assert data["skipped_empty_rows"] == 1
    assert data["skipped_noise_rows"] == 3

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    rows = rows_response.json()["data"]["items"]
    assert [row["row_no"] for row in rows] == [6]
    assert rows[0]["raw_json"]["상품코드"] == "P100"
    assert rows[0]["normalized_json"]["product_code"] == "P100"


def test_excel_upload_detects_header_row_and_maps_esp_product_headers(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_esp_product_admin")
    content = _xlsx_bytes(
        ["품목코드", "바코드", "품목명", "품목명(원명)", "쿠팡바코드", "Packing Unit", "Inner Qty", "사용"],
        [["ESP-001", "8801234567890", "샘플 상품", "원명", "C-8801234567890", "12.0", "6.0", "사용"]],
        leading_rows=[["상품코드 안내"], ["작성일", "2026-01-01"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["header_row_no"] == 3
    assert data["total_read_rows"] == 1
    assert data["mapped_headers"]["product_code"] == "품목코드"
    assert data["mapped_headers"]["primary_barcode"] == "바코드"
    assert data["mapped_headers"]["product_name"] == "품목명"
    assert data["mapped_headers"]["original_product_name"] == "품목명(원명)"
    assert data["mapped_headers"]["additional_barcode"] == "쿠팡바코드"
    assert data["mapped_headers"]["unit_qty"] == "Packing Unit"
    assert data["mapped_headers"]["inner_qty"] == "Inner Qty"

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    assert row["row_no"] == 4
    assert row["raw_json"]["Packing Unit"] == "12.0"
    assert row["normalized_json"]["product_code"] == "ESP-001"
    assert row["normalized_json"]["primary_barcode"] == "8801234567890"
    assert row["normalized_json"]["unit_qty"] == "12"
    assert row["normalized_json"]["inner_qty"] == "6"
    assert row["normalized_json"]["is_active"] == "true"


def test_excel_upload_maps_real_esp_product_sample_headers(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_real_esp_product_admin")
    content = _xlsx_bytes(
        [
            "품목코드",
            "바코드",
            "품목명",
            "품목명(원명)",
            "쿠팡바코드/G-Code",
            "Packing Unit(카톤입수)",
            "Inner Qty(입수수량)",
            "사용",
        ],
        [["ESP-REAL-001", "8801234567890", "샘플 상품", "샘플 원명", "C-8801234567890", "24.0", "6.0", "사용"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mapped_headers"]["product_code"] == "품목코드"
    assert data["mapped_headers"]["primary_barcode"] == "바코드"
    assert data["mapped_headers"]["product_name"] == "품목명"
    assert data["mapped_headers"]["original_product_name"] == "품목명(원명)"
    assert data["mapped_headers"]["additional_barcode"] == "쿠팡바코드/G-Code"
    assert data["mapped_headers"]["unit_qty"] == "Packing Unit(카톤입수)"
    assert data["mapped_headers"]["inner_qty"] == "Inner Qty(입수수량)"

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    assert row["normalized_json"]["primary_barcode"] == "8801234567890"
    assert row["normalized_json"]["additional_barcode"] == "C-8801234567890"
    assert row["normalized_json"]["unit_qty"] == "24"
    assert row["normalized_json"]["inner_qty"] == "6"
    assert row["normalized_json"]["is_active"] == "true"


def test_excel_upload_normalizes_return_tracking_date_and_qty(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_RETURN")
    owner = _create_user(
        db_session,
        login_id="return_intake_owner",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = _create_job(
        db_session,
        import_type="RETURN_INTAKE",
        source_type="EXCEL_FILE",
        client_row=client_row,
        created_by=owner,
    )
    headers = _admin_headers(client, db_session, "excel_return_intake_admin")
    content = _xlsx_bytes(
        ["요청일", "원송장번호", "반품송장 번호", "ERP코드", "상품명", "수량"],
        [["45000", "1234-5678-9012", "9999 8888 7777", "ERP-001", "반품 상품", "1개"]],
        leading_rows=[["반품리스트 안내"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["header_row_no"] == 2
    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    normalized = row["normalized_json"]
    assert normalized["request_date"] == "2023-03-15"
    assert normalized["original_tracking_no"] == "123456789012"
    assert normalized["original_tracking_no_original"] == "1234-5678-9012"
    assert normalized["return_tracking_no"] == "999988887777"
    assert normalized["return_tracking_no_original"] == "9999 8888 7777"
    assert normalized["product_code"] == "ERP-001"
    assert normalized["qty"] == "1"


def test_excel_upload_splits_vendor_original_and_return_tracking_headers(client: TestClient, db_session: Session):
    client_row = _create_client(db_session, "CLIENT_VENDOR_RETURN")
    owner = _create_user(
        db_session,
        login_id="vendor_return_owner",
        role_code="INTERNAL_ADMIN",
        permissions=["IMPORT_VIEW"],
    )
    job = _create_job(
        db_session,
        import_type="VENDOR_RETURN_DETAIL",
        source_type="EXCEL_FILE",
        client_row=client_row,
        created_by=owner,
    )
    headers = _admin_headers(client, db_session, "excel_vendor_return_admin")
    content = _xlsx_bytes(
        ["요청일", "원송장번호", "반품송장 번호", "ERP코드", "상품명", "수량"],
        [["2026.06.08", "1111-2222-3333", "9999 8888 7777", "ERP-001", "반품 상품", "1"]],
        leading_rows=[["반품리스트 안내"], ["담당자 메모"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["header_row_no"] == 3
    assert data["mapped_headers"]["request_date"] == "요청일"
    assert data["mapped_headers"]["original_tracking_no"] == "원송장번호"
    assert data["mapped_headers"]["return_tracking_no"] == "반품송장 번호"
    assert data["mapped_headers"]["product_code"] == "ERP코드"
    assert data["mapped_headers"]["qty"] == "수량"

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    assert row["row_no"] == 4
    assert row["normalized_json"]["original_tracking_no"] == "111122223333"
    assert row["normalized_json"]["return_tracking_no"] == "999988887777"
    assert row["normalized_json"]["request_date"] == "2026-06-08"


def test_excel_upload_maps_common_field_aliases(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_alias_admin")
    content = _xlsx_bytes(
        ["품목코드", "상품명", "대표바코드", "비고"],
        [["P010", "Alias product", "B010", "ignored memo"]],
        sheet_name="AliasProducts",
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mapped_headers"] == {
        "product_code": "품목코드",
        "product_name": "상품명",
        "primary_barcode": "대표바코드",
        "memo": "비고",
    }
    assert data["unmapped_headers"] == []

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    assert row["raw_json"]["비고"] == "ignored memo"
    assert row["normalized_json"]["product_code"] == "P010"
    assert row["normalized_json"]["product_name"] == "Alias product"
    assert row["normalized_json"]["barcode"] == "B010"


def test_excel_upload_maps_sku_option_barcode_and_unit_qty_aliases(client: TestClient, db_session: Session):
    job = _create_job(db_session, import_type="PRODUCT_BARCODE")
    headers = _admin_headers(client, db_session, "excel_sku_alias_admin")
    content = _xlsx_bytes(
        ["SKU", "옵션명", "바코드번호", "입수"],
        [["P020", "Option product", "B020", "3"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mapped_headers"] == {
        "product_code": "SKU",
        "product_name": "옵션명",
        "barcode": "바코드번호",
        "unit_qty": "입수",
    }
    assert data["unmapped_headers"] == []

    validate_response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)
    assert validate_response.status_code == 200
    assert validate_response.json()["data"]["status"] == "VALIDATED"


def test_excel_upload_keeps_first_mapping_when_aliases_overlap(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_duplicate_alias_admin")
    content = _xlsx_bytes(
        ["SKU", "상품코드", "상품명", "바코드"],
        [["P030", "P031", "Duplicate alias product", "B030"]],
    )

    response = _upload(client, job.id, headers=headers, content=content)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mapped_headers"]["product_code"] == "SKU"
    assert "상품코드" in data["unmapped_headers"]

    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    row = rows_response.json()["data"]["items"][0]
    assert row["raw_json"]["상품코드"] == "P031"
    assert row["normalized_json"]["product_code"] == "P030"


def test_excel_upload_allows_validate_and_reuses_import_validation(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_validate_admin")
    content = _xlsx_bytes(
        ["product_code", "product_name", "barcode"],
        [
            ["P001", "Valid product", "B001"],
            ["P002", "Warning product", ""],
            ["P003", "", "B003"],
        ],
    )
    upload_response = _upload(client, job.id, headers=headers, content=content)
    assert upload_response.status_code == 200

    validate_response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert validate_response.status_code == 200
    data = validate_response.json()["data"]
    assert data["status"] == "HAS_ERRORS"
    assert data["valid_rows"] == 2
    assert data["warning_rows"] == 1
    assert data["invalid_rows"] == 1
    rows_response = client.get(f"/api/import-jobs/{job.id}/rows", headers=headers)
    assert [row["validation_status"] for row in rows_response.json()["data"]["items"]] == ["VALID", "WARNING", "INVALID"]
    errors_response = client.get(f"/api/import-jobs/{job.id}/errors", headers=headers)
    assert {error["error_code"] for error in errors_response.json()["data"]["items"]} == {
        "PRODUCT_BARCODE_MISSING",
        "REQUIRED_FIELD_MISSING",
    }


def test_excel_upload_without_file_returns_400(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_no_file_admin")

    response = client.post(f"/api/import-jobs/{job.id}/files/excel", headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_EXCEL_FILE_REQUIRED"


def test_excel_upload_blocks_non_excel_file(client: TestClient, db_session: Session):
    job = _create_job(db_session)
    headers = _admin_headers(client, db_session, "excel_type_admin")

    response = _upload(client, job.id, headers=headers, content=b"not xlsx", file_name="products.csv")

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_EXCEL_FILE_TYPE_INVALID"


def test_excel_upload_blocks_wrong_source_type(client: TestClient, db_session: Session):
    job = _create_job(db_session, source_type="PASTE")
    headers = _admin_headers(client, db_session, "excel_wrong_source_admin")

    response = _upload(client, job.id, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_EXCEL_UPLOAD_SOURCE_TYPE_INVALID"


def test_excel_validate_without_rows_is_blocked(client: TestClient, db_session: Session):
    job = _create_job(db_session, status="READY_TO_VALIDATE")
    headers = _admin_headers(client, db_session, "excel_no_rows_admin")

    response = client.post(f"/api/import-jobs/{job.id}/validate", json={}, headers=headers)

    assert response.status_code == 400
    assert response.json()["result_code"] == "IMPORT_JOB_VALIDATE_NO_ROWS"
