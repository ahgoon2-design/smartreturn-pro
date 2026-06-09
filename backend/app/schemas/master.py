"""P0 기준정보 read-only API schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PageData(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total_count: int


class ClientSummary(BaseModel):
    client_id: int
    agency_id: int | None = None
    agency_name: str | None = None
    client_code: str
    client_name: str
    active_yn: bool


class ClientDetail(ClientSummary):
    business_no: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    use_oms: bool
    use_wms: bool
    use_returns: bool
    use_settlement: bool
    remarks: str | None = None


class ClientCreateRequest(BaseModel):
    client_code: str
    client_name: str
    business_no: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    use_oms: bool = False
    use_wms: bool = True
    use_returns: bool = True
    use_settlement: bool = False
    remarks: str | None = None

    @field_validator("client_code", "client_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("business_no", "contact_name", "contact_phone", "contact_email", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ClientUpdateRequest(BaseModel):
    client_name: str | None = None
    business_no: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    use_oms: bool | None = None
    use_wms: bool | None = None
    use_returns: bool | None = None
    use_settlement: bool | None = None
    remarks: str | None = None

    @field_validator("client_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("business_no", "contact_name", "contact_phone", "contact_email", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class WarehouseSummary(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str | None = None
    active_yn: bool


class WarehouseCreateRequest(BaseModel):
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str | None = None
    address: str | None = None
    remarks: str | None = None

    @field_validator("warehouse_code", "warehouse_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("warehouse_type", "address", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class WarehouseUpdateRequest(BaseModel):
    warehouse_name: str | None = None
    warehouse_type: str | None = None
    address: str | None = None
    remarks: str | None = None

    @field_validator("warehouse_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("warehouse_type", "address", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ClientWarehouseSummary(BaseModel):
    setting_id: int
    client_id: int
    client_code: str | None = None
    client_name: str
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str | None = None
    warehouse_active_yn: bool | None = None
    usage_type: str
    usage_type_label: str
    is_default: bool
    active_yn: bool
    allowed_actions: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClientWarehouseSettingResponse(ClientWarehouseSummary):
    pass


class ClientUnitResponse(BaseModel):
    unit_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    unit_code: str
    unit_name: str
    unit_type: str | None = None
    default_warehouse_id: int | None = None
    default_warehouse_name: str | None = None
    return_warehouse_id: int | None = None
    return_warehouse_name: str | None = None
    active_yn: bool
    sort_order: int
    memo: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClientUnitCreateRequest(BaseModel):
    unit_code: str
    unit_name: str
    unit_type: str | None = None
    default_warehouse_id: int | None = None
    return_warehouse_id: int | None = None
    sort_order: int = 0
    memo: str | None = None

    @field_validator("unit_code", "unit_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("unit_type", "memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ClientUnitUpdateRequest(BaseModel):
    unit_name: str | None = None
    unit_type: str | None = None
    default_warehouse_id: int | None = None
    return_warehouse_id: int | None = None
    sort_order: int | None = None
    memo: str | None = None

    @field_validator("unit_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("unit_type", "memo")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnJudgmentWarehouseRouteResponse(BaseModel):
    route_id: int
    client_id: int
    client_code: str | None = None
    client_name: str | None = None
    client_unit_id: int | None = None
    client_unit_name: str | None = None
    judgment_code: str
    warehouse_id: int
    warehouse_code: str | None = None
    warehouse_name: str | None = None
    active_yn: bool
    sort_order: int
    memo: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReturnJudgmentWarehouseRouteCreateRequest(BaseModel):
    client_unit_id: int | None = None
    judgment_code: str
    warehouse_id: int
    sort_order: int = 0
    memo: str | None = None

    @field_validator("judgment_code")
    @classmethod
    def _required_judgment_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("memo")
    @classmethod
    def _optional_memo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReturnJudgmentWarehouseRouteUpdateRequest(BaseModel):
    client_unit_id: int | None = None
    judgment_code: str | None = None
    warehouse_id: int | None = None
    sort_order: int | None = None
    memo: str | None = None

    @field_validator("judgment_code")
    @classmethod
    def _optional_judgment_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("memo")
    @classmethod
    def _optional_memo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ClientWarehouseSettingCreateRequest(BaseModel):
    client_id: int
    warehouse_id: int
    usage_type: str
    is_default: bool = False

    @field_validator("usage_type")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value


class ClientWarehouseSettingUpdateRequest(BaseModel):
    usage_type: str | None = None

    @field_validator("usage_type")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value


class ClientWarehouseSettingNestedCreateRequest(BaseModel):
    warehouse_id: int
    usage_type: str
    is_default: bool = False

    @field_validator("usage_type")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value


class WarehouseOptionResponse(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str | None = None
    active_yn: bool
    already_linked: bool
    linked_usage_types: list[str] = Field(default_factory=list)
    default_usage_types: list[str] = Field(default_factory=list)


class ProductBarcodeDto(BaseModel):
    barcode_id: int
    barcode: str
    barcode_type: str
    unit_qty: int
    active_yn: bool
    remarks: str | None = None


class ProductSummary(BaseModel):
    product_id: int
    client_id: int
    client_name: str
    product_code: str
    product_name: str
    barcode: str | None = None
    active_yn: bool


class ProductDetail(ProductSummary):
    specification: str | None = None
    unit_name: str | None = None
    remarks: str | None = None
    barcodes: list[ProductBarcodeDto] = Field(default_factory=list)


class CommonCodeGroupSummary(BaseModel):
    group_id: int
    group_code: str
    group_name: str
    active_yn: bool


class CommonCodeSummary(BaseModel):
    code_id: int
    group_code: str
    code_value: str
    code_name: str
    sort_order: int
    active_yn: bool


class CommonCodeGroupCreateRequest(BaseModel):
    group_code: str
    group_name: str
    description: str | None = None

    @field_validator("group_code", "group_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("description")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CommonCodeGroupUpdateRequest(BaseModel):
    group_name: str | None = None
    description: str | None = None

    @field_validator("group_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("description")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CommonCodeCreateRequest(BaseModel):
    group_id: int
    code_value: str
    code_name: str
    sort_order: int = 0
    description: str | None = None

    @field_validator("code_value", "code_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("description")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CommonCodeUpdateRequest(BaseModel):
    code_name: str | None = None
    sort_order: int | None = None
    description: str | None = None

    @field_validator("code_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("description")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProductCreateRequest(BaseModel):
    client_id: int
    product_code: str
    product_name: str
    barcode: str | None = None
    specification: str | None = None
    unit_name: str | None = None
    remarks: str | None = None

    @field_validator("product_code", "product_name")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("barcode", "specification", "unit_name", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProductUpdateRequest(BaseModel):
    product_code: str | None = None
    product_name: str | None = None
    barcode: str | None = None
    specification: str | None = None
    unit_name: str | None = None
    remarks: str | None = None

    @field_validator("product_code", "product_name")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("barcode", "specification", "unit_name", "remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProductBarcodeCreateRequest(BaseModel):
    product_id: int
    barcode: str
    barcode_type: str
    unit_qty: int = Field(ge=1)
    remarks: str | None = None

    @field_validator("barcode", "barcode_type")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProductBarcodeUpdateRequest(BaseModel):
    barcode: str | None = None
    barcode_type: str | None = None
    unit_qty: int | None = Field(default=None, ge=1)
    remarks: str | None = None

    @field_validator("barcode", "barcode_type")
    @classmethod
    def _optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("required")
        return value

    @field_validator("remarks")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None
