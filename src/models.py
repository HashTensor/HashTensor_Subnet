from pydantic import BaseModel, Field


class HotkeyWorkerRegistration(BaseModel):
    hotkey: str = Field(..., description="Bittensor hotkey")
    worker: str = Field(..., description="Kaspa worker name")
    signature: str = Field(..., description="Signature for verification")
