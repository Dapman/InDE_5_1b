"""
InDE MVP v5.1b.0 - IRC ITD Integration

Primary Deliverable F: Provides the .irc canvas data to the ITD Composition
Engine for integration into ITD Layer 2 (Evidence Architecture). Also
contributes resource pattern signals to Layers 5 and 6 when IML data is available.

Functions:
- get_itd_layer2_resource_data: Resource landscape for Layer 2
- get_itd_layer5_resource_patterns: Pattern intelligence for Layer 5
- get_itd_layer6_resource_projection: Forward projection for Layer 6

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Dict, Any, Optional

from .resource_entry_manager import ResourceEntryManager, AvailabilityStatus, CostConfidence
from .consolidation_engine import IRCConsolidationEngine

logger = logging.getLogger("inde.irc.itd_integration")


class IRCITDIntegration:
    """
    Integration layer between IRC and ITD modules.
    Provides resource landscape data for ITD composition.
    """

    def __init__(self, db, llm_client=None):
        """
        Initialize ITD integration.

        Args:
            db: Database instance
            llm_client: Optional IRCLLMClient for narrative generation
        """
        self.db = db
        self.llm_client = llm_client
        self.resource_manager = ResourceEntryManager(db)
        self.consolidation_engine = IRCConsolidationEngine(db)

    def get_itd_layer2_resource_data(self, pursuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Return the resource landscape summary for ITD Layer 2.

        Returns None if no .irc artifact exists (non-blocking for ITD).

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Dict with resource landscape data, or None if not available
        """
        # Get canvas
        canvas = self.consolidation_engine.get_canvas(pursuit_id)

        if not canvas:
            logger.debug(f"[IRCITDIntegration] No canvas for pursuit {pursuit_id}")
            return None

        # Get resources for narrative
        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)

        # Build Layer 2 data
        secured_count = canvas.get("secured_count", 0)
        open_count = canvas.get("unresolved_count", 0) + canvas.get("unknown_cost_count", 0)
        total_low = canvas.get("total_cost_low", 0)
        total_high = canvas.get("total_cost_high", 0)

        # Determine cost confidence level
        cost_confidence = self._determine_overall_cost_confidence(resources)

        # Generate prose summary
        prose = self._generate_layer2_prose(
            secured_count=secured_count,
            open_count=open_count,
            total_low=total_low,
            total_high=total_high,
            resources=resources,
        )

        # Generate ITD narrative
        itd_narrative = self._generate_itd_narrative(canvas, resources)

        return {
            "resource_summary_prose": prose,
            "resources_by_phase": canvas.get("resources_by_phase", {}),
            "cost_range": {
                "low": total_low,
                "high": total_high,
                "confidence": cost_confidence,
            },
            "open_questions_count": open_count,
            "secured_count": secured_count,
            "itd_narrative": itd_narrative,
            "canvas_completeness": canvas.get("canvas_completeness", 0),
            "itd_ready": canvas.get("itd_ready", False),
        }

    def get_itd_layer5_resource_patterns(self, pursuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Query IML for resource patterns from similar pursuits.

        Returns pattern intelligence for ITD Layer 5 (Pattern Connections).
        Returns None if IML has insufficient data (non-blocking).

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Resource pattern data, or None if insufficient data
        """
        try:
            # Get pursuit context for pattern matching
            pursuit = self.db.get_pursuit(pursuit_id)
            if not pursuit:
                return None

            archetype = pursuit.get("methodology_archetype", "general")

            # Query IML for resource patterns
            # In production, this would call the IML module
            patterns = self._query_iml_resource_patterns(archetype)

            if not patterns:
                return None

            return {
                "pattern_source": "IML",
                "archetype": archetype,
                "patterns": patterns,
                "pattern_count": len(patterns),
            }

        except Exception as e:
            logger.warning(f"[IRCITDIntegration] Layer 5 pattern query error: {e}")
            return None

    def get_itd_layer6_resource_projection(self, pursuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Return resource-dimension forward projection data for ITD Layer 6.

        Example: "Pursuits at this stage commonly discover that [resource type]
        becomes more critical in the first 90 days post-launch."

        Returns None if insufficient IML data (non-blocking).

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Resource projection data, or None if insufficient data
        """
        try:
            # Get canvas
            canvas = self.consolidation_engine.get_canvas(pursuit_id)
            if not canvas:
                return None

            # Get pursuit phase
            pursuit = self.db.get_pursuit(pursuit_id)
            if not pursuit:
                return None

            current_phase = pursuit.get("current_phase", "PITCH")

            # Query IML for forward projections
            projections = self._query_iml_resource_projections(current_phase)

            if not projections:
                return None

            return {
                "projection_source": "IML",
                "current_phase": current_phase,
                "projections": projections,
                "projection_count": len(projections),
            }

        except Exception as e:
            logger.warning(f"[IRCITDIntegration] Layer 6 projection error: {e}")
            return None

    def _generate_layer2_prose(
        self,
        secured_count: int,
        open_count: int,
        total_low: float,
        total_high: float,
        resources: list,
    ) -> str:
        """Generate prose summary for Layer 2."""
        total = len(resources)

        if total == 0:
            return "Resource requirements have not yet been captured."

        parts = []

        # Secured summary
        if secured_count > 0:
            if secured_count == 1:
                parts.append("One key resource is in place")
            else:
                parts.append(f"{secured_count} key resources are in place")
        else:
            parts.append("No resources are yet fully secured")

        # Open summary
        if open_count > 0:
            if open_count == 1:
                parts.append("one area is still being developed")
            else:
                parts.append(f"{open_count} areas are still being developed")

        # Cost summary
        if total_low > 0 or total_high > 0:
            if total_low == total_high:
                parts.append(f"with an estimated cost of ${total_low:,.0f}")
            else:
                parts.append(f"with estimated costs in the ${total_low:,.0f}–${total_high:,.0f} range")

        return ", ".join(parts) + "."

    def _generate_itd_narrative(
        self,
        canvas: Dict,
        resources: list,
    ) -> str:
        """Generate ITD narrative for how resource landscape fits the story."""
        completeness = canvas.get("canvas_completeness", 0)
        secured = canvas.get("secured_count", 0)
        total = len(resources)

        if total == 0:
            return "The resource landscape is still emerging from coaching conversations."

        readiness = secured / total if total > 0 else 0

        if readiness >= 0.8:
            return (
                "The pursuit has a well-developed understanding of its resource requirements, "
                "with most key elements already in place or being actively arranged."
            )
        elif readiness >= 0.5:
            return (
                "The pursuit has identified its core resource needs, with some elements "
                "secured and others in development. The resource picture continues to evolve."
            )
        else:
            return (
                "The pursuit is still developing its resource picture. Several key needs "
                "have been identified, and the innovator is working through how to address them."
            )

    def _determine_overall_cost_confidence(self, resources: list) -> str:
        """Determine overall cost confidence from resources."""
        if not resources:
            return "unknown"

        confidences = [r.get("cost_confidence", "UNKNOWN") for r in resources]

        # Count each level
        known = sum(1 for c in confidences if c == CostConfidence.KNOWN.value)
        estimated = sum(1 for c in confidences if c == CostConfidence.ESTIMATED.value)
        rough = sum(1 for c in confidences if c == CostConfidence.ROUGH_ORDER.value)
        unknown = sum(1 for c in confidences if c == CostConfidence.UNKNOWN.value)

        total = len(confidences)

        if known / total >= 0.7:
            return "confirmed"
        elif (known + estimated) / total >= 0.6:
            return "working_estimate"
        elif unknown / total >= 0.5:
            return "preliminary"
        else:
            return "rough_order"

    def _query_iml_resource_patterns(self, archetype: str) -> list:
        """
        Query IML for resource patterns.

        In production, this would call the IML module.
        For now, returns placeholder data.
        """
        # Placeholder - would integrate with actual IML
        try:
            patterns = list(self.db.db.iml_resource_patterns.find({
                "archetype": archetype,
            }).limit(5))

            return [
                {
                    "pattern_type": p.get("pattern_type", ""),
                    "description": p.get("description", ""),
                    "frequency": p.get("frequency", 0),
                }
                for p in patterns
            ]
        except Exception:
            return []

    def _query_iml_resource_projections(self, phase: str) -> list:
        """
        Query IML for resource projections.

        In production, this would call the IML module.
        For now, returns placeholder data.
        """
        # Placeholder - would integrate with actual IML
        try:
            projections = list(self.db.db.iml_resource_projections.find({
                "phase": phase,
            }).limit(3))

            return [
                {
                    "horizon": p.get("horizon", ""),
                    "projection": p.get("projection", ""),
                    "confidence": p.get("confidence", 0),
                }
                for p in projections
            ]
        except Exception:
            return []
