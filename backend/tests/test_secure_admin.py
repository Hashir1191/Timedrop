from pathlib import Path

from app.secure_admin import rotate_env_secret


def test_rotate_env_secret_replaces_secret_and_removes_duplicates(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=development\n"
        "SECRET_KEY=old-secret\n"
        "JWT_ALGORITHM=HS256\n"
        "SECRET_KEY=duplicate-secret\n",
        encoding="utf-8",
    )

    rotate_env_secret(env_file)

    lines = env_file.read_text(encoding="utf-8").splitlines()
    secret_lines = [line for line in lines if line.startswith("SECRET_KEY=")]

    assert len(secret_lines) == 1
    assert secret_lines[0] != "SECRET_KEY=old-secret"
    assert secret_lines[0] != "SECRET_KEY=duplicate-secret"
    assert "APP_ENV=development" in lines
    assert "JWT_ALGORITHM=HS256" in lines
