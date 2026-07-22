from pydantic import BaseModel, Field
from typing import List, Optional


class InvoiceItem(BaseModel):
    name: str = Field(default="Unknown Product", description="Product name")
    price: float = Field(..., description="Unit price before tax")
    qty: int = Field(1, description="Quantity")
    is_reduced_vat: bool = Field(True, description="Whether item qualifies for reduced VAT (e.g., 8%)")


class InvoicePayload(BaseModel):
    items: List[InvoiceItem] = Field(..., description="List of items in the invoice")
    total: float = Field(..., description="Stated total price on the invoice including tax")


class RetailChatResponse(BaseModel):
    answer: str = Field(..., description="The main response text to the user")
    confidence: float = Field(1.0, description="Confidence score from 0.0 to 1.0")
    sources: Optional[List[str]] = Field(None, description="List of URLs or document IDs referenced")


class ProductExtraction(BaseModel):
    sku: Optional[str] = Field(None, description="Extracted SKU")
    category: str = Field(..., description="Product category")
    base_price: float = Field(..., description="Base price before tax")
