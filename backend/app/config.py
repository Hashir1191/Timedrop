from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "TimeDrop API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./timedrop.db"
    secret_key: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    resend_api_key: str = ""
    notification_from_email: str = "TimeDrop <onboarding@resend.dev>"
    notification_worker_poll_seconds: int = 5
    notification_max_attempts: int = 5
    msg91_auth_key: str = ""
    msg91_flow_template_id: str = ""
    msg91_otp_template_id: str = ""
    sms_notifications_enabled: bool = False
    phone_otp_expose_in_development: bool = True
    phone_otp_expire_minutes: int = 5
    phone_otp_max_attempts: int = 5
    route_mapping_enabled: bool = False
    route_geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    route_router_url: str = "https://router.project-osrm.org/route/v1/driving"
    route_provider_user_agent: str = "TimeDrop/1.0 (route-planning; configure-contact-email)"
    route_geocode_timeout_seconds: float = 8.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

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
