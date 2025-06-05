# tests/test_metrics.py
import pytest
from src.metrics import MetricsClient


def test_fetch_metrics_stub():
    assert True  # Placeholder


def test_metrics_client_init():
    url = "http://pool.hashtensor.com:9090"
    client = MetricsClient(endpoint=url)
    assert client.endpoint == url


@pytest.mark.asyncio
async def test_metrics_client_fetch():
    url = "http://pool.hashtensor.com:9090"
    client = MetricsClient(endpoint=url)
    metrics = await client.fetch_metrics()
    assert metrics is not None
