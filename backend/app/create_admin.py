import os
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


def main() -> None:
    email = os.getenv("TIMEDROP_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("TIMEDROP_ADMIN_PASSWORD", "")
    full_name = os.getenv("TIMEDROP_ADMIN_NAME", "TimeDrop Operations")

    if not email or not password:
        raise SystemExit(
            "Set TIMEDROP_ADMIN_EMAIL and TIMEDROP_ADMIN_PASSWORD before running this command."
        )
    if len(password) < 12:
        raise SystemExit("Admin password must be at least 12 characters long.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            raise SystemExit(f"An account already exists for {email}. No changes made.")

        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Operations administrator created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
