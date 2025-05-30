# main.py
# FastAPI entry point for the validator

from fastapi import Depends, FastAPI, HTTPException, Header
from typing import Annotated
import json
import time

from fiber import SubstrateInterface

from .utils import get_netuid, is_hotkey_registered, verify_signature

from .interfaces.worker_provider import WorkerProvider

from .validator import Validator

from .models import HotkeyWorkerRegistration

from .config import ValidatorSettings, load_config

from .dependencies import (
    get_database_service,
    get_substrate,
    get_validator,
    get_worker_provider,
)
from .interfaces.database import DatabaseService

app = FastAPI(prefix="/api", title="HashTensor Validator")


@app.get("/health")
def health_check():
    return {"status": "ok"}


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
    if not verify_signature(reg.hotkey, reg_json, x_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    # 4. Check hotkey is registered
    if not is_hotkey_registered(
        reg.hotkey, substrate, get_netuid(config.subtensor_network)
    ):
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
async def get_metrics(validator: Annotated[Validator, Depends(get_validator)]):
    return await validator.get_hotkey_metrics_map()


@app.get("/ratings")
async def get_ratings(validator: Annotated[Validator, Depends(get_validator)]):
    return await validator.compute_ratings()
