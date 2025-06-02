from fastapi import Depends
from typing import Annotated

from fiber import SubstrateInterface


from .mapping import MappingManager, MappingSource

from .metrics import MetricsClient

from .interfaces.worker_provider import WorkerProvider

from .interfaces.database import (
    DatabaseService,
    DynamicConfigService,
    SqliteMappingSource,
)
from .validator import Validator
from .config import ValidatorSettings, load_config


substrate: SubstrateInterface | None = None
worker_provider: WorkerProvider | None = None


def get_metrics_client(
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> MetricsClient:
    return MetricsClient(config.prometheus_endpoint)


def get_mapping_source(
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> MappingSource:
    if config.mapping_source == "database":
        return SqliteMappingSource()
    raise ValueError(f"Invalid mapping source: {config.mapping_source}")


def get_mapping_manager(
    mapping_source: Annotated[MappingSource, Depends(get_mapping_source)],
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> MappingManager:
    return MappingManager(mapping_source, config.cache_ttl.total_seconds())


def get_worker_provider(
    metrics_client: Annotated[MetricsClient, Depends(get_metrics_client)],
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> WorkerProvider:
    global worker_provider
    if worker_provider is None:
        worker_provider = WorkerProvider(
            metrics_client, config.cache_ttl.total_seconds()
        )
    return worker_provider


def get_database_service(
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> DatabaseService:
    # In production, you might want to use a singleton  or DI container
    return DatabaseService(config.database_url)


def get_validator(
    config: Annotated[ValidatorSettings, Depends(load_config)],
    metrics_client: Annotated[MetricsClient, Depends(get_metrics_client)],
    mapping_manager: Annotated[MappingManager, Depends(get_mapping_manager)],
) -> Validator:
    return Validator(config, metrics_client, mapping_manager)


def get_substrate(
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> SubstrateInterface:
    global substrate
    if substrate is None:
        from fiber.chain.interface import get_substrate

        substrate = get_substrate(config.subtensor_network)
    return substrate


def get_dynamic_config_service(
    config: Annotated[ValidatorSettings, Depends(load_config)],
) -> DynamicConfigService:
    return DynamicConfigService(config.database_url)
