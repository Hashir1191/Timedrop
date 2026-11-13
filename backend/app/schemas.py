from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("A valid email address is required.")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    delivery_instructions: str | None = Field(default=None, max_length=500)
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
    warehouse_location: str | None = None
    delivery_instructions: str | None
    preferred_delivery_date: date | None
    status: str
    created_at: datetime


class ParcelStatusUpdate(BaseModel):
    status: ParcelStatus


class DeliverySlotCreate(BaseModel):
    delivery_date: date
    start_time: time
    end_time: time
    capacity: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class DeliverySlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    delivery_date: date
    start_time: time
    end_time: time
    capacity: int
    booked_count: int
    is_active: bool

    @property
    def available_capacity(self) -> int:
        return self.capacity - self.booked_count


class DeliverySlotAvailability(BaseModel):
    id: int
    delivery_date: date
    start_time: time
    end_time: time
    capacity: int
    booked_count: int
    remaining_capacity: int


class BookingCreate(BaseModel):
    slot_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    id: int
    parcel_id: int
    slot_id: int
    delivery_date: date
    start_time: time
    end_time: time
    status: str
    booked_at: datetime
    updated_at: datetime


class AdminBookingResponse(BaseModel):
    id: int
    parcel_id: int
    slot_id: int
    status: str
    booked_at: datetime
    updated_at: datetime
    parcel: ParcelResponse
    slot: DeliverySlotResponse


class DeliveryPartnerCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    phone: str = Field(min_length=10, max_length=20)
    vehicle_type: str = Field(default="two_wheeler", min_length=2, max_length=40)
    max_active_assignments: int = Field(default=5, ge=1, le=50)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class DeliveryPartnerResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    phone: str
    vehicle_type: str
    is_available: bool
    is_active: bool
    active_assignments: int
    max_active_assignments: int = 5


class DeliveryRouteStop(BaseModel):
    parcel_id: int
    tracking_number: str
    recipient_name: str
    city: str
    state: str
    pincode: str
    delivery_date: date
    slot_start: time
    slot_end: time
    suggested_partner_id: int | None
    suggested_partner_name: str | None
    route_sequence: int | None
    partner_active_jobs: int
    zone_key: str
    recommendation: str
    latitude: float | None = None
    longitude: float | None = None
    leg_distance_m: int | None = None
    leg_duration_seconds: int | None = None
    map_url: str | None = None


class DeliveryRoutePlanResponse(BaseModel):
    delivery_date: date
    generated_at: datetime
    total_unassigned: int
    recommended: int
    unassigned_without_partner: int
    mapping_enabled: bool = False
    routing_provider: str = "pin_prefix_heuristic"
    stops: list[DeliveryRouteStop]


class DeliveryAssignmentCreate(BaseModel):
    partner_id: int = Field(gt=0)


class DeliveryAssignmentStatus(str, Enum):
    ACCEPTED = "accepted"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryAssignmentStatusUpdate(BaseModel):
    status: DeliveryAssignmentStatus
    failure_reason: str | None = Field(default=None, min_length=3, max_length=300)

    @model_validator(mode="after")
    def require_failure_reason(self):
        if self.status == DeliveryAssignmentStatus.FAILED and not self.failure_reason:
            raise ValueError("failure_reason is required when delivery fails.")
        return self


class DeliveryEtaUpdate(BaseModel):
    estimated_delivery_start: datetime
    estimated_delivery_end: datetime

    @model_validator(mode="after")
    def validate_eta_window(self):
        if self.estimated_delivery_start.tzinfo is None or self.estimated_delivery_end.tzinfo is None:
            raise ValueError("ETA timestamps must include a timezone.")
        if self.estimated_delivery_start >= self.estimated_delivery_end:
            raise ValueError("ETA end must be later than ETA start.")
        if self.estimated_delivery_end <= datetime.now(self.estimated_delivery_end.tzinfo):
            raise ValueError("ETA window must be in the future.")
        return self


class DeliveryAssignmentResponse(BaseModel):
    id: int
    parcel_id: int
    partner_id: int
    status: str
    assigned_at: datetime
    updated_at: datetime
    tracking_number: str
    recipient_name: str
    phone: str
    address_line: str
    city: str
    state: str
    pincode: str
    delivery_date: date
    start_time: time
    end_time: time
    partner_name: str
    failure_reason: str | None = None
    delivered_at: datetime | None = None
    estimated_delivery_start: datetime | None = None
    estimated_delivery_end: datetime | None = None
    proof_recipient_name: str | None = None


class DeliveryEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    parcel_id: int
    actor_id: int
    actor_name: str
    event_type: str
    from_status: str | None
    to_status: str
    note: str | None
    created_at: datetime


class DeliveryCodeResponse(BaseModel):
    code: str
    expires_at: datetime


class DeliveryProofSubmit(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")
    recipient_name: str = Field(min_length=2, max_length=120)

    @field_validator("recipient_name")
    @classmethod
    def normalize_recipient_name(cls, value: str) -> str:
        return " ".join(value.split())


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    parcel_id: int | None
    event_type: str
    title: str
    message: str
    created_at: datetime
    read_at: datetime | None


class PhoneVerificationRequest(BaseModel):
    phone_number: str = Field(min_length=10, max_length=16)

    @field_validator("phone_number")
    @classmethod
    def normalize_indian_mobile(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) == 10:
            digits = "91" + digits
        if len(digits) != 12 or not digits.startswith("91") or digits[2] not in "6789":
            raise ValueError("Enter a valid 10-digit Indian mobile number, optionally with +91.")
        return "+" + digits


class PhoneVerificationSubmit(BaseModel):
    code: str = Field(pattern=r"^[0-9]{6}$")


class PhoneVerificationStatus(BaseModel):
    phone_number: str | None
    phone_verified: bool
    sms_notifications_consent: bool


class SmsConsentUpdate(BaseModel):
    enabled: bool


class ParcelTimelineEvent(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    status: str
    created_at: datetime
