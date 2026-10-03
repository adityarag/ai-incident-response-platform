"""
Pydantic schemas for Order Service.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OrderCreateRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    item: str = Field(..., description="Item or product name")
    quantity: int = Field(default=1, gt=0, description="Quantity ordered")
    amount: float = Field(..., gt=0, description="Order monetary value")
    currency: str = Field(default="USD", max_length=10)


class OrderResponse(BaseModel):
    order_id: str
    customer_id: str
    item: str
    quantity: int
    amount: float
    currency: str
    status: str
    payment_id: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
