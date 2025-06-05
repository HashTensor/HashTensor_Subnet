# metrics.py
# Handles Prometheus client and metrics parsing for Kaspa Stratum Bridge

import asyncio
from datetime import timedelta, datetime
from typing import Dict, Any, NamedTuple
from pydantic import BaseModel, ConfigDict, Field
import aiohttp


class MinerKey(BaseModel):
    wallet: str  # Kaspa wallet
    worker: str  # Worker ID

    model_config = ConfigDict(frozen=True)


class MinerMetrics(BaseModel):
    uptime: float
    valid_shares: int
    invalid_shares: int
    difficulty: float
    hashrate: float | None = None  # Optional, may depend on time window
    worker_name: str | None = None

    model_config = ConfigDict(frozen=True)


PROM_QUERY = (
    "sum(increase(ks_valid_share_counter[{resolution}])) by (wallet, worker)"
)


class MetricsClient:
    def __init__(
        self, endpoint: str, window: timedelta = timedelta(minutes=60), pool_owner_wallet: str | None = None
    ):
        self.endpoint = endpoint
        self.window = window
        self.pool_owner_wallet = pool_owner_wallet

    async def _fetch_metric(
        self, session: aiohttp.ClientSession, query: str, value_type=int
    ) -> Dict[MinerKey, Any]:
        """Generic Prometheus query fetcher for (wallet, worker) keyed results."""
        url = f"{self.endpoint}/api/v1/query"
        params = {"query": query}
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
        result = {}
        for item in data.get("data", {}).get("result", []):
            metric = item["metric"]
            if metric.get("wallet") is None or metric.get("worker") is None:
                continue
            value = float(item["value"][1])
            miner_key = MinerKey(**metric)
            result[miner_key] = value_type(value)
        return result

    async def _get_valid_shares(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, int]:
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"sum(increase(ks_valid_share_counter[{resolution}])) by (wallet, worker)"
        return await self._fetch_metric(session, query, int)

    async def _get_invalid_shares(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, int]:
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"sum(increase(ks_invalid_share_counter[{resolution}])) by (wallet, worker)"
        return await self._fetch_metric(session, query, int)

    async def _get_share_diff_counter(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, float]:
        resolution = f"{int(self.window.total_seconds())}s"
        query = f'ks_valid_share_diff_counter{{wallet=~".+", worker=~".+"}}[{resolution}]'
        return await self._fetch_metric(session, query, float)

    async def _get_avg_hashrate(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, float]:
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"sum(rate(ks_valid_share_diff_counter[{resolution}])) by (wallet, worker) * 1e9"
        return await self._fetch_metric(session, query, float)

    async def _get_uptime(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, float]:
        """Query Prometheus and return uptime (ks_miner_uptime_seconds) per (wallet, worker)."""
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"sum(increase(ks_miner_uptime_seconds[{resolution}])) by (wallet, worker)"
        return await self._fetch_metric(session, query, float)

    async def fetch_metrics(self) -> Dict[MinerKey, MinerMetrics]:
        """Fetch and parse metrics from Prometheus endpoint for all wallets."""
        async with aiohttp.ClientSession() as session:
            (
                valid_shares_map,
                invalid_shares_map,
                share_diff_map,
                avg_hashrate_map,
                uptime_map,
            ) = await asyncio.gather(
                self._get_valid_shares(session),
                self._get_invalid_shares(session),
                self._get_share_diff_counter(session),
                self._get_avg_hashrate(session),
                self._get_uptime(session),
            )
            result = {}
            for miner_key, valid_shares in valid_shares_map.items():
                if self.pool_owner_wallet and miner_key.wallet != self.pool_owner_wallet:
                    continue
                miner_metrics = MinerMetrics(
                    uptime=uptime_map.get(miner_key, 0.0),
                    valid_shares=valid_shares,
                    invalid_shares=invalid_shares_map.get(miner_key, 0),
                    difficulty=share_diff_map.get(miner_key, 0.0),
                    hashrate=avg_hashrate_map.get(miner_key, 0.0),
                    worker_name=miner_key.worker,
                )
                result[miner_key] = miner_metrics
            return result
