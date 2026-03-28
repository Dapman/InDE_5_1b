"""
InDE MVP v5.1b.0 - IRC IML Integration

Primary Deliverable G: Write-to and query-from IML for resource pattern
intelligence. Creates new pattern type "resource_snapshot" that feeds
future consolidation recommendations and phase-timing suggestions.

Functions:
- contribute_resource_pattern: Write resource snapshot to IML
- query_similar_resource_patterns: Get patterns from similar pursuits

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .resource_entry_manager import ResourceEntryManager, AvailabilityStatus, PhaseAlignment, ResourceCategory
from .consolidation_engine import IRCConsolidationEngine

logger = logging.getLogger("inde.irc.iml_integration")


# =============================================================================
# PATTERN SCHEMA
# =============================================================================

RESOURCE_PATTERN_SCHEMA_VERSION = "1.0"


# =============================================================================
# IML INTEGRATION
# =============================================================================

class IRCIMLIntegration:
    """
    Integration layer between IRC and IML modules.
    Contributes resource patterns and queries for similar patterns.
    """

    def __init__(self, db):
        """
        Initialize IML integration.

        Args:
            db: Database instance
        """
        self.db = db
        self.resource_manager = ResourceEntryManager(db)
        self.consolidation_engine = IRCConsolidationEngine(db)

    def contribute_resource_pattern(
        self,
        pursuit_id: str,
        contribution_trigger: str,
    ) -> Optional[str]:
        """
        Write a resource_snapshot pattern to IML when canvas is consolidated.

        Pattern includes:
        - Archetype
        - Phase at consolidation
        - Resource category distribution
        - Availability status distribution
        - Cost range
        - Completeness score

        Args:
            pursuit_id: The pursuit ID
            contribution_trigger: What triggered the contribution
                                  (e.g., "CANVAS_CONSOLIDATED", "PURSUIT_COMPLETED")

        Returns:
            Pattern ID if successfully contributed, None otherwise
        """
        try:
            # Get pursuit context
            pursuit = self.db.get_pursuit(pursuit_id)
            if not pursuit:
                logger.warning(f"[IRCIMLIntegration] Pursuit not found: {pursuit_id}")
                return None

            # Get canvas
            canvas = self.consolidation_engine.get_canvas(pursuit_id)
            if not canvas:
                logger.debug(f"[IRCIMLIntegration] No canvas for pursuit {pursuit_id}")
                return None

            # Get resources
            resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)
            if not resources:
                logger.debug(f"[IRCIMLIntegration] No resources for pursuit {pursuit_id}")
                return None

            # Build pattern
            pattern = self._build_resource_pattern(
                pursuit=pursuit,
                canvas=canvas,
                resources=resources,
                trigger=contribution_trigger,
            )

            # Check IKF eligibility
            if not self._is_ikf_eligible(pursuit, pattern):
                logger.debug(f"[IRCIMLIntegration] Pattern not IKF eligible")
                # Still write locally, just not federated
                pattern["ikf_eligible"] = False
            else:
                pattern["ikf_eligible"] = True

            # Write to IML
            result = self.db.db.iml_resource_patterns.insert_one(pattern)
            pattern_id = str(result.inserted_id)

            logger.info(
                f"[IRCIMLIntegration] Contributed pattern {pattern_id} "
                f"for pursuit {pursuit_id} (trigger: {contribution_trigger})"
            )
            return pattern_id

        except Exception as e:
            logger.error(f"[IRCIMLIntegration] Contribution error: {e}")
            return None

    def _build_resource_pattern(
        self,
        pursuit: Dict,
        canvas: Dict,
        resources: List[Dict],
        trigger: str,
    ) -> Dict:
        """Build the resource pattern document."""
        now = datetime.now(timezone.utc)

        # Category distribution
        category_dist = {cat.value: 0 for cat in ResourceCategory}
        for r in resources:
            cat = r.get("category", "SERVICES")
            if cat in category_dist:
                category_dist[cat] += 1

        # Availability distribution
        availability_dist = {status.value: 0 for status in AvailabilityStatus}
        for r in resources:
            status = r.get("availability_status", "UNKNOWN")
            if status in availability_dist:
                availability_dist[status] += 1

        # Phase distribution
        phase_dist = {phase.value: 0 for phase in PhaseAlignment}
        for r in resources:
            for phase in r.get("phase_alignment", []):
                if phase in phase_dist:
                    phase_dist[phase] += 1

        return {
            "schema_version": RESOURCE_PATTERN_SCHEMA_VERSION,
            "pattern_type": "resource_snapshot",
            "created_at": now,
            "pursuit_id": pursuit.get("_id") or pursuit.get("id"),
            "archetype": pursuit.get("methodology_archetype", "general"),
            "phase_at_contribution": pursuit.get("current_phase", "UNKNOWN"),
            "contribution_trigger": trigger,

            # Distribution data (anonymized for IKF)
            "resource_count": len(resources),
            "category_distribution": category_dist,
            "availability_distribution": availability_dist,
            "phase_distribution": phase_dist,

            # Canvas metrics
            "canvas_completeness": canvas.get("canvas_completeness", 0),
            "total_cost_low": canvas.get("total_cost_low", 0),
            "total_cost_high": canvas.get("total_cost_high", 0),
            "secured_ratio": canvas.get("secured_count", 0) / len(resources) if resources else 0,

            # Pattern learning signals
            "consolidation_count": canvas.get("consolidation_count", 1),
        }

    def _is_ikf_eligible(self, pursuit: Dict, pattern: Dict) -> bool:
        """Check if pattern is eligible for IKF federation."""
        # Practice pursuits are excluded
        if pursuit.get("is_practice", False):
            return False

        # Must have minimum completeness
        if pattern.get("canvas_completeness", 0) < 0.40:
            return False

        # Must have minimum resources
        if pattern.get("resource_count", 0) < 3:
            return False

        return True

    def query_similar_resource_patterns(
        self,
        archetype: str,
        phase: str,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Query IML for resource patterns from similar pursuits.

        Used for:
        - Consolidation timing suggestions
        - Common resource categories by phase
        - Typical cost ranges

        Args:
            archetype: The methodology archetype
            phase: The current phase
            limit: Maximum patterns to return

        Returns:
            List of similar resource patterns
        """
        try:
            # Query patterns matching archetype and phase
            patterns = list(self.db.db.iml_resource_patterns.find({
                "archetype": archetype,
                "phase_at_contribution": phase,
                "canvas_completeness": {"$gte": 0.50},  # Only reasonably complete
            }).sort("created_at", -1).limit(limit))

            # Aggregate insights
            return [self._summarize_pattern(p) for p in patterns]

        except Exception as e:
            logger.warning(f"[IRCIMLIntegration] Query error: {e}")
            return []

    def get_archetype_resource_insights(self, archetype: str) -> Dict[str, Any]:
        """
        Get aggregate resource insights for an archetype.

        Returns:
            Aggregated insights for the archetype
        """
        try:
            # Aggregate across all patterns for this archetype
            pipeline = [
                {"$match": {"archetype": archetype}},
                {"$group": {
                    "_id": "$archetype",
                    "avg_resource_count": {"$avg": "$resource_count"},
                    "avg_completeness": {"$avg": "$canvas_completeness"},
                    "avg_cost_low": {"$avg": "$total_cost_low"},
                    "avg_cost_high": {"$avg": "$total_cost_high"},
                    "total_patterns": {"$sum": 1},
                }},
            ]

            results = list(self.db.db.iml_resource_patterns.aggregate(pipeline))

            if not results:
                return {"archetype": archetype, "data_available": False}

            result = results[0]
            return {
                "archetype": archetype,
                "data_available": True,
                "avg_resource_count": round(result.get("avg_resource_count", 0), 1),
                "avg_completeness": round(result.get("avg_completeness", 0), 2),
                "avg_cost_range": {
                    "low": result.get("avg_cost_low", 0),
                    "high": result.get("avg_cost_high", 0),
                },
                "pattern_count": result.get("total_patterns", 0),
            }

        except Exception as e:
            logger.warning(f"[IRCIMLIntegration] Insights query error: {e}")
            return {"archetype": archetype, "data_available": False}

    def _summarize_pattern(self, pattern: Dict) -> Dict:
        """Summarize a pattern for external use (hide pursuit_id for privacy)."""
        return {
            "archetype": pattern.get("archetype"),
            "phase": pattern.get("phase_at_contribution"),
            "resource_count": pattern.get("resource_count", 0),
            "canvas_completeness": pattern.get("canvas_completeness", 0),
            "secured_ratio": pattern.get("secured_ratio", 0),
            "cost_range": {
                "low": pattern.get("total_cost_low", 0),
                "high": pattern.get("total_cost_high", 0),
            },
            "category_distribution": pattern.get("category_distribution", {}),
        }
