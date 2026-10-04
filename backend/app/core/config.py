from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_HOSTS = ("localhost", "127.0.0.1")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "DronaAI.fit API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    # Local development only: HTTP proxy for networks that block port 5432.
    OUTBOUND_PROXY: str = ""

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # Auth cookie. Cross-site deployments need SECURE=true and SAMESITE=none.
    COOKIE_NAME: str = "fitness_session"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # Comma-separated list of allowed origins
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @model_validator(mode="after")
    def check_production_settings(self) -> "Settings":
        """Refuse to start in production with settings that would break or weaken the deploy."""
        if not self.is_production:
            return self

        problems = []
        if len(self.JWT_SECRET_KEY) < 32 or "change_me" in self.JWT_SECRET_KEY:
            problems.append("JWT_SECRET_KEY must be a random string of at least 32 characters")
        if not self.COOKIE_SECURE:
            problems.append("COOKIE_SECURE must be true")
        if self.OUTBOUND_PROXY:
            problems.append("OUTBOUND_PROXY is for local development only")
        for name in ("DATABASE_URL", "DATABASE_URL_SYNC", "BACKEND_CORS_ORIGINS"):
            if any(host in getattr(self, name) for host in LOCAL_HOSTS):
                problems.append(f"{name} must not point at localhost")
        if not self.cors_origins or any(not o.startswith("https://") for o in self.cors_origins):
            problems.append("BACKEND_CORS_ORIGINS must list explicit https:// origins (no *)")
        if "ssl=require" not in self.DATABASE_URL:
            problems.append("DATABASE_URL must end with ?ssl=require")
        if "sslmode=require" not in self.DATABASE_URL_SYNC:
            problems.append("DATABASE_URL_SYNC must end with ?sslmode=require")

        if problems:
            raise ValueError("Unsafe production settings:\n- " + "\n- ".join(problems))
        return self


settings = Settings()  # type: ignore[call-arg]
