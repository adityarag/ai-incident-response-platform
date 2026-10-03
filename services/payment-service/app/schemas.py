"""
Pydantic schemas for Payment Service.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PaymentProcessRequest(BaseModel):
    order_id: str = Field(..., description="ID of the order being paid")
    customer_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Payment amount must be positive")
    currency: str = Field(default="USD", max_length=10)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    customer_id: str
    amount: float
    currency: str
    status: str
    idempotency_key: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
