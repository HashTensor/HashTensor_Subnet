import asyncio
import json
from fiber import Keypair, SubstrateInterface
from fiber.chain import weights
from fiber.utils import get_logger

from .dependencies import (
    get_mapping_manager,
    get_mapping_source,
    get_metrics_client,
    get_validator,
)

from . import __spec_version__


logger = get_logger(__name__)


from .utils import get_nodes_for_netuid_cached


def set_weights(
    hotkey_to_rating: dict[str, float],
    substrate: SubstrateInterface,
    keypair: Keypair,
    netuid: int,
) -> bool:
    if not hotkey_to_rating:
        logger.warning("No ratings provided, skipping weight set")
        return

    if not any(hotkey_to_rating.values()):
        logger.warning("All ratings are 0, skipping weight set")
        return

    nodes = get_nodes_for_netuid_cached(substrate, netuid)
    try:
        validator_node_id = next(
            node for node in nodes if node.hotkey == keypair.ss58_address
        ).node_id
    except StopIteration:
        message = f"Validator node not found for hotkey {keypair.ss58_address}"
        logger.error(message)
        raise ValueError(message)

    logger.info(f"Validator node id: {validator_node_id}")

    node_ids = [node.node_id for node in nodes]
    node_weights = [hotkey_to_rating.get(node.hotkey, 0) for node in nodes]

    return weights.set_node_weights(
        substrate=substrate,
        keypair=keypair,
        node_ids=node_ids,
        node_weights=node_weights,
        netuid=netuid,
        validator_node_id=validator_node_id,
        version_key=__spec_version__,
        wait_for_inclusion=True,
        wait_for_finalization=True,
    )


async def __main__():
    from fiber.chain import chain_utils
    from .config import load_config
    from .dependencies import get_substrate

    config = load_config()
    substrate = get_substrate(config)
    metrics_client = get_metrics_client(config)
    mapping_source = get_mapping_source(config)
    mapping_manager = get_mapping_manager(mapping_source, config)
    validator = get_validator(config, metrics_client, mapping_manager)
    keypair = chain_utils.load_hotkey_keypair(
        wallet_name=config.wallet_name, hotkey_name=config.wallet_hotkey
    )

    ratings = await validator.compute_ratings()
    logger.info(f"Computed ratings: {json.dumps(ratings, indent=4)}")

    set_weights(
        substrate=substrate,
        keypair=keypair,
        netuid=config.netuid,
        hotkey_to_rating=ratings,
    )


if __name__ == "__main__":
    asyncio.run(__main__())
