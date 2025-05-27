# tests/test_rating.py
import pytest
from src.rating import RatingCalculator
from src.metrics import MinerMetrics


@pytest.mark.parametrize(
    "scenario,metrics_dict,expected",
    [
        (
            "single hotkey, single worker, perfect uptime",
            {
                "hotkey1": [
                    MinerMetrics(
                        uptime=1.0,
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
                        uptime=1.0,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=1.0,
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
                        uptime=0.5,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=1.0,
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
                        uptime=1.0,
                        valid_shares=50,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    ),
                    MinerMetrics(
                        uptime=0.5,
                        valid_shares=50,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    ),
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=1.0,
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
                        uptime=1.0,
                        valid_shares=0,
                        invalid_shares=0,
                        difficulty=2.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=1.0,
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
                "5GEQ4ZkrXcz7y3HK8TAd4V9ZeERJKPNeF21EifKqCJRkZGaY": [
                    MinerMetrics(
                        uptime=0.0,
                        valid_shares=1274,
                        invalid_shares=0,
                        difficulty=15647.46811773941,
                        hashrate=783547108.9145503,
                    )
                ],
                "hotkey2": [
                    MinerMetrics(
                        uptime=1.0,
                        valid_shares=1000,
                        invalid_shares=0,
                        difficulty=10000.0,
                        hashrate=500000000.0,
                    )
                ],
            },
            {
                "5GEQ4ZkrXcz7y3HK8TAd4V9ZeERJKPNeF21EifKqCJRkZGaY": 0.0,
                "hotkey2": 0.5016334594528169,
            },
        ),
        (
            "realistic metrics example 2",
            {
                "5GEQ4ZkrXcz7y3HK8TAd4V9ZeERJKPNeF21EifKqCJRkZGaY": [
                    MinerMetrics(
                        uptime=0.0,
                        valid_shares=1001,
                        invalid_shares=0,
                        difficulty=15664.64798692341,
                        hashrate=619774754.039591,
                    )
                ],
                "5Dw1pwoWUH7sBMdapAGPTi698VR1GZufFBbsTEP4cx8BkjLF": [
                    MinerMetrics(
                        uptime=1748268814,
                        valid_shares=33,
                        invalid_shares=0,
                        difficulty=116.82311045120004,
                        hashrate=34039063.383851625,
                    )
                ],
            },
            {
                "5GEQ4ZkrXcz7y3HK8TAd4V9ZeERJKPNeF21EifKqCJRkZGaY": 0.0,
                "5Dw1pwoWUH7sBMdapAGPTi698VR1GZufFBbsTEP4cx8BkjLF": 1.0,
            },
        ),
        (
            "midrange scores",
            {
                "hotkeyA": [
                    MinerMetrics(
                        uptime=0.6,
                        valid_shares=100,
                        invalid_shares=0,
                        difficulty=100.0,
                        hashrate=1000.0,
                    )
                ],
                "hotkeyB": [
                    MinerMetrics(
                        uptime=0.9,
                        valid_shares=200,
                        invalid_shares=0,
                        difficulty=100.0,
                        hashrate=2000.0,
                    )
                ],
            },
            {
                "hotkeyA": pytest.approx(0.18, abs=0.01),
                "hotkeyB": pytest.approx(0.81, abs=0.01),
            },
        ),
    ],
)
def test_rating_calculator(scenario, metrics_dict, expected):
    calc = RatingCalculator()
    result = calc.rate_all(metrics_dict)
    for hotkey, exp_score in expected.items():
        assert (
            result[hotkey] == exp_score
        ), f"Scenario: {scenario}, Hotkey: {hotkey}, Expected: {exp_score}, Actual: {result[hotkey]}"


def test_rating_calculator_stub():
    assert True  # Placeholder
