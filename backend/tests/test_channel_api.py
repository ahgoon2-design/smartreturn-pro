from collections.abc import Generator
from datetime import datetime, timezone
import hashlib
import json

import pytest
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
from app.models.channels import ChannelAccount, ChannelRawEvent, ChannelReturnCandidate, ChannelSyncJob, ProductChannelMapping
from app.models.master import Client, ClientUnit, Product, ProductBarcode, Warehouse
from app.models.returns import ReturnIntakeBatch, ReturnIntakeRow


TEST_PASSWORD = "DummyPass123!"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):
    return compiler.visit_JSON(_type, **kwargs)


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
        ClientUnit.__table__,
        Product.__table__,
        ProductBarcode.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        ChannelAccount.__table__,
        ChannelSyncJob.__table__,
        ChannelRawEvent.__table__,
        ReturnIntakeBatch.__table__,
        ReturnIntakeRow.__table__,
        ChannelReturnCandidate.__table__,
        ProductChannelMapping.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A") -> Client:
    row = Client(client_code=code, client_name=f"{code} Name", active_yn=True)
    db.add(row)
    db.commit()
    return row


def _create_unit(db: Session, client_id: int, code: str = "UNIT_A") -> ClientUnit:
    row = ClientUnit(client_id=client_id, unit_code=code, unit_name=f"{code} Name", active_yn=True)
    db.add(row)
    db.commit()
    return row


def _create_product(db: Session, client_id: int, product_code: str = "P-READY", barcode: str | None = None) -> Product:
    product = Product(
        client_id=client_id,
        product_code=product_code,
        product_name=f"{product_code} 상품",
        barcode=barcode,
        active_yn=True,
    )
    db.add(product)
    db.commit()
    return product


