from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql://ois_user:ois_pass@localhost:5432/ois_discovery"

    # CORS — comma-separated list of allowed origins, or "*" for all
    CORS_ORIGINS: str = "*"

    # Challenge TTL in seconds
    CHALLENGE_TTL_SECONDS: int = 300

    # Whether to enforce origin validation in WebAuthn assertion verification.
    # Set to False in dev if you need to cross origins during testing.
    WEBAUTHN_VERIFY_ORIGIN: bool = True

    # Admin API key for protected admin endpoints. Generate with: openssl rand -hex 32
    ADMIN_API_KEY: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
