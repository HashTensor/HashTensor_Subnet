# tests/test_rating.py
import pytest
from src.rating import RatingCalculator
from src.metrics import MinerMetrics
from unittest.mock import patch

FIXED_NOW = 1_800_000_000  # Arbitrary fixed timestamp for deterministic tests

@pytest.mark.parametrize(
    "scenario,metrics_dict,expected",
    [
        (
            "single hotkey, single worker, perfect uptime",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,  # started exactly at window start
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ]
            },
            {"hotkey1": 1.0},
        ),
        (
            "two hotkeys, one is more productive",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=50,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=500.0,
                    )
                ],
            },
            {"hotkey1": 1.0, "hotkey2": 0.5},
        ),
        (
            "uptime penalty",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 1800,  # started halfway through window
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
            },
            {"hotkey1": 0.25, "hotkey2": 1.0},  # 0.5^2 = 0.25
        ),
        (
            "multiple workers per hotkey",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=50,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    ),
                    MinerMetrics(
                        uptime=FIXED_NOW - 1800,  # started halfway through window
                        valid_shares=50,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    ),
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
            },
            {
                "hotkey1": pytest.approx(0.5625),
                "hotkey2": 1.0,
            },  # avg uptime = 0.75, 0.75^2 = 0.5625
        ),
        (
            "zero work",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=0,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
            },
            {"hotkey1": 0.0, "hotkey2": 1.0},
        ),
        (
            "realistic metrics example 1",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW,  # started now, so 0 uptime in window
                        valid_shares=1274,
                        invalid_shares=0,
                        difficulty=15647.46811773941,
                        hashrate=783547108.9145503,
                    ),
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=1000,
                        invalid_shares=0,
                        difficulty=10000.0,
                        hashrate=500000000.0,
                    ),
                ]
            },
            {
                "hotkey1": 0.25, # 0.5^2 = 0.25
            },
        ),
        (
            "realistic metrics example 2",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=FIXED_NOW,  # started now, so 0 uptime in window
                        valid_shares=1001,
                        invalid_shares=0,
                        difficulty=15664.64798692341,
                        hashrate=619774754.039591,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 3600,
                        valid_shares=33,
                        invalid_shares=0,
                        difficulty=116.82311045120004,
                        hashrate=34039063.383851625,
                    )
                ],
            },
            {
                "hotkey1": 0.0,
                "hotkey2": pytest.approx(0.00024586, abs=1e-8),
            },
        ),
        (
            "midrange scores",
            {
                "hotkeyA": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 1440,  # 1440 seconds ago (24 min)
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=100.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkeyB": [
                    MinerMetrics(
                        uptime=FIXED_NOW - 360,  # 6 min ago
                        valid_shares=200,
                        invalid_shares=0,
                        difficulty=100.0,
                        hashrate=2000.0,
                    )
                ],
            },
            {
                "hotkeyA": pytest.approx(0.08, abs=1e-8),
                "hotkeyB": pytest.approx(0.01, abs=1e-8),
            },
        ),
    ],
)
def test_rating_calculator(scenario, metrics_dict, expected):
    with patch("time.time", return_value=FIXED_NOW):
        calc = RatingCalculator()
        result = calc.rate_all(metrics_dict)
        for hotkey, exp_score in expected.items():
            assert (
                result[hotkey] == exp_score
            ), f"Scenario: {scenario}, Hotkey: {hotkey}, Expected: {exp_score}, Actual: {result[hotkey]}"


def test_rating_calculator_stub():
    assert True  # Placeholder


def test_rating_calculator_real_data():
    with patch("time.time", return_value=FIXED_NOW):
        calc = RatingCalculator()
        metrics_dict = {
            "hotkey1": [
                MinerMetrics(
                    uptime=FIXED_NOW - 3600,  # started at window start
                    valid_shares=119,
                    invalid_shares=0,
                    difficulty=33260.226740223945,
                    hashrate=894925502.344341,
                )
            ],
            "hotkey2": [
                MinerMetrics(
                    uptime=FIXED_NOW - 3599,  # started 1 second after window start
                    valid_shares=5,
                    invalid_shares=0,
                    difficulty=85.89934592,
                    hashrate=26177825.669120003,
                )
            ],
        }
        result = calc.rate_all(metrics_dict)
        expected = {
            "hotkey1": 1.0,
            "hotkey2": pytest.approx(0.00010845, abs=1e-8),
        }
        for hotkey, exp_score in expected.items():
            assert result[hotkey] == exp_score


def test_rating_calculator_stub_data():
    with patch("time.time", return_value=FIXED_NOW):
        calc = RatingCalculator()
        metrics_dict = {
            "stub1": [
                MinerMetrics(
                    uptime=FIXED_NOW - 3600,  # 1 hour before now
                    valid_shares=119,
                    invalid_shares=0,
                    difficulty=33260.226740223945,
                    hashrate=89492552.244341,
                ),
                MinerMetrics(
                    uptime=FIXED_NOW - 3600,  # 1 hour before now
                    valid_shares=0,
                    invalid_shares=0,
                    difficulty=0,
                    hashrate=0,
                ),
            ],
            "stub2": [
                MinerMetrics(
                    uptime=FIXED_NOW - 3600,  # 1 hour before now
                    valid_shares=5,
                    invalid_shares=0,
                    difficulty=85.89934592,
                    hashrate=26177825.669120003,
                )
            ],
        }
        result = calc.rate_all(metrics_dict)
        print("stub test result:", result)
        assert result["stub1"] > result["stub2"]
        assert result["stub1"] > 0
        assert result["stub2"] >= 0
