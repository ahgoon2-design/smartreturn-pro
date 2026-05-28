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
from app.models.master import Client, Product, ProductBarcode, Warehouse


TEST_PASSWORD = "DummyPass123!"


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
        Product.__table__,
        ProductBarcode.__table__,
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


def _create_client(db: Session, code: str = "CLIENT_A", name: str = "Test Client") -> Client:
    client = Client(client_code=code, client_name=name, active_yn=True)
    db.add(client)
    db.commit()
    return client


def _create_product(
    db: Session,
    client_id: int,
    *,
    product_code: str = "PROD_A",
    product_name: str = "Test Product",
    barcode: str | None = "880000000001",
    active_yn: bool = True,
) -> Product:
    product = Product(
        client_id=client_id,
        product_code=product_code,
        product_name=product_name,
        barcode=barcode,
        active_yn=active_yn,
    )
    db.add(product)
    db.commit()
    return product


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
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": TEST_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _product_payload(client_id: int, **overrides) -> dict:
    payload = {
        "client_id": client_id,
        "product_code": "PROD_NEW",
        "product_name": "New Product",
        "barcode": "880000000099",
        "specification": "EA",
        "unit_name": "EA",
        "remarks": "test",
    }
    payload.update(overrides)
    return payload


def _manage_permissions() -> list[str]:
    return ["MASTER_MANAGE", "PRODUCT_MANAGE"]


def _assert_no_sensitive_values(data: dict) -> None:
    text = str(data).lower()
    for value in ("password", "secret", "token", "hash"):
        assert value not in text


def test_product_manage_requires_auth(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)

    response = client.post("/api/master/products", json=_product_payload(client_row.id))

    assert response.status_code == 401
    assert response.json()["result_code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize("role_code", ["READ_ONLY", "CLIENT_ADMIN", "INTERNAL_WORKER"])
def test_product_manage_blocks_roles_without_manage_permission(
    client: TestClient,
    db_session: Session,
    role_code: str,
):
    client_row = _create_client(db_session)
    permissions = ["MASTER_VIEW"] if role_code != "INTERNAL_WORKER" else []
    user_client_id = client_row.id if role_code in {"READ_ONLY", "CLIENT_ADMIN"} else None
    _create_user(
        db_session,
        login_id=f"blocked_{role_code.lower()}",
        role_code=role_code,
        permissions=permissions,
        client_id=user_client_id,
    )

    response = client.post(
        "/api/master/products",
        json=_product_payload(client_row.id),
        headers=_login(client, f"blocked_{role_code.lower()}"),
    )

    assert response.status_code == 403
    assert response.json()["result_code"] == "PERMISSION_DENIED"


def test_internal_admin_can_create_product(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_user(
        db_session,
        login_id="product_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/products",
        json=_product_payload(client_row.id),
        headers=_login(client, "product_admin"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result_code"] == "MASTER_PRODUCT_CREATED"
    assert data["data"]["product_code"] == "PROD_NEW"
    _assert_no_sensitive_values(data)


def test_product_create_blocks_duplicate_product_code(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id, product_code="PROD_DUP", barcode=None)
    _create_user(
        db_session,
        login_id="duplicate_code_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/products",
        json=_product_payload(client_row.id, product_code="PROD_DUP", barcode="880000000100"),
        headers=_login(client, "duplicate_code_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_PRODUCT_CODE_DUPLICATED"


def test_product_create_blocks_duplicate_representative_barcode(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    _create_product(db_session, client_row.id, barcode="880000000777")
    _create_user(
        db_session,
        login_id="duplicate_barcode_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )

    response = client.post(
        "/api/master/products",
        json=_product_payload(client_row.id, barcode="880000000777"),
        headers=_login(client, "duplicate_barcode_admin"),
    )

    assert response.status_code == 400
    assert response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_DUPLICATED"


def test_product_update_disable_enable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id, barcode="880000000010")
    _create_user(
        db_session,
        login_id="product_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "product_update_admin")

    update_response = client.patch(
        f"/api/master/products/{product.id}",
        json={"product_name": "Updated Product", "barcode": "880000000011"},
        headers=headers,
    )
    disable_response = client.post(f"/api/master/products/{product.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/products/{product.id}/enable", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["result_code"] == "MASTER_PRODUCT_UPDATED"
    assert update_response.json()["data"]["product_name"] == "Updated Product"
    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_PRODUCT_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_PRODUCT_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True


def test_product_barcode_create_blocks_duplicate_and_invalid_qty(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id, barcode="880000000020")
    existing = ProductBarcode(
        client_id=client_row.id,
        product_id=product.id,
        barcode="188000000020",
        barcode_norm="188000000020",
        barcode_type="BOX",
        unit_qty=10,
        active_yn=True,
    )
    db_session.add(existing)
    db_session.commit()
    _create_user(
        db_session,
        login_id="barcode_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "barcode_admin")

    create_response = client.post(
        "/api/master/product-barcodes",
        json={"product_id": product.id, "barcode": "288000000020", "barcode_type": "CARTON", "unit_qty": 20},
        headers=headers,
    )
    duplicate_response = client.post(
        "/api/master/product-barcodes",
        json={"product_id": product.id, "barcode": "188000000020", "barcode_type": "BOX", "unit_qty": 10},
        headers=headers,
    )
    invalid_qty_response = client.post(
        "/api/master/product-barcodes",
        json={"product_id": product.id, "barcode": "388000000020", "barcode_type": "BOX", "unit_qty": 0},
        headers=headers,
    )

    assert create_response.status_code == 200
    assert create_response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_CREATED"
    assert create_response.json()["data"]["unit_qty"] == 20
    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_DUPLICATED"
    assert invalid_qty_response.status_code == 422


def test_product_barcode_update_disable_enable(client: TestClient, db_session: Session):
    client_row = _create_client(db_session)
    product = _create_product(db_session, client_row.id, barcode="880000000030")
    product_barcode = ProductBarcode(
        client_id=client_row.id,
        product_id=product.id,
        barcode="188000000030",
        barcode_norm="188000000030",
        barcode_type="BOX",
        unit_qty=10,
        active_yn=True,
    )
    db_session.add(product_barcode)
    db_session.commit()
    _create_user(
        db_session,
        login_id="barcode_update_admin",
        role_code="INTERNAL_ADMIN",
        permissions=_manage_permissions(),
    )
    headers = _login(client, "barcode_update_admin")

    update_response = client.patch(
        f"/api/master/product-barcodes/{product_barcode.id}",
        json={"barcode": "188000000031", "unit_qty": 12, "remarks": "updated"},
        headers=headers,
    )
    disable_response = client.post(f"/api/master/product-barcodes/{product_barcode.id}/disable", headers=headers)
    enable_response = client.post(f"/api/master/product-barcodes/{product_barcode.id}/enable", headers=headers)

    assert update_response.status_code == 200
    assert update_response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_UPDATED"
    assert update_response.json()["data"]["barcode"] == "188000000031"
    assert update_response.json()["data"]["unit_qty"] == 12
    assert disable_response.status_code == 200
    assert disable_response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_DISABLED"
    assert disable_response.json()["data"]["active_yn"] is False
    assert enable_response.status_code == 200
    assert enable_response.json()["result_code"] == "MASTER_PRODUCT_BARCODE_ENABLED"
    assert enable_response.json()["data"]["active_yn"] is True
