from pydantic import BaseModel, Field, field_validator
from scalecodec.utils.ss58 import ss58_decode
from typing import Optional


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
