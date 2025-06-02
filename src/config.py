# config.py
# Loads configuration using pydantic-settings (BaseSettings) with Pydantic v2 syntax

from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from fiber.constants import FINNEY_NETWORK, FINNEY_TEST_NETWORK
from .utils import get_netuid


class ValidatorSettings(BaseSettings):
    prometheus_endpoint: str = "http://localhost:9090"
    mapping_source: Literal[
        "database", "rest", "github", "evm", "json_file"
    ] = "database"
    rating_weight: float = 1.0
    window: timedelta = timedelta(minutes=60)
    database_url: str = "sqlite:///data/mapping.db"
    cache_ttl: timedelta = timedelta(seconds=15)
    kaspa_pool_owner_wallet: str
    subtensor_network: Literal[FINNEY_NETWORK, FINNEY_TEST_NETWORK] = FINNEY_NETWORK  # type: ignore
    registration_time_tolerance: timedelta = timedelta(minutes=1)
    verify_signature: bool = True
    set_weights_interval: timedelta = timedelta(minutes=60)

    wallet_name: str = "default"
    wallet_hotkey: str = "default"
    wallet_path: str = "~/.bittensor/wallets/"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def netuid(self) -> int:
        return get_netuid(self.subtensor_network)


def load_config() -> ValidatorSettings:
    """Load config from environment variables and .env file."""
    return ValidatorSettings()
