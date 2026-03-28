"""
InDE v4.8 - Horizon Generator

Analyzes a TrajectoryDataset and produces three horizon blocks:
  - 90-day horizon: immediate challenges and actions
  - 180-day horizon: growth inflections and direction signals
  - 365-day horizon: transformation patterns and compounding leverage points

Each horizon block contains:
  - common_patterns: list of patterns observed in >=30% of similar pursuits
  - success_correlated_actions: actions most associated with positive trajectories
  - confidence: data confidence score (0.0-1.0) based on sample size + quality
  - narrative_seed: structured data consumed by the LLM narrative generator

Language Sovereignty applies to all narrative_seed values. This module
generates structured data, not prose. Prose generation happens in the
Forward Projection Engine via the LLM client.

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass, field
from typing import List, Dict, Callable
from .trajectory_analyzer import TrajectoryDataset


@dataclass
class HorizonBlock:
    """A single horizon block (90, 180, or 365 days)."""
    horizon_days: int
    common_patterns: List[str]
    success_correlated_actions: List[str]
    confidence: float
    sample_basis: int  # number of similar pursuits with data at this horizon
    narrative_seed: Dict  # structured context for LLM narrative generation


@dataclass
class HorizonSet:
    """Complete set of three horizon blocks."""
    day_90: HorizonBlock
    day_180: HorizonBlock
    day_365: HorizonBlock
    overall_projection_confidence: float
    data_quality: str


class HorizonGenerator:
    """
    Derives horizon blocks from a TrajectoryDataset.
    """

    PATTERN_FREQUENCY_THRESHOLD = 0.30  # >=30% of similar pursuits

    def generate(self, dataset: TrajectoryDataset) -> HorizonSet:
        """
        Generate all three horizon blocks from the trajectory dataset.

        Args:
            dataset: TrajectoryDataset with similar pursuits

        Returns:
            HorizonSet with 90, 180, and 365-day blocks
        """
        if dataset.sample_size == 0:
            return self._low_confidence_horizon_set()

        day_90 = self._analyze_horizon(
            dataset, horizon_days=90,
            event_filter=lambda e: self._within_days(e, 90)
        )
        day_180 = self._analyze_horizon(
            dataset, horizon_days=180,
            event_filter=lambda e: (
                self._within_days(e, 180)
                and not self._within_days(e, 90)
            )
        )
        day_365 = self._analyze_horizon(
            dataset, horizon_days=365,
            event_filter=lambda e: (
                self._within_days(e, 365)
                and not self._within_days(e, 180)
            )
        )

        overall_confidence = (
            day_90.confidence * 0.4
            + day_180.confidence * 0.35
            + day_365.confidence * 0.25
        )

        return HorizonSet(
            day_90=day_90,
            day_180=day_180,
            day_365=day_365,
            overall_projection_confidence=round(overall_confidence, 3),
            data_quality=dataset.data_quality,
        )

    def _analyze_horizon(
        self,
        dataset: TrajectoryDataset,
        horizon_days: int,
        event_filter: Callable
    ) -> HorizonBlock:
        """Extract patterns from post-completion records within horizon window."""
        horizon_events = []
        for pursuit in dataset.similar_pursuits:
            matching = [
                e for e in pursuit.post_completion_records
                if event_filter(e)
            ]
            horizon_events.extend(matching)

        pattern_counts: Dict[str, int] = {}
        success_action_counts: Dict[str, int] = {}

        for event in horizon_events:
            pattern = event.get("pattern_tag", event.get("event_type", ""))
            if pattern:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            if event.get("outcome_positive"):
                action = event.get("action_tag", "")
                if action:
                    success_action_counts[action] = (
                        success_action_counts.get(action, 0) + 1
                    )

        threshold = max(
            1, int(dataset.sample_size * self.PATTERN_FREQUENCY_THRESHOLD)
        )
        common = [
            p for p, count in pattern_counts.items() if count >= threshold
        ]
        success_actions = sorted(
            success_action_counts.keys(),
            key=lambda a: success_action_counts[a],
            reverse=True
        )[:5]

        sample_basis = sum(
            1 for p in dataset.similar_pursuits
            if any(event_filter(e) for e in p.post_completion_records)
        )
        confidence = self._compute_confidence(
            sample_basis, len(common), dataset.data_quality
        )

        return HorizonBlock(
            horizon_days=horizon_days,
            common_patterns=common[:8],
            success_correlated_actions=success_actions,
            confidence=confidence,
            sample_basis=sample_basis,
            narrative_seed={
                "horizon_days": horizon_days,
                "archetype": dataset.archetype_of_subject,
                "domain": dataset.domain_of_subject,
                "common_patterns": common[:8],
                "success_actions": success_actions,
                "sample_size": dataset.sample_size,
                "sample_basis": sample_basis,
                "data_quality": dataset.data_quality,
            }
        )

    def _compute_confidence(
        self, sample_basis: int, pattern_count: int, data_quality: str
    ) -> float:
        """Compute confidence score based on sample size and data quality."""
        base = min(1.0, sample_basis / 10.0)
        quality_multiplier = {
            "HIGH": 1.0,
            "MEDIUM": 0.8,
            "LOW": 0.55
        }.get(data_quality, 0.55)
        return round(base * quality_multiplier, 3)

    def _within_days(self, event: dict, days: int) -> bool:
        """Check if event falls within N days of pursuit completion."""
        days_since = event.get("days_since_completion")
        if days_since is None:
            return False
        try:
            return 0 <= int(days_since) <= days
        except (ValueError, TypeError):
            return False

    def _low_confidence_horizon_set(self) -> HorizonSet:
        """Returns a structurally valid but minimally-populated HorizonSet."""
        def empty_block(days: int) -> HorizonBlock:
            return HorizonBlock(
                horizon_days=days,
                common_patterns=[],
                success_correlated_actions=[],
                confidence=0.0,
                sample_basis=0,
                narrative_seed={"data_available": False, "horizon_days": days},
            )

        return HorizonSet(
            day_90=empty_block(90),
            day_180=empty_block(180),
            day_365=empty_block(365),
            overall_projection_confidence=0.0,
            data_quality="LOW",
        )
