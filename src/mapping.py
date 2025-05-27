# mapping.py
# Manages Bittensor hotkey <-> Kaspa worker name resolution

import time
from typing import Dict, Optional


class MappingSource:
    async def load_mapping(self) -> Dict[str, str]:
        """Load worker -> hotkey mapping from a source."""
        pass


class MappingManager:
    def __init__(self, source: MappingSource, cache_ttl: int = 15):
        self.source = source
        self.cache_ttl = cache_ttl
        self._mapping: Dict[str, str] = {}
        self._last_update: float = 0.0

    async def _get_mapping(self) -> Dict[str, str]:
        now = time.time()
        if now - self._last_update > self.cache_ttl:
            self._mapping = await self.source.load_mapping()
            self._last_update = now
        return self._mapping

    async def get_hotkey(self, worker: str) -> Optional[str]:
        mapping = await self._get_mapping()
        return mapping.get(worker)

    async def get_worker(self, hotkey: str) -> Optional[str]:
        mapping = await self._get_mapping()
        for worker, hk in mapping.items():
            if hk == hotkey:
                return worker
        return None
