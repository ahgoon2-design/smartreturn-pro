from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import AuthError
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.inventory import CurrentInventory, InventoryEvent
from app.models.master import (
    Agency,
    Client,
    ClientUnit,
    ClientWarehouseSetting,
    Product,
    ProductBarcode,
    ReturnJudgmentWarehouseRoute,
    Warehouse,
)
from app.models.returns import (
    ReturnExternalOutboundBatch,
    ReturnIntakeBatch,
    ReturnIntakeRow,
    ReturnProcessingAttachment,
)
from app.repositories import inventory_repository
from app.schemas.auth import AuthContext
from app.schemas.returns import (
    ReturnClosingConfirmRequest,
    ReturnDisposalConfirmRequest,
    ReturnExternalOutboundConfirmRequest,
)
from app.services import return_intake_service


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, compiler, **kwargs):  # type: ignore[no-untyped-def]
    return compiler.visit_JSON(_type, **kwargs)


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
        ClientUnit.__table__,
        ReturnJudgmentWarehouseRoute.__table__,
        ClientWarehouseSetting.__table__,
        Product.__table__,
        ProductBarcode.__table__,
        Role.__table__,
        Permission.__table__,
        User.__table__,
        UserRole.__table__,
        RolePermission.__table__,
        InventoryEvent.__table__,
        CurrentInventory.__table__,
        ReturnIntakeBatch.__table__,
        ReturnExternalOutboundBatch.__table__,
        ReturnIntakeRow.__table__,
        ReturnProcessingAttachment.__table__,
    ):
        table.create(bind=engine)

    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _make_agency_client(db: Session, code: str) -> tuple[Agency, Client]:
    agency = Agency(agency_code=f"AGC_{code}", agency_name=f"{code} Agency", active_yn=True)
    db.add(agency)
    db.flush()
    client = Client(client_code=code, client_name=f"{code} Client", agency_id=agency.id, active_yn=True)
    db.add(client)
    db.flush()
    return agency, client


def _make_client_unit(db: Session, client: Client, code: str = "UNIT") -> ClientUnit:
    unit = ClientUnit(
        agency_id=client.agency_id,
        client_id=client.id,
        unit_code=f"{code}_{client.id}",
        unit_name=f"{code} Unit",
        unit_type="TEAM",
        active_yn=True,
    )
    db.add(unit)
    db.flush()
    return unit


def _make_warehouse_with_setting(db: Session, client: Client, code: str = "WH") -> Warehouse:
    warehouse = Warehouse(
        warehouse_code=f"{code}_{client.id}",
        warehouse_name=f"{code} Warehouse",
        warehouse_type="RETURN",
        active_yn=True,
    )
    db.add(warehouse)
    db.flush()
    db.add(
        ClientWarehouseSetting(
            agency_id=client.agency_id,
            client_id=client.id,
            warehouse_id=warehouse.id,
            usage_type="RETURN_GOOD",
            is_default=True,
            active_yn=True,
        )
    )
    db.flush()
    return warehouse


def _make_product(db: Session, client: Client, code: str = "P001") -> Product:
    product = Product(
        agency_id=client.agency_id,
        client_id=client.id,
        product_code=code,
        product_name=f"{code} Product",
        barcode=f"BC-{code}",
        active_yn=True,
    )
    db.add(product)
    db.flush()
    return product


def _make_batch(db: Session, client: Client) -> ReturnIntakeBatch:
    batch = ReturnIntakeBatch(
        agency_id=client.agency_id,
        client_id=client.id,
        source_type="PASTE",
        status="READY_FOR_PROCESSING",
        created_by=1,
    )
    db.add(batch)
    db.flush()
    return batch


def _make_completed_row(
    db: Session,
    *,
    client: Client,
    batch: ReturnIntakeBatch,
    judgement: str,
    warehouse_id: int | None,
    client_unit_id: int | None,
    product_code: str = "P001",
    qty: int = 2,
    is_over_review_required: bool = False,
    over_review_reason: str | None = None,
    inventory_reflected_yn: bool = False,
    inventory_event_id: int | None = None,
    return_management_no: str | None = "RTN-MNG-001",
) -> ReturnIntakeRow:
    row = ReturnIntakeRow(
        batch_id=batch.id,
        agency_id=client.agency_id,
        client_id=client.id,
        client_unit_id=client_unit_id,
        row_no=1,
        product_code=product_code,
        barcode=f"BC-{product_code}",
        qty=qty,
        status="COMPLETED",
        judgement_status=judgement,
        raw_data={},
        validation_status="VALID",
        is_over_review_required=is_over_review_required,
        over_review_reason=over_review_reason,
        inventory_reflected_yn=inventory_reflected_yn,
        inventory_event_id=inventory_event_id,
        final_warehouse_id=warehouse_id,
        return_management_no=return_management_no,
    )
    db.add(row)
    db.flush()
    return row


