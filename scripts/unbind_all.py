import argparse
import os
import socket
import struct
import asyncio
import json
import time
import sys

# Only keep needed constants
FINNEY_NETWORK = "finney"
FINNEY_TEST_NETWORK = "test"
FINNEY_SUBTENSOR_ADDRESS = "wss://entrypoint-finney.opentensor.ai:443"
FINNEY_TEST_SUBTENSOR_ADDRESS = "wss://test.finney.opentensor.ai:443/"

SS58_FORMAT = 42

SUBTENSOR_NETWORK_TO_SUBTENSOR_ADDRESS = {
    FINNEY_NETWORK: FINNEY_SUBTENSOR_ADDRESS,
    FINNEY_TEST_NETWORK: FINNEY_TEST_SUBTENSOR_ADDRESS,
}


FINNEY_NETUID = 16
FINNEY_TEST_NETUID = 368

NETWORK_TO_NETUID = {
    FINNEY_NETWORK: FINNEY_NETUID,
    FINNEY_TEST_NETWORK: FINNEY_TEST_NETUID,
}


def check_dependencies():
    required_packages = {
        "bittensor_wallet": "bittensor-wallet",
        "async_substrate_interface": "async-substrate-interface",
        "scalecodec": "scalecodec",
        "aiohttp": "aiohttp",
    }

    missing_packages = []
    for module, package in required_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(
            "Error: Missing required packages. Please install them using pip:"
        )
        print(f"pip install {' '.join(missing_packages)}")
        sys.exit(1)


check_dependencies()

import aiohttp
from bittensor_wallet import Wallet, Config
from async_substrate_interface import AsyncSubstrateInterface
from scalecodec.utils.ss58 import ss58_encode


def get_chain_endpoint(
    subtensor_network: str | None, subtensor_address: str | None
) -> str:
    if subtensor_network is None and subtensor_address is None:
        raise ValueError(
            "subtensor_network and subtensor_address cannot both be None"
        )
    if subtensor_address is not None:
        print(f"Using chain address: {subtensor_address}")
        return subtensor_address
    if subtensor_network not in SUBTENSOR_NETWORK_TO_SUBTENSOR_ADDRESS:
        raise ValueError(f"Unrecognized chain network: {subtensor_network}")
    subtensor_address = SUBTENSOR_NETWORK_TO_SUBTENSOR_ADDRESS[
        subtensor_network
    ]
    print(
        f"Using the chain network: {subtensor_network} and therefore chain address: {subtensor_address}"
    )
    return subtensor_address


def get_substrate(
    subtensor_network: str | None = FINNEY_NETWORK,
    subtensor_address: str | None = None,
) -> AsyncSubstrateInterface:
    subtensor_address = get_chain_endpoint(
        subtensor_network, subtensor_address
    )
    substrate = AsyncSubstrateInterface(
        ss58_format=SS58_FORMAT,
        use_remote_preset=True,
        url=subtensor_address,
    )
    return substrate


def ss58_encode_address(
    address: list[int] | list[list[int]], ss58_format: int = SS58_FORMAT
) -> str:
    if not isinstance(address[0], int):
        address = address[0]
    return ss58_encode(bytes(address).hex(), ss58_format)


def parse_ip(ip_int: int):
    ip_bytes = struct.pack(">I", ip_int)  # Little-endian unsigned int
    return socket.inet_ntoa(ip_bytes)


async def get_nodes_for_uid(
    substrate: AsyncSubstrateInterface, netuid: int, block: int | None = None
):
    block_hash = (
        await substrate.get_block_hash(block) if block is not None else None
    )
    response = await substrate.runtime_call(
        api="SubnetInfoRuntimeApi",
        method="get_metagraph",
        params=[netuid],
        block_hash=block_hash,
    )
    metagraph = response.value
    nodes = []
    for uid in range(len(metagraph["hotkeys"])):
        axon = metagraph["axons"][uid]
        node = dict(
            hotkey=ss58_encode_address(metagraph["hotkeys"][uid], SS58_FORMAT),
            coldkey=ss58_encode_address(
                metagraph["coldkeys"][uid], SS58_FORMAT
            ),
            node_id=uid,
            incentive=metagraph["incentives"][uid],
            netuid=metagraph["netuid"],
            alpha_stake=metagraph["alpha_stake"][uid] * 10**-9,
            tao_stake=metagraph["tao_stake"][uid] * 10**-9,
            stake=metagraph["total_stake"][uid] * 10**-9,
            trust=metagraph["trust"][uid],
            vtrust=metagraph["dividends"][uid],
            last_updated=float(metagraph["last_update"][uid]),
            ip=parse_ip(axon["ip"]),
            ip_type=axon["ip_type"],
            port=axon["port"],
            protocol=axon["protocol"],
        )
        nodes.append(node)
    return nodes


async def is_hashtensor_validator(node):
    url = f"http://{node['ip']}:{node['port']}/openapi.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                return (
                    data.get("info", {}).get("title") == "HashTensor Validator"
                )
    except Exception:
        return False


async def get_validators(
    substrate: AsyncSubstrateInterface, netuid: int, block: int | None = None
) -> list[dict]:
    nodes = await get_nodes_for_uid(substrate, netuid, block)
    # Filter nodes with a real IP
    real_nodes = [node for node in nodes if node["ip"] != "0.0.0.0"]
    # Run all checks concurrently
    results = (
        await asyncio.gather(
            *(is_hashtensor_validator(node) for node in real_nodes)
        )
        if real_nodes
        else []
    )
    # Return only nodes that passed the check
    return [node for node, is_valid in zip(real_nodes, results) if is_valid]


