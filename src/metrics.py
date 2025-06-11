# metrics.py
# Handles Prometheus client and metrics parsing for Kaspa Stratum Bridge

import asyncio
from datetime import timedelta, datetime
from typing import Dict, Any, NamedTuple, Self
from pydantic import BaseModel, ConfigDict, Field
import aiohttp


class MinerKey(BaseModel):
    wallet: str  # Kaspa wallet
    worker: str  # Worker ID

    model_config = ConfigDict(frozen=True)


class MinerMetrics(BaseModel):
    uptime: float = 0.0
    valid_shares: int = 0
    invalid_shares: int = 0
    difficulty: float = 0.0
    hashrate: float = 0.0
    worker_name: str | None = None

    model_config = ConfigDict(frozen=True)

    @classmethod
    def default_instance(cls, worker_name: str | None = None) -> Self:
        return cls(
            worker_name=worker_name
        )


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
            if "value" in item:
                value = float(item["value"][1])
            elif "values" in item and item["values"]:
                value = float(item["values"][-1][1])  # last value in the range
            else:
                continue
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

    async def _get_total_share_diff(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, float]:
        """Fetch total difficulty (increase of ks_valid_share_diff_counter) per (wallet, worker)."""
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"sum(increase(ks_valid_share_diff_counter[{resolution}])) by (wallet, worker)"
        return await self._fetch_metric(session, query, float)

    async def _get_uptime(
        self, session: aiohttp.ClientSession
    ) -> Dict[MinerKey, float]:
        """Query Prometheus and return uptime (ks_miner_uptime_seconds) per (wallet, worker)."""
        resolution = f"{int(self.window.total_seconds())}s"
        query = f"ks_miner_uptime_seconds[{resolution}]"
        return await self._fetch_metric(session, query, float)

    async def fetch_metrics(self) -> Dict[MinerKey, MinerMetrics]:
        """Fetch and parse metrics from Prometheus endpoint for all wallets."""
        async with aiohttp.ClientSession() as session:
            (
                valid_shares_map,
                invalid_shares_map,
                total_diff_map,
                uptime_map,
            ) = await asyncio.gather(
                self._get_valid_shares(session),
                self._get_invalid_shares(session),
                self._get_total_share_diff(session),
                self._get_uptime(session),
            )
            result = {}
            window_seconds = int(self.window.total_seconds())
            for miner_key, valid_shares in valid_shares_map.items():
                if self.pool_owner_wallet and miner_key.wallet != self.pool_owner_wallet:
                    continue
                total_diff = total_diff_map.get(miner_key, 0.0)
                avg_difficulty = total_diff / valid_shares if valid_shares > 0 else 0.0
                hashrate = (valid_shares * avg_difficulty * 2**32) / window_seconds if valid_shares > 0 else 0.0
                miner_metrics = MinerMetrics(
                    uptime=uptime_map.get(miner_key, 0.0),
                    valid_shares=valid_shares,
                    invalid_shares=invalid_shares_map.get(miner_key, 0),
                    difficulty=avg_difficulty,
                    hashrate=hashrate,
                    worker_name=miner_key.worker,
                )
                result[miner_key] = miner_metrics
            return result
