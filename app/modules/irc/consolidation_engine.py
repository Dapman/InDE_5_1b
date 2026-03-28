"""
InDE MVP v5.1b.0 - IRC Consolidation Engine

Primary Deliverable C: Produces the .irc canvas artifact through a coached
walk-through. Triggered by the IRC_CONSOLIDATION Moment Type when signal
density and conversational pause conditions are met.

Components:
- ConsolidationTriggerEvaluator: Determines when to offer consolidation
- CanvasComputer: Computes derived canvas metrics
- IRCConsolidationEngine: Orchestrates the consolidation process

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

from .resource_entry_manager import (
    ResourceEntryManager,
    AvailabilityStatus,
    CostConfidence,
    PhaseAlignment,
)

logger = logging.getLogger("inde.irc.consolidation")


# =============================================================================
# CONSOLIDATION TRIGGER EVALUATOR
# =============================================================================

class ConsolidationTriggerEvaluator:
    """
    Evaluates whether IRC consolidation should be offered.

    Trigger conditions:
    - Signal density threshold met (any of):
        - total entries >= 4
        - unresolved >= 1 AND entries with cost >= 2
        - total >= 2 AND phase transition just occurred

    - Conversational pause point (any of):
        - Phase transition detected
        - Cost/budget/feasibility language
        - Forward-planning/next-steps language
        - Wrap-up/summarizing language

    Suppression overrides:
        - Consolidation within last 5 sessions
        - Declined in last 3 sessions
        - Higher-priority moment active
        - Active high-engagement flow
    """

    # Pause point language patterns
    PAUSE_PATTERNS = {
        "cost_budget": [
            "budget", "cost", "afford", "investment", "funding",
            "feasibility", "feasible", "capital", "expenses",
        ],
        "forward_planning": [
            "next steps", "going forward", "plan to", "moving forward",
            "what's next", "after that", "then we", "roadmap",
        ],
        "wrap_up": [
            "to summarize", "in summary", "overall", "to wrap up",
            "all in all", "that covers", "that's the picture",
        ],
    }

    def __init__(self, db):
        """Initialize the evaluator."""
        self.db = db
        self.resource_manager = ResourceEntryManager(db)
        self._cooldown_sessions = 5
        self._decline_memory_sessions = 3

    def evaluate(
        self,
        pursuit_id: str,
        conversation_context: Dict[str, Any],
    ) -> bool:
        """
        Evaluate whether consolidation should be triggered.

        Args:
            pursuit_id: The pursuit ID
            conversation_context: Current conversation context

        Returns:
            True if consolidation should be offered
        """
        # Check suppression conditions first
        if self._is_suppressed(pursuit_id, conversation_context):
            return False

        # Check signal density
        density = self.resource_manager.get_signal_density(pursuit_id)

        if not self._meets_density_threshold(density, conversation_context):
            return False

        # Check for conversational pause point
        if not self._is_pause_point(conversation_context):
            return False

        logger.info(
            f"[ConsolidationTrigger] Triggered for pursuit {pursuit_id}: "
            f"density={density['total_entries']}, eligible={density['consolidation_eligible']}"
        )
        return True

    def _meets_density_threshold(
        self,
        density: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Check if signal density meets consolidation threshold."""
        # Already computed by resource manager
        if density["consolidation_eligible"]:
            return True

        # Additional check: phase transition with 2+ resources
        if context.get("phase_transition_pending") and density["total_entries"] >= 2:
            return True

        return False

    def _is_pause_point(self, context: Dict[str, Any]) -> bool:
        """Check if current conversation is at a natural pause point."""
        # Phase transition is always a pause point
        if context.get("phase_transition_pending"):
            return True

        # Check last message for pause language
        last_message = context.get("last_user_message", "").lower()

        for category, patterns in self.PAUSE_PATTERNS.items():
            if any(pattern in last_message for pattern in patterns):
                logger.debug(f"[ConsolidationTrigger] Pause point: {category}")
                return True

        return False

    def _is_suppressed(
        self,
        pursuit_id: str,
        context: Dict[str, Any],
    ) -> bool:
        """Check suppression conditions."""
        # Check session cooldown
        if self._check_cooldown(pursuit_id):
            logger.debug("[ConsolidationTrigger] Suppressed: cooldown active")
            return True

        # Check decline memory
        if self._check_decline_memory(pursuit_id):
            logger.debug("[ConsolidationTrigger] Suppressed: recent decline")
            return True

        # Check high-priority moment
        if context.get("active_high_priority_moment"):
            logger.debug("[ConsolidationTrigger] Suppressed: high-priority moment")
            return True

        # Check high engagement flow
        if context.get("momentum_state", {}).get("flow_level", 0) > 0.8:
            logger.debug("[ConsolidationTrigger] Suppressed: high engagement")
            return True

        return False

    def _check_cooldown(self, pursuit_id: str) -> bool:
        """Check if consolidation is in cooldown period."""
        try:
            canvas = self.db.db.irc_canvases.find_one({"pursuit_id": pursuit_id})
            if not canvas:
                return False

            # Check sessions since last consolidation
            last_consolidation = canvas.get("generated_at")
            if not last_consolidation:
                return False

            # Get sessions since then
            sessions = self.db.db.coaching_sessions.count_documents({
                "pursuit_id": pursuit_id,
                "created_at": {"$gt": last_consolidation},
            })

            return sessions < self._cooldown_sessions

        except Exception as e:
            logger.warning(f"[ConsolidationTrigger] Cooldown check error: {e}")
            return False

    def _check_decline_memory(self, pursuit_id: str) -> bool:
        """Check if user declined consolidation recently."""
        try:
            # Look for recent decline events
            decline = self.db.db.irc_events.find_one({
                "pursuit_id": pursuit_id,
                "event_type": "CONSOLIDATION_DECLINED",
            }, sort=[("created_at", -1)])

            if not decline:
                return False

            # Count sessions since decline
            sessions = self.db.db.coaching_sessions.count_documents({
                "pursuit_id": pursuit_id,
                "created_at": {"$gt": decline["created_at"]},
            })

            return sessions < self._decline_memory_sessions

        except Exception as e:
            logger.warning(f"[ConsolidationTrigger] Decline check error: {e}")
            return False


