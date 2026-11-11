from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TimeDrop API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./timedrop.db"
    # Development-only fallback. Production startup rejects this value.
    secret_key: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_for_startup(self) -> None:
        if self.app_env.lower() == "production":
            if self.secret_key == "development-only-change-this-secret" or len(self.secret_key) < 32:
                raise RuntimeError("Production requires a SECRET_KEY of at least 32 characters.")
            if self.database_url.startswith("sqlite"):
                raise RuntimeError("Production must use PostgreSQL; SQLite is only supported for local development.")


settings = Settings()