def _raw_hash(payload: dict) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _create_raw_event(db: Session, account_id: int, raw_json: dict, *, channel_type: str = "NAVER_SMARTSTORE") -> ChannelRawEvent:
    event = ChannelRawEvent(
        channel_account_id=account_id,
        channel_type=channel_type,
        event_type=raw_json.get("eventType", "RETURN_CLAIM"),
        external_order_id=raw_json.get("orderId"),
        external_product_order_id=raw_json.get("productOrderId"),
        external_claim_id=raw_json.get("claimId"),
        external_tracking_no_hash=None,
        raw_hash=_raw_hash(raw_json),
        raw_json=raw_json,
        process_status="RECEIVED",
        collected_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    return event


def _ready_candidate(
    client: TestClient,
    db: Session,
    headers: dict[str, str],
    *,
    client_row: Client | None = None,
    unit: ClientUnit | None = None,
    product: Product | None = None,
    return_tracking_no: str = "RTN-EXPECTED",
    original_tracking_no: str | None = "ORG-EXPECTED",
    external_product_order_id: str = "PO-EXPECTED",
    external_claim_id: str = "CLAIM-EXPECTED",
    qty: int = 1,
    external_account_id: str | None = None,
) -> dict:
    client_row = client_row or _create_client(db)
    unit = unit or _create_unit(db, client_row.id)
    product = product or _create_product(db, client_row.id, "P-EXPECTED")
    account_id = _create_account(
        client,
        headers,
        client_row.id,
        client_unit_id=unit.id,
        external_account_id=external_account_id or f"store-{external_product_order_id}-{return_tracking_no}",
    )
    raw_payload = {
        "eventType": "RETURN_CLAIM",
        "orderId": f"ORDER-{external_product_order_id}",
        "productOrderId": external_product_order_id,
        "claimId": external_claim_id,
        "returnTrackingNo": return_tracking_no,
        "sellerProductCode": product.product_code,
        "qty": qty,
        "claimReason": "단순변심",
        "claimStatus": "RETURN_REQUESTED",
    }
    if original_tracking_no:
        raw_payload["originalTrackingNo"] = original_tracking_no
    raw_event = _create_raw_event(db, account_id, raw_payload)
    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["candidate"]


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


def _admin_headers(client: TestClient, db: Session, login_id: str = "channel_admin") -> dict[str, str]:
    _create_user(
        db,
        login_id=login_id,
        role_code="INTERNAL_ADMIN",
        permissions=["RETURN_VIEW", "RETURN_MANAGE"],
    )
    return _login(client, login_id)


def _account_payload(client_id: int, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "channel_type": "NAVER_SMARTSTORE",
        "account_name": "네이버 기본 계정",
        "store_name": "테스트 스토어",
        "external_account_id": "store-dry-run",
        "credential_ref": "channel/naver/test-store",
        "sync_enabled": True,
    }
    payload.update(overrides)
    return payload


def _create_account(client: TestClient, headers: dict[str, str], client_id: int, **overrides) -> int:
    response = client.post("/api/channels/accounts", headers=headers, json=_account_payload(client_id, **overrides))
    assert response.status_code == 200
    return response.json()["data"]["id"]


def _assert_no_secret_fields(data) -> None:
    text = str(data).lower()
    assert "secret" not in text
    assert "password" not in text
    assert "token" not in text
    assert "password_hash" not in text
    assert "credential_ref':" not in text


def test_channel_account_create_list_update_disable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    headers = _admin_headers(client, db_session)

    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)

    list_response = client.get("/api/channels/accounts", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"][0]["id"] == account_id
    assert list_response.json()["data"]["items"][0]["credential_ref_masked"] == "chan***tore"

    update_response = client.patch(
        f"/api/channels/accounts/{account_id}",
        headers=headers,
        json={"store_name": "수정 스토어", "sync_enabled": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["store_name"] == "수정 스토어"
    assert update_response.json()["data"]["sync_enabled"] is False

    disable_response = client.post(f"/api/channels/accounts/{account_id}/disable", headers=headers)
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["status"] == "INACTIVE"
    assert disable_response.json()["data"]["sync_enabled"] is False


def test_channel_accounts_respect_client_scope(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, "CLIENT_A")
    client_b = _create_client(db_session, "CLIENT_B")
    admin_headers = _admin_headers(client, db_session)
    account_a_id = _create_account(client, admin_headers, client_a.id, external_account_id="store-a")
    account_b_id = _create_account(client, admin_headers, client_b.id, external_account_id="store-b")

    _create_user(
        db_session,
        login_id="client_user",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_VIEW"],
        client_id=client_a.id,
    )
    client_headers = _login(client, "client_user")

    list_response = client.get("/api/channels/accounts", headers=client_headers)
    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json()["data"]["items"]}
    assert ids == {account_a_id}

    blocked_response = client.get(f"/api/channels/accounts/{account_b_id}", headers=client_headers)
    assert blocked_response.status_code == 403


def test_channel_connection_dry_run_does_not_expose_secrets(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    response = client.post(f"/api/channels/accounts/{account_id}/test-connection", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dry_run"] is True
    assert data["success"] is True
    assert data["provider_name"] == "NAVER_SMARTSTORE_DRY_RUN"
    _assert_no_secret_fields(data)


def test_channel_dry_run_creates_job_and_raw_event_without_raw_json_in_list(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dry_run"] is True
    assert data["collected_event_count"] == 1
    assert data["inserted_event_count"] == 1
    assert data["updated_event_count"] == 0
    assert data["job"]["status"] == "SUCCESS"

    events_response = client.get("/api/channels/raw-events", headers=headers)
    assert events_response.status_code == 200
    event_item = events_response.json()["data"]["items"][0]
    assert event_item["channel_type"] == "NAVER_SMARTSTORE"
    assert event_item["external_tracking_no_hash"]
    assert "raw_json" not in event_item


def test_channel_raw_event_dry_run_upserts_duplicate(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)

    first_response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})
    second_response = client.post(f"/api/channels/accounts/{account_id}/sync-jobs/dry-run", headers=headers, json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["data"]["inserted_event_count"] == 1
    assert second_response.json()["data"]["inserted_event_count"] == 0
    assert second_response.json()["data"]["updated_event_count"] == 1
    assert db_session.query(ChannelRawEvent).count() == 1


def test_channel_account_rejects_literal_secret_like_credential_ref(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    headers = _admin_headers(client, db_session)

    response = client.post(
        "/api/channels/accounts",
        headers=headers,
        json=_account_payload(client_row.id, credential_ref="secret-real-value"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "CHANNEL_CREDENTIAL_REF_UNSAFE"


def test_channel_raw_event_transform_creates_ready_candidate(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-READY")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-READY",
            "productOrderId": "PO-READY",
            "claimId": "CLAIM-READY",
            "returnTrackingNo": "RTN-READY",
            "originalTrackingNo": "ORG-READY",
            "sellerProductCode": product.product_code,
            "productName": "테스트 상품",
            "optionName": "기본",
            "qty": 1,
            "claimReason": "단순변심",
            "claimStatus": "RETURN_REQUESTED",
        },
    )

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["candidate"]["match_status"] == "READY_FOR_INTAKE"
    assert data["candidate"]["product_id"] == product.id
    assert data["candidate"]["client_unit_id"] == unit.id
    assert data["candidate"]["tracking_no_for_scan"] == "RTNREADY"
    assert data["candidate"]["original_tracking_no"] == "ORGREADY"


def test_channel_transform_original_tracking_only_goes_pending(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-ORIGINAL")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-ORIGINAL",
            "productOrderId": "PO-ORIGINAL",
            "claimId": "CLAIM-ORIGINAL",
            "originalTrackingNo": "ORG-ONLY",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    candidate = response.json()["data"]["candidate"]
    assert candidate["match_status"] == "RETURN_TRACKING_PENDING"
    assert candidate["tracking_no_for_scan"] is None
    assert "RETURN_TRACKING_REQUIRED" in candidate["risk_flags"]


def test_channel_transform_without_account_unit_goes_team_pending(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id, "P-TEAM")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id)
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-TEAM",
            "productOrderId": "PO-TEAM",
            "claimId": "CLAIM-TEAM",
            "returnTrackingNo": "RTN-TEAM",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    candidate = response.json()["data"]["candidate"]
    assert candidate["match_status"] == "TEAM_ASSIGN_PENDING"
    assert "TEAM_ASSIGN_REQUIRED" in candidate["risk_flags"]


def test_channel_transform_unknown_product_goes_product_pending(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-PRODUCT",
            "productOrderId": "PO-PRODUCT",
            "claimId": "CLAIM-PRODUCT",
            "returnTrackingNo": "RTN-PRODUCT",
            "productName": "이름만 있는 상품",
            "optionName": "단품",
            "qty": 1,
        },
    )

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    candidate = response.json()["data"]["candidate"]
    assert candidate["match_status"] == "PRODUCT_MATCH_PENDING"
    assert "PRODUCT_MATCH_REQUIRED" in candidate["risk_flags"]


def test_channel_transform_return_tracking_conflict_goes_needs_review(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CONFLICT")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    first = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-CONFLICT-1",
            "productOrderId": "PO-CONFLICT-1",
            "claimId": "CLAIM-CONFLICT-1",
            "returnTrackingNo": "RTN-CONFLICT",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )
    second = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-CONFLICT-2",
            "productOrderId": "PO-CONFLICT-2",
            "claimId": "CLAIM-CONFLICT-2",
            "returnTrackingNo": "RTN-CONFLICT",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )

    first_response = client.post(f"/api/channels/raw-events/{first.id}/transform", headers=headers)
    second_response = client.post(f"/api/channels/raw-events/{second.id}/transform", headers=headers)

    assert first_response.status_code == 200
    assert first_response.json()["data"]["candidate"]["match_status"] == "READY_FOR_INTAKE"
    assert second_response.status_code == 200
    candidate = second_response.json()["data"]["candidate"]
    assert candidate["match_status"] == "NEEDS_REVIEW"
    assert "RETURN_TRACKING_CONFLICT" in candidate["risk_flags"]


def test_channel_transform_missing_identifiers_is_blocked(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    raw_event = _create_raw_event(db_session, account_id, {"eventType": "RETURN_CLAIM"})

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    candidate = response.json()["data"]["candidate"]
    assert candidate["match_status"] == "BLOCKED"
    assert "MISSING_EXTERNAL_IDENTIFIER" in candidate["risk_flags"]


def test_channel_candidate_list_hides_canonical_json_and_respects_scope(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, "CLIENT_A")
    client_b = _create_client(db_session, "CLIENT_B")
    unit_a = _create_unit(db_session, client_a.id, "UNIT_A")
    unit_b = _create_unit(db_session, client_b.id, "UNIT_B")
    product_a = _create_product(db_session, client_a.id, "P-SCOPE-A")
    product_b = _create_product(db_session, client_b.id, "P-SCOPE-B")
    admin_headers = _admin_headers(client, db_session)
    account_a = _create_account(client, admin_headers, client_a.id, client_unit_id=unit_a.id, external_account_id="scope-a")
    account_b = _create_account(client, admin_headers, client_b.id, client_unit_id=unit_b.id, external_account_id="scope-b")
    event_a = _create_raw_event(
        db_session,
        account_a,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-SCOPE-A",
            "productOrderId": "PO-SCOPE-A",
            "claimId": "CLAIM-SCOPE-A",
            "returnTrackingNo": "RTN-SCOPE-A",
            "sellerProductCode": product_a.product_code,
            "qty": 1,
        },
    )
    event_b = _create_raw_event(
        db_session,
        account_b,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-SCOPE-B",
            "productOrderId": "PO-SCOPE-B",
            "claimId": "CLAIM-SCOPE-B",
            "returnTrackingNo": "RTN-SCOPE-B",
            "sellerProductCode": product_b.product_code,
            "qty": 1,
        },
    )
    client.post(f"/api/channels/raw-events/{event_a.id}/transform", headers=admin_headers)
    client.post(f"/api/channels/raw-events/{event_b.id}/transform", headers=admin_headers)

    _create_user(
        db_session,
        login_id="candidate_client_user",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_VIEW"],
        client_id=client_a.id,
    )
    scoped_headers = _login(client, "candidate_client_user")

    list_response = client.get("/api/channels/return-candidates", headers=scoped_headers)

    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["client_id"] == client_a.id
    assert "canonical_json" not in items[0]
    text = str(list_response.json()).lower()
    assert "secret" not in text
    assert "token" not in text
    assert "password" not in text


def test_channel_account_bulk_transform_and_mark_reviewed(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-BULK")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-BULK",
            "productOrderId": "PO-BULK",
            "claimId": "CLAIM-BULK",
            "returnTrackingNo": "RTN-BULK",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )

    transform_response = client.post(f"/api/channels/accounts/{account_id}/raw-events/transform", headers=headers)

    assert transform_response.status_code == 200
    data = transform_response.json()["data"]
    assert data["transformed_count"] == 1
    assert data["created_count"] == 1
    candidate_id = data["candidates"][0]["id"]
    assert data["summary"]["READY_FOR_INTAKE"] == 1

    reviewed_response = client.post(f"/api/channels/return-candidates/{candidate_id}/mark-reviewed", headers=headers)

    assert reviewed_response.status_code == 200
    reviewed = reviewed_response.json()["data"]["candidate"]
    assert reviewed["reviewed_at"] is not None


def test_channel_ready_candidate_creates_return_intake_row_and_scan_finds_it(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CREATE")
    headers = _admin_headers(client, db_session)
    candidate = _ready_candidate(
        client,
        db_session,
        headers,
        client_row=client_row,
        unit=unit,
        product=product,
        return_tracking_no="RTN-CREATE",
        external_product_order_id="PO-CREATE",
        external_claim_id="CLAIM-CREATE",
    )

    response = client.post(f"/api/channels/return-candidates/{candidate['id']}/create-return-expected", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["created"] is True
    assert data["return_expected_id"]
    assert data["candidate"]["return_expected_create_status"] == "CREATED"
    row = db_session.get(ReturnIntakeRow, data["return_expected_id"])
    assert row is not None
    assert row.status == "READY_FOR_PROCESSING"
    assert row.validation_status == "VALID"
    assert row.return_tracking_no == "RTNCREATE"
    assert row.original_tracking_no == "ORGEXPECTED"
    assert row.client_unit_id == unit.id
    assert row.product_code == product.product_code
    assert row.raw_data["channel_return_candidate_id"] == candidate["id"]
    assert "raw_json" not in row.raw_data

    scan_response = client.get("/api/returns/processing/tasks?tracking_no=RTNCREATE", headers=headers)
    assert scan_response.status_code == 200
    items = scan_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["row_id"] == row.id
    assert items[0]["return_tracking_no"] == "RTNCREATE"
    assert items[0]["source_type"] == "CHANNEL_API"
    assert items[0]["source_origin"] == "NAVER_SMARTSTORE"
    assert items[0]["channel_return_candidate_id"] == candidate["id"]


def test_channel_create_return_expected_blocks_non_ready_candidate(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-NONREADY")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id)
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-NONREADY",
            "productOrderId": "PO-NONREADY",
            "claimId": "CLAIM-NONREADY",
            "originalTrackingNo": "ORG-NONREADY",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )
    transform_response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)
    candidate = transform_response.json()["data"]["candidate"]
    assert candidate["match_status"] == "RETURN_TRACKING_PENDING"

    response = client.post(f"/api/channels/return-candidates/{candidate['id']}/create-return-expected", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["created"] is False
    assert data["skipped_duplicate"] is False
    assert data["candidate"]["return_expected_create_status"] == "FAILED"
    assert "READY_FOR_INTAKE" in data["message"]
    assert db_session.query(ReturnIntakeRow).count() == 0


def test_channel_create_return_expected_blocks_missing_unit_product_or_qty(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-BLOCK")
    headers = _admin_headers(client, db_session)
    candidate = _ready_candidate(client, db_session, headers, client_row=client_row, unit=unit, product=product)
    candidate_row = db_session.get(ChannelReturnCandidate, candidate["id"])
    assert candidate_row is not None

    for field, value, expected_text in (
        ("client_unit_id", None, "팀/운영단위"),
        ("product_id", None, "상품마스터"),
        ("qty", 0, "수량"),
    ):
        setattr(candidate_row, field, value)
        candidate_row.return_expected_create_status = "NOT_CREATED"
        candidate_row.return_expected_create_error = None
        db_session.commit()

        response = client.post(f"/api/channels/return-candidates/{candidate_row.id}/create-return-expected", headers=headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["created"] is False
        assert data["candidate"]["return_expected_create_status"] == "FAILED"
        assert expected_text in data["message"]
        candidate_row = db_session.get(ChannelReturnCandidate, candidate_row.id)
        assert candidate_row is not None
        candidate_row.client_unit_id = unit.id
        candidate_row.product_id = product.id
        candidate_row.product_code = product.product_code
        candidate_row.qty = 1
        db_session.commit()


def test_channel_create_return_expected_skips_duplicate_external_claim(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-DUPE-CLAIM")
    headers = _admin_headers(client, db_session)
    first = _ready_candidate(
        client,
        db_session,
        headers,
        client_row=client_row,
        unit=unit,
        product=product,
        return_tracking_no="RTN-DUPE-A",
        external_product_order_id="PO-DUPE",
        external_claim_id="CLAIM-DUPE",
    )
    first_response = client.post(f"/api/channels/return-candidates/{first['id']}/create-return-expected", headers=headers)
    assert first_response.status_code == 200
    expected_id = first_response.json()["data"]["return_expected_id"]
    second = _ready_candidate(
        client,
        db_session,
        headers,
        client_row=client_row,
        unit=unit,
        product=product,
        return_tracking_no="RTN-DUPE-B",
        external_product_order_id="PO-DUPE",
        external_claim_id="CLAIM-DUPE",
    )

    second_response = client.post(f"/api/channels/return-candidates/{second['id']}/create-return-expected", headers=headers)

    assert second_response.status_code == 200
    data = second_response.json()["data"]
    assert data["created"] is False
    assert data["skipped_duplicate"] is True
    assert data["return_expected_id"] == expected_id
    assert data["candidate"]["return_expected_create_status"] == "SKIPPED_DUPLICATE"
    assert db_session.query(ReturnIntakeRow).count() == 1


def test_channel_create_return_expected_skips_existing_tracking_product_without_modifying_completed_row(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-DUPE-TRACK")
    headers = _admin_headers(client, db_session)
    batch = ReturnIntakeBatch(
        client_id=client_row.id,
        client_unit_id=unit.id,
        source_type="PASTE",
        source_name="기존 반품접수",
        status="READY_FOR_PROCESSING",
        total_rows=1,
        valid_rows=1,
        warning_rows=0,
        error_rows=0,
        created_by=1,
    )
    db_session.add(batch)
    db_session.flush()
    existing = ReturnIntakeRow(
        batch_id=batch.id,
        client_id=client_row.id,
        client_unit_id=unit.id,
        team_assign_status="ASSIGNED",
        row_no=1,
        order_no="ORDER-EXISTING",
        return_tracking_no="RTNDUPEEXISTING",
        original_tracking_no=None,
        product_code=product.product_code,
        barcode=None,
        product_name=product.product_name,
        option_name=None,
        qty=1,
        raw_data={"source": "existing"},
        validation_status="VALID",
        status="COMPLETED",
        judgement_status="GOOD",
        inventory_reflected_yn=True,
    )
    db_session.add(existing)
    db_session.commit()
    candidate = _ready_candidate(
        client,
        db_session,
        headers,
        client_row=client_row,
        unit=unit,
        product=product,
        return_tracking_no="RTN-DUPE-EXISTING",
        external_product_order_id="PO-DUPE-EXISTING",
        external_claim_id="CLAIM-DUPE-EXISTING",
    )

    response = client.post(f"/api/channels/return-candidates/{candidate['id']}/create-return-expected", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["created"] is False
    assert data["skipped_duplicate"] is True
    assert data["return_expected_id"] == existing.id
    db_session.refresh(existing)
    assert existing.status == "COMPLETED"
    assert existing.inventory_reflected_yn is True
    assert db_session.query(ReturnIntakeRow).count() == 1


def test_channel_bulk_create_return_expected_and_scope(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, "CLIENT_CREATE_A")
    client_b = _create_client(db_session, "CLIENT_CREATE_B")
    unit_a = _create_unit(db_session, client_a.id, "UNIT_CREATE_A")
    unit_b = _create_unit(db_session, client_b.id, "UNIT_CREATE_B")
    product_a = _create_product(db_session, client_a.id, "P-BULK-CREATE-A")
    product_b = _create_product(db_session, client_b.id, "P-BULK-CREATE-B")
    admin_headers = _admin_headers(client, db_session)
    account_a = _create_account(client, admin_headers, client_a.id, client_unit_id=unit_a.id, external_account_id="create-a")
    account_b = _create_account(client, admin_headers, client_b.id, client_unit_id=unit_b.id, external_account_id="create-b")
    event_a = _create_raw_event(
        db_session,
        account_a,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-BULK-CREATE-A",
            "productOrderId": "PO-BULK-CREATE-A",
            "claimId": "CLAIM-BULK-CREATE-A",
            "returnTrackingNo": "RTN-BULK-CREATE-A",
            "sellerProductCode": product_a.product_code,
            "qty": 1,
        },
    )
    event_b = _create_raw_event(
        db_session,
        account_b,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-BULK-CREATE-B",
            "productOrderId": "PO-BULK-CREATE-B",
            "claimId": "CLAIM-BULK-CREATE-B",
            "returnTrackingNo": "RTN-BULK-CREATE-B",
            "sellerProductCode": product_b.product_code,
            "qty": 1,
        },
    )
    client.post(f"/api/channels/raw-events/{event_a.id}/transform", headers=admin_headers)
    client.post(f"/api/channels/raw-events/{event_b.id}/transform", headers=admin_headers)

    response = client.post(f"/api/channels/accounts/{account_a}/return-candidates/create-return-expected", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_requested"] == 1
    assert data["created_count"] == 1
    assert data["skipped_duplicate_count"] == 0
    assert db_session.query(ReturnIntakeRow).count() == 1
    text = str(response.json()).lower()
    assert "raw_json" not in text
    assert "secret" not in text
    assert "token" not in text
    assert "password" not in text

    _create_user(
        db_session,
        login_id="candidate_create_client_user",
        role_code="CLIENT_ADMIN",
        permissions=["RETURN_VIEW", "RETURN_MANAGE"],
        client_id=client_a.id,
    )
    scoped_headers = _login(client, "candidate_create_client_user")
    blocked_response = client.post(
        f"/api/channels/accounts/{account_b}/return-candidates/create-return-expected",
        headers=scoped_headers,
    )
    assert blocked_response.status_code == 403


def test_channel_team_pending_correction_reprocesses_to_ready(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CORR-TEAM")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, external_account_id="corr-team")
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-CORR-TEAM",
            "productOrderId": "PO-CORR-TEAM",
            "claimId": "CLAIM-CORR-TEAM",
            "returnTrackingNo": "RTN-CORR-TEAM",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )
    candidate = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers).json()["data"]["candidate"]
    assert candidate["match_status"] == "TEAM_ASSIGN_PENDING"

    correction = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"client_unit_id": unit.id, "review_note": "팀 확인"},
    )
    assert correction.status_code == 200
    assert correction.json()["data"]["candidate"]["correction_status"] == "CORRECTED"

    reprocessed = client.post(f"/api/channels/return-candidates/{candidate['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 200
    ready = reprocessed.json()["data"]["candidate"]
    assert ready["match_status"] == "READY_FOR_INTAKE"
    assert ready["client_unit_id"] == unit.id
    assert ready["manual_client_unit_id"] == unit.id


def test_channel_product_pending_correction_reprocesses_to_ready_and_learns_mapping(
    client: TestClient,
    db_session: Session,
):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CORR-PRODUCT")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id, external_account_id="corr-product")
    payload = {
        "eventType": "RETURN_CLAIM",
        "orderId": "ORDER-CORR-PRODUCT",
        "productOrderId": "PO-CORR-PRODUCT",
        "claimId": "CLAIM-CORR-PRODUCT",
        "returnTrackingNo": "RTN-CORR-PRODUCT",
        "sellerProductCode": "SELLER-CORR-PRODUCT",
        "productName": "외부 상품명",
        "optionName": "검정",
        "qty": 1,
    }
    raw_event = _create_raw_event(db_session, account_id, payload)
    candidate = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers).json()["data"]["candidate"]
    assert candidate["match_status"] == "PRODUCT_MATCH_PENDING"

    correction = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"product_id": product.id},
    )
    assert correction.status_code == 200
    assert db_session.query(ProductChannelMapping).count() == 1

    reprocessed = client.post(f"/api/channels/return-candidates/{candidate['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 200
    ready = reprocessed.json()["data"]["candidate"]
    assert ready["match_status"] == "READY_FOR_INTAKE"
    assert ready["product_id"] == product.id
    assert ready["manual_product_id"] == product.id

    next_raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            **payload,
            "orderId": "ORDER-CORR-PRODUCT-2",
            "productOrderId": "PO-CORR-PRODUCT-2",
            "claimId": "CLAIM-CORR-PRODUCT-2",
            "returnTrackingNo": "RTN-CORR-PRODUCT-2",
        },
    )
    next_candidate = client.post(f"/api/channels/raw-events/{next_raw_event.id}/transform", headers=headers)
    assert next_candidate.status_code == 200
    assert next_candidate.json()["data"]["candidate"]["match_status"] == "READY_FOR_INTAKE"
    assert next_candidate.json()["data"]["candidate"]["product_id"] == product.id


def test_channel_return_tracking_pending_correction_reprocesses_to_ready(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CORR-TRACK")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id, external_account_id="corr-track")
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-CORR-TRACK",
            "productOrderId": "PO-CORR-TRACK",
            "claimId": "CLAIM-CORR-TRACK",
            "originalTrackingNo": "ORG-CORR-TRACK",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )
    candidate = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers).json()["data"]["candidate"]
    assert candidate["match_status"] == "RETURN_TRACKING_PENDING"

    correction = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"return_tracking_no": "RTN-CORR-TRACK"},
    )
    assert correction.status_code == 200
    reprocessed = client.post(f"/api/channels/return-candidates/{candidate['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 200
    ready = reprocessed.json()["data"]["candidate"]
    assert ready["match_status"] == "READY_FOR_INTAKE"
    assert ready["tracking_no_for_scan"] == "RTNCORRTRACK"


def test_channel_original_tracking_only_correction_does_not_make_ready(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CORR-ORG")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id, external_account_id="corr-org")
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-CORR-ORG",
            "productOrderId": "PO-CORR-ORG",
            "claimId": "CLAIM-CORR-ORG",
            "originalTrackingNo": "ORG-CORR-ORG",
            "sellerProductCode": product.product_code,
            "qty": 1,
        },
    )
    candidate = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers).json()["data"]["candidate"]

    correction = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"original_tracking_no": "ORG-CORR-ORG-2"},
    )
    assert correction.status_code == 200
    reprocessed = client.post(f"/api/channels/return-candidates/{candidate['id']}/reprocess", headers=headers)
    assert reprocessed.status_code == 200
    data = reprocessed.json()["data"]["candidate"]
    assert data["match_status"] == "RETURN_TRACKING_PENDING"
    assert data["tracking_no_for_scan"] is None


