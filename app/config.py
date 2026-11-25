"""HealthTrack application configuration.

Settings are loaded from environment variables with sensible defaults,
so the app works out-of-the-box without any configuration file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./healthtrack.db"

    # Symptom severity bounds (1-10 inclusive)
    severity_min: int = 1
    severity_max: int = 10

    # Field length limits
    description_max_len: int = 500
    patient_id_max_len: int = 64

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
