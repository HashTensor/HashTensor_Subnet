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
from fastapi.middleware.cors import CORSMiddleware

from fiber import SubstrateInterface

from .mapping import MappingManager

from .tasks import set_weights_task, sync_hotkey_workers_task

from .utils import is_hotkey_registered, verify_signature

from .interfaces.worker_provider import WorkerProvider

from .validator import Validator

from .models import HotkeyWorkerRegistration, MetricsResponse, UnbindWorkerRequest

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
from . import __version__ as version


logger = get_logger(__name__)


# CORS setup
ENV = os.environ.get("ENV", "prod")
REMOTE_SITE_ORIGIN = os.environ.get(
    "REMOTE_SITE_ORIGIN", "https://hashtensor.com"
)

if ENV == "test":
    origins = ["http://localhost", "http://localhost:3000", "http://127.0.0.1"]
else:
    origins = [REMOTE_SITE_ORIGIN]


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
    db_service = get_database_service(config)

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

    async def sync_hotkey_workers_loop():
        while True:
            try:
                await asyncio.to_thread(
                    lambda: asyncio.run(
                        sync_hotkey_workers_task(db_service, config, substrate)
                    )
                )
            except Exception as e:
                logger.exception(f"Error in sync_hotkey_workers_task: {e}")
            await asyncio.sleep(
                config.sync_hotkey_workers_interval.total_seconds()
            )

    # Create tasks conditionally based on feature flags
    tasks = []
    
    if not config.disable_set_weights:
        task1 = asyncio.create_task(weights_loop())
        tasks.append(task1)
        logger.info("Set weights task started")
    else:
        logger.info("Set weights task disabled by DISABLE_SET_WEIGHTS flag")
    
    task2 = asyncio.create_task(sync_hotkey_workers_loop())
    tasks.append(task2)
    
    yield


app = FastAPI(
    prefix="/api",
    title="HashTensor Validator",
    lifespan=lifespan,
    version=version,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if ENV == "test" else [REMOTE_SITE_ORIGIN]
    ),  # Not recommended for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    # 1. Log incoming request data
    logger.debug(f"/register request: payload={reg.model_dump()}")
    reg_dict = reg.model_dump()
    reg_json = json.dumps(reg_dict, sort_keys=True, separators=(",", ":"))
    logger.debug(f"/register reg_json: {reg_json}")
    logger.debug(f"/register X-Signature: {x_signature}")
    now = time.time()
    if (
        abs(now - reg.registration_time)
        > config.registration_time_tolerance.total_seconds()
    ):
        raise HTTPException(
            status_code=400,
            detail="Registration time is too far from current UTC time.",
        )
    # Extract wallet and worker name by splitting by first dot
    if "." not in reg.worker:
        raise HTTPException(status_code=400, detail="Worker must be in the format <wallet>.<workername>")
    wallet_part, worker_name = reg.worker.split(".", 1)
    # Validate kaspa wallet format
    if not wallet_part.startswith("kaspa:") or len(wallet_part) < 10:
        raise HTTPException(status_code=400, detail=f"Invalid kaspa wallet: {wallet_part}")
    # Security check: worker name must contain the hotkey
    if reg.hotkey not in worker_name:
        raise HTTPException(
            status_code=400,
            detail="Worker name must contain the hotkey for security validation.",
        )
    # 3. Verify signature on the full request object (sorted keys)
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
        # Store registration_time as float seconds, db will convert to int microseconds
        await db_service.add_mapping(
            reg.hotkey, reg.worker, x_signature, reg.registration_time, wallet=wallet_part
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dict(message="Registration successful")


@app.get("/metrics")
async def get_metrics(
    validator: Annotated[Validator, Depends(get_validator)]
) -> List[MetricsResponse]:
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


@app.get("/mappings")
async def get_mappings(
    mapping_manager: Annotated[MappingManager, Depends(get_mapping_manager)]
):
    return await mapping_manager.get_mapping()


@app.get("/hotkey_workers")
async def get_hotkey_workers(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    since_timestamp: float = 0.0,
    page_size: int = 100,
    page_number: int = 1,
):
    return await db_service.get_hotkey_workers_by_time(
        since_timestamp=since_timestamp,
        page_size=page_size,
        page_number=page_number,
    )


# Only define /ratings if ENV == "test"
if ENV == "test":

    @app.get("/ratings")
    async def get_ratings(
        validator: Annotated[Validator, Depends(get_validator)]
    ):
        return await validator.compute_ratings()



@app.post("/unbind")
async def unbind_worker(
    req: UnbindWorkerRequest,
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    config: Annotated[ValidatorSettings, Depends(load_config)],
    substrate: Annotated[SubstrateInterface, Depends(get_substrate)],
    x_signature: Annotated[str, Header(alias="X-Signature")],
):
    # Log request
    logger.debug(f"/unbind request: payload={req.model_dump()}")
    req_dict = req.model_dump()
    req_json = json.dumps(req_dict, sort_keys=True, separators=(",", ":"))
    logger.debug(f"/unbind req_json: {req_json}")
    logger.debug(f"/unbind X-Signature: {x_signature}")
    # Extract wallet and worker name by splitting by first dot
    if "." not in req.worker:
        raise HTTPException(status_code=400, detail="Worker must be in the format <wallet>.<workername>")
    wallet_part, worker_name = req.worker.split(".", 1)
    # Validate kaspa wallet format
    if not wallet_part.startswith("kaspa:") or len(wallet_part) < 10:
        raise HTTPException(status_code=400, detail=f"Invalid kaspa wallet: {wallet_part}")
    # Verify signature on the full request object (sorted keys)
    if config.verify_signature and not verify_signature(
        req.hotkey, req_json, x_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")
    # Check hotkey is registered
    if not is_hotkey_registered(req.hotkey, substrate, config.netuid):
        raise HTTPException(
            status_code=400,
            detail="Hotkey not registered. To register in subnet use btcli command: `btcli subnet register`",
        )
    try:
        await db_service.mark_worker_unbound(
            req.hotkey, worker_name, x_signature, wallet=wallet_part
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dict(message="Worker unbound successfully")


@app.get("/validator_sync_offsets")
async def get_validator_sync_offsets(
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
    page_size: int = 100,
    page_number: int = 1,
):
    return await db_service.get_all_validator_sync_offsets(
        page_size=page_size,
        page_number=page_number,
    )
