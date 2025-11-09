"""Application configuration using Pydantic settings."""

import logging
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: Literal["development", "production"] = "development"
    log_level: str = "INFO"

    # Supabase Configuration
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Database Configuration
    database_url: str

    # Eleven Labs API Configuration
    eleven_labs_api_key: str

    # FSRS Parameters
    fsrs_desired_retention: float = 0.9
    fsrs_learning_steps: str = "1,5"  # minutes (1 min for immediate retry, 5 mins for same-session review)
    fsrs_maximum_interval: int = 365  # days
    max_new_cards_per_day: int = 10
    max_reviews_per_day: int = 20  # Total reviews per day (new + due cards)

    # CORS Settings
    cors_origins: str = "http://localhost:5173"  # comma-separated

    @property
    def learning_steps_list(self) -> list[int]:
        """Get learning steps as a list of integers."""
        return [int(x.strip()) for x in self.fsrs_learning_steps.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list of strings."""
        return [x.strip() for x in self.cors_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()


# Configure logging
def setup_logging() -> None:
    """Configure application logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# Initialize logging on module import
setup_logging()
