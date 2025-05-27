# main.py
# FastAPI entry point for the validator

from fastapi import Depends, FastAPI, HTTPException
from typing import Annotated

from .validator import Validator

from .models import HotkeyWorkerRegistration

from .dependencies import get_database_service, get_validator
from .interfaces.database import DatabaseService

app = FastAPI(prefix="/api", title="HashTensor Validator")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register")
async def register_hotkey_worker(
    reg: HotkeyWorkerRegistration,
    db_service: Annotated[DatabaseService, Depends(get_database_service)],
):
    error = await db_service.add_mapping(reg.hotkey, reg.worker, reg.signature)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return dict(message="Registration successful")


@app.get("/metrics")
async def get_metrics(validator: Annotated[Validator, Depends(get_validator)]):
    return await validator.get_hotkey_metrics_map()


@app.get("/ratings")
async def get_ratings(validator: Annotated[Validator, Depends(get_validator)]):
    return await validator.compute_ratings()
