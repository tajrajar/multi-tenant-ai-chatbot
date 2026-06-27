"""
Configuration loader for the application.

This module loads all required environment variables using Pydantic,
validates them strictly, and fails with a clear error message if
anything is missing or invalid. No secrets are ever hardcoded here.
"""

from functools import lru_cache
from typing import List, Union

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Name of the application (used in FastAPI docs / title)
    APP_NAME: str = Field(..., min_length=1)

    # Must be one of these 3 values only (prevents typos like "prod")
    ENVIRONMENT: str = Field(..., pattern="^(development|staging|production)$")

    # Accepts EITHER a comma-separated string OR a JSON list from .env
    # (the validator below converts it into a clean Python list either way)
    ALLOWED_ORIGINS: Union[str, List[str]]

    # Database connection string (Postgres/Supabase later in Ticket-002)
    DATABASE_URL: str = Field(..., min_length=1)

    # Used for signing/encryption — must be long and random
    SECRET_KEY: str = Field(..., min_length=32)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def parse_allowed_origins(cls, value):
        """
        Normalizes ALLOWED_ORIGINS into a clean list of strings.

        Supports two formats in .env:
        1. Comma-separated:  ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:5173
        2. JSON array:       ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:5173"]
        """
        if isinstance(value, str):
            value = value.strip()

            # Case: looks like a JSON array -> parse it as JSON
            if value.startswith("[") and value.endswith("]"):
                import json
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError as exc:
                    raise ValueError("Invalid JSON format for ALLOWED_ORIGINS") from exc

            # Case: comma-separated string -> split and clean whitespace
            return [origin.strip() for origin in value.split(",") if origin.strip()]

        # Case: already a list (e.g. passed directly in code/tests)
        if isinstance(value, list):
            return value

        raise ValueError("ALLOWED_ORIGINS must be a list or comma-separated string")


@lru_cache
def get_settings() -> Settings:
    """
    Loads and caches the Settings object.
    Raises a clear RuntimeError listing exactly which env vars are missing,
    instead of a confusing Pydantic traceback.
    """
    try:
        return Settings()
    except ValidationError as exc:
        missing = []
        for error in exc.errors():
            if error.get("type") == "missing":
                field = ".".join(str(v) for v in error["loc"])
                missing.append(field)

        if missing:
            fields = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Missing required environment variables: {fields}"
            ) from exc

        raise RuntimeError(f"Configuration validation failed: {exc}") from exc


# Singleton settings instance used throughout the app
settings = get_settings()