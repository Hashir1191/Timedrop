from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ParcelDocument, ServiceablePincode, User
from app.security import hash_password


def test_customer_registration_automatically_issues_private_verifiable_pdf_receipt():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add(User(email="receipt-admin@example.com", full_name="Receipt Admin", password_hash=hash_password("StrongAdminPassword123!"), role="admin"))
    db.add(ServiceablePincode(pincode="211001", city="Prayagraj", state="Uttar Pradesh"))
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
            client.post("/api/v1/auth/register", json={"email":"receipt-owner@example.com","full_name":"Receipt Owner","password":"CustomerPassword123!"})
            login = client.post("/api/v1/auth/login", json={"email":"receipt-owner@example.com","password":"CustomerPassword123!"})
            owner = {"Authorization":"Bearer "+login.json()["access_token"]}
            created = client.post("/api/v1/parcels/", headers=owner, json={
                "tracking_number":"TD-RECEIPT-001","recipient_name":"Receipt Owner",
                "phone":"9876543210","address_line":"12 Example Road",
                "city":"Prayagraj","state":"Uttar Pradesh","pincode":"211001",
            })
            assert created.status_code == 201
            parcel_id = created.json()["id"]

            pdf = client.get(f"/api/v1/parcels/{parcel_id}/receipt.pdf", headers=owner)
            assert pdf.status_code == 200
            assert pdf.headers["content-type"].startswith("application/pdf")
            assert pdf.content.startswith(b"%PDF")
            assert pdf.headers["x-document-number"].startswith("TD-R-")
            assert len(pdf.headers["x-document-sha256"]) == 64

            session = sessions()
            receipt = session.scalar(select(ParcelDocument).where(ParcelDocument.parcel_id == parcel_id))
            assert receipt is not None
            assert receipt.sha256 == pdf.headers["x-document-sha256"]
            verified = client.get("/api/v1/documents/verify/"+receipt.verification_code)
            assert verified.status_code == 200
            assert verified.json()["valid"] is True
            assert verified.json()["tracking_number"] == "TD-RECEIPT-001"
            assert "address" not in verified.json()
            session.close()

            client.post("/api/v1/auth/register", json={"email":"receipt-other@example.com","full_name":"Other User","password":"CustomerPassword123!"})
            other_login = client.post("/api/v1/auth/login", json={"email":"receipt-other@example.com","password":"CustomerPassword123!"})
            other = {"Authorization":"Bearer "+other_login.json()["access_token"]}
            assert client.get(f"/api/v1/parcels/{parcel_id}/receipt.pdf", headers=other).status_code == 404
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
