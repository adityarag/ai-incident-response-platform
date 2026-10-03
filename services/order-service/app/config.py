"""
Configuration for the Order Service.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Order Service configuration."""

    service_name: str = "order-service"
    service_version: str = "0.1.0"

    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "info"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "incident_platform"
    postgres_user: str = "platform"
    postgres_password: str = "changeme_in_production"

    # Downstream Payment Service
    payment_service_url: str = "http://localhost:8002"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_prefix": "ORDER_", "case_sensitive": False}


def get_settings() -> Settings:
    return Settings()
