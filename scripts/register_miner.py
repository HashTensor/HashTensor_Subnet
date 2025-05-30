import argparse
import os
import socket
import struct
import asyncio
import aiohttp
import json
import time
from bittensor_wallet import Wallet, Config
from async_substrate_interface import AsyncSubstrateInterface
from scalecodec.utils.ss58 import ss58_encode
from tenacity import retry, stop_after_attempt, wait_exponential

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

MOCKED_VALIDATORS = os.environ.get("MOCKED_VALIDATORS", "").split(",")


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
)
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


async def get_validators(
    substrate: AsyncSubstrateInterface, netuid: int, block: int | None = None
) -> list[dict]:
    nodes = await get_nodes_for_uid(substrate, netuid, block)
    return (
        [node for node in nodes if node["vtrust"] > 0]
        if not MOCKED_VALIDATORS
        else [node for node in nodes if node["hotkey"] in MOCKED_VALIDATORS]
    )


async def post_to_validator(session, node, payload, signature):
    url = f"http://{node['ip']}:{node['port']}/register"
    headers = {"X-Signature": signature}
    try:
        async with session.post(
            url, json=payload, headers=headers, ssl=False
        ) as response:
            text = await response.text()
            print(f"Validator {node['hotkey']} responded: {text}")
            return text
    except Exception as e:
        print(f"POST to {url} failed: {e}")
        return None


def build_registration_payload(
    wallet: Wallet, worker: str
) -> tuple[dict, str]:
    registration_time = time.time()
    payload = {
        "hotkey": wallet.get_hotkey().ss58_address,
        "worker": worker,
        "registration_time": registration_time,
    }
    # Sign the JSON with sorted keys
    reg_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = wallet.get_hotkey().sign(reg_json).hex()
    return payload, signature


async def main():
    parser = argparse.ArgumentParser()
    Wallet.add_args(parser)
    parser.add_argument(
        "--worker", type=str, required=True, help="Worker name or ID"
    )
    parser.add_argument(
        "--subtensor.network",
        type=str,
        required=False,
        help="Subtensor network",
        default=FINNEY_NETWORK,
    )
    args = parser.parse_args()
    worker = getattr(args, "worker", None)
    wallet_name = getattr(args, "wallet.name", "default")
    wallet_hotkey = getattr(args, "wallet.hotkey", "default")
    wallet_path = getattr(args, "wallet.path", "~/.bittensor/wallets/")
    subtensor_network = getattr(args, "subtensor.network", FINNEY_NETWORK)
    wallet = Wallet(config=Config(wallet_name, wallet_hotkey, wallet_path))
    async with get_substrate(subtensor_network) as substrate:
        netuid = NETWORK_TO_NETUID[subtensor_network]
        nodes = await get_validators(substrate, netuid)
    if not nodes:
        print("No validators found")
        return
    payload, signature = build_registration_payload(wallet, worker)
    print(f"Registration payload: {json.dumps(payload, indent=2)}")
    print(f"Signature (X-Signature): {signature}")
    async with aiohttp.ClientSession() as session:
        tasks = [
            post_to_validator(session, node, payload, signature)
            for node in nodes
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
