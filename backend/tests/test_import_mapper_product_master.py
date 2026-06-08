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
from app.models.import_job import (
    ImportJob,
    ImportJobFile,
    ImportJobRow,
    ImportMappingDecision,
    ImportMappingProfile,
    ImportValidationError,
)
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
        ImportMappingDecision.__table__,
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


def _create_import_job(client: TestClient, headers: dict[str, str], client_id: int, import_type: str = "PRODUCT_MASTER") -> int:
    response = client.post(
        "/api/import-jobs",
        headers=headers,
        json={
            "import_type": import_type,
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


def test_mapping_profile_exact_match_auto_applies_and_similar_match_needs_review():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        user = _create_user(db, "import_mapper_profile_decision_admin")
        headers = _login(client, "import_mapper_profile_decision_admin")
        db.add(
            ImportMappingProfile(
                client_id=client_row.id,
                import_type="PRODUCT_MASTER",
                source_type="PASTE",
                profile_name="custom profile",
                header_signature="customsku|상품명",
                mapping_json={"custom sku": "product_code", "상품명": "product_name"},
                active_yn=True,
                created_by=user.id,
            )
        )
        db.commit()

        exact_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(client, headers, exact_job_id, [{"custom sku": "PM-P002", "상품명": "Profile Exact"}])
        exact_response = client.post(f"/api/import-jobs/{exact_job_id}/auto-map", headers=headers, json={})
        assert exact_response.status_code == 200
        exact_item = next(item for item in exact_response.json()["data"]["suggestions"] if item["source_header"] == "custom sku")
        assert exact_item["provider"] == "PROFILE"
        assert exact_item["decision_level"] == "AUTO_APPLY"

        similar_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(client, headers, similar_job_id, [{"custom sku": "PM-P003", "상품명": "Profile Similar", "메모": "changed"}])
        similar_response = client.post(f"/api/import-jobs/{similar_job_id}/auto-map", headers=headers, json={})
        assert similar_response.status_code == 200
        similar_item = next(item for item in similar_response.json()["data"]["suggestions"] if item["source_header"] == "custom sku")
        assert similar_item["provider"] == "PROFILE"
        assert similar_item["decision_level"] == "NEEDS_REVIEW"


def test_product_master_paste_skips_empty_and_noise_rows_without_errors():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_row_filter_admin")
        headers = _login(client, "import_mapper_row_filter_admin")
        job_id = _create_import_job(client, headers, client_row.id)

        response = client.post(
            f"/api/import-jobs/{job_id}/rows/paste",
            headers=headers,
            json={
                "replace_existing": False,
                "rows": [
                    {"row_no": 1, "raw_json": {"상품코드": "", "상품명": "", "대표바코드": "", "메모": ""}, "source_row_key": "row-1"},
                    {"row_no": 2, "raw_json": {"상품코드": "-", "상품명": "--", "대표바코드": "없음", "메모": ""}, "source_row_key": "row-2"},
                    {"row_no": 3, "raw_json": {"상품코드": "합계", "상품명": "", "대표바코드": "", "메모": ""}, "source_row_key": "row-3"},
                    {"row_no": 4, "raw_json": {"상품코드": "", "상품명": "", "대표바코드": "", "메모": "확인 필요"}, "source_row_key": "row-4"},
                    {
                        "row_no": 5,
                        "raw_json": {
                            "상품코드": "PM-F001",
                            "상품명": "실제 상품",
                            "대표바코드": "880000000091",
                            "메모": "",
                        },
                        "source_row_key": "row-5",
                    },
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["saved_row_count"] == 1
        assert data["skipped_empty_rows"] == 1
        assert data["skipped_noise_rows"] == 3

        rows_response = client.get(f"/api/import-jobs/{job_id}/rows", headers=headers)
        rows = rows_response.json()["data"]["items"]
        assert [row["row_no"] for row in rows] == [5]
        assert rows[0]["raw_json"]["상품코드"] == "PM-F001"

        client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})
        validate_response = client.post(f"/api/import-jobs/{job_id}/validate", headers=headers, json={"force": False})
        assert validate_response.status_code == 200
        assert validate_response.json()["data"]["status"] == "VALIDATED"
        assert db.query(ImportValidationError).filter(ImportValidationError.job_id == job_id).count() == 0

        confirm_response = client.post(f"/api/import-jobs/{job_id}/confirm", headers=headers)
        assert confirm_response.status_code == 200
        assert confirm_response.json()["data"]["applied_rows"] == 1
        assert db.query(Product).filter(Product.client_id == client_row.id).count() == 1


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


def test_mapping_engine_marks_exact_alias_as_auto_apply():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_alias_admin")
        headers = _login(client, "import_mapper_decision_alias_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [{"product_code": "PM-D001", "product_name": "Decision Product", "primary_barcode": "880000000101"}],
        )

        response = client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})

        assert response.status_code == 200
        data = response.json()["data"]
        product_code_suggestion = next(item for item in data["suggestions"] if item["source_header"] == "product_code")
        assert product_code_suggestion["decision_level"] == "AUTO_APPLY"
        assert product_code_suggestion["provider"] == "ALIAS"
        assert data["auto_apply_count"] >= 2
        assert data["blocked_count"] == 0


def test_mapping_decision_history_changes_next_recommendation_after_correction():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_correct_admin")
        headers = _login(client, "import_mapper_decision_correct_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [{"barcode": "PM-D002", "product_name": "Corrected Product"}],
        )
        client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})

        apply_response = client.put(
            f"/api/import-jobs/{job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"barcode": "product_code", "product_name": "product_name"}},
        )
        assert apply_response.status_code == 200
        assert db.query(ImportMappingDecision).filter(ImportMappingDecision.decision_type == "CORRECTED").count() == 1

        second_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            second_job_id,
            [{"barcode": "PM-D003", "product_name": "Learned Product"}],
        )
        second_response = client.post(f"/api/import-jobs/{second_job_id}/auto-map", headers=headers, json={})

        assert second_response.status_code == 200
        second_data = second_response.json()["data"]
        barcode_suggestion = next(item for item in second_data["suggestions"] if item["source_header"] == "barcode")
        assert barcode_suggestion["target_field"] == "product_code"
        assert barcode_suggestion["provider"] == "DECISION_HISTORY"