def _make_closing_event(
    db: Session,
    *,
    row: ReturnIntakeRow,
    warehouse_id: int,
    product_id: int,
    qty: int | None = None,
    stock_status: str | None = None,
) -> InventoryEvent:
    safe_stock_status = stock_status or (row.judgement_status or "GOOD")
    safe_qty = qty if qty is not None else row.qty or 1
    event = InventoryEvent(
        event_no=f"RTN-CLOSE-{row.id}",
        agency_id=row.agency_id,
        client_id=row.client_id,
        warehouse_id=warehouse_id,
        location_id=None,
        product_id=product_id,
        product_code=row.product_code,
        stock_status=safe_stock_status,
        event_type="RETURN_JUDGEMENT_IN",
        qty_delta=safe_qty,
        source_type="RETURN_CLOSING",
        source_id=row.id,
        source_line_id=row.id,
        idempotency_key=f"return-closing:{row.id}:{safe_stock_status.lower()}",
        event_reason="test setup",
        created_by=1,
        raw_json={},
    )
    db.add(event)
    db.flush()
    return event


def _make_current_inventory(
    db: Session,
    *,
    client: Client,
    warehouse_id: int,
    product_id: int,
    stock_status: str,
    qty: int,
) -> CurrentInventory:
    current = CurrentInventory(
        agency_id=client.agency_id,
        client_id=client.id,
        warehouse_id=warehouse_id,
        location_id=None,
        product_id=product_id,
        stock_status=stock_status,
        qty_on_hand=qty,
    )
    db.add(current)
    db.flush()
    return current


def _internal_auth(user_id: int = 1) -> AuthContext:
    return AuthContext(
        user_id=user_id,
        login_id="internal_worker",
        user_name="Internal Worker",
        roles=["INTERNAL_WORKER"],
        permissions=["RETURN_VIEW", "RETURN_CLOSE", "RETURN_OUTBOUND"],
        is_internal_user=True,
    )


def _portal_auth(client: Client, role: str) -> AuthContext:
    return AuthContext(
        user_id=2,
        login_id="portal_user",
        user_name="Portal User",
        roles=[role],
        permissions=["RETURN_VIEW", "RETURN_CLOSE", "RETURN_OUTBOUND"],
        client_id=client.id,
        agency_id=client.agency_id,
        is_client_user=True,
    )


def _closing_request(row_id: int, client_id: int | None = None) -> ReturnClosingConfirmRequest:
    return ReturnClosingConfirmRequest(row_ids=[row_id], client_id=client_id, confirm_good_only=False)


def _prepared_row(
    db: Session,
    code: str,
    *,
    judgement: str = "GOOD",
    qty: int = 2,
    with_unit: bool = True,
    with_warehouse: bool = True,
    return_management_no: str | None = "RTN-MNG-001",
    is_over_review_required: bool = False,
    over_review_reason: str | None = None,
) -> tuple[Agency, Client, ClientUnit | None, Warehouse | None, Product, ReturnIntakeBatch, ReturnIntakeRow]:
    agency, client = _make_agency_client(db, code)
    unit = _make_client_unit(db, client) if with_unit else None
    warehouse = _make_warehouse_with_setting(db, client, code=f"WH_{code}") if with_warehouse else None
    product = _make_product(db, client)
    batch = _make_batch(db, client)
    row = _make_completed_row(
        db,
        client=client,
        batch=batch,
        judgement=judgement,
        warehouse_id=warehouse.id if warehouse is not None else None,
        client_unit_id=unit.id if unit is not None else None,
        qty=qty,
        return_management_no=return_management_no,
        is_over_review_required=is_over_review_required,
        over_review_reason=over_review_reason,
    )
    return agency, client, unit, warehouse, product, batch, row


def _mark_inventory_reflected(
    db: Session,
    *,
    row: ReturnIntakeRow,
    warehouse: Warehouse,
    product: Product,
    qty: int | None = None,
    stock_status: str | None = None,
) -> InventoryEvent:
    event = _make_closing_event(
        db,
        row=row,
        warehouse_id=warehouse.id,
        product_id=product.id,
        qty=qty,
        stock_status=stock_status,
    )
    row.inventory_reflected_yn = True
    row.inventory_event_id = event.id
    _make_current_inventory(
        db,
        client=db.get(Client, row.client_id),
        warehouse_id=warehouse.id,
        product_id=product.id,
        stock_status=event.stock_status,
        qty=event.qty_delta,
    )
    db.flush()
    return event


