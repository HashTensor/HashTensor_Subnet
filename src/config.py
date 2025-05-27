# config.py
# Loads configuration using pydantic-settings (BaseSettings) with Pydantic v2 syntax

from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class ValidatorSettings(BaseSettings):
    prometheus_endpoint: str = "http://localhost:9090"
    mapping_source: Literal[
        "database", "rest", "github", "evm", "json_file"
    ] = "database"
    rating_weight: float = 1.0
    window: timedelta = timedelta(minutes=60)
    database_url: str = "sqlite:///data/mapping.db"
    cache_ttl: timedelta = timedelta(seconds=15)

    model_config = SettingsConfigDict(env_file=".env")


def load_config() -> ValidatorSettings:
    """Load config from environment variables and .env file."""
    return ValidatorSettings()
