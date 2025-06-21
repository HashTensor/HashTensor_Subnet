# tests/test_registration.py

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.models import HotkeyWorkerRegistration


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_dependencies(monkeypatch):
    """Mock all dependencies for testing"""
    
    # Mock database service
    mock_db = AsyncMock()
    mock_db.add_mapping = AsyncMock()
    monkeypatch.setattr("src.main.get_database_service", lambda: mock_db)
    
    # Mock worker provider
    mock_worker_provider = AsyncMock()
    mock_worker_provider.is_worker_exists = AsyncMock(return_value=True)
    monkeypatch.setattr("src.main.get_worker_provider", lambda: mock_worker_provider)
    
    # Mock config
    mock_config = MagicMock()
    mock_config.registration_time_tolerance.total_seconds.return_value = 300
    mock_config.verify_signature = False
    mock_config.kaspa_pool_owner_wallet = "test_wallet"
    mock_config.netuid = 1
    monkeypatch.setattr("src.main.load_config", lambda: mock_config)
    
    # Mock substrate
    mock_substrate = MagicMock()
    monkeypatch.setattr("src.main.get_substrate", lambda: mock_substrate)
    
    # Mock is_hotkey_registered
    monkeypatch.setattr("src.main.is_hotkey_registered", lambda *args: True)
    
    return {
        "db": mock_db,
        "worker_provider": mock_worker_provider,
        "config": mock_config,
        "substrate": mock_substrate
    }


@patch('time.time')
def test_worker_name_must_contain_hotkey(mock_time, client, mock_dependencies):
    """Test that registration fails when worker name doesn't contain hotkey"""
    
    # Mock current time
    current_time = 1234567890.0
    mock_time.return_value = current_time
    
    # Valid hotkey and worker name (worker contains hotkey)
    valid_hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    valid_worker = f"worker_{valid_hotkey}_01"
    
    # Invalid worker name (doesn't contain hotkey)
    invalid_worker = "worker1"
    
    # Test valid case
    valid_payload = {
        "hotkey": valid_hotkey,
        "worker": valid_worker,
        "registration_time": current_time
    }
    
    response = client.post("/register", json=valid_payload, headers={"X-Signature": "test_signature"})
    assert response.status_code == 200
    
    # Test invalid case
    invalid_payload = {
        "hotkey": valid_hotkey,
        "worker": invalid_worker,
        "registration_time": current_time
    }
    
    response = client.post("/register", json=invalid_payload, headers={"X-Signature": "test_signature"})
    assert response.status_code == 400
    assert "Worker name must contain the hotkey for security validation" in response.json()["detail"]


@patch('time.time')
def test_worker_name_validation_examples(mock_time, client, mock_dependencies):
    """Test various valid and invalid worker name formats"""
    
    # Mock current time
    current_time = 1234567890.0
    mock_time.return_value = current_time
    
    hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    
    # Valid examples
    valid_examples = [
        hotkey,  # hotkey as worker name
        f"my_worker_{hotkey}",  # hotkey at the end
        f"{hotkey}_worker1",  # hotkey at the beginning
        f"worker_{hotkey}_01",  # hotkey in the middle
    ]
    
    # Invalid examples
    invalid_examples = [
        "worker1",
        "my_miner",
        "kaspa_worker",
        "miner_123",
    ]
    
    # Test valid examples
    for worker in valid_examples:
        payload = {
            "hotkey": hotkey,
            "worker": worker,
            "registration_time": current_time
        }
        response = client.post("/register", json=payload, headers={"X-Signature": "test_signature"})
        assert response.status_code == 200, f"Failed for valid worker: {worker}"
    
    # Test invalid examples
    for worker in invalid_examples:
        payload = {
            "hotkey": hotkey,
            "worker": worker,
            "registration_time": current_time
        }
        response = client.post("/register", json=payload, headers={"X-Signature": "test_signature"})
        assert response.status_code == 400, f"Should have failed for invalid worker: {worker}"
        assert "Worker name must contain the hotkey for security validation" in response.json()["detail"]


@patch('time.time')
def test_case_sensitive_validation(mock_time, client, mock_dependencies):
    """Test that hotkey validation is case sensitive"""
    
    # Mock current time
    current_time = 1234567890.0
    mock_time.return_value = current_time
    
    hotkey = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
    
    # Test with lowercase hotkey in worker name
    worker_with_lowercase = f"worker_{hotkey.lower()}"
    
    payload = {
        "hotkey": hotkey,
        "worker": worker_with_lowercase,
        "registration_time": current_time
    }
    
    response = client.post("/register", json=payload, headers={"X-Signature": "test_signature"})
    assert response.status_code == 400
    assert "Worker name must contain the hotkey for security validation" in response.json()["detail"] 