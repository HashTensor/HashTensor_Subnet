from fiber import SubstrateInterface
from fiber.chain.fetch_nodes import get_nodes_for_netuid
from fiber.chain import models
import time
from typing import Tuple, Optional
from .constants import NETWORK_TO_NETUID, SECONDS_IN_BLOCK
import struct
import socket
import aiohttp
import json
from . import __version__ as version

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


def parse_ip(ip_int: int):
    ip_bytes = struct.pack(">I", ip_int)  # Little-endian unsigned int
    return socket.inet_ntoa(ip_bytes)


def fix_node_ip(node):
    node.ip = parse_ip(int(node.ip))
    return node


async def is_hashtensor_validator(ip, port):
    url = f"http://{ip}:{port}/openapi.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                info = data.get("info", {})
                return (
                    info.get("title") == "HashTensor Validator"
                    and info.get("version") == version
                )
    except Exception:
        return False


async def fetch_hotkey_workers_from_validator(session, ip, port, since_timestamp=0.0):
    url = f"http://{ip}:{port}/hotkey_workers"
    params = {
        "since_timestamp": since_timestamp
    }
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                return []
            return await resp.json()
    except Exception:
        return []


def get_stake_weights(node: models.Node) -> float:
    return node.alpha_stake + 0.18 * node.tao_stake