def test_channel_correction_rejects_invalid_scope_and_qty(client: TestClient, db_session: Session):
    client_a = _create_client(db_session, "CLIENT_CORR_A")
    client_b = _create_client(db_session, "CLIENT_CORR_B")
    unit_a = _create_unit(db_session, client_a.id, "UNIT_CORR_A")
    unit_b = _create_unit(db_session, client_b.id, "UNIT_CORR_B")
    product_a = _create_product(db_session, client_a.id, "P-CORR-SCOPE-A")
    product_b = _create_product(db_session, client_b.id, "P-CORR-SCOPE-B")
    headers = _admin_headers(client, db_session)
    candidate = _ready_candidate(
        client,
        db_session,
        headers,
        client_row=client_a,
        unit=unit_a,
        product=product_a,
        external_product_order_id="PO-CORR-SCOPE",
        external_claim_id="CLAIM-CORR-SCOPE",
    )

    bad_unit = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"client_unit_id": unit_b.id},
    )
    assert bad_unit.status_code == 400
    bad_product = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"product_id": product_b.id},
    )
    assert bad_product.status_code == 400
    bad_qty = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"qty": 0},
    )
    assert bad_qty.status_code == 400


def test_channel_linked_candidate_cannot_be_corrected_or_reprocessed(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product = _create_product(db_session, client_row.id, "P-CORR-LINKED")
    headers = _admin_headers(client, db_session)
    candidate = _ready_candidate(client, db_session, headers, client_row=client_row, unit=unit, product=product)
    create_response = client.post(f"/api/channels/return-candidates/{candidate['id']}/create-return-expected", headers=headers)
    assert create_response.status_code == 200

    correction = client.patch(
        f"/api/channels/return-candidates/{candidate['id']}/correction",
        headers=headers,
        json={"qty": 2},
    )
    assert correction.status_code == 400
    reprocess = client.post(f"/api/channels/return-candidates/{candidate['id']}/reprocess", headers=headers)
    assert reprocess.status_code == 400


def test_channel_mapping_conflict_does_not_auto_confirm_product(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    unit = _create_unit(db_session, client_row.id)
    product_a = _create_product(db_session, client_row.id, "P-MAP-A")
    product_b = _create_product(db_session, client_row.id, "P-MAP-B")
    headers = _admin_headers(client, db_session)
    account_id = _create_account(client, headers, client_row.id, client_unit_id=unit.id, external_account_id="map-conflict")
    for product in (product_a, product_b):
        db_session.add(
            ProductChannelMapping(
                client_id=client_row.id,
                client_unit_id=unit.id,
                channel_type="NAVER_SMARTSTORE",
                channel_account_id=account_id,
                external_seller_product_code="SELLERMAPCONFLICT",
                external_product_name_norm="외부상품충돌",
                external_option_name_norm="기본",
                product_id=product.id,
                product_code=product.product_code,
                decision_type="CORRECTED",
                confidence=100,
            )
        )
    db_session.commit()
    raw_event = _create_raw_event(
        db_session,
        account_id,
        {
            "eventType": "RETURN_CLAIM",
            "orderId": "ORDER-MAP-CONFLICT",
            "productOrderId": "PO-MAP-CONFLICT",
            "claimId": "CLAIM-MAP-CONFLICT",
            "returnTrackingNo": "RTN-MAP-CONFLICT",
            "sellerProductCode": "SELLER-MAP-CONFLICT",
            "productName": "외부 상품 충돌",
            "optionName": "기본",
            "qty": 1,
        },
    )

    response = client.post(f"/api/channels/raw-events/{raw_event.id}/transform", headers=headers)

    assert response.status_code == 200
    candidate = response.json()["data"]["candidate"]
    assert candidate["match_status"] == "PRODUCT_MATCH_PENDING"
    assert candidate["product_id"] is None
