import re

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class InvoiceItem(BaseModel):
    name: str = Field(default="Unknown Product", description="Product name")
    price: float = Field(..., description="Unit price before tax")
    qty: int = Field(1, description="Quantity")
    is_reduced_vat: Optional[bool] = Field(
        None,
        description="None = chưa rõ diện thuế -> validator áp mặc định 10%; True nếu thuộc diện giảm 8%",
    )

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be >= 0")
        return v

    @field_validator("qty")
    @classmethod
    def qty_at_least_one(cls, v: int) -> int:
        if v < 1:
            raise ValueError("qty must be >= 1")
        return v


class InvoicePayload(BaseModel):
    items: List[InvoiceItem] = Field(..., description="List of items in the invoice")
    total: float = Field(..., description="Stated total price on the invoice including tax")

    @field_validator("total")
    @classmethod
    def total_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("total must be > 0")
        return v


# ---------------------------------------------------------------------------
# Manufacturing OCR (San Xuất) — unified schema for material-batch-intake and
# customer-order documents, T-10-01: sanitize any VLM-parsed text field
# against embedded prompt-override phrases before it ever reaches a response.
# ---------------------------------------------------------------------------

_INJECTION_PATTERN = re.compile(
    r"(ignore\s+(the\s+)?(previous|prior|above)\s+instructions?"
    r"|disregard\s+(the\s+)?above"
    r"|disregard\s+(the\s+)?(previous|prior)\s+instructions?"
    r"|system\s*:"
    r"|assistant\s*:"
    r"|you\s+are\s+now\b)",
    re.IGNORECASE,
)


def _sanitize_optional_str(v):
    """None stays None (honesty bar: field genuinely absent). Otherwise strip
    control chars, neutralize prompt-override phrases, and collapse an
    all-neutralized/whitespace-only result back to None."""
    if v is None:
        return None
    if not isinstance(v, str):
        return v
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", v)
    cleaned = _INJECTION_PATTERN.sub("[removed]", cleaned)
    cleaned = cleaned.strip()
    return cleaned or None


def _sanitize_name(v):
    """Same stripping as _sanitize_optional_str, but falls back to
    'Unknown Item' instead of None since name stays a required str field."""
    if not isinstance(v, str):
        return "Unknown Item"
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", v)
    cleaned = _INJECTION_PATTERN.sub("[removed]", cleaned)
    cleaned = cleaned.strip()
    return cleaned or "Unknown Item"


class ManufacturingInvoiceItem(BaseModel):
    sku: Optional[str] = Field(None, description="Material/product SKU code, None if unreadable")
    name: str = Field(default="Unknown Item", description="Item name")
    qty: float = Field(0, description="Số lượng, có thể lẻ (vd 12.5 kg)")
    unit_price: float = Field(0, description="Unit price before tax")

    @field_validator("sku", mode="before")
    @classmethod
    def sanitize_sku(cls, v):
        return _sanitize_optional_str(v)

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_item_name(cls, v):
        return _sanitize_name(v)

    @field_validator("qty")
    @classmethod
    def qty_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("qty must be >= 0")
        return v

    @field_validator("unit_price")
    @classmethod
    def unit_price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("unit_price must be >= 0")
        return v


class ManufacturingInvoicePayload(BaseModel):
    items: List[ManufacturingInvoiceItem] = Field(
        default_factory=list, description="List of items; empty if unreadable"
    )
    total: float = Field(0, description="Stated total; 0 if unreadable")
    farmer: Optional[str] = Field(None, description="Farmer/HTX name (material-batch intake)")
    region_grown: Optional[str] = Field(None, description="Region grown (material-batch intake)")
    part: Optional[str] = Field(None, description="Plant part, e.g. lá/rễ/hoa (material-batch intake)")
    form: Optional[str] = Field(None, description="Form, e.g. tươi/khô (material-batch intake)")
    gacp_cert: Optional[str] = Field(None, description="GACP certificate number (material-batch intake)")
    doc_no: Optional[str] = Field(None, description="Document number (customer order)")
    customer_code: Optional[str] = Field(None, description="Customer code (customer order)")
    region: Optional[str] = Field(None, description="Delivery region (customer order)")
    deadline: Optional[str] = Field(None, description="Deadline (customer order)")

    @field_validator(
        "farmer", "region_grown", "part", "form", "gacp_cert",
        "doc_no", "customer_code", "region", "deadline",
        mode="before",
    )
    @classmethod
    def sanitize_optional_text_fields(cls, v):
        return _sanitize_optional_str(v)

    @field_validator("total")
    @classmethod
    def total_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("total must be >= 0")
        return v

    def populated_metadata_families(self) -> set[str]:
        """Return document families represented by non-null metadata."""
        families = set()
        if any(
            getattr(self, field) is not None
            for field in ("farmer", "region_grown", "part", "form", "gacp_cert")
        ):
            families.add("material_batch")
        if any(
            getattr(self, field) is not None
            for field in ("doc_no", "customer_code", "region", "deadline")
        ):
            families.add("customer_order")
        return families


class RetailChatResponse(BaseModel):
    answer: str = Field(..., description="The main response text to the user")
    # confidence: None = chưa đo (thành thật) thay vì 1.0 giả. Chỉ set khi có tín hiệu thật.
    confidence: Optional[float] = Field(None, description="Confidence 0.0–1.0; None nếu chưa đo")
    sources: Optional[List[str]] = Field(None, description="List of URLs or document IDs referenced")

    @field_validator("confidence")
    @classmethod
    def confidence_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class ProductExtraction(BaseModel):
    # Tất cả Optional: OCR tự do thường thiếu trường -> tránh ValidationError làm rớt cả kết quả.
    sku: Optional[str] = Field(None, description="Extracted SKU")
    category: Optional[str] = Field(None, description="Product category (None nếu OCR không đọc được)")
    base_price: Optional[float] = Field(None, description="Base price before tax (None nếu chưa đọc được)")

    @field_validator("base_price")
    @classmethod
    def base_price_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("base_price must be >= 0")
        return v
