import time
import aiohttp
from typing import Set
from ..metrics import MetricsClient


class WorkerProvider:
    def __init__(self, metrics_client: MetricsClient, cache_ttl: int = 15):
        self.metrics_client = metrics_client
        self.cache_ttl = cache_ttl
        self._cache = (set(), 0.0)  # (workers, last_update_time)

    async def fetch_pool_workers(self) -> Set[str]:
        now = time.time()
        workers, last_update = self._cache
        if now - last_update < self.cache_ttl:
            return workers
        async with aiohttp.ClientSession() as session:
            uptimes = await self.metrics_client._get_uptime(session)
        workers = {key.worker for key, uptime in uptimes.items() if uptime > 0}
        self._cache = (workers, now)
        return workers
