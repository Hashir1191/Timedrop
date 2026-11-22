import base64
from datetime import date, datetime, time, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    DeliveryAssignment, DeliveryBooking, DeliveryPartner, DeliverySlot,
    Parcel, ParcelCustodyEvent, User,
)
from app.security import hash_password


def test_partner_must_sign_the_recorded_release_before_accepting_assignment():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    admin = User(email="handover-admin@example.com", full_name="Operations Admin", password_hash=hash_password("StrongAdminPassword123!"), role="admin")
    partner_user = User(email="handover-partner@example.com", full_name="Delivery Partner", password_hash=hash_password("StrongPartnerPassword123!"), role="delivery_partner")
    db.add_all([admin, partner_user])
    db.flush()
    partner = DeliveryPartner(user_id=partner_user.id, phone="9876543210")
    parcel = Parcel(
        owner_id=admin.id, tracking_number="TD-HANDOVER-001", recipient_name="Parcel Recipient",
        phone="9876543211", address_line="10 Test Road", city="Prayagraj",
        state="Uttar Pradesh", pincode="211001", status="registered",
    )
    slot = DeliverySlot(delivery_date=date.today()+timedelta(days=3), start_time=time(10), end_time=time(12), capacity=10)
    db.add_all([partner, parcel, slot])
    db.flush()
    db.add(DeliveryBooking(parcel_id=parcel.id, slot_id=slot.id))
    assignment = DeliveryAssignment(parcel_id=parcel.id, partner_id=partner.id, status="assigned")
    db.add(assignment)
    db.flush()
    now = datetime.now(timezone.utc)
    db.add_all([
        ParcelCustodyEvent(parcel_id=parcel.id, actor_id=admin.id, event_type="received", package_condition="intact", received_from="Sender", created_at=now-timedelta(minutes=2)),
        ParcelCustodyEvent(parcel_id=parcel.id, actor_id=admin.id, event_type="released", handed_to=partner_user.full_name, note="Released to assigned partner", created_at=now-timedelta(minutes=1)),
    ])
    assignment_id = assignment.id
    db.commit()
    db.close()

    def override_get_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            login = client.post("/api/v1/auth/login", json={"email":"handover-partner@example.com","password":"StrongPartnerPassword123!"})
            headers = {"Authorization":"Bearer "+login.json()["access_token"]}
            rows = client.get("/api/v1/delivery/my-assignments", headers=headers)
            assert rows.status_code == 200
            assert rows.json()[0]["handover_signature_required"] is True

            blocked = client.patch(f"/api/v1/delivery/assignments/{assignment_id}/status", headers=headers, json={"status":"accepted"})
            assert blocked.status_code == 409

            invalid = client.post(f"/api/v1/delivery/assignments/{assignment_id}/handover-signature", headers=headers, json={
                "signed_name":"Delivery Partner",
                "signature_data_url":"data:image/png;base64,not-a-valid-png",
            })
            assert invalid.status_code == 422

            image = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-signature-bytes").decode("ascii")
            signed = client.post(f"/api/v1/delivery/assignments/{assignment_id}/handover-signature", headers=headers, json={
                "signed_name":"Delivery Partner",
                "signature_data_url":"data:image/png;base64,"+image,
            })
            assert signed.status_code == 201
            assert signed.json()["signature_sha256"]
            assert signed.json()["acknowledgement_text"].startswith("I confirm that I have physically received")

            duplicate = client.post(f"/api/v1/delivery/assignments/{assignment_id}/handover-signature", headers=headers, json={
                "signed_name":"Delivery Partner",
                "signature_data_url":"data:image/png;base64,"+image,
            })
            assert duplicate.status_code == 409

            accepted = client.patch(f"/api/v1/delivery/assignments/{assignment_id}/status", headers=headers, json={"status":"accepted"})
            assert accepted.status_code == 200
            assert accepted.json()["handover_signature_required"] is False
            assert accepted.json()["handover_signed_at"] is not None
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
