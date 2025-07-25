import asyncio
import aiohttp
import sys
import json

from src.config import ValidatorSettings
from src.interfaces.database import DatabaseService
from src.utils import (
    fetch_hotkey_workers_from_validator,
    verify_signature,
)
from fiber.utils import get_logger

logger = get_logger(__name__)

async def fetch_workers_paginated(session, ip, port, db_service: DatabaseService):
    page_size = 100
    page_number = 1
    last_registration_time = 0
    total_added = 0
    total_failed = 0
    while True:
        url = f"http://{ip}:{port}/hotkey_workers"
        params = {
            "since_timestamp": last_registration_time,
            "page_size": page_size,
            "page_number": page_number,
        }
        async with session.get(url, params=params, timeout=10) as resp:
            if resp.status != 200:
                logger.error(f"Failed to fetch workers: {resp.status}")
                break
            workers = await resp.json()
        if not workers:
            break
        logger.info(f"[sync_mappings] Fetched {len(workers)} workers from {ip}:{port} (page {page_number})")
        page_added = 0
        page_failed = 0
        max_registration_time = last_registration_time
        for worker_obj in workers:
            worker = worker_obj["worker"]
            worker_hotkey = worker_obj["hotkey"]
            registration_time = worker_obj["registration_time"]
            signature = worker_obj["signature"]
            if registration_time > max_registration_time:
                max_registration_time = registration_time
            reg_dict = {
                "hotkey": worker_hotkey,
                "worker": worker,
                "registration_time": registration_time,
            }
            reg_json = json.dumps(reg_dict, sort_keys=True, separators=(",", ":"))
            if not verify_signature(worker_hotkey, reg_json, signature):
                logger.warning(f"Signature verification failed for worker {worker}")
                page_failed += 1
                continue
            try:
                await db_service.add_mapping(
                    worker_hotkey, worker, signature, registration_time
                )
                logger.info(f"Added worker {worker} from remote validator API")
                page_added += 1
            except Exception as e:
                logger.error(f"Failed to add worker {worker}: {e}")
                page_failed += 1
        total_added += page_added
        total_failed += page_failed
        if len(workers) < page_size:
            break
        page_number += 1
        last_registration_time = max_registration_time
    logger.info(f"[sync_mappings] Total Added: {total_added}, Total Failed: {total_failed}")

async def sync_single_source(ip: str, port: int, db_service: DatabaseService):
    logger.info(f"[sync_mappings] Syncing from {ip}:{port}")
    async with aiohttp.ClientSession() as session:
        await fetch_workers_paginated(session, ip, port, db_service)

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/sync_mappings.py <ip> <port>")
        sys.exit(1)
    ip = sys.argv[1]
    port = int(sys.argv[2])
    db_service = DatabaseService()  # Adjust as needed for your project
    asyncio.run(sync_single_source(ip, port, db_service))

if __name__ == "__main__":
    main()
