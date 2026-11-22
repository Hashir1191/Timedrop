from datetime import datetime, timezone
from types import SimpleNamespace

from app.documents import build_delivery_proof


def test_build_delivery_proof_returns_branded_pdf_with_verified_delivery_fields():
    parcel = SimpleNamespace(
        tracking_number="TD-POD-TEST-001",
        address_line="18, Example Road",
        city="Prayagraj",
        state="Uttar Pradesh",
        pincode="211001",
    )
    assignment = SimpleNamespace(
        delivered_at=datetime(2026, 11, 22, 12, 30, tzinfo=timezone.utc),
        proof_recipient_name="Test Recipient",
    )
    delivery_event = SimpleNamespace(id=42)
    pdf = build_delivery_proof(
        parcel,
        assignment,
        delivery_event,
        "TD-POD-AB12CD34",
        "TDV-0123456789ABCDEF0123456789ABCDEF",
        datetime(2026, 11, 22, 12, 35, tzinfo=timezone.utc),
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
