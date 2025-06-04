# rating.py
# Computes normalized ratings for Bittensor hotkeys based on miner metrics

from datetime import timedelta
from typing import Dict, List
import math

from .metrics import MinerMetrics
from fiber.utils import get_logger


logger = get_logger(__name__)

import time

class RatingCalculator:
    def __init__(self, uptime_alpha: float = 2.0, window: timedelta = timedelta(hours=1), ndigits: int = 8):
        self.uptime_alpha = float(uptime_alpha)
        self.window_seconds = window.total_seconds()  # length of the window (24h)
        self.ndigits = ndigits

    def compute_effective_work(self, metrics: List[MinerMetrics]) -> float:
        """Sum of valid_shares * difficulty."""
        return sum(m.valid_shares * m.difficulty for m in metrics)

    def compute_fractional_uptime(self, start_timestamp: float) -> float:
        """Convert the worker's unix start timestamp to a fractional uptime for the window."""
        now = time.time()
        window_start = now - self.window_seconds

        # If the start timestamp is in the future, consider the worker as not started in this window
        if start_timestamp > now:
            return 0.0

        # If the start is before the window, the worker was online for the entire window
        if start_timestamp < window_start:
            return 1.0

        # Otherwise, the worker started within the window, so was online from start to now:
        uptime_seconds = now - start_timestamp  # always < window_seconds
        return uptime_seconds / self.window_seconds

    def compute_avg_uptime(self, metrics: List[MinerMetrics]) -> float:
        """
        For each worker, take the uptime fraction (less than 1),
        then average across all workers for a single hotkey.
        """
        if not metrics:
            return 0.0
        # Convert each unix timestamp to a fraction
        uptimes = [self.compute_fractional_uptime(m.uptime) for m in metrics]
        # Clamp fractions to [0.0, 1.0] just in case
        uptimes = [max(0.0, min(1.0, u)) for u in uptimes]
        return sum(uptimes) / len(uptimes)

    def rate_all(self, metrics: Dict[str, List[MinerMetrics]]) -> Dict[str, float]:
        """
        First, compute effective work (valid_shares * difficulty),
        normalize, apply uptime penalty, and clamp the result.
        """
        # 1. Total work
        work = {
            hotkey: self.compute_effective_work(ms) for hotkey, ms in metrics.items()
        }
        max_work = max(work.values(), default=1.0)

        # 2. Normalization + penalty
        scores: Dict[str, float] = {}
        for hotkey, ms in metrics.items():
            norm_score = 0.0 if max_work == 0 else work[hotkey] / max_work
            avg_uptime = self.compute_avg_uptime(ms)  # ∈ [0.0, 1.0]
            penalized = norm_score * (avg_uptime ** self.uptime_alpha)
            # 3. Clamp to [0.0, 1.0]
            scores[hotkey] = round(max(0.0, min(1.0, penalized)), self.ndigits)
        return scores