"""
Cohort Aggregator

InDE MVP v4.5.0 — The Engagement Engine

Computes anonymized aggregate metrics for the innovator cohort.
All data is aggregated — no individual user information is ever exposed.

Metrics:
- active_24h: Unique users with any activity in last 24 hours
- active_7d: Unique users with any activity in last 7 days
- artifacts_7d: Total artifacts generated in last 7 days
- pursuits_advancing_7d: Pursuits with significant progress in last 7 days
- cohort_momentum_signal: Tier-based signal (buzzing, active, warming_up, getting_started)

The cohort_momentum_signal is a simple 4-tier classification:
- buzzing: 60%+ of 7d users active in 24h
- active: 30-60% of 7d users active in 24h
- warming_up: 10-30% of 7d users active in 24h
- getting_started: <10% of 7d users active in 24h (or very small cohort)

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Cache duration in seconds
CACHE_DURATION_SECONDS = 900  # 15 minutes


@dataclass
class CohortSignals:
    """Cohort presence metrics."""
    active_24h: int                    # Users active in last 24 hours
    active_7d: int                     # Users active in last 7 days
    artifacts_7d: int                  # Artifacts generated in last 7 days
    pursuits_advancing_7d: int         # Pursuits with progress in last 7 days
    cohort_momentum_signal: str        # buzzing | active | warming_up | getting_started
    signal_label: str                  # Innovator-facing description
    computed_at: str                   # ISO 8601 timestamp


class CohortAggregator:
    """
    Aggregates anonymized cohort presence signals.

    Uses a simple in-memory cache with 15-minute TTL to avoid
    recomputing on every request.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access
        """
        self.db = db
        self._cache: Optional[CohortSignals] = None
        self._cache_time: Optional[datetime] = None

    def get_signals(self, force_refresh: bool = False) -> CohortSignals:
        """
        Get current cohort signals, using cache if available.

        Args:
            force_refresh: If True, bypass cache and recompute

        Returns:
            CohortSignals with current aggregate metrics
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if not force_refresh and self._cache and self._cache_time:
            age = (now - self._cache_time).total_seconds()
            if age < CACHE_DURATION_SECONDS:
                return self._cache

        # Compute fresh signals
        signals = self._compute_signals()
        self._cache = signals
        self._cache_time = now

        return signals

    def _compute_signals(self) -> CohortSignals:
        """Compute cohort signals from database."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        try:
            # Active users in last 24 hours
            # Uses coaching_sessions collection for activity tracking
            active_24h = self._count_active_users(day_ago)

            # Active users in last 7 days
            active_7d = self._count_active_users(week_ago)

            # Artifacts generated in last 7 days
            artifacts_7d = self._count_artifacts(week_ago)

            # Pursuits with progress in last 7 days
            pursuits_advancing_7d = self._count_advancing_pursuits(week_ago)

            # Compute momentum signal
            signal, label = self._compute_momentum_signal(active_24h, active_7d)

        except Exception as e:
            logger.warning(f"Cohort aggregation failed: {e}")
            # Return safe defaults
            active_24h = 0
            active_7d = 0
            artifacts_7d = 0
            pursuits_advancing_7d = 0
            signal = "getting_started"
            label = "The community is just getting started"

        return CohortSignals(
            active_24h=active_24h,
            active_7d=active_7d,
            artifacts_7d=artifacts_7d,
            pursuits_advancing_7d=pursuits_advancing_7d,
            cohort_momentum_signal=signal,
            signal_label=label,
            computed_at=now.isoformat(),
        )

    def _count_active_users(self, since: datetime) -> int:
        """Count unique users with activity since the given time."""
        try:
            # Count unique user_ids from coaching_sessions
            pipeline = [
                {"$match": {"created_at": {"$gte": since}}},
                {"$group": {"_id": "$user_id"}},
                {"$count": "total"}
            ]
            result = list(self.db.db.coaching_sessions.aggregate(pipeline))
            return result[0]["total"] if result else 0
        except Exception:
            # Fallback: count from pursuits
            try:
                pipeline = [
                    {"$match": {"updated_at": {"$gte": since}}},
                    {"$group": {"_id": "$user_id"}},
                    {"$count": "total"}
                ]
                result = list(self.db.db.pursuits.aggregate(pipeline))
                return result[0]["total"] if result else 0
            except Exception:
                return 0

    def _count_artifacts(self, since: datetime) -> int:
        """Count artifacts created since the given time."""
        try:
            return self.db.db.artifacts.count_documents({
                "created_at": {"$gte": since}
            })
        except Exception:
            return 0

    def _count_advancing_pursuits(self, since: datetime) -> int:
        """Count pursuits with significant progress since the given time."""
        try:
            # Pursuits with artifact creation or phase transition
            return self.db.db.pursuits.count_documents({
                "updated_at": {"$gte": since},
                "state": "ACTIVE"
            })
        except Exception:
            return 0

    def _compute_momentum_signal(self, active_24h: int, active_7d: int) -> tuple:
        """
        Compute the cohort momentum signal from activity ratios.

        Returns:
            (signal_key: str, signal_label: str)
        """
        if active_7d < 3:
            # Very small cohort
            return "getting_started", "The community is just getting started"

        ratio = active_24h / active_7d if active_7d > 0 else 0

        if ratio >= 0.6:
            return "buzzing", "The community is buzzing with activity"
        elif ratio >= 0.3:
            return "active", "Innovators are actively exploring"
        elif ratio >= 0.1:
            return "warming_up", "The community is warming up"
        else:
            return "getting_started", "New innovators are joining"
