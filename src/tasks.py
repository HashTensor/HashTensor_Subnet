import asyncio
import time

from fiber import Keypair, SubstrateInterface

from .set_weights import set_weights

from .config import ValidatorSettings
from .validator import Validator
from fiber.utils import get_logger

from .interfaces.database import DynamicConfigService

logger = get_logger(__name__)


async def set_weights_task(
    dynamic_config_service: DynamicConfigService,
    config: ValidatorSettings,
    validator: Validator,
    substrate: SubstrateInterface,
    keypair: Keypair,
):
    interval = config.set_weights_interval.total_seconds()
    last_set = dynamic_config_service.get_last_set_weights_time()
    now = time.time()
    if now - last_set < interval:
        logger.debug(
            f"Not setting weights because it was set less than {interval} seconds ago"
        )
        return

    logger.info(f"Setting weights for {config.netuid}")
    # Compute ratings and set weights
    ratings = await validator.compute_ratings()
    success = set_weights(
        substrate=substrate,
        keypair=keypair,
        netuid=config.netuid,
        hotkey_to_rating=ratings,
    )
    if success:
        dynamic_config_service.set_last_set_weights_time(now)
    else:
        logger.error("Failed to set weights")
