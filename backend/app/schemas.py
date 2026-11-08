from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ParcelStatus(str, Enum):
    REGISTERED = "registered"
    SCHEDULED = "scheduled"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ParcelCreate(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=64)
    recipient_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    address_line: str = Field(min_length=5, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    delivery_instructions: str | None = Field(
        default=None,
        max_length=500,
    )
    preferred_delivery_date: date | None = None


class ParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracking_number: str
    recipient_name: str
    phone: str
    address_line: str
    city: str
    state: str
    pincode: str
    delivery_instructions: str | None
    preferred_delivery_date: date | None
    status: str
    created_at: datetime


class ParcelStatusUpdate(BaseModel):
    status: ParcelStatus