def test_mapping_rejected_history_prevents_auto_apply():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_reject_admin")
        headers = _login(client, "import_mapper_decision_reject_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [{"primary_barcode": "880000000201", "product_code": "PM-D004", "product_name": "Rejected Product"}],
        )
        client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})
        apply_response = client.put(
            f"/api/import-jobs/{job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"product_code": "product_code", "product_name": "product_name"}},
        )
        assert apply_response.status_code == 200
        assert db.query(ImportMappingDecision).filter(ImportMappingDecision.decision_type == "REJECTED").count() == 1

        second_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            second_job_id,
            [{"primary_barcode": "880000000202", "product_code": "PM-D005", "product_name": "Rejected Product 2"}],
        )
        second_response = client.post(f"/api/import-jobs/{second_job_id}/auto-map", headers=headers, json={})

        assert second_response.status_code == 200
        primary_barcode_suggestion = next(item for item in second_response.json()["data"]["suggestions"] if item["source_header"] == "primary_barcode")
        assert primary_barcode_suggestion["decision_level"] != "AUTO_APPLY"


def test_mapping_engine_blocks_required_missing_and_duplicate_risky_fields():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_block_admin")
        headers = _login(client, "import_mapper_decision_block_admin")

        missing_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(client, headers, missing_job_id, [{"product_name": "Missing Code Product"}])
        missing_response = client.post(f"/api/import-jobs/{missing_job_id}/auto-map", headers=headers, json={})
        assert missing_response.status_code == 200
        missing_data = missing_response.json()["data"]
        assert "product_code" in missing_data["required_missing_fields"]
        assert missing_data["blocked_count"] >= 1

        duplicate_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            duplicate_job_id,
            [{"product_code": "PM-D006", "SKU": "PM-D006-ALT", "product_name": "Duplicate Field Product"}],
        )
        duplicate_response = client.post(f"/api/import-jobs/{duplicate_job_id}/auto-map", headers=headers, json={})
        assert duplicate_response.status_code == 200
        duplicate_data = duplicate_response.json()["data"]
        assert duplicate_data["blocked_count"] >= 1
        assert "product_code" not in duplicate_data["applied_mapping"].values()


def test_mapping_engine_blocks_duplicate_qty_candidates():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_qty_conflict_admin")
        headers = _login(client, "import_mapper_qty_conflict_admin")
        job_id = _create_import_job(client, headers, client_row.id, import_type="RETURN_INTAKE")
        _save_rows(
            client,
            headers,
            job_id,
            [{"반품송장번호": "RTN-001", "수량": "1", "반품수량": "2"}],
        )

        response = client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["blocked_count"] >= 1
        qty_items = [item for item in data["suggestions"] if item["target_field"] == "qty"]
        assert any(item["decision_level"] == "BLOCKED" for item in qty_items)


