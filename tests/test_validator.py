# tests/test_validator.py

import pytest
from unittest.mock import AsyncMock
from src.validator import Validator
from src.metrics import MinerMetrics, MinerKey


@pytest.mark.asyncio
async def test_get_hotkey_metrics_map():
    # Mock config
    class DummyConfig:
        rating_weight = 1.0

    # Mock MetricsClient
    metrics_client = AsyncMock()
    miner_key1 = MinerKey(wallet="w1", worker="worker1")
    miner_key2 = MinerKey(wallet="w2", worker="worker2")
    metrics_client.fetch_metrics.return_value = {
        miner_key1: MinerMetrics(
            uptime=1,
            valid_shares=10,
            invalid_shares=0,
            difficulty=1.0,
            hashrate=100.0,
        ),
        miner_key2: MinerMetrics(
            uptime=2,
            valid_shares=20,
            invalid_shares=1,
            difficulty=2.0,
            hashrate=200.0,
        ),
    }

    # Mock MappingManager
    mapping_manager = AsyncMock()
    mapping_manager.get_hotkey.side_effect = lambda worker: {
        "worker1": "hotkey1",
        "worker2": "hotkey2",
    }.get(worker)

    validator = Validator(DummyConfig(), metrics_client, mapping_manager)
    result = await validator.get_hotkey_metrics_map()
    assert set(result.keys()) == {"hotkey1", "hotkey2"}
    assert result["hotkey1"][0].valid_shares == 10
    assert result["hotkey2"][0].valid_shares == 20
