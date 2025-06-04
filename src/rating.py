# rating.py
# Computes normalized ratings for Bittensor hotkeys based on miner metrics

from typing import Dict, List
import math

from .metrics import MinerMetrics
from fiber.utils import get_logger


logger = get_logger(__name__)

class RatingCalculator:
    def __init__(self, uptime_alpha: float = 2.0):
        self.uptime_alpha = uptime_alpha

    def compute_effective_work(self, metrics: List[MinerMetrics]) -> float:
        """Sum valid_shares * difficulty for all workers."""
        effective_work = sum(m.valid_shares * m.difficulty for m in metrics)
        logger.debug(f"Computed effective work: {effective_work} from metrics: {metrics}")
        return effective_work

    def compute_avg_uptime(self, metrics: List[MinerMetrics]) -> float:
        if not metrics:
            logger.debug("No metrics provided to compute_avg_uptime, returning 0.0")
            return 0.0
        avg_uptime = sum(m.uptime for m in metrics) / len(metrics)
        logger.debug(f"Computed average uptime: {avg_uptime} from metrics: {metrics}")
        return avg_uptime

    def rate_all(
        self, metrics: Dict[str, List[MinerMetrics]]
    ) -> Dict[str, float]:
        """Compute normalized, uptime-penalized scores for all hotkeys."""
        # 1. Aggregate effective work
        work = {
            hotkey: self.compute_effective_work(ms)
            for hotkey, ms in metrics.items()
        }
        logger.debug(f"Aggregated effective work per hotkey: {work}")
        max_work = max(work.values(), default=1.0)
        logger.debug(f"Max effective work: {max_work}")
        # 2. Normalize and apply uptime penalty
        scores = {}
        for hotkey, ms in metrics.items():
            if max_work == 0:
                norm_score = 0.0
            else:
                norm_score = work[hotkey] / max_work
            avg_uptime = self.compute_avg_uptime(ms)
            penalized = norm_score * (avg_uptime**self.uptime_alpha)
            logger.debug(
                f"Hotkey: {hotkey}, norm_score: {norm_score}, avg_uptime: {avg_uptime}, penalized: {penalized}"
            )
            # 3. Clamp to [0.0, 1.0]
            scores[hotkey] = max(0.0, min(1.0, penalized))
        logger.debug(f"Final scores: {scores}")
        return scores
