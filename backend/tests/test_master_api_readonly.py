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
from app.models.master import (
    Agency,
    Client,
    ClientWarehouseSetting,
    CommonCode,
    CommonCodeGroup,
    Product,
    ProductBarcode,
    Warehouse,
)


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
        ClientWarehouseSetting.__table__,
        Product.__table__,
        ProductBarcode.__table__,
        CommonCodeGroup.__table__,
        CommonCode.__table__,
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


def _seed_master_data(db: Session) -> dict[str, object]:
    agency_a = Agency(agency_code="AGENCY_A", agency_name="테스트 대리점 A", active_yn=True)
    agency_b = Agency(agency_code="AGENCY_B", agency_name="테스트 대리점 B", active_yn=True)
    db.add_all([agency_a, agency_b])
    db.flush()
    client_a = Client(client_code="CLIENT_A", client_name="테스트 고객사 A", agency_id=agency_a.id, active_yn=True)
    client_b = Client(client_code="CLIENT_B", client_name="테스트 고객사 B", agency_id=agency_b.id, active_yn=True)
    warehouse_a = Warehouse(
        warehouse_code="WH_A",
        warehouse_name="테스트 창고 A",
        warehouse_type="RETURN",
        active_yn=True,
    )
    warehouse_b = Warehouse(
        warehouse_code="WH_B",
        warehouse_name="테스트 창고 B",
        warehouse_type="STORAGE",
        active_yn=True,
    )
    db.add_all([client_a, client_b, warehouse_a, warehouse_b])
    db.flush()

    db.add_all(
        [
            ClientWarehouseSetting(
                agency_id=agency_a.id,
                client_id=client_a.id,
                warehouse_id=warehouse_a.id,
                usage_type="RETURN_GOOD",
                is_default=True,
                active_yn=True,
            ),
            ClientWarehouseSetting(
                agency_id=agency_b.id,
                client_id=client_b.id,
                warehouse_id=warehouse_b.id,
                usage_type="STORAGE",
                is_default=True,
                active_yn=True,
            ),
        ]
    )

    product_a = Product(
        agency_id=agency_a.id,
        client_id=client_a.id,
        product_code="PROD_A",
        product_name="테스트 상품 A",
        barcode="880000000001",
        specification="EA",
        unit_name="개",
        active_yn=True,
    )
    product_b = Product(
        agency_id=agency_b.id,
        client_id=client_b.id,
        product_code="PROD_B",
        product_name="테스트 상품 B",
        barcode="880000000002",
        active_yn=True,
    )
    db.add_all([product_a, product_b])
    db.flush()
    db.add(
        ProductBarcode(
            agency_id=agency_a.id,
            client_id=client_a.id,
            product_id=product_a.id,
            barcode="1880000000008",
            barcode_norm="1880000000008",
            barcode_type="BOX",
            unit_qty=10,
            active_yn=True,
        )
    )

    group = CommonCodeGroup(group_code="RETURN_STATUS", group_name="반품상태", active_yn=True)
    db.add(group)
    db.flush()
    db.add_all(
        [
            CommonCode(
                group_id=group.id,
                code_value="CREATED",
                code_name="생성",
                sort_order=1,
                active_yn=True,
            ),
            CommonCode(
                group_id=group.id,
                code_value="COMPLETED",
                code_name="완료",
                sort_order=2,
                active_yn=True,
            ),
        ]
    )
    db.commit()
    return {
        "client_a": client_a,
        "client_b": client_b,
        "agency_a": agency_a,
        "agency_b": agency_b,
        "warehouse_a": warehouse_a,
        "warehouse_b": warehouse_b,
        "product_a": product_a,
        "product_b": product_b,
    }


def _create_user(
    db: Session,
    *,
    login_id: str,
    role_code: str,
    permissions: list[str] | None = None,
    client_id: int | None = None,
    agency_id: int | None = None,
    must_change_password: bool = False,
) -> User:
    role_type = "INTERNAL" if role_code in {"SUPER_ADMIN", "INTERNAL_ADMIN", "INTERNAL_WORKER"} else "AGENCY" if role_code == "AGENCY_ADMIN" else "CLIENT"
    role = Role(role_code=role_code, role_name=role_code, role_type=role_type, active_yn=True)
    user = User(
        login_id=login_id,
        user_name=f"{login_id} 사용자",
        password_hash=hash_password("DummyPass123!"),
        agency_id=agency_id,
        client_id=client_id,
        active_yn=True,
        must_change_password=must_change_password,
    )
    db.add_all([role, user])
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    for permission_code in permissions or []:
        permission = Permission(
            permission_code=permission_code,
            permission_name=permission_code,
            active_yn=True,
        )
        db.add(permission)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db.commit()
    return user


