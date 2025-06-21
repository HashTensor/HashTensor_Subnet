import asyncio
import time
import aiohttp
import json

from fiber import Keypair, SubstrateInterface

from src.constants import MIN_WEIGHTED_STAKE

from .set_weights import set_weights

from .config import ValidatorSettings
from .validator import Validator
from fiber.utils import get_logger

from .interfaces.database import (
    DynamicConfigService,
    DatabaseService,
    HotkeyWorker,
)
from .utils import (
    get_stake_weights,
    verify_signature,
    fix_node_ip,
    is_hashtensor_validator,
    fetch_hotkey_workers_from_validator,
)

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


async def sync_hotkey_workers_task(
    db_service: DatabaseService,
    config: ValidatorSettings,
    substrate: SubstrateInterface,
):
    from fiber.chain.fetch_nodes import get_nodes_for_netuid

    netuid = config.netuid
    logger.info("[sync_hotkey_workers_task] Starting sync task...")
    nodes = get_nodes_for_netuid(substrate, netuid)
    real_nodes = [
        fix_node_ip(node)
        for node in nodes
        if getattr(node, "ip", None) != "0.0.0.0"
        and get_stake_weights(node) >= MIN_WEIGHTED_STAKE
    ]
    validator_endpoints = [(node.ip, node.port) for node in real_nodes]
    logger.info(
        f"[sync_hotkey_workers_task] Found {len(validator_endpoints)} endpoints to check."
    )

    # Check which endpoints are HashTensor Validators
    is_valid_list = await asyncio.gather(
        *[
            is_hashtensor_validator(ip, port)
            for ip, port in validator_endpoints
        ]
    )
    filtered_endpoints = [
        ep
        for ep, is_valid in zip(validator_endpoints, is_valid_list)
        if is_valid
    ]
    logger.info(
        f"[sync_hotkey_workers_task] {len(filtered_endpoints)} endpoints are valid HashTensor Validators."
    )

    if not filtered_endpoints:
        logger.warning("[sync_hotkey_workers_task] No valid endpoints found.")
        return

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            *[
                fetch_hotkey_workers_from_validator(session, ip, port)
                for ip, port in filtered_endpoints
            ]
        )
        all_workers = [worker for sublist in results for worker in sublist]
    logger.info(
        f"[sync_hotkey_workers_task] Fetched {len(all_workers)} workers from all validators."
    )

    # Sort workers by registration_time ascending
    all_workers.sort(key=lambda w: w["registration_time"])

    added = 0
    skipped = 0
    failed = 0
    for worker_obj in all_workers:
        worker = worker_obj["worker"]
        hotkey = worker_obj["hotkey"]
        registration_time = worker_obj["registration_time"]
        signature = worker_obj["signature"]

        exists = db_service.session.query(
            db_service.session.query(HotkeyWorker)
            .filter_by(worker=worker)
            .exists()
        ).scalar()
        if exists:
            skipped += 1
            continue
        reg_dict = {
            "hotkey": hotkey,
            "worker": worker,
            "registration_time": registration_time,
        }
        reg_json = json.dumps(reg_dict, sort_keys=True, separators=(",", ":"))
        if not verify_signature(hotkey, reg_json, signature):
            logger.warning(
                f"Signature verification failed for worker {worker}"
            )
            failed += 1
            continue
        try:
            await db_service.add_mapping(
                hotkey, worker, signature, registration_time
            )
            logger.info(f"Added worker {worker} from remote validator API")
            added += 1
        except Exception as e:
            logger.error(f"Failed to add worker {worker}: {e}")
            failed += 1
    logger.info(
        f"[sync_hotkey_workers_task] Done. Added: {added}, Skipped: {skipped}, Failed: {failed}"
    )

# TODO: Add task to clean up workers that are unbound