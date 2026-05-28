"""P0 기준정보 read-only API schema."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PageData(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total_count: int


class ClientSummary(BaseModel):
    client_id: int
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


class WarehouseSummary(BaseModel):
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    warehouse_type: str | None = None
    active_yn: bool


class ClientWarehouseSummary(BaseModel):
    client_id: int
    client_name: str
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    usage_type: str
    is_default: bool
    active_yn: bool


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
