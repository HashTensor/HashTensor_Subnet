from pydantic import BaseModel, Field, field_validator, computed_field
from scalecodec.utils.ss58 import ss58_decode
from typing import List, Optional

from .metrics import MinerMetrics


class HotkeyWorkerRegistration(BaseModel):
    hotkey: str = Field(..., description="Bittensor hotkey")
    worker: str = Field(..., description="Kaspa worker name")
    registration_time: float = Field(
        ..., description="UTC timestamp sent by miner"
    )

    @field_validator("hotkey")
    @classmethod
    def validate_ss58_address(cls, v):
        try:
            ss58_decode(v)
        except Exception:
            raise ValueError("Invalid ss58 address")
        return v


class MetricsResponse(BaseModel):
    hotkey: str = Field(..., description="Bittensor hotkey")
    active_workers: int = Field(..., description="Number of active workers")
    total_workers: int = Field(..., description="Total number of workers")
    metrics: List[MinerMetrics] = Field(..., description="Miner metrics")

    @computed_field
    @property
    def is_active(self) -> bool:
        return self.active_workers != 0