# =============================================================================
# CANVAS COMPUTER
# =============================================================================

class CanvasComputer:
    """
    Computes derived .irc canvas fields from included .resource entries.
    All computations are deterministic (no LLM calls).
    """

    # Completeness weights for field population
    COMPLETENESS_WEIGHTS = {
        "resource_name": 1.0,         # Required
        "category": 0.5,              # Required
        "phase_alignment": 0.5,       # Important
        "availability_status": 1.0,   # Important
        "cost_estimate_low": 0.5,     # Valuable
        "cost_estimate_high": 0.5,    # Valuable
        "cost_confidence": 0.3,       # Supporting
        "criticality": 0.3,           # Supporting
        "duration_type": 0.2,         # Nice to have
    }

    def compute(
        self,
        pursuit_id: str,
        included_resources: List[Dict],
    ) -> Dict[str, Any]:
        """
        Compute all derived .irc canvas fields.

        Args:
            pursuit_id: The pursuit ID
            included_resources: List of .resource entries to include

        Returns:
            Computed canvas data
        """
        # Group by phase
        resources_by_phase = {phase.value: [] for phase in PhaseAlignment}
        for r in included_resources:
            for phase in r.get("phase_alignment", [PhaseAlignment.ACROSS_ALL.value]):
                if phase in resources_by_phase:
                    resources_by_phase[phase].append(r.get("artifact_id"))

        # Group by category
        resources_by_category = {}
        for r in included_resources:
            cat = r.get("category", "SERVICES")
            if cat not in resources_by_category:
                resources_by_category[cat] = []
            resources_by_category[cat].append(r.get("artifact_id"))

        # Compute cost totals
        total_cost_low = sum(
            r.get("cost_estimate_low", 0) or 0
            for r in included_resources
        )
        total_cost_high = sum(
            r.get("cost_estimate_high", 0) or 0
            for r in included_resources
        )

        # Cost by phase
        cost_by_phase = {}
        for phase in PhaseAlignment:
            phase_resources = [
                r for r in included_resources
                if phase.value in r.get("phase_alignment", [])
            ]
            cost_by_phase[phase.value] = {
                "low": sum(r.get("cost_estimate_low", 0) or 0 for r in phase_resources),
                "high": sum(r.get("cost_estimate_high", 0) or 0 for r in phase_resources),
            }

        # Count statuses
        unresolved_count = sum(
            1 for r in included_resources
            if r.get("availability_status") in [
                AvailabilityStatus.UNRESOLVED.value,
                AvailabilityStatus.UNKNOWN.value
            ]
        )
        unknown_cost_count = sum(
            1 for r in included_resources
            if r.get("cost_confidence") == CostConfidence.UNKNOWN.value
        )
        secured_count = sum(
            1 for r in included_resources
            if r.get("availability_status") == AvailabilityStatus.SECURED.value
        )

        # Compute completeness score
        completeness = self._compute_completeness(included_resources)

        return {
            "pursuit_id": pursuit_id,
            "resources_by_phase": resources_by_phase,
            "resources_by_category": resources_by_category,
            "total_cost_low": total_cost_low,
            "total_cost_high": total_cost_high,
            "cost_by_phase": cost_by_phase,
            "unresolved_count": unresolved_count,
            "unknown_cost_count": unknown_cost_count,
            "secured_count": secured_count,
            "canvas_completeness": completeness,
            "itd_ready": completeness >= 0.60,
            "total_resources": len(included_resources),
        }

    def _compute_completeness(self, resources: List[Dict]) -> float:
        """
        Compute weighted field population score.

        Returns value between 0.0 and 1.0.
        """
        if not resources:
            return 0.0

        total_weight = sum(self.COMPLETENESS_WEIGHTS.values()) * len(resources)
        achieved_weight = 0.0

        for r in resources:
            for field, weight in self.COMPLETENESS_WEIGHTS.items():
                value = r.get(field)

                # Check if field has meaningful value
                if field in ["cost_estimate_low", "cost_estimate_high"]:
                    has_value = value is not None
                elif field in ["phase_alignment"]:
                    has_value = bool(value) and value != [PhaseAlignment.ACROSS_ALL.value]
                elif field in ["availability_status", "cost_confidence", "criticality", "duration_type"]:
                    has_value = value not in [None, "UNKNOWN"]
                else:
                    has_value = bool(value)

                if has_value:
                    achieved_weight += weight

        return achieved_weight / total_weight if total_weight > 0 else 0.0