def test_good_closing_applies_event_and_current_inventory(db_session: Session) -> None:
    _agency, client, _unit, warehouse, product, _batch, row = _prepared_row(db_session, "TC01")
    assert warehouse is not None
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    row_result = result["row_results"][0]
    assert row_result["result"] == "APPLIED"
    assert result["reflected_rows"] == 1
    assert result["event_count"] == 1

    db_session.expire_all()
    updated_row = db_session.get(ReturnIntakeRow, row.id)
    assert updated_row is not None
    assert updated_row.inventory_reflected_yn is True
    assert updated_row.inventory_event_id is not None

    event = db_session.get(InventoryEvent, updated_row.inventory_event_id)
    assert event is not None
    assert event.event_type == "RETURN_GOOD_IN"
    assert event.qty_delta == 2

    current = db_session.query(CurrentInventory).filter(
        CurrentInventory.client_id == client.id,
        CurrentInventory.warehouse_id == warehouse.id,
        CurrentInventory.product_id == product.id,
        CurrentInventory.stock_status == "GOOD",
    ).one_or_none()
    assert current is not None
    assert current.qty_on_hand == 2


def test_disposal_closing_applies_positive_inventory_before_confirm(db_session: Session) -> None:
    _agency, client, _unit, warehouse, _product, _batch, row = _prepared_row(
        db_session,
        "TC02",
        judgement="DISPOSAL",
        qty=3,
    )
    assert warehouse is not None
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["row_results"][0]["result"] == "APPLIED"
    current = db_session.query(CurrentInventory).filter(
        CurrentInventory.client_id == client.id,
        CurrentInventory.warehouse_id == warehouse.id,
        CurrentInventory.stock_status == "DISPOSAL",
    ).one_or_none()
    assert current is not None
    assert current.qty_on_hand == 3


def test_refurb_generic_is_blocked_as_ambiguous_grade(db_session: Session) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, row = _prepared_row(
        db_session,
        "TC03",
        judgement="REFURB",
    )
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["blocked_rows"] == 1
    assert result["row_results"][0]["result"] == "BLOCKED_AMBIGUOUS_GRADE"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


def test_over_review_row_is_blocked_with_reason(db_session: Session) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, row = _prepared_row(
        db_session,
        "TC04",
        judgement="GOOD",
        is_over_review_required=True,
        over_review_reason="QUANTITY_OVER",
    )
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["blocked_rows"] == 1
    row_result = result["row_results"][0]
    assert row_result["result"] == "BLOCKED_OVER_REVIEW"
    assert row_result["reason"] == "QUANTITY_OVER"
    assert db_session.get(ReturnIntakeRow, row.id).over_review_reason == "QUANTITY_OVER"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


def test_missing_client_unit_is_blocked_even_when_warehouse_exists(db_session: Session) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, row = _prepared_row(
        db_session,
        "TC05",
        judgement="GOOD",
        with_unit=False,
        with_warehouse=True,
    )
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["blocked_rows"] == 1
    assert result["row_results"][0]["result"] == "BLOCKED_MISSING_CLIENT_UNIT"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


def test_already_applied_row_is_skipped(db_session: Session) -> None:
    _agency, _client, _unit, warehouse, product, _batch, row = _prepared_row(db_session, "TC06")
    assert warehouse is not None
    event = _make_closing_event(db_session, row=row, warehouse_id=warehouse.id, product_id=product.id)
    row.inventory_reflected_yn = True
    row.inventory_event_id = event.id
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["skipped_rows"] == 1
    assert result["row_results"][0]["result"] == "SKIPPED_ALREADY_APPLIED"


def test_no_warehouse_is_blocked_without_event_or_current_inventory(db_session: Session) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, row = _prepared_row(
        db_session,
        "TC07",
        judgement="GOOD",
        with_unit=True,
        with_warehouse=False,
    )
    db_session.commit()

    result = return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    assert result["blocked_rows"] == 1
    assert result["row_results"][0]["result"] == "BLOCKED_NO_WAREHOUSE"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


