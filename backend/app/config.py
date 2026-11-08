from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TimeDrop API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    # Replace this development-only value with a long random secret in .env.
    secret_key: str = "development-only-change-this-secret-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
