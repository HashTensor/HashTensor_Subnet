# main.py
# FastAPI entry point for the validator

from datetime import timedelta
import os
from fastapi import Depends, FastAPI, HTTPException, Header
from typing import Annotated, List
import json
import time
from contextlib import asynccontextmanager
import asyncio

from fiber import SubstrateInterface

from .tasks import set_weights_task

from .utils import is_hotkey_registered, verify_signature

from .interfaces.worker_provider import WorkerProvider

from .validator import Validator

from .models import HotkeyWorkerRegistration, MetricsResponse

from .config import ValidatorSettings, load_config
from fiber.chain import chain_utils
from fiber.utils import get_logger

from .dependencies import (
    get_database_service,
    get_dynamic_config_service,
    get_mapping_manager,
    get_mapping_source,
    get_metrics_client,
    get_substrate,
    get_validator,
    get_worker_provider,
)
from .interfaces.database import DatabaseService


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    dynamic_config_service = get_dynamic_config_service(config)
    metrics_client = get_metrics_client(config)
    mapping_source = get_mapping_source(config)
    mapping_manager = get_mapping_manager(mapping_source, config)
    validator = get_validator(
        config,
        metrics_client,
        mapping_manager,
    )
    substrate = get_substrate(config)
    keypair = chain_utils.load_hotkey_keypair(
        wallet_name=config.wallet_name, hotkey_name=config.wallet_hotkey
    )

    async def weights_loop():
        while True:
            try:
                await asyncio.sleep(timedelta(minutes=1).total_seconds())
                await asyncio.to_thread(
                    lambda: asyncio.run(
                        set_weights_task(
                            dynamic_config_service,
                            config,
                            validator,
                            substrate,
                            keypair,
                        )
                    )
                )
            except Exception as e:
                logger.exception(f"Error in set_weights task: {e}")
                os._exit(1)

    task = asyncio.create_task(weights_loop())
    yield


app = FastAPI(prefix="/api", title="HashTensor Validator", lifespan=lifespan)


@app.get("/health")
def health_check():
    return {"status": "OK"}


@app.post("/register")
async def register_hotkey_worker(
    reg: HotkeyWorkerRegistration,
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    worker_provider: Annotated[WorkerProvider, Depends(get_worker_provider)],
    config: Annotated[ValidatorSettings, Depends(load_config)],
    substrate: Annotated[SubstrateInterface, Depends(get_substrate)],
    x_signature: Annotated[str, Header(alias="X-Signature")],
):
    # 1. Check registration_time is close to current UTC time
    now = time.time()
    if (
        abs(now - reg.registration_time)
        > config.registration_time_tolerance.total_seconds()
    ):
        raise HTTPException(
            status_code=400,
            detail="Registration time is too far from current UTC time.",
        )
    # 2. Check worker exists
    if not await worker_provider.is_worker_exists(
        config.kaspa_pool_owner_wallet, reg.worker
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Worker not found. Make sure you are using the correct wallet address\n"
            + f"Kaspa Pool Owner Wallet: {config.kaspa_pool_owner_wallet}",
        )
    # 3. Verify signature on the full request object (sorted keys)
    reg_dict = reg.model_dump()
    reg_json = json.dumps(reg_dict, sort_keys=True, separators=(",", ":"))
    if config.verify_signature and not verify_signature(
        reg.hotkey, reg_json, x_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")
    # 4. Check hotkey is registered
    if not is_hotkey_registered(reg.hotkey, substrate, config.netuid):
        raise HTTPException(
            status_code=400,
            detail="Hotkey not registered. To register in subnet use btcli command: `btcli subnet register`",
        )
    try:
        await db_service.add_mapping(
            reg.hotkey, reg.worker, x_signature, reg.registration_time
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dict(message="Registration successful")


@app.get("/metrics")
async def get_metrics(validator: Annotated[Validator, Depends(get_validator)]) -> List[MetricsResponse]:
    hotkey_metrics = await validator.get_hotkey_metrics_map()
    return [
        MetricsResponse(
            hotkey=hotkey,
            active_workers=len([m for m in metrics if m.uptime > 0]),
            total_workers=len(metrics),
            metrics=metrics,
        )
        for hotkey, metrics in hotkey_metrics.items()
    ]


@app.get("/ratings")
async def get_ratings(validator: Annotated[Validator, Depends(get_validator)]):
    return await validator.compute_ratings()
