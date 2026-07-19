"""Application configuration.

Loaded from environment variables (with sensible local-dev defaults) via
pydantic-settings.  Mirrors the configuration surface of the original
Node backend: a database URL, a JWT signing secret, and the directory
where uploaded files are stored.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Async SQLAlchemy URL (asyncpg driver). Overridden in Docker.
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobility"

    # Same default secret as the legacy backend so behaviour is identical.
    JWT_SECRET: str = "taw-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_HOURS: int = 24

    # Directory (relative to the working dir) where uploads are written.
    UPLOAD_DIR: str = "uploads"

    @property
    def sync_database_url(self) -> str:
        """Synchronous URL used by Alembic (psycopg2 instead of asyncpg)."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


settings = Settings()
