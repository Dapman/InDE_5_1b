"""
Learning Velocity Engine

InDE MVP v4.5.0 — The Engagement Engine

Computes a user's learning velocity based on their activity patterns across
pursuits. Velocity measures how actively a user is engaging with and
progressing through their innovation journey.

Components of velocity:
  1. Conversation Activity — Messages sent in coaching sessions
  2. Artifact Generation — Vision, fears, hypothesis artifacts created
  3. Scaffolding Progress — Elements filled in across pursuits
  4. Pursuit Momentum — Phase progression and session frequency

The score is 0–100 where:
  - 0–30: Low activity (dormant or just starting)
  - 31–50: Moderate activity (steady engagement)
  - 51–70: Good velocity (active learning)
  - 71–100: High velocity (intensive engagement)

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LearningVelocityEngine:
    """
    Computes learning velocity metrics for a user.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access pattern
        """
        self.db = db

    def compute_velocity(self, user_id: str) -> Dict:
        """
        Compute learning velocity for a user.

        Returns:
            {
                "score": float (0-100),
                "trend": float (positive = improving, negative = declining),
                "history": List[Dict] (last 10 data points),
                "conversion_rate": float (0-1, pursuits with artifacts / total),
                "org_average": float (0-100, average across all users)
            }
        """
        try:
            # Get user's pursuits
            pursuits = list(self.db.db.pursuits.find(
                {"user_id": user_id},
                {"pursuit_id": 1, "created_at": 1, "state": 1}
            ))
            pursuit_ids = [p["pursuit_id"] for p in pursuits]

            if not pursuit_ids:
                return self._empty_velocity()

            # Compute component scores
            conversation_score = self._compute_conversation_activity(pursuit_ids)
            artifact_score = self._compute_artifact_generation(pursuit_ids)
            scaffolding_score = self._compute_scaffolding_progress(pursuit_ids)
            momentum_score = self._compute_pursuit_momentum(pursuit_ids)

            # Weighted composite score
            # Conversation is most important (40%), then artifacts (25%),
            # scaffolding (20%), momentum (15%)
            composite = (
                conversation_score * 0.40 +
                artifact_score * 0.25 +
                scaffolding_score * 0.20 +
                momentum_score * 0.15
            )

            # Compute trend (compare last 7 days to prior 7 days)
            trend = self._compute_trend(pursuit_ids)

            # Build history (last 10 days of activity)
            history = self._build_history(pursuit_ids)

            # Compute conversion rate (pursuits with artifacts / total)
            conversion_rate = self._compute_conversion_rate(pursuit_ids)

            # Get org average (simplified - average of all active users)
            org_average = self._compute_org_average()

            return {
                "score": round(composite, 1),
                "trend": round(trend, 2),
                "history": history,
                "conversion_rate": round(conversion_rate, 3),
                "org_average": round(org_average, 1),
            }

        except Exception as e:
            logger.error(f"Learning velocity computation failed for {user_id}: {e}")
            return self._empty_velocity()

    def _empty_velocity(self) -> Dict:
        """Return empty velocity for users with no data."""
        return {
            "score": 0,
            "trend": 0,
            "history": [],
            "conversion_rate": 0,
            "org_average": 50,
        }

    def _compute_conversation_activity(self, pursuit_ids: List[str]) -> float:
        """
        Score based on conversation activity in the last 14 days.
        More recent messages weighted higher.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # Count messages in last 7 days
        recent_count = self.db.db.conversation_history.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "timestamp": {"$gte": seven_days_ago}
        })

        # Count messages in prior 7 days
        prior_count = self.db.db.conversation_history.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "timestamp": {"$gte": fourteen_days_ago, "$lt": seven_days_ago}
        })

        # Also count total messages for baseline
        total_count = self.db.db.conversation_history.count_documents({
            "pursuit_id": {"$in": pursuit_ids}
        })

        # Score: recent activity weighted 2x prior activity
        # Normalize to 0-100 scale
        # 0 messages = 0, 5+ recent messages = 100
        weighted_activity = (recent_count * 2) + prior_count
        score = min(100, (weighted_activity / 10) * 100)

        # Boost for consistent activity
        if recent_count > 0 and prior_count > 0:
            score = min(100, score * 1.1)

        return score

    def _compute_artifact_generation(self, pursuit_ids: List[str]) -> float:
        """
        Score based on artifacts generated.
        Each artifact type has different weight.
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Count recent artifacts by type
        recent_artifacts = list(self.db.db.artifacts.find({
            "pursuit_id": {"$in": pursuit_ids},
            "created_at": {"$gte": thirty_days_ago}
        }, {"artifact_type": 1}))

        if not recent_artifacts:
            # Check for any artifacts ever
            total_artifacts = self.db.db.artifacts.count_documents({
                "pursuit_id": {"$in": pursuit_ids}
            })
            if total_artifacts > 0:
                return 30  # Has artifacts but none recent
            return 0

        # Weight artifacts: vision=30, fears=25, hypothesis=25, other=20
        artifact_weights = {
            "vision": 30,
            "fears": 25,
            "hypothesis": 25,
        }

        score = 0
        for artifact in recent_artifacts:
            atype = artifact.get("artifact_type", "other")
            score += artifact_weights.get(atype, 20)

        return min(100, score)

    def _compute_scaffolding_progress(self, pursuit_ids: List[str]) -> float:
        """
        Score based on scaffolding element completion.
        """
        scaffolding_states = list(self.db.db.scaffolding_states.find({
            "pursuit_id": {"$in": pursuit_ids}
        }))

        if not scaffolding_states:
            return 0

        total_elements = 0
        filled_elements = 0

        for state in scaffolding_states:
            for element_type in ["vision_elements", "fear_elements", "hypothesis_elements"]:
                elements = state.get(element_type, {})
                for key, value in elements.items():
                    total_elements += 1
                    if value and (isinstance(value, dict) and value.get("text")) or value:
                        filled_elements += 1

        if total_elements == 0:
            return 0

        completion_rate = filled_elements / total_elements
        return completion_rate * 100

    def _compute_pursuit_momentum(self, pursuit_ids: List[str]) -> float:
        """
        Score based on pursuit activity and momentum snapshots.
        """
        # Check for recent momentum snapshots
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        recent_snapshots = list(self.db.db.momentum_snapshots.find({
            "pursuit_id": {"$in": pursuit_ids},
            "recorded_at": {"$gte": seven_days_ago}
        }, {"composite_score": 1}))

        if recent_snapshots:
            # Average recent momentum scores
            avg_momentum = sum(s.get("composite_score", 0.5) for s in recent_snapshots) / len(recent_snapshots)
            return avg_momentum * 100

        # Fallback: check coaching sessions
        session_count = self.db.db.coaching_sessions.count_documents({
            "pursuit_id": {"$in": pursuit_ids}
        })

        # 0 sessions = 20, 1-3 = 40, 4-6 = 60, 7+ = 80
        if session_count >= 7:
            return 80
        elif session_count >= 4:
            return 60
        elif session_count >= 1:
            return 40
        return 20

    def _compute_trend(self, pursuit_ids: List[str]) -> float:
        """
        Compute trend by comparing recent activity to prior period.
        Returns positive for improving, negative for declining.
        """
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # Count all activity in each period
        recent_messages = self.db.db.conversation_history.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "timestamp": {"$gte": seven_days_ago}
        })

        prior_messages = self.db.db.conversation_history.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "timestamp": {"$gte": fourteen_days_ago, "$lt": seven_days_ago}
        })

        recent_artifacts = self.db.db.artifacts.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "created_at": {"$gte": seven_days_ago}
        })

        prior_artifacts = self.db.db.artifacts.count_documents({
            "pursuit_id": {"$in": pursuit_ids},
            "created_at": {"$gte": fourteen_days_ago, "$lt": seven_days_ago}
        })

        recent_total = recent_messages + (recent_artifacts * 5)
        prior_total = prior_messages + (prior_artifacts * 5)

        if prior_total == 0:
            return 1 if recent_total > 0 else 0

        # Calculate percentage change, capped at +/- 1
        change = (recent_total - prior_total) / max(prior_total, 1)
        return max(-1, min(1, change))

    def _build_history(self, pursuit_ids: List[str]) -> List[Dict]:
        """
        Build activity history for the last 10 days.
        """
        now = datetime.now(timezone.utc)
        history = []

        for days_ago in range(9, -1, -1):
            day_start = (now - timedelta(days=days_ago)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)

            # Count messages for this day
            message_count = self.db.db.conversation_history.count_documents({
                "pursuit_id": {"$in": pursuit_ids},
                "timestamp": {"$gte": day_start, "$lt": day_end}
            })

            # Count artifacts for this day
            artifact_count = self.db.db.artifacts.count_documents({
                "pursuit_id": {"$in": pursuit_ids},
                "created_at": {"$gte": day_start, "$lt": day_end}
            })

            # Weighted daily score (artifacts worth more)
            daily_score = min(100, (message_count * 10) + (artifact_count * 30))

            history.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "value": daily_score
            })

        return history

    def _compute_conversion_rate(self, pursuit_ids: List[str]) -> float:
        """
        Compute pursuit-to-artifact conversion rate.
        How many pursuits have generated at least one artifact?
        """
        if not pursuit_ids:
            return 0

        pursuits_with_artifacts = 0
        for pursuit_id in pursuit_ids:
            has_artifact = self.db.db.artifacts.count_documents({
                "pursuit_id": pursuit_id
            }) > 0
            if has_artifact:
                pursuits_with_artifacts += 1

        return pursuits_with_artifacts / len(pursuit_ids)

    def _compute_org_average(self) -> float:
        """
        Compute organization-wide average velocity.
        Simplified: sample recent active users and average their scores.
        """
        try:
            # Find users with recent activity
            now = datetime.now(timezone.utc)
            thirty_days_ago = now - timedelta(days=30)

            # Get unique user_ids from recent conversations
            pipeline = [
                {"$match": {"timestamp": {"$gte": thirty_days_ago}}},
                {"$group": {"_id": "$user_id"}},
                {"$limit": 50}
            ]

            # This requires user_id in conversation_history, which may not exist
            # Fallback to pursuits
            recent_pursuits = list(self.db.db.pursuits.find(
                {"created_at": {"$gte": thirty_days_ago}},
                {"user_id": 1}
            ).limit(50))

            if not recent_pursuits:
                return 50  # Default org average

            user_ids = list(set(p.get("user_id") for p in recent_pursuits if p.get("user_id")))

            if len(user_ids) <= 1:
                return 50  # Not enough users for meaningful average

            # Sample a few users and compute their scores
            # (Don't recursively call compute_velocity to avoid infinite loop)
            total_score = 0
            count = 0

            for uid in user_ids[:10]:
                pursuits = list(self.db.db.pursuits.find(
                    {"user_id": uid},
                    {"pursuit_id": 1}
                ))
                pids = [p["pursuit_id"] for p in pursuits]
                if pids:
                    conv_score = self._compute_conversation_activity(pids)
                    total_score += conv_score
                    count += 1

            if count == 0:
                return 50

            return total_score / count

        except Exception as e:
            logger.warning(f"Org average computation failed: {e}")
            return 50
