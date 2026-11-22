from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


def test_customer_support_case_is_private_and_admin_can_reply():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add(User(email="case-admin@example.com", full_name="Case Admin", password_hash=hash_password("StrongAdminPassword123!"), role="admin"))
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
            client.post("/api/v1/auth/register", json={"email":"case-owner@example.com","full_name":"Case Owner","password":"CustomerPassword123!"})
            login = client.post("/api/v1/auth/login", json={"email":"case-owner@example.com","password":"CustomerPassword123!"})
            customer = {"Authorization":"Bearer "+login.json()["access_token"]}
            created = client.post("/api/v1/support/cases", headers=customer, json={
                "category":"missing_parcel",
                "subject":"Parcel has not arrived",
                "description":"The parcel has not arrived and I need the delivery team to investigate.",
            })
            assert created.status_code == 201
            case_id = created.json()["id"]
            other_login = client.post("/api/v1/auth/register", json={"email":"case-other@example.com","full_name":"Other Customer","password":"CustomerPassword123!"})
            assert other_login.status_code == 201
            other_token = client.post("/api/v1/auth/login", json={"email":"case-other@example.com","password":"CustomerPassword123!"}).json()["access_token"]
            assert client.get("/api/v1/support/cases/"+str(case_id), headers={"Authorization":"Bearer "+other_token}).status_code == 404

            admin_login = client.post("/api/v1/auth/login", json={"email":"case-admin@example.com","password":"StrongAdminPassword123!"})
            admin = {"Authorization":"Bearer "+admin_login.json()["access_token"]}
            note = client.post("/api/v1/support/admin/cases/"+str(case_id)+"/messages", headers=admin, json={
                "body":"Internal investigation note for the support team.",
                "is_internal":True,
            })
            assert note.status_code == 200
            customer_view = client.get("/api/v1/support/cases/"+str(case_id), headers=customer).json()
            assert all(not message["is_internal"] for message in customer_view["messages"])
            assert "Internal investigation" not in str(customer_view["messages"])
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_support_evidence_is_private_scoped_and_type_validated():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    db = sessions()
    db.add(User(email="evidence-admin@example.com", full_name="Evidence Admin", password_hash=hash_password("StrongAdminPassword123!"), role="admin"))
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
            client.post("/api/v1/auth/register", json={"email":"evidence-owner@example.com","full_name":"Evidence Owner","password":"CustomerPassword123!"})
            login = client.post("/api/v1/auth/login", json={"email":"evidence-owner@example.com","password":"CustomerPassword123!"})
            owner = {"Authorization":"Bearer "+login.json()["access_token"]}
            created = client.post("/api/v1/support/cases", headers=owner, json={
                "category":"missing_parcel","subject":"Parcel missing from doorstep",
                "description":"The parcel was marked delivered but is not at my address.",
            })
            case_id = created.json()["id"]
            public_file = client.post(
                f"/api/v1/support/cases/{case_id}/attachments",
                headers=owner,
                files={"file":("delivery-photo.pdf",b"%PDF-1.4\nproof document","application/pdf")},
            )
            assert public_file.status_code == 201
            assert len(public_file.json()["attachments"]) == 1
            public_attachment_id = public_file.json()["attachments"][0]["id"]

            admin_login = client.post("/api/v1/auth/login", json={"email":"evidence-admin@example.com","password":"StrongAdminPassword123!"})
            admin = {"Authorization":"Bearer "+admin_login.json()["access_token"]}
            private_file = client.post(
                f"/api/v1/support/admin/cases/{case_id}/attachments",
                headers=admin,
                data={"is_internal":"true"},
                files={"file":("internal-note.pdf",b"%PDF-1.4\nprivate note","application/pdf")},
            )
            assert private_file.status_code == 201
            assert len(private_file.json()["attachments"]) == 2

            customer_view = client.get(f"/api/v1/support/cases/{case_id}", headers=owner).json()
            assert len(customer_view["attachments"]) == 1
            assert customer_view["attachments"][0]["filename"] == "delivery-photo.pdf"
            download = client.get(
                f"/api/v1/support/cases/{case_id}/attachments/{public_attachment_id}",
                headers=owner,
            )
            assert download.status_code == 200
            assert download.content.startswith(b"%PDF-")
            assert len(download.headers["x-evidence-sha256"]) == 64

            admin_view = client.get(f"/api/v1/support/admin/cases/{case_id}", headers=admin).json()
            private_id = next(item["id"] for item in admin_view["attachments"] if item["is_internal"])
            hidden = client.get(f"/api/v1/support/cases/{case_id}/attachments/{private_id}", headers=owner)
            assert hidden.status_code == 404

            rejected = client.post(
                f"/api/v1/support/cases/{case_id}/attachments",
                headers=owner,
                files={"file":("payload.exe",b"MZ-not-a-pdf","application/octet-stream")},
            )
            assert rejected.status_code == 415
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
