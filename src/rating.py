# rating.py
# Computes normalized ratings for Bittensor hotkeys based on miner metrics

from datetime import timedelta
from typing import Dict, List
import math

from .metrics import MinerMetrics
from fiber.utils import get_logger


logger = get_logger(__name__)



class RatingCalculator:
    def __init__(
        self,
        uptime_alpha: float = 2.0,
        window: timedelta = timedelta(hours=1),
        ndigits: int = 8,
        max_difficulty: float = 16384.0,
        shares_per_minute: int = 20,  # New field for share rate limit
    ):
        self.uptime_alpha = float(uptime_alpha)
        self.window_seconds = (
            window.total_seconds()
        )  # length of the window (24h)
        self.ndigits = ndigits
        self.max_difficulty = max_difficulty
        self.shares_per_minute = shares_per_minute  # Store the new field

    def compute_effective_work(self, metrics: List[MinerMetrics]) -> float:
        """
        Sum of valid_shares * difficulty, with difficulty clamped to self.max_difficulty,
        and apply a per-worker penalty if difficulty exceeds max_difficulty.
        Also applies an exponential penalty if valid_shares exceeds allowed shares per window.
        """
        window_minutes = self.window_seconds / 60.0
        allowed_shares = window_minutes * self.shares_per_minute
        work = 0.0
        for m in metrics:
            if m.valid_shares > allowed_shares:
                excess = m.valid_shares - allowed_shares
                share_penalty = math.exp(-excess / allowed_shares)
            else:
                share_penalty = 1.0
            work += m.valid_shares * min(m.difficulty, self.max_difficulty) * self.penalty_exponential(m.difficulty) * share_penalty
        return work

    def compute_fractional_uptime(self, uptime_seconds: float) -> float:
        """Convert the worker's uptime_seconds to a fractional uptime for the window."""
        # Clamp to [0, window_seconds]
        uptime = max(0.0, min(uptime_seconds, self.window_seconds))
        return uptime / self.window_seconds

    def compute_avg_uptime(self, metrics: List[MinerMetrics]) -> float:
        """
        For each worker, take the uptime fraction (less than 1),
        then average across all workers for a single hotkey.
        """
        if not metrics:
            return 0.0
        # Use uptime_seconds instead of uptime
        uptimes = [self.compute_fractional_uptime(m.uptime_seconds) for m in metrics]
        # Clamp fractions to [0.0, 1.0] just in case
        uptimes = [max(0.0, min(1.0, u)) for u in uptimes]
        return sum(uptimes) / len(uptimes)

    def penalty_exponential(self, difficulty: float) -> float:
        """
        Applies an exponential penalty if difficulty exceeds max_difficulty.
        Returns a penalty factor in [0, 1].
        """
        if difficulty > self.max_difficulty:
            return math.exp(-(difficulty - self.max_difficulty) / self.max_difficulty)
        return 1.0

    def rate_all(
        self, metrics: Dict[str, List[MinerMetrics]]
    ) -> Dict[str, float]:
        """
        First, compute effective work (valid_shares * difficulty),
        normalize, apply uptime penalty, and clamp the result.
        """
        # 1. Total work (now includes per-worker penalty)
        work = {
            hotkey: self.compute_effective_work(ms)
            for hotkey, ms in metrics.items()
        }
        max_work = max(work.values(), default=1.0)

        # 2. Normalization + penalty
        scores: Dict[str, float] = {}
        for hotkey, ms in metrics.items():
            norm_score = 0.0 if max_work == 0 else work[hotkey] / max_work
            avg_uptime = self.compute_avg_uptime(ms)  # ∈ [0.0, 1.0]
            penalized = norm_score * (avg_uptime**self.uptime_alpha)
            # 3. Clamp to [0.0, 1.0]
            scores[hotkey] = round(max(0.0, min(1.0, penalized)), self.ndigits)
        return scores
