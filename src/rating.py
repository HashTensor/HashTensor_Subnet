# rating.py
# Computes normalized ratings for Bittensor hotkeys based on miner metrics

from typing import Dict, List
import math

from .metrics import MinerMetrics


class RatingCalculator:
    def __init__(self, uptime_alpha: float = 2.0):
        self.uptime_alpha = uptime_alpha

    def compute_effective_work(self, metrics: List[MinerMetrics]) -> float:
        """Sum valid_shares * difficulty for all workers."""
        return sum(m.valid_shares * m.difficulty for m in metrics)

    def compute_avg_uptime(self, metrics: List[MinerMetrics]) -> float:
        if not metrics:
            return 0.0
        return sum(m.uptime for m in metrics) / len(metrics)

    def rate_all(
        self, metrics: Dict[str, List[MinerMetrics]]
    ) -> Dict[str, float]:
        """Compute normalized, uptime-penalized scores for all hotkeys."""
        # 1. Aggregate effective work
        work = {
            hotkey: self.compute_effective_work(ms)
            for hotkey, ms in metrics.items()
        }
        max_work = max(work.values(), default=1.0)
        # 2. Normalize and apply uptime penalty
        scores = {}
        for hotkey, ms in metrics.items():
            if max_work == 0:
                norm_score = 0.0
            else:
                norm_score = work[hotkey] / max_work
            avg_uptime = self.compute_avg_uptime(ms)
            penalized = norm_score * (avg_uptime**self.uptime_alpha)
            # 3. Clamp to [0.0, 1.0]
            scores[hotkey] = max(0.0, min(1.0, penalized))
        return scores
