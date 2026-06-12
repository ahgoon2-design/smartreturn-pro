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
from app.models.master import Agency, Client, Warehouse


TEST_PASSWORD = "DummyPass123!"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):
    return compiler.visit_JSON(_type, **kwargs)


def _create_tables(engine) -> None:
    for table in (
        Agency.__table__,
        Client.__table__,
        Warehouse.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_IMPORT_LEARNING") -> Client:
    agency = Agency(agency_code=f"AGENCY_{code}", agency_name=f"{code} Agency", active_yn=True)
    db.add(agency)
    db.flush()
    client = Client(client_code=code, client_name=f"{code} Name", agency_id=agency.id, active_yn=True)
    db.add(client)
    db.commit()
    return client


def _create_user(
    db: Session,
    *,
    login_id: str,
    role_code: str,
    permissions: list[str] | None = None,
    client_id: int | None = None,
    agency_id: int | None = None,
) -> User:
    role_type = "INTERNAL" if role_code in {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"} else "CLIENT"
    if role_code == "AGENCY_ADMIN":
        role_type = "AGENCY"
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
        agency_id=agency_id,
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
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_product_master_job(db: Session, *, client_row: Client, created_by: User) -> ImportJob:
    job = ImportJob(
        agency_id=client_row.agency_id,
        import_type="PRODUCT_MASTER",
        source_type="PASTE",
        source_name="mapping learning",
        requested_client_id=client_row.id,
        requested_warehouse_id=None,
        status="READY_TO_VALIDATE",
        total_rows=1,
        parsed_rows=1,
        valid_rows=0,
        invalid_rows=0,
        inserted_rows=0,
        updated_rows=0,
        skipped_rows=0,
        error_rows=0,
        progress_percent=0,
        raw_json={},
        created_by=created_by.id,
    )
    db.add(job)
    db.flush()
    db.add(
        ImportJobRow(
            agency_id=client_row.agency_id,
            job_id=job.id,
            client_id=client_row.id,
            row_no=3,
            source_row_key="row-3",
            raw_json={"legacy sku": "SKU-001", "product_name": "Learning Product"},
            normalized_json={"product_code": "OLD", "product_name": "Before"},
            validation_status="NOT_VALIDATED",
        )
    )
    db.commit()
    return job


def _auto_map(client: TestClient, headers: dict[str, str], job_id: int) -> dict:
    response = client.post(f"/api/import-jobs/{job_id}/auto-map", headers=headers, json={})
    assert response.status_code == 200
    return response.json()["data"]


def test_inactive_profile_is_excluded_and_reactivation_restores_provider():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        admin = _create_user(db, login_id="learning_profile_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW", "IMPORT_MANAGE"])
        headers = _login(client, "learning_profile_admin")
        profile = ImportMappingProfile(
            client_id=client_row.id,
            import_type="PRODUCT_MASTER",
            source_type="PASTE",
            profile_name="legacy profile",
            header_signature="legacysku|productname",
            mapping_json={"legacy sku": "product_code", "product_name": "product_name"},
            active_yn=True,
            created_by=admin.id,
        )
        db.add(profile)
        db.commit()

        first_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        first_data = _auto_map(client, headers, first_job.id)
        first_suggestion = next(item for item in first_data["suggestions"] if item["source_header"] == "legacy sku")
        assert first_suggestion["provider"] == "PROFILE"
        assert first_suggestion["source_profile_id"] == profile.id
        assert first_suggestion["source_decision_id"] is None

        deactivate = client.patch(
            f"/api/import-jobs/mapping-profiles/{profile.id}/deactivate",
            headers=headers,
            json={"reason": "wrong profile mapping"},
        )
        assert deactivate.status_code == 200
        assert deactivate.json()["data"]["active_yn"] is False
        assert db.get(ImportMappingProfile, profile.id) is not None

        second_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        second_data = _auto_map(client, headers, second_job.id)
        second_suggestion = next(item for item in second_data["suggestions"] if item["source_header"] == "legacy sku")
        assert second_suggestion["provider"] != "PROFILE"
        assert second_suggestion["source_profile_id"] is None

        active_list = client.get("/api/import-jobs/mapping-profiles", headers=headers)
        assert all(item["profile_id"] != profile.id for item in active_list.json()["data"]["items"])
        all_list = client.get("/api/import-jobs/mapping-profiles?include_inactive=true", headers=headers)
        assert any(item["profile_id"] == profile.id for item in all_list.json()["data"]["items"])

        activate = client.patch(f"/api/import-jobs/mapping-profiles/{profile.id}/activate", headers=headers)
        assert activate.status_code == 200
        third_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        third_data = _auto_map(client, headers, third_job.id)
        third_suggestion = next(item for item in third_data["suggestions"] if item["source_header"] == "legacy sku")
        assert third_suggestion["provider"] == "PROFILE"
        assert third_suggestion["source_profile_id"] == profile.id


def test_inactive_decision_is_excluded_and_reactivation_restores_provider_without_row_mutation():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        admin = _create_user(db, login_id="learning_decision_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW", "IMPORT_MANAGE"])
        headers = _login(client, "learning_decision_admin")
        decision = ImportMappingDecision(
            client_id=client_row.id,
            import_type="PRODUCT_MASTER",
            source_type="PASTE",
            original_header="legacy sku",
            normalized_header="legacysku",
            canonical_field="product_code",
            decision_type="CORRECTED",
            confidence_before=0.5,
            confidence_after=1.0,
            active_yn=True,
            confirmed_by=admin.id,
        )
        db.add(decision)
        db.commit()

        first_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        first_data = _auto_map(client, headers, first_job.id)
        first_suggestion = next(item for item in first_data["suggestions"] if item["source_header"] == "legacy sku")
        assert first_suggestion["provider"] == "DECISION_HISTORY"
        assert first_suggestion["source_decision_id"] == decision.id
        assert first_suggestion["source_profile_id"] is None
        row_before = db.query(ImportJobRow).filter(ImportJobRow.job_id == first_job.id).one()
        original_row_no = row_before.row_no
        original_raw = dict(row_before.raw_json)
        original_normalized = dict(row_before.normalized_json)

        deactivate = client.patch(
            f"/api/import-jobs/mapping-decisions/{decision.id}/deactivate",
            headers=headers,
            json={"reason": "wrong learned decision"},
        )
        assert deactivate.status_code == 200
        assert deactivate.json()["data"]["active_yn"] is False
        row_after = db.query(ImportJobRow).filter(ImportJobRow.job_id == first_job.id).one()
        assert row_after.row_no == original_row_no
        assert row_after.raw_json == original_raw
        assert row_after.normalized_json == original_normalized
        assert db.get(ImportMappingDecision, decision.id) is not None

        second_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        second_data = _auto_map(client, headers, second_job.id)
        second_suggestion = next(item for item in second_data["suggestions"] if item["source_header"] == "legacy sku")
        assert second_suggestion["provider"] != "DECISION_HISTORY"
        assert second_suggestion["source_decision_id"] is None

        active_list = client.get("/api/import-jobs/mapping-decisions", headers=headers)
        assert all(item["decision_id"] != decision.id for item in active_list.json()["data"]["items"])
        all_list = client.get("/api/import-jobs/mapping-decisions?include_inactive=true", headers=headers)
        assert any(item["decision_id"] == decision.id for item in all_list.json()["data"]["items"])

        activate = client.patch(f"/api/import-jobs/mapping-decisions/{decision.id}/activate", headers=headers)
        assert activate.status_code == 200
        third_job = _create_product_master_job(db, client_row=client_row, created_by=admin)
        third_data = _auto_map(client, headers, third_job.id)
        third_suggestion = next(item for item in third_data["suggestions"] if item["source_header"] == "legacy sku")
        assert third_suggestion["provider"] == "DECISION_HISTORY"
        assert third_suggestion["source_decision_id"] == decision.id