async def get_mappings_from_validator(session, node):
    """Fetch mappings from a validator"""
    url = f"http://{node['ip']}:{node['port']}/mappings"
    try:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                print(f"Failed to get mappings from {node['hotkey']}: {resp.status}")
                return {}
            return await resp.json()
    except Exception as e:
        print(f"Error getting mappings from {node['hotkey']}: {e}")
        return {}


async def post_unbind_to_validator(session, node, payload, signature):
    """Post unbind request to a validator"""
    url = f"http://{node['ip']}:{node['port']}/unbind"
    headers = {"X-Signature": signature}
    try:
        async with session.post(
            url, json=payload, headers=headers, ssl=False
        ) as response:
            text = await response.text()
            print(f"Validator {node['hotkey']} unbind response: {text}")
            return text
    except Exception as e:
        print(f"POST unbind to {url} failed: {e}")
        return None


def build_unbind_payload(
    wallet: Wallet, worker: str
) -> tuple[dict, str]:
    payload = {
        "hotkey": wallet.get_hotkey().ss58_address,
        "worker": worker,
    }
    # Sign the JSON with sorted keys
    unbind_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = wallet.get_hotkey().sign(unbind_json).hex()
    return payload, signature


def filter_workers_by_hotkey(mappings: dict, hotkey_address: str) -> list[str]:
    """Filter mappings to get workers for a specific hotkey"""
    workers = []
    for worker, hotkey in mappings.items():
        if hotkey == hotkey_address:
            workers.append(worker)
    return workers


async def main():
    parser = argparse.ArgumentParser()
    Wallet.add_args(parser)
    parser.add_argument(
        "--subtensor.network",
        type=str,
        required=False,
        help="Subtensor network",
        default=FINNEY_NETWORK,
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt and proceed with unbinding",
    )
    args = parser.parse_args()
    
    wallet_name = getattr(args, "wallet.name", "default")
    wallet_hotkey = getattr(args, "wallet.hotkey", "default")
    wallet_path = getattr(args, "wallet.path", "~/.bittensor/wallets/")
    subtensor_network = getattr(args, "subtensor.network", FINNEY_NETWORK)
    confirm = getattr(args, "confirm", False)
    
    wallet = Wallet(config=Config(wallet_name, wallet_hotkey, wallet_path))
    hotkey_address = wallet.get_hotkey().ss58_address
    
    print(f"Wallet hotkey: {hotkey_address}")
    print(f"Network: {subtensor_network}")
    
    async with get_substrate(subtensor_network) as substrate:
        netuid = NETWORK_TO_NETUID[subtensor_network]
        nodes = await get_validators(substrate, netuid)
    
    if not nodes:
        print("No validators found")
        return
    
    print(f"Found {len(nodes)} validators")
    
    # Fetch mappings from all validators
    print("\nFetching mappings from validators...")
    async with aiohttp.ClientSession() as session:
        mapping_tasks = [
            get_mappings_from_validator(session, node) for node in nodes
        ]
        mappings_results = await asyncio.gather(*mapping_tasks)
    
    # Collect all workers for this hotkey
    all_workers = set()
    for i, mappings in enumerate(mappings_results):
        if mappings:
            validator_hotkey = nodes[i]['hotkey']
            workers = filter_workers_by_hotkey(mappings, hotkey_address)
            if workers:
                print(f"Found {len(workers)} workers in validator {validator_hotkey}: {workers}")
                all_workers.update(workers)
    
    if not all_workers:
        print("No workers found for this hotkey")
        return
    
    print(f"\nTotal unique workers to unbind: {len(all_workers)}")
    print(f"Workers: {list(all_workers)}")
    
    # Handle confirmation
    if confirm:
        print("\nProceeding with unbinding (--confirm flag used)")
    else:
        try:
            response = input(f"\nDo you want to unbind all {len(all_workers)} workers? (yes/no): ")
            if response.lower() != 'yes':
                print("Unbind cancelled")
                return
        except (EOFError, KeyboardInterrupt):
            # Try to use /dev/tty for interactive input when stdin is redirected
            try:
                import sys
                with open('/dev/tty', 'r') as tty:
                    print(f"\nDo you want to unbind all {len(all_workers)} workers? (yes/no): ", end='', flush=True)
                    response = tty.readline().strip()
                    if response.lower() != 'yes':
                        print("Unbind cancelled")
                        return
            except (FileNotFoundError, PermissionError, OSError):
                print("\n\nError: Cannot read input interactively. Use --confirm flag to skip confirmation prompt.")
                print("Example: curl -s https://raw.githubusercontent.com/HashTensor/HashTensor_Subnet/main/scripts/unbind_all.py | python3 - --wallet.name my_wallet --wallet.hotkey my_hotkey --subtensor.network finney --confirm")
                return
    
    # Unbind all workers
    print(f"\nUnbinding {len(all_workers)} workers...")
    async with aiohttp.ClientSession() as session:
        for worker in all_workers:
            print(f"\nUnbinding worker: {worker}")
            payload, signature = build_unbind_payload(wallet, worker)
            
            # Send unbind request to all validators
            unbind_tasks = [
                post_unbind_to_validator(session, node, payload, signature)
                for node in nodes
            ]
            await asyncio.gather(*unbind_tasks)
    
    print(f"\nUnbind process completed for {len(all_workers)} workers")


if __name__ == "__main__":
    asyncio.run(main())
