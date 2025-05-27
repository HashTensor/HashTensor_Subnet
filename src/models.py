from pydantic import BaseModel, Field, field_validator
from scalecodec.utils.ss58 import ss58_decode


class HotkeyWorkerRegistration(BaseModel):
    hotkey: str = Field(..., description="Bittensor hotkey")
    worker: str = Field(..., description="Kaspa worker name")
    signature: str = Field(..., description="Signature for verification")

    @field_validator('hotkey')
    @classmethod
    def validate_ss58_address(cls, v):
        try:
            ss58_decode(v)
        except Exception:
            raise ValueError('Invalid ss58 address')
        return v