def test_disposal_confirm_creates_negative_event_and_deducts_inventory(db_session: Session) -> None:
    _agency, client, _unit, warehouse, product, _batch, row = _prepared_row(
        db_session,
        "TC08",
        judgement="DISPOSAL",
        qty=3,
    )
    assert warehouse is not None
    _mark_inventory_reflected(db_session, row=row, warehouse=warehouse, product=product, qty=3, stock_status="DISPOSAL")
    db_session.commit()

    result = return_intake_service.confirm_return_disposal_task(
        db_session,
        _internal_auth(),
        row.id,
        ReturnDisposalConfirmRequest(disposal_reason="DISPOSAL"),
    )

    assert result["disposal_status"] == "DISPOSAL_CONFIRMED"
    deduction_event = db_session.get(InventoryEvent, result["deduction_event_id"])
    assert deduction_event is not None
    assert deduction_event.event_type == "RETURN_DISPOSAL_OUT"
    assert deduction_event.source_type == "RETURN_DISPOSAL"
    assert deduction_event.idempotency_key == f"return-disposal:{row.id}:disposal"
    assert deduction_event.qty_delta == -3

    current = db_session.query(CurrentInventory).filter(
        CurrentInventory.client_id == client.id,
        CurrentInventory.warehouse_id == warehouse.id,
        CurrentInventory.product_id == product.id,
        CurrentInventory.stock_status == "DISPOSAL",
    ).one()
    assert current.qty_on_hand == 0


def test_external_outbound_confirm_creates_negative_event_and_deducts_inventory(db_session: Session) -> None:
    _agency, client, _unit, warehouse, product, _batch, row = _prepared_row(
        db_session,
        "TC09",
        judgement="REFURB_A",
        qty=2,
        return_management_no="OUTBOUND-001",
    )
    assert warehouse is not None
    _mark_inventory_reflected(db_session, row=row, warehouse=warehouse, product=product, qty=2, stock_status="REFURB_A")
    db_session.commit()

    result = return_intake_service.confirm_return_external_outbound(
        db_session,
        _internal_auth(),
        ReturnExternalOutboundConfirmRequest(row_ids=[row.id]),
    )

    assert result["confirmed_rows"] == 1
    row_result = result["row_results"][0]
    assert row_result["result"] == "CONFIRMED"
    deduction_event = db_session.get(InventoryEvent, row_result["inventory_event_id"])
    assert deduction_event is not None
    assert deduction_event.event_type == "RETURN_EXTERNAL_OUTBOUND_OUT"
    assert deduction_event.source_type == "RETURN_EXTERNAL_OUTBOUND"
    assert deduction_event.idempotency_key == f"return-external-outbound:{row.id}:refurb_a"
    assert deduction_event.qty_delta == -2

    current = db_session.query(CurrentInventory).filter(
        CurrentInventory.client_id == client.id,
        CurrentInventory.warehouse_id == warehouse.id,
        CurrentInventory.product_id == product.id,
        CurrentInventory.stock_status == "REFURB_A",
    ).one()
    assert current.qty_on_hand == 0


def test_inventory_not_reflected_blocks_disposal_and_outbound_without_failed(db_session: Session) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, disposal_row = _prepared_row(
        db_session,
        "TC10D",
        judgement="DISPOSAL",
    )
    _agency2, _client2, _unit2, _warehouse2, _product2, _batch2, outbound_row = _prepared_row(
        db_session,
        "TC10O",
        judgement="REFURB_A",
        return_management_no="OUTBOUND-010",
    )
    db_session.commit()

    with pytest.raises(AuthError) as disposal_error:
        return_intake_service.confirm_return_disposal_task(
            db_session,
            _internal_auth(),
            disposal_row.id,
            ReturnDisposalConfirmRequest(disposal_reason="DISPOSAL"),
        )
    assert disposal_error.value.result_code == "BLOCKED_INVENTORY_NOT_REFLECTED"

    result = return_intake_service.confirm_return_external_outbound(
        db_session,
        _internal_auth(),
        ReturnExternalOutboundConfirmRequest(row_ids=[outbound_row.id]),
    )
    assert result["failed_rows"] == 0
    assert result["blocked_rows"] == 1
    assert result["row_results"][0]["result"] == "BLOCKED_INVENTORY_NOT_REFLECTED"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0


