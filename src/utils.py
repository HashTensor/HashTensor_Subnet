from fiber import SubstrateInterface
from fiber.chain.fetch_nodes import get_nodes_for_netuid
from fiber.chain import models
import time
from typing import Tuple, Optional
from .constants import NETWORK_TO_NETUID, SECONDS_IN_BLOCK

# Simple in-memory cache: (key: tuple, value: (timestamp, result))
_nodes_cache: dict[
    Tuple[int, Optional[int]], Tuple[float, list[models.Node]]
] = {}
_CACHE_TTL = SECONDS_IN_BLOCK  # seconds


def get_nodes_for_netuid_cached(
    substrate: SubstrateInterface, netuid: int, block: int | None = None
) -> list[models.Node]:
    key = (netuid, block)
    now = time.time()
    if key in _nodes_cache:
        ts, result = _nodes_cache[key]
        if now - ts < _CACHE_TTL:
            return result
    result = get_nodes_for_netuid(substrate, netuid, block)
    _nodes_cache[key] = (now, result)
    return result


def is_hotkey_registered(
    hotkey: str,
    substrate: SubstrateInterface,
    netuid: int,
    block: int | None = None,
) -> bool:
    nodes = get_nodes_for_netuid_cached(substrate, netuid, block)
    for node in nodes:
        if node.hotkey == hotkey:
            return True
    return False


def verify_signature(hotkey: str, worker: str, signature: str) -> bool:
    from fiber import Keypair

    keypair = Keypair(hotkey)
    try:
        return keypair.verify(worker, bytes.fromhex(signature))
    except (TypeError, ValueError):
        return False


def get_netuid(network: str) -> int:
    try:
        return NETWORK_TO_NETUID[network]
    except KeyError:
        raise ValueError(f"Netuid not found for network: {network}")
