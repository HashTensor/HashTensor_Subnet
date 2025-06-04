# validator.py
# Main validation logic for Bittensor subnet

from .metrics import MetricsClient
from .mapping import MappingManager
from .rating import RatingCalculator
from .config import ValidatorSettings
from typing import Dict, List
from src.metrics import MinerMetrics
from collections import defaultdict


class Validator:
    def __init__(
        self,
        config: ValidatorSettings,
        metrics_client: MetricsClient,
        mapping_manager: MappingManager,
    ):
        self.config = config
        self.metrics_client = metrics_client
        self.mapping_manager = mapping_manager
        self.rating_calculator = RatingCalculator(config.rating_weight, config.window)

    async def compute_ratings(self):
        """Fetch metrics, update mapping, compute ratings, and send to Bittensor."""
        hotkey_metrics = await self.get_hotkey_metrics_map()
        ratings = self.rating_calculator.rate_all(hotkey_metrics)
        return ratings

    async def get_hotkey_metrics_map(self) -> Dict[str, List[MinerMetrics]]:
        """Load mapping and map metrics to hotkeys. Returns dict[hotkey, List[MinerMetrics]]."""
        metrics = await self.metrics_client.fetch_metrics()
        hotkey_metrics: Dict[str, List[MinerMetrics]] = defaultdict(list)
        for miner_key, miner_metrics in metrics.items():
            hotkey = await self.mapping_manager.get_hotkey(miner_key.worker)
            if hotkey:
                hotkey_metrics[hotkey].append(miner_metrics)
        return dict(hotkey_metrics)