# =============================================================================
# IRC CONSOLIDATION ENGINE
# =============================================================================

class IRCConsolidationEngine:
    """
    Orchestrates IRC consolidation process.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, db, llm_client=None):
        """
        Initialize the consolidation engine.

        Args:
            db: Database instance
            llm_client: Optional IRCLLMClient for synthesis notes
        """
        self.db = db
        self.llm_client = llm_client
        self.resource_manager = ResourceEntryManager(db)
        self.canvas_computer = CanvasComputer()
        self.trigger_evaluator = ConsolidationTriggerEvaluator(db)

    async def create_or_update_canvas(
        self,
        pursuit_id: str,
        include_resource_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create or update the .irc canvas for a pursuit.

        Args:
            pursuit_id: The pursuit ID
            include_resource_ids: Optional specific resources to include.
                                  If None, includes all resources.

        Returns:
            The created/updated canvas document
        """
        # Get resources
        if include_resource_ids:
            resources = [
                self.resource_manager.get_resource(rid)
                for rid in include_resource_ids
            ]
            resources = [r for r in resources if r]  # Filter None
        else:
            resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)

        if not resources:
            logger.warning(f"[Consolidation] No resources for pursuit {pursuit_id}")
            return {}

        # Compute canvas
        computed = self.canvas_computer.compute(pursuit_id, resources)

        # Generate synthesis notes
        synthesis_notes = ""
        if self.llm_client:
            try:
                synthesis_notes = await self.llm_client.generate_synthesis_notes(
                    computed
                )
            except Exception as e:
                logger.warning(f"[Consolidation] Synthesis notes error: {e}")

        # Check for existing canvas
        existing = self.db.db.irc_canvases.find_one({"pursuit_id": pursuit_id})
        consolidation_count = (existing.get("consolidation_count", 0) + 1) if existing else 1

        # Build canvas document
        now = datetime.now(timezone.utc)
        canvas_doc = {
            "pursuit_id": pursuit_id,
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": now,
            "consolidation_count": consolidation_count,
            "resources_by_phase": computed["resources_by_phase"],
            "resources_by_category": computed["resources_by_category"],
            "total_cost_low": computed["total_cost_low"],
            "total_cost_high": computed["total_cost_high"],
            "cost_by_phase": computed["cost_by_phase"],
            "unresolved_count": computed["unresolved_count"],
            "unknown_cost_count": computed["unknown_cost_count"],
            "secured_count": computed["secured_count"],
            "canvas_completeness": computed["canvas_completeness"],
            "coach_synthesis_notes": synthesis_notes,
            "itd_ready": computed["itd_ready"],
            "included_resource_ids": [r["artifact_id"] for r in resources],
        }

        # Upsert
        if existing:
            self.db.db.irc_canvases.update_one(
                {"pursuit_id": pursuit_id},
                {"$set": canvas_doc},
            )
            canvas_doc["_id"] = existing["_id"]
        else:
            result = self.db.db.irc_canvases.insert_one(canvas_doc)
            canvas_doc["_id"] = result.inserted_id

        # Mark resources as included
        self.resource_manager.mark_irc_included([r["artifact_id"] for r in resources])

        logger.info(
            f"[Consolidation] Canvas {'updated' if existing else 'created'} "
            f"for pursuit {pursuit_id}: completeness={computed['canvas_completeness']:.2f}"
        )

        return self._serialize_canvas(canvas_doc)

    def get_canvas(self, pursuit_id: str) -> Optional[Dict[str, Any]]:
        """Get the IRC canvas for a pursuit."""
        canvas = self.db.db.irc_canvases.find_one({"pursuit_id": pursuit_id})
        return self._serialize_canvas(canvas) if canvas else None

    def record_consolidation_event(
        self,
        pursuit_id: str,
        event_type: str,
        data: Optional[Dict] = None,
    ) -> None:
        """Record a consolidation-related event."""
        self.db.db.irc_events.insert_one({
            "pursuit_id": pursuit_id,
            "event_type": event_type,
            "data": data or {},
            "created_at": datetime.now(timezone.utc),
        })

    def _serialize_canvas(self, canvas: Dict) -> Dict[str, Any]:
        """Serialize canvas for API response."""
        if not canvas:
            return {}

        return {
            "artifact_id": str(canvas.get("_id", "")),
            "pursuit_id": canvas.get("pursuit_id", ""),
            "schema_version": canvas.get("schema_version", "1.0"),
            "generated_at": canvas.get("generated_at", "").isoformat()
                if hasattr(canvas.get("generated_at"), 'isoformat')
                else str(canvas.get("generated_at", "")),
            "consolidation_count": canvas.get("consolidation_count", 0),
            "resources_by_phase": canvas.get("resources_by_phase", {}),
            "resources_by_category": canvas.get("resources_by_category", {}),
            "total_cost_low": canvas.get("total_cost_low", 0),
            "total_cost_high": canvas.get("total_cost_high", 0),
            "cost_by_phase": canvas.get("cost_by_phase", {}),
            "unresolved_count": canvas.get("unresolved_count", 0),
            "unknown_cost_count": canvas.get("unknown_cost_count", 0),
            "secured_count": canvas.get("secured_count", 0),
            "canvas_completeness": canvas.get("canvas_completeness", 0.0),
            "coach_synthesis_notes": canvas.get("coach_synthesis_notes", ""),
            "itd_ready": canvas.get("itd_ready", False),
            "included_resource_ids": canvas.get("included_resource_ids", []),
        }


# =============================================================================
# MDS INTEGRATION
# =============================================================================

def get_irc_consolidation_moment_definition():
    """
    Returns the MDS Moment Definition for IRC_CONSOLIDATION.

    This is called by the coaching pipeline to register the IRC consolidation
    trigger with the Moment Detection System.
    """
    return {
        "moment_type": "IRC_CONSOLIDATION",
        "priority": 4,           # Slightly higher than RESOURCE_SIGNAL
        "cooldown_sessions": 5,  # Session-based cooldown
        "description": "Sufficient resource signals accumulated; natural pause point detected",
    }
