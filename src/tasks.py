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
    validator_endpoints = [(node.ip, node.port, node.hotkey) for node in real_nodes]
    logger.info(
        f"[sync_hotkey_workers_task] Found {len(validator_endpoints)} endpoints to check."
    )

    # Check which endpoints are HashTensor Validators
    is_valid_list = await asyncio.gather(
        *[
            is_hashtensor_validator(ip, port)
            for ip, port, _ in validator_endpoints
        ]
    )
    filtered_endpoints = [
        (ip, port, hotkey)
        for (ip, port, hotkey), is_valid in zip(validator_endpoints, is_valid_list)
        if is_valid
    ]
    logger.info(
        f"[sync_hotkey_workers_task] {len(filtered_endpoints)} endpoints are valid HashTensor Validators."
    )

    if not filtered_endpoints:
        logger.warning("[sync_hotkey_workers_task] No valid endpoints found.")
        return

    # Sync each validator
    total_added = 0
    total_skipped = 0
    total_failed = 0
    
    async with aiohttp.ClientSession() as session:
        for ip, port, hotkey in filtered_endpoints:
            logger.info(f"[sync_hotkey_workers_task] Syncing validator {hotkey} at {ip}:{port}")
            
            # Get the last registration time synced for this validator
            last_registration_time = await db_service.get_validator_sync_offset(hotkey)
            latest_registration_time = last_registration_time
            
            logger.debug(f"[sync_hotkey_workers_task] Fetching workers from {hotkey} since {last_registration_time}")
            
            workers = await fetch_hotkey_workers_from_validator(
                session, ip, port, last_registration_time
            )
            
            if not workers:
                logger.debug(f"[sync_hotkey_workers_task] No new workers from {hotkey}")
                continue
            
            logger.info(f"[sync_hotkey_workers_task] Fetched {len(workers)} workers from {hotkey}")
            
            # Process workers
            page_added = 0
            page_skipped = 0
            page_failed = 0
            max_registration_time = latest_registration_time
            
            for worker_obj in workers:
                worker = worker_obj["worker"]
                worker_hotkey = worker_obj["hotkey"]
                registration_time = worker_obj["registration_time"]
                signature = worker_obj["signature"]
                wallet = worker_obj["wallet"]
                
                # Track the max registration_time seen in this batch
                if registration_time > max_registration_time:
                    max_registration_time = registration_time
                
                # Security check: worker name must contain the hotkey
                if worker_hotkey not in worker:
                    logger.warning(
                        f"Worker name {worker} does not contain hotkey {worker_hotkey} - skipping for security"
                    )
                    page_failed += 1
                    continue
                
                # Update the latest registration time seen
                if registration_time > latest_registration_time:
                    latest_registration_time = registration_time

                exists = db_service.session.query(
                    db_service.session.query(HotkeyWorker)
                    .filter_by(worker=worker)
                    .exists()
                ).scalar()
                if exists:
                    page_skipped += 1
                    continue
                    
                reg_dict = {
                    "hotkey": worker_hotkey,
                    "worker": f"{wallet}.{worker}",  # To restore original worker name
                    "registration_time": registration_time,
                } # TODO: Maybe we have to check for pool owner wallet for backwards signature compatibility
                reg_json = json.dumps(reg_dict, sort_keys=True, separators=(",", ":"))
                if not verify_signature(worker_hotkey, reg_json, signature):
                    logger.warning(
                        f"Signature verification failed for worker {worker}"
                    )
                    page_failed += 1
                    continue
                    
                try:
                    await db_service.add_mapping(
                        worker_hotkey, worker, signature, registration_time, wallet
                    )
                    logger.info(f"Added worker {worker} from remote validator API")
                    page_added += 1
                except Exception as e:
                    logger.error(f"Failed to add worker {worker}: {e}")
                    page_failed += 1
            
            total_added += page_added
            total_skipped += page_skipped
            total_failed += page_failed
            
            # Update the last registration time for this validator
            # If no workers were added but there were workers, update offset to max_registration_time
            if page_added == 0 and workers:
                if max_registration_time > last_registration_time:
                    await db_service.update_validator_sync_offset(hotkey, max_registration_time)
                    logger.info(f"[sync_hotkey_workers_task] Updated sync offset for {hotkey} to {max_registration_time} (all workers errored)")
            elif latest_registration_time > last_registration_time:
                await db_service.update_validator_sync_offset(hotkey, latest_registration_time)
                logger.info(f"[sync_hotkey_workers_task] Updated sync offset for {hotkey} to {latest_registration_time}")
            
            logger.info(f"[sync_hotkey_workers_task] {hotkey}: Added: {page_added}, Skipped: {page_skipped}, Failed: {page_failed}")
    
    logger.info(
        f"[sync_hotkey_workers_task] Done. Total Added: {total_added}, Total Skipped: {total_skipped}, Total Failed: {total_failed}"
    )

# TODO: Add task to clean up workers that are unbound (optional cleanup task)