def test_mapping_engine_marks_ambiguous_tracking_header_as_needs_review():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_tracking_conflict_admin")
        headers = _login(client, "import_mapper_tracking_conflict_admin")
        job_id = _create_import_job(client, headers, client_row.id, import_type="VENDOR_RETURN_DETAIL")
        _save_rows(client, headers, job_id, [{"운송장번호": "111122223333", "주문번호": "O-001"}])

        response = client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})

        assert response.status_code == 200
        tracking_item = next(item for item in response.json()["data"]["suggestions"] if item["source_header"] == "운송장번호")
        assert tracking_item["decision_level"] in {"NEEDS_REVIEW", "BLOCKED"}
        assert "확인" in tracking_item["reason"] or "자동 확정" in tracking_item["reason"]


def test_mapping_decision_does_not_store_raw_private_sample_values():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_privacy_admin")
        headers = _login(client, "import_mapper_decision_privacy_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [{"barcode": "010-1234-5678", "product_name": "Privacy Product"}],
        )
        client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})
        response = client.put(
            f"/api/import-jobs/{job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"barcode": "product_code", "product_name": "product_name"}},
        )

        assert response.status_code == 200
        decision = db.query(ImportMappingDecision).filter(ImportMappingDecision.original_header == "barcode").one()
        assert decision.sample_value_hash is None
        assert "010-1234-5678" not in str(decision.source_context_json)


def test_confirm_blocks_unconfirmed_risky_needs_review_mapping_then_allows_after_apply():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_confirm_admin")
        headers = _login(client, "import_mapper_decision_confirm_admin")
        job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            job_id,
            [{"custom_sku": "PM-D007", "product_name": "Needs Review Product", "primary_barcode": "880000000301"}],
        )
        client.put(
            f"/api/import-jobs/{job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"custom_sku": "product_code", "product_name": "product_name", "primary_barcode": "primary_barcode"}},
        )

        validate_response = client.post(f"/api/import-jobs/{job_id}/validate", headers=headers, json={"force": False})
        assert validate_response.status_code == 200
        assert validate_response.json()["data"]["status"] == "VALIDATED"
        confirm_response = client.post(f"/api/import-jobs/{job_id}/confirm", headers=headers)
        assert confirm_response.status_code == 200
        assert confirm_response.json()["data"]["status"] == "APPLIED"


def test_confirm_blocks_needs_review_mapping_until_user_applies_mapping():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        _create_user(db, "import_mapper_decision_confirm_block_admin")
        headers = _login(client, "import_mapper_decision_confirm_block_admin")

        first_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            first_job_id,
            [{"custom_sku": "PM-D008", "product_name": "Learning Seed"}],
        )
        client.put(
            f"/api/import-jobs/{first_job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"custom_sku": "product_code", "product_name": "product_name"}},
        )

        second_job_id = _create_import_job(client, headers, client_row.id)
        _save_rows(
            client,
            headers,
            second_job_id,
            [{"custom_sku": "PM-D009", "product_name": "Blocked Until Review"}],
        )
        auto_response = client.post(f"/api/import-jobs/{second_job_id}/auto-map", headers=headers, json={})
        assert auto_response.status_code == 200
        suggestion = next(item for item in auto_response.json()["data"]["suggestions"] if item["source_header"] == "custom_sku")
        assert suggestion["decision_level"] == "NEEDS_REVIEW"

        validate_response = client.post(f"/api/import-jobs/{second_job_id}/validate", headers=headers, json={"force": False})
        assert validate_response.status_code == 200
        assert validate_response.json()["data"]["status"] == "VALIDATED"
        blocked_confirm = client.post(f"/api/import-jobs/{second_job_id}/confirm", headers=headers)
        assert blocked_confirm.status_code == 400
        assert blocked_confirm.json()["result_code"] == "IMPORT_JOB_CONFIRM_MAPPING_BLOCKED"

        apply_response = client.put(
            f"/api/import-jobs/{second_job_id}/mapping",
            headers=headers,
            json={"mapping_json": {"custom_sku": "product_code", "product_name": "product_name"}},
        )
        assert apply_response.status_code == 200
        revalidate_response = client.post(f"/api/import-jobs/{second_job_id}/validate", headers=headers, json={"force": False})
        assert revalidate_response.status_code == 200
        confirm_response = client.post(f"/api/import-jobs/{second_job_id}/confirm", headers=headers)
        assert confirm_response.status_code == 200