@pytest.mark.parametrize("role", ["CLIENT_ADMIN", "CLIENT_USER"])
def test_portal_users_cannot_confirm_inventory_paths(db_session: Session, role: str) -> None:
    _agency, client, _unit, warehouse, product, _batch, row = _prepared_row(db_session, f"TC11{role}")
    assert warehouse is not None
    disposal_row = _make_completed_row(
        db_session,
        client=client,
        batch=_make_batch(db_session, client),
        judgement="DISPOSAL",
        warehouse_id=warehouse.id,
        client_unit_id=row.client_unit_id,
        product_code="P001",
    )
    outbound_row = _make_completed_row(
        db_session,
        client=client,
        batch=_make_batch(db_session, client),
        judgement="REFURB_A",
        warehouse_id=warehouse.id,
        client_unit_id=row.client_unit_id,
        product_code="P001",
        return_management_no="OUTBOUND-PORTAL",
    )
    _mark_inventory_reflected(db_session, row=disposal_row, warehouse=warehouse, product=product, stock_status="DISPOSAL")
    _mark_inventory_reflected(db_session, row=outbound_row, warehouse=warehouse, product=product, stock_status="REFURB_A")
    db_session.commit()
    auth = _portal_auth(client, role)

    with pytest.raises(AuthError) as closing_error:
        return_intake_service.confirm_return_closing(db_session, auth, _closing_request(row.id))
    assert closing_error.value.status_code == 403
    assert closing_error.value.result_code == "PERMISSION_DENIED"

    with pytest.raises(AuthError) as outbound_error:
        return_intake_service.confirm_return_external_outbound(
            db_session,
            auth,
            ReturnExternalOutboundConfirmRequest(row_ids=[outbound_row.id]),
        )
    assert outbound_error.value.status_code == 403
    assert outbound_error.value.result_code == "PERMISSION_DENIED"

    with pytest.raises(AuthError) as disposal_error:
        return_intake_service.confirm_return_disposal_task(
            db_session,
            auth,
            disposal_row.id,
            ReturnDisposalConfirmRequest(disposal_reason="DISPOSAL"),
        )
    assert disposal_error.value.status_code == 403
    assert disposal_error.value.result_code == "PERMISSION_DENIED"


def test_mixed_client_batch_is_rejected_without_partial_apply(db_session: Session) -> None:
    _agency1, client1, _unit1, _warehouse1, _product1, _batch1, row1 = _prepared_row(
        db_session,
        "TC12A",
        judgement="REFURB_A",
        return_management_no="OUTBOUND-A",
    )
    _agency2, client2, _unit2, _warehouse2, _product2, _batch2, row2 = _prepared_row(
        db_session,
        "TC12B",
        judgement="REFURB_A",
        return_management_no="OUTBOUND-B",
    )
    db_session.commit()

    with pytest.raises(AuthError) as error:
        return_intake_service.confirm_return_external_outbound(
            db_session,
            _internal_auth(),
            ReturnExternalOutboundConfirmRequest(row_ids=[row1.id, row2.id]),
        )

    assert error.value.result_code == "BLOCKED_SCOPE_MISMATCH"
    assert db_session.get(ReturnIntakeRow, row1.id).external_outbound_status != "CONFIRMED"
    assert db_session.get(ReturnIntakeRow, row2.id).external_outbound_status != "CONFIRMED"
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0
    assert client1.id != client2.id


def test_current_inventory_repository_rejects_direct_change_without_event(db_session: Session) -> None:
    _agency, client, _unit, warehouse, product, _batch, _row = _prepared_row(db_session, "TC13")
    assert warehouse is not None

    with pytest.raises(ValueError):
        inventory_repository.increase_current_inventory(
            db_session,
            inventory_event_id=None,
            agency_id=client.agency_id,
            client_id=client.id,
            warehouse_id=warehouse.id,
            location_id=None,
            product_id=product.id,
            stock_status="GOOD",
            qty_delta=1,
        )
    with pytest.raises(ValueError):
        inventory_repository.decrease_current_inventory(
            db_session,
            inventory_event_id=None,
            agency_id=client.agency_id,
            client_id=client.id,
            warehouse_id=warehouse.id,
            location_id=None,
            product_id=product.id,
            stock_status="GOOD",
            qty_delta=1,
        )
    assert db_session.query(CurrentInventory).count() == 0


def test_closing_rolls_back_inventory_event_and_current_inventory_together(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _agency, _client, _unit, _warehouse, _product, _batch, row = _prepared_row(db_session, "TC14")
    db_session.commit()

    def _raise_after_event(*args, **kwargs):
        raise RuntimeError("stop after event creation")

    monkeypatch.setattr(return_intake_service.inventory_repository, "increase_current_inventory", _raise_after_event)

    with pytest.raises(RuntimeError):
        return_intake_service.confirm_return_closing(db_session, _internal_auth(), _closing_request(row.id))

    db_session.expire_all()
    updated_row = db_session.get(ReturnIntakeRow, row.id)
    assert updated_row is not None
    assert updated_row.inventory_reflected_yn is False
    assert updated_row.inventory_event_id is None
    assert db_session.query(InventoryEvent).count() == 0
    assert db_session.query(CurrentInventory).count() == 0
