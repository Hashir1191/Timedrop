from datetime import date, datetime, time
import math
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


class OperationsAuditLogResponse(BaseModel):
    id: int
    actor_id: int
    actor_name: str
    action: str
    entity_type: str
    entity_id: int
    summary: str
    changed_fields: list[str]
    created_at: datetime


class DeliveryBlackoutCreate(BaseModel):
    delivery_date: date
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_reason(self):
        if not self.reason:
            raise ValueError("A blackout reason is required.")
        return self


class DeliveryBlackoutUpdate(BaseModel):
    reason: str | None = Field(default=None, min_length=3, max_length=255)
    is_active: bool | None = None

    @field_validator("reason")
    @classmethod
    def normalize_updated_reason(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide a reason or active status to update.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        if self.reason is not None and not self.reason:
            raise ValueError("A blackout reason cannot be blank.")
        return self


class DeliveryBlackoutStatusResponse(BaseModel):
    delivery_date: date
    is_blackout: bool
    reason: str | None = None


class DeliveryBlackoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delivery_date: date
    reason: str
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class ServiceablePincodeCreate(BaseModel):
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)

    @field_validator("city", "state")
    @classmethod
    def normalize_area_text(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_area_text(self):
        if not self.city or not self.state:
            raise ValueError("City and state cannot be blank.")
        return self


class ServiceablePincodeUpdate(BaseModel):
    pincode: str | None = Field(default=None, pattern=r"^[1-9][0-9]{5}$")
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None

    @field_validator("city", "state")
    @classmethod
    def normalize_updated_area_text(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one service area field to update.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        for field_name in ("city", "state"):
            value = getattr(self, field_name)
            if value is not None and not value:
                raise ValueError(f"{field_name} cannot be blank.")
        return self


class ServiceablePincodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pincode: str
    city: str
    state: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceabilityCheckResponse(BaseModel):
    pincode: str
    serviceable: bool
    city: str | None = None
    state: str | None = None
    message: str


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


class BulkParcelCreate(BaseModel):
    parcels: list[ParcelCreate] = Field(min_length=1, max_length=50)


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
    is_active: bool = True


class DeliverySlotUpdate(BaseModel):
    capacity: int | None = Field(default=None, ge=1, le=500)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide a new capacity or active status.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


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


class DeliveryPartnerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    vehicle_type: str | None = Field(default=None, min_length=2, max_length=40)
    max_active_assignments: int | None = Field(default=None, ge=1, le=50)
    is_available: bool | None = None
    is_active: bool | None = None

    @field_validator("full_name", "phone", "vehicle_type")
    @classmethod
    def normalize_partner_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one partner field to update.")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        for field_name in ("full_name", "phone", "vehicle_type"):
            value = getattr(self, field_name)
            if value is not None and not value:
                raise ValueError(f"{field_name} cannot be blank.")
        if self.is_active is False and self.is_available is True:
            raise ValueError("An inactive partner cannot be available for assignments.")
        return self


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
    availability_enabled: bool = False


class PartnerAvailabilityWindow(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_time <= self.start_time:
            raise ValueError("Availability end_time must be later than start_time.")
        return self


class PartnerAvailabilitySettings(BaseModel):
    enabled: bool = False
    windows: list[PartnerAvailabilityWindow] = Field(default_factory=list, max_length=28)

    @model_validator(mode="after")
    def validate_non_overlapping_windows(self):
        by_day: dict[int, list[PartnerAvailabilityWindow]] = {}
        for window in self.windows:
            by_day.setdefault(window.weekday, []).append(window)
        for weekday, windows in by_day.items():
            ordered = sorted(windows, key=lambda item: item.start_time)
            for previous, current in zip(ordered, ordered[1:]):
                if current.start_time < previous.end_time:
                    raise ValueError(f"Availability windows overlap on weekday {weekday}.")
        return self


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
    # GeoJSON coordinate order: [longitude, latitude]. Present on the first
    # stop only so each partner route path is transmitted once.
    route_geometry: list[list[float]] | None = None

    @field_validator("route_geometry")
    @classmethod
    def validate_route_geometry(cls, value):
        if value is None:
            return value
        if len(value) < 2:
            raise ValueError("Route geometry must contain at least two coordinates.")
        for coordinate in value:
            if len(coordinate) != 2:
                raise ValueError("Each route coordinate must contain longitude and latitude.")
            longitude, latitude = coordinate
            if not (math.isfinite(longitude) and math.isfinite(latitude)):
                raise ValueError("Route coordinates must be finite numbers.")
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                raise ValueError("Route coordinates are outside valid geographic bounds.")
        return value


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


class DeliveryLocationPingCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=1000)


class DeliveryLiveLocationResponse(BaseModel):
    parcel_id: int
    assignment_id: int
    location_status: str
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = None
    recorded_at: datetime | None = None
    is_live: bool
    estimated_delivery_start: datetime | None = None
    estimated_delivery_end: datetime | None = None


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
    handover_signature_required: bool = False
    handover_signed_at: datetime | None = None


class DeliveryHandoverSignatureCreate(BaseModel):
    signed_name: str = Field(min_length=2, max_length=120)
    signature_data_url: str = Field(min_length=40, max_length=350000, pattern=r"^data:image/png;base64,[A-Za-z0-9+/=]+$")

    @field_validator("signed_name")
    @classmethod
    def normalize_signer_name(cls, value: str) -> str:
        return " ".join(value.split())


class DeliveryHandoverSignatureResponse(BaseModel):
    id: int
    assignment_id: int
    parcel_id: int
    custody_event_id: int
    partner_user_id: int
    signed_name: str
    acknowledgement_text: str
    signature_sha256: str
    created_at: datetime


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
    action_url: str | None = None
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


class SupportCaseCreate(BaseModel):
    category: str = Field(pattern=r"^(missing_parcel|suspected_theft|damaged_parcel|delivery_not_received|app_bug|other)$")
    subject: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    parcel_id: int | None = Field(default=None, gt=0)

    @field_validator("subject", "description")
    @classmethod
    def normalize_support_text(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_support_text(self):
        if not self.subject or not self.description:
            raise ValueError("A subject and a description are required.")
        return self


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=2, max_length=5000)
    is_internal: bool = False

    @field_validator("body")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_message(self):
        if not self.body:
            raise ValueError("A message cannot be blank.")
        return self


class SupportCaseUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(open|triaged|in_progress|waiting_customer|resolved|closed)$")
    priority: str | None = Field(default=None, pattern=r"^(low|normal|high|urgent)$")
    assigned_to_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one support case field to update.")
        return self


class SupportCaseMessageResponse(BaseModel):
    id: int
    author_id: int
    author_name: str
    body: str
    is_internal: bool
    created_at: datetime


class SupportCaseAttachmentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    file_size: int
    sha256: str
    uploader_id: int
    is_internal: bool
    created_at: datetime


class SupportCaseResponse(BaseModel):
    id: int
    case_number: str
    customer_id: int
    customer_name: str
    parcel_id: int | None
    tracking_number: str | None
    category: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_to_id: int | None
    assigned_to_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    messages: list[SupportCaseMessageResponse] = Field(default_factory=list)
    attachments: list[SupportCaseAttachmentResponse] = Field(default_factory=list)


class DocumentVerificationResponse(BaseModel):
    valid: bool
    document_number: str
    document_type: str
    tracking_number: str
    issued_at: datetime
    sha256: str
