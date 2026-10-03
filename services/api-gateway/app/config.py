"""
Configuration for the API Gateway service.

Uses Pydantic Settings to load from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API Gateway configuration."""

    # Service identity
    service_name: str = "api-gateway"
    service_version: str = "0.1.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "incident_platform"
    postgres_user: str = "platform"
    postgres_password: str = "changeme_in_production"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_prefix": "", "case_sensitive": False}


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
