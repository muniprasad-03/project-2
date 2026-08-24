from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from environment variables or from the
    local .env file during development.

    Secrets must never be hardcoded in this file.
    """

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------

    ENVIRONMENT: str = "development"

    PORT: int = 8000

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    DATABASE_URL: str

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------

    SUPABASE_URL: str

    SUPABASE_KEY: str

    # ------------------------------------------------------------------
    # LLM providers
    # ------------------------------------------------------------------

    GEMINI_API_KEY: str

    GROQ_API_KEY: str = ""

    # ------------------------------------------------------------------
    # Google Cloud
    # ------------------------------------------------------------------

    GOOGLE_CLOUD_PROJECT: str = ""

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    # ------------------------------------------------------------------
    # Pydantic Settings configuration
    # ------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # CORS validator
    # ------------------------------------------------------------------

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """
        Support both JSON-list and comma-separated CORS values.

        Examples:

        CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

        or:

        CORS_ORIGINS=http://localhost:3000,http://localhost:5173
        """

        if isinstance(value, list):
            return value

        if isinstance(value, str):

            value = value.strip()

            if not value:
                return []

            # JSON format
            if value.startswith("["):
                try:
                    parsed = json.loads(value)

                    if isinstance(parsed, list):
                        return [
                            str(origin).strip()
                            for origin in parsed
                        ]

                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "CORS_ORIGINS contains invalid JSON."
                    ) from exc

            # Comma-separated format
            return [
                origin.strip()
                for origin in value.split(",")
                if origin.strip()
            ]

        raise ValueError(
            "CORS_ORIGINS must be a list or a JSON/comma-separated string."
        )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_development(self) -> bool:
        """Return True when running in development."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Return the application settings.

    lru_cache ensures that the Settings object is created only once
    during the application's lifetime.
    """
    return Settings()


settings = get_settings()