import os
import secrets
import tempfile
from getpass import getpass
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password

PLACEHOLDER_ADMIN_EMAIL = "your-email@example.com"


def rotate_env_secret(env_path: Path) -> None:
    """Replace SECRET_KEY in the project .env file without printing the new value."""
    if not env_path.is_file():
        raise SystemExit(
            f"{env_path} was not found. Run this command from the repository root."
        )

    lines = env_path.read_text(encoding="utf-8").splitlines()
    secret_indexes = [
        index for index, line in enumerate(lines)
        if line.strip().startswith("SECRET_KEY=")
    ]
    if not secret_indexes:
        raise SystemExit("No SECRET_KEY entry was found in .env.")

    new_secret = secrets.token_urlsafe(48)
    first_index = secret_indexes[0]
    lines[first_index] = f"SECRET_KEY={new_secret}"
    for index in reversed(secret_indexes[1:]):
        del lines[index]

    content = "\n".join(lines) + "\n"
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n",
            dir=env_path.parent, delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_name = temp_file.name
        os.replace(temp_name, env_path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> None:
    print("TimeDrop admin security maintenance")
    email = input("Existing real admin email: ").strip().lower()
    if not email or email == PLACEHOLDER_ADMIN_EMAIL:
        raise SystemExit("Enter your real admin email, not the placeholder email.")

    password = getpass("New admin password (minimum 12 characters): ")
    confirmation = getpass("Confirm new admin password: ")
    if len(password) < 12:
        raise SystemExit("Admin password must be at least 12 characters long.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    env_path = Path(".env")
    if not env_path.is_file():
        raise SystemExit("Run this command from the repository root; .env was not found.")
    if not any(line.strip().startswith("SECRET_KEY=") for line in env_path.read_text(encoding="utf-8").splitlines()):
        raise SystemExit("No SECRET_KEY entry was found in .env.")

    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == email))
        if admin is None:
            raise SystemExit(f"No account exists for {email}.")
        if admin.role != "admin" or not admin.is_active:
            raise SystemExit("The selected account must be an active operations admin.")

        placeholder = db.scalar(
            select(User).where(User.email == PLACEHOLDER_ADMIN_EMAIL)
        )

        # Rotate the signing key to invalidate previously issued access tokens.
        rotate_env_secret(env_path)

        admin.password_hash = hash_password(password)
        if placeholder is not None:
            if placeholder.id == admin.id:
                raise SystemExit("Refusing to disable the selected real admin account.")
            placeholder.is_active = False
            placeholder.password_hash = hash_password(secrets.token_urlsafe(48))

        db.commit()
        print(f"Password updated for {email}.")
        if placeholder is not None:
            print("The placeholder admin account has been deactivated.")
        else:
            print("No placeholder admin account was found.")
        print("The .env JWT signing key was rotated; restart the API server.")
        print("Previously issued access tokens are now invalid.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