def _login(client: TestClient, login_id: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": "DummyPass123!"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_master_clients_requires_auth(client: TestClient):
    response = client.get("/api/master/clients")

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


def test_master_clients_blocks_password_change_required(client: TestClient, db_session: Session):
    _seed_master_data(db_session)
    _create_user(
        db_session,
        login_id="must_change",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW"],
        must_change_password=True,
    )

    response = client.get("/api/master/clients", headers=_login(client, "must_change"))

    assert response.status_code == 403
    assert response.json()["result_code"] == "PASSWORD_CHANGE_REQUIRED"


def test_master_clients_requires_master_view_permission(client: TestClient, db_session: Session):
    _seed_master_data(db_session)
    _create_user(db_session, login_id="worker", role_code="INTERNAL_WORKER", permissions=[])

    response = client.get("/api/master/clients", headers=_login(client, "worker"))

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_super_admin_can_list_all_clients(client: TestClient, db_session: Session):
    _seed_master_data(db_session)
    _create_user(db_session, login_id="super", role_code="SUPER_ADMIN", permissions=[])

    response = client.get("/api/master/clients", headers=_login(client, "super"))

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2


def test_client_admin_sees_only_own_client(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="client_admin",
        role_code="CLIENT_ADMIN",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get("/api/master/clients", headers=_login(client, "client_admin"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["client_id"] == client_a.id


def test_client_user_cannot_get_other_client_detail(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    client_b = seeded["client_b"]
    _create_user(
        db_session,
        login_id="client_user",
        role_code="CLIENT_USER",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get(f"/api/master/clients/{client_b.id}", headers=_login(client, "client_user"))

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_client_warehouses_are_scoped_by_client(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="client_warehouse",
        role_code="CLIENT_USER",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get("/api/master/client-warehouses", headers=_login(client, "client_warehouse"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["client_id"] == client_a.id


def test_internal_user_can_query_client_warehouses_by_client_id(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_b = seeded["client_b"]
    _create_user(
        db_session,
        login_id="internal_admin",
        role_code="INTERNAL_ADMIN",
        permissions=["MASTER_VIEW"],
    )

    response = client.get(
        f"/api/master/client-warehouses?client_id={client_b.id}",
        headers=_login(client, "internal_admin"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["client_id"] == client_b.id


def test_warehouses_are_internal_only(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="client_warehouse_all",
        role_code="CLIENT_ADMIN",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get("/api/master/warehouses", headers=_login(client, "client_warehouse_all"))

    assert response.status_code == 403


def test_products_return_page_data_and_apply_client_scope(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="client_products",
        role_code="READ_ONLY",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get("/api/master/products?page=1&page_size=20", headers=_login(client, "client_products"))

    assert response.status_code == 200
    page = response.json()["data"]
    assert page["total_count"] == 1
    assert page["items"][0]["client_id"] == client_a.id


def test_agency_admin_products_are_scoped_by_agency_without_client_filter(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    agency_a = seeded["agency_a"]
    client_a = seeded["client_a"]
    _create_user(
        db_session,
        login_id="agency_products",
        role_code="AGENCY_ADMIN",
        permissions=["MASTER_VIEW"],
        agency_id=agency_a.id,
    )

    response = client.get("/api/master/products?page=1&page_size=20", headers=_login(client, "agency_products"))

    assert response.status_code == 200
    page = response.json()["data"]
    assert page["total_count"] == 1
    assert page["items"][0]["client_id"] == client_a.id
    assert page["items"][0]["agency_id"] == agency_a.id


def test_client_user_cannot_request_other_client_products(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    client_b = seeded["client_b"]
    _create_user(
        db_session,
        login_id="client_products_denied",
        role_code="CLIENT_USER",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get(
        f"/api/master/products?client_id={client_b.id}",
        headers=_login(client, "client_products_denied"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_product_detail_validates_client_scope(client: TestClient, db_session: Session):
    seeded = _seed_master_data(db_session)
    client_a = seeded["client_a"]
    product_b = seeded["product_b"]
    _create_user(
        db_session,
        login_id="client_product_detail",
        role_code="CLIENT_ADMIN",
        permissions=["MASTER_VIEW"],
        client_id=client_a.id,
    )

    response = client.get(f"/api/master/products/{product_b.id}", headers=_login(client, "client_product_detail"))

    assert response.status_code == 403
    assert response.json()["result_code"] == "CLIENT_SCOPE_DENIED"


def test_common_code_groups_and_codes(client: TestClient, db_session: Session):
    _seed_master_data(db_session)
    _create_user(db_session, login_id="common_admin", role_code="INTERNAL_ADMIN", permissions=["MASTER_VIEW"])
    headers = _login(client, "common_admin")

    group_response = client.get("/api/master/common-code-groups", headers=headers)
    code_response = client.get("/api/master/common-codes?group_code=RETURN_STATUS", headers=headers)

    assert group_response.status_code == 200
    assert group_response.json()["data"][0]["group_code"] == "RETURN_STATUS"
    assert code_response.status_code == 200
    assert [row["code_value"] for row in code_response.json()["data"]] == ["CREATED", "COMPLETED"]
