from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.inventory import CurrentInventory
from app.models.master import Agency, Client, Product, ProductBarcode, Warehouse


TEST_PASSWORD = "DummyPass123!"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        Agency.__table__,
        Client.__table__,
        Warehouse.__table__,
        Product.__table__,
        ProductBarcode.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        CurrentInventory.__table__,
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


def _seed_inventory(db: Session) -> dict[str, int]:
    """단일 고객사 + 단일 상품 + 두 창고에 등급별 현재고를 직접 적재한다."""
    agency = Agency(agency_code="AG1", agency_name="AG1", active_yn=True)
    db.add(agency)
    db.flush()
    client_row = Client(client_code="C1", client_name="고객사1", agency_id=agency.id, active_yn=True)
    db.add(client_row)
    db.flush()

    wh1 = Warehouse(warehouse_code="WH1", warehouse_name="창고1", warehouse_type="RETURN", active_yn=True)
    wh2 = Warehouse(warehouse_code="WH2", warehouse_name="창고2", warehouse_type="RETURN", active_yn=True)
    db.add_all([wh1, wh2])
    db.flush()

    product = Product(
        agency_id=agency.id,
        client_id=client_row.id,
        product_code="P1",
        product_name="상품1",
        barcode="BC1",
        active_yn=True,
    )
    db.add(product)
    db.flush()

    # 같은 상품·같은 등급(GOOD)을 두 창고에 분산 → 합산 대상.
    # 다른 등급(REFURB_B/DISPOSAL)은 합쳐지면 안 됨.
    db.add_all(
        [
            CurrentInventory(agency_id=agency.id, client_id=client_row.id, warehouse_id=wh1.id,
                             location_id=None, product_id=product.id, stock_status="GOOD", qty_on_hand=5),
            CurrentInventory(agency_id=agency.id, client_id=client_row.id, warehouse_id=wh2.id,
                             location_id=None, product_id=product.id, stock_status="GOOD", qty_on_hand=3),
            CurrentInventory(agency_id=agency.id, client_id=client_row.id, warehouse_id=wh1.id,
                             location_id=None, product_id=product.id, stock_status="REFURB_B", qty_on_hand=2),
            CurrentInventory(agency_id=agency.id, client_id=client_row.id, warehouse_id=wh2.id,
                             location_id=None, product_id=product.id, stock_status="DISPOSAL", qty_on_hand=4),
        ]
    )
    db.commit()
    return {"client_id": client_row.id, "warehouse1_id": wh1.id, "warehouse2_id": wh2.id, "product_id": product.id}


def _login_super_admin(db: Session, client: TestClient) -> dict[str, str]:
    role = Role(role_code="SUPER_ADMIN", role_name="SUPER_ADMIN", role_type="INTERNAL", active_yn=True)
    db.add(role)
    db.flush()
    permission = Permission(permission_code="INVENTORY_VIEW", permission_name="INVENTORY_VIEW", active_yn=True)
    db.add(permission)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    user = User(
        login_id="admin1",
        user_name="admin1",
        password_hash=hash_password(TEST_PASSWORD),
        client_id=None,
        active_yn=True,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()

    response = client.post("/api/auth/login", json={"login_id": "admin1", "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _rows_by_status(items: list[dict]) -> dict[str, dict]:
    return {item["stock_status"]: item for item in items}


def test_aggregated_when_warehouse_not_selected(db_session: Session, client: TestClient) -> None:
    _seed_inventory(db_session)
    headers = _login_super_admin(db_session, client)

    response = client.get("/api/inventory/current", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]

    # 합산 모드 플래그
    assert data["aggregated"] is True
    # 같은 상품에 등급 3종 → 3개 그룹 행
    assert data["total_count"] == 3
    by_status = _rows_by_status(data["items"])
    assert set(by_status) == {"GOOD", "REFURB_B", "DISPOSAL"}

    # 양성: GOOD은 두 창고(5+3) 합산 = 8, 합산 창고 수 = 2
    assert by_status["GOOD"]["qty"] == 8
    assert by_status["GOOD"]["warehouse_count"] == 2
    assert by_status["GOOD"]["warehouse_id"] is None
    assert by_status["GOOD"]["inventory_id"] is None

    # 음성: 다른 등급은 GOOD에 합쳐지지 않고 각자 유지
    assert by_status["REFURB_B"]["qty"] == 2
    assert by_status["REFURB_B"]["warehouse_count"] == 1
    assert by_status["DISPOSAL"]["qty"] == 4
    assert by_status["DISPOSAL"]["warehouse_count"] == 1


def test_per_warehouse_when_warehouse_selected_no_aggregation(db_session: Session, client: TestClient) -> None:
    ids = _seed_inventory(db_session)
    headers = _login_super_admin(db_session, client)

    response = client.get(
        f"/api/inventory/current?warehouse_id={ids['warehouse1_id']}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()["data"]

    # 회귀: 창고 선택 시 기존 창고별 동작 보존(합산 아님)
    assert data["aggregated"] is False
    by_status = _rows_by_status(data["items"])
    # 창고1에는 GOOD(5), REFURB_B(2)만 존재. 창고2의 GOOD(3)/DISPOSAL(4)은 포함 안 됨.
    assert set(by_status) == {"GOOD", "REFURB_B"}
    assert by_status["GOOD"]["qty"] == 5
    assert by_status["GOOD"]["warehouse_id"] == ids["warehouse1_id"]
    assert by_status["REFURB_B"]["qty"] == 2


def test_stock_status_filter_in_aggregated_mode(db_session: Session, client: TestClient) -> None:
    _seed_inventory(db_session)
    headers = _login_super_admin(db_session, client)

    response = client.get("/api/inventory/current?stock_status=GOOD", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["aggregated"] is True
    assert data["total_count"] == 1
    assert data["items"][0]["stock_status"] == "GOOD"
    assert data["items"][0]["qty"] == 8