def test_mapping_learning_admin_policy_blocks_customer_agency_and_rejected_decision():
    for client, db in _client_with_db():
        client_row = _create_client(db)
        admin = _create_user(db, login_id="learning_policy_admin", role_code="INTERNAL_ADMIN", permissions=["IMPORT_VIEW", "IMPORT_MANAGE"])
        _create_user(
            db,
            login_id="learning_policy_client",
            role_code="CLIENT_ADMIN",
            permissions=["RETURN_CLIENT_SUBMIT"],
            client_id=client_row.id,
            agency_id=client_row.agency_id,
        )
        _create_user(
            db,
            login_id="learning_policy_agency",
            role_code="AGENCY_ADMIN",
            permissions=["IMPORT_VIEW", "IMPORT_MANAGE"],
            agency_id=client_row.agency_id,
        )
        admin_headers = _login(client, "learning_policy_admin")
        client_headers = _login(client, "learning_policy_client")
        agency_headers = _login(client, "learning_policy_agency")
        rejected = ImportMappingDecision(
            client_id=client_row.id,
            import_type="PRODUCT_MASTER",
            source_type="PASTE",
            original_header="legacy sku",
            normalized_header="legacysku",
            canonical_field="product_code",
            decision_type="REJECTED",
            active_yn=True,
            confirmed_by=admin.id,
        )
        db.add(rejected)
        db.commit()

        for forbidden_headers in (client_headers, agency_headers):
            response = client.patch(
                f"/api/import-jobs/mapping-decisions/{rejected.id}/deactivate",
                headers=forbidden_headers,
                json={"reason": "not allowed role"},
            )
            assert response.status_code == 403
            assert response.json()["result_code"] == "PERMISSION_DENIED"

        short_reason = client.patch(
            f"/api/import-jobs/mapping-decisions/{rejected.id}/deactivate",
            headers=admin_headers,
            json={"reason": "bad"},
        )
        assert short_reason.status_code == 422

        rejected_response = client.patch(
            f"/api/import-jobs/mapping-decisions/{rejected.id}/deactivate",
            headers=admin_headers,
            json={"reason": "block rejected decision"},
        )
        assert rejected_response.status_code == 400
        assert rejected_response.json()["result_code"] == "IMPORT_MAPPING_REJECTED_DECISION_CANNOT_BE_DEACTIVATED"
        assert db.get(ImportMappingDecision, rejected.id).active_yn is True
