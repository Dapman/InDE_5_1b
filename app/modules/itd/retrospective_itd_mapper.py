"""
InDE MVP v4.7.0 - Retrospective to ITD Mapper

Maps retrospective conversation answers and artifact data to ITD layers.

Mapping Strategy:
- Journey highlights → Narrative Arc (acts content)
- Key learnings → Coach's Perspective (themes)
- Surprise factors → Evidence Architecture (pivot triggers)
- Methodology assessment → Thesis Statement (archetype context)
- Fear resolutions → Evidence Architecture (confidence changes)

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("inde.itd.retrospective_mapper")


# =============================================================================
# RETROSPECTIVE QUESTION CATEGORIES
# =============================================================================

# Maps retrospective prompt categories to ITD layers
CATEGORY_TO_LAYER_MAP = {
    "HYPOTHESIS_VALIDATION": [
        "evidence_architecture",
        "narrative_arc",
    ],
    "LEARNING_VELOCITY": [
        "evidence_architecture",
        "coachs_perspective",
    ],
    "PIVOT_POINTS": [
        "evidence_architecture",
        "narrative_arc",
    ],
    "METHODOLOGY_EFFECTIVENESS": [
        "thesis_statement",
        "narrative_arc",
    ],
    "SURPRISE_FACTORS": [
        "evidence_architecture",
        "narrative_arc",
    ],
    "FEAR_RESOLUTION": [
        "evidence_architecture",
        "coachs_perspective",
    ],
    "FUTURE_ADAPTATIONS": [
        "narrative_arc",
        "coachs_perspective",
    ],
}


# =============================================================================
# RETROSPECTIVE ITD MAPPER
# =============================================================================

class RetrospectiveITDMapper:
    """
    Maps retrospective data to ITD layer inputs.

    Transforms retrospective answers and artifacts into structured
    data that feeds ITD layer generators.
    """

    def __init__(self, db=None):
        """
        Initialize RetrospectiveITDMapper.

        Args:
            db: Optional database instance for fetching retrospective data
        """
        self.db = db

    def map_retrospective_to_itd(
        self,
        pursuit_id: str,
        retrospective_id: str = None,
    ) -> Dict[str, Dict]:
        """
        Map retrospective data to ITD layer inputs.

        Args:
            pursuit_id: The pursuit ID
            retrospective_id: Optional specific retrospective ID

        Returns:
            Dict mapping layer names to input data:
            {
                "thesis_statement": {...},
                "evidence_architecture": {...},
                "narrative_arc": {...},
                "coachs_perspective": {...},
            }
        """
        logger.info(f"[RetroMapper] Mapping retrospective for pursuit: {pursuit_id}")

        # Get retrospective data
        retro_data = self._get_retrospective(pursuit_id, retrospective_id)

        if not retro_data:
            logger.warning(f"[RetroMapper] No retrospective found for pursuit: {pursuit_id}")
            return self._empty_mapping()

        # Extract artifact data
        artifact = retro_data.get("artifact", {})
        conversations = retro_data.get("conversation_log", [])

        # Build layer mappings
        mapping = {
            "thesis_statement": self._map_to_thesis(artifact, conversations),
            "evidence_architecture": self._map_to_evidence(artifact, conversations),
            "narrative_arc": self._map_to_narrative(artifact, conversations),
            "coachs_perspective": self._map_to_coach(artifact, conversations),
        }

        logger.info(f"[RetroMapper] Mapped retrospective to {len(mapping)} layers")
        return mapping

    def _get_retrospective(
        self,
        pursuit_id: str,
        retrospective_id: str = None
    ) -> Optional[Dict]:
        """Get retrospective document from database."""
        if not self.db:
            return None

        try:
            if retrospective_id:
                return self.db.db.retrospectives.find_one({
                    "retrospective_id": retrospective_id
                })
            else:
                # Get most recent retrospective for pursuit
                return self.db.db.retrospectives.find_one(
                    {"pursuit_id": pursuit_id},
                    sort=[("completed_at", -1)]
                )
        except Exception as e:
            logger.error(f"[RetroMapper] Error fetching retrospective: {e}")
            return None

    def _map_to_thesis(self, artifact: Dict, conversations: List) -> Dict:
        """
        Map retrospective data to thesis statement layer inputs.

        Extracts:
        - Methodology assessment for archetype context
        - Outcome state for thesis framing
        """
        methodology = artifact.get("methodology_assessment", {})

        return {
            "methodology_effectiveness": methodology.get("effectiveness_score", 0),
            "methodology_feedback": methodology.get("feedback", ""),
            "outcome_state": artifact.get("outcome_state", "UNKNOWN"),
            "key_achievement": artifact.get("key_achievement", ""),
        }

    def _map_to_evidence(self, artifact: Dict, conversations: List) -> Dict:
        """
        Map retrospective data to evidence architecture layer inputs.

        Extracts:
        - Hypothesis outcomes for confidence data
        - Surprise factors as pivot triggers
        - Fear resolutions for validation events
        """
        # Extract hypothesis validations
        hypothesis_outcomes = artifact.get("hypothesis_outcomes", [])
        validated = [h for h in hypothesis_outcomes if h.get("outcome") == "validated"]
        invalidated = [h for h in hypothesis_outcomes if h.get("outcome") == "invalidated"]

        # Extract surprise factors (potential pivots)
        surprise_factors = artifact.get("surprise_factors", [])

        # Get fear resolutions
        fear_resolutions = []
        try:
            if self.db:
                cursor = self.db.db.fear_resolutions.find({
                    "pursuit_id": artifact.get("pursuit_id")
                })
                fear_resolutions = list(cursor)
        except Exception:
            pass

        return {
            "hypotheses_validated": len(validated),
            "hypotheses_invalidated": len(invalidated),
            "hypothesis_details": hypothesis_outcomes,
            "surprise_factors": surprise_factors,
            "fear_resolutions": fear_resolutions,
            "pivot_triggers": [
                {"type": "surprise", "description": s}
                for s in surprise_factors
            ] + [
                {"type": "invalidation", "description": h.get("evidence", "")}
                for h in invalidated
            ],
        }

    def _map_to_narrative(self, artifact: Dict, conversations: List) -> Dict:
        """
        Map retrospective data to narrative arc layer inputs.

        Extracts:
        - Journey highlights for act content
        - Timeline events for story structure
        - Key moments from conversations
        """
        # Extract journey highlights
        key_learnings = artifact.get("key_learnings", [])
        pivot_points = artifact.get("pivot_points", [])

        # Build journey timeline
        timeline_events = []
        for learning in key_learnings:
            timeline_events.append({
                "type": "learning",
                "description": learning.get("learning", ""),
                "category": learning.get("category", "general"),
            })

        for pivot in pivot_points:
            timeline_events.append({
                "type": "pivot",
                "description": pivot.get("decision", pivot.get("description", "")),
            })

        # Extract key conversation moments
        conversation_highlights = self._extract_conversation_highlights(conversations)

        return {
            "journey_highlights": key_learnings,
            "pivot_points": pivot_points,
            "timeline_events": timeline_events,
            "conversation_highlights": conversation_highlights,
            "duration_days": artifact.get("duration_days", 0),
            "outcome_reflection": artifact.get("outcome_reflection", ""),
        }

    def _map_to_coach(self, artifact: Dict, conversations: List) -> Dict:
        """
        Map retrospective data to coach's perspective layer inputs.

        Extracts:
        - Key learnings for coaching themes
        - Conversation highlights for moment selection
        - Methodology feedback for reflection
        """
        key_learnings = artifact.get("key_learnings", [])

        # Extract themes from learning categories
        themes = list(set(
            l.get("category", "general")
            for l in key_learnings
            if l.get("category")
        ))

        # Get methodology feedback
        methodology = artifact.get("methodology_assessment", {})

        return {
            "learning_themes": themes,
            "key_learnings": key_learnings,
            "methodology_feedback": methodology.get("feedback", ""),
            "future_recommendations": artifact.get("future_recommendations", []),
            "conversation_log": conversations,
        }

    def _extract_conversation_highlights(self, conversations: List) -> List[Dict]:
        """
        Extract significant moments from retrospective conversations.

        Looks for:
        - Aha moments (user realizations)
        - Pivotal decisions
        - Key reflections
        """
        highlights = []

        for i, msg in enumerate(conversations):
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "").lower()

            # Check for significant indicators
            is_highlight = any([
                "realized" in content,
                "learned" in content,
                "should have" in content,
                "key takeaway" in content,
                "most important" in content,
                "pivotal" in content,
                "changed everything" in content,
            ])

            if is_highlight:
                highlights.append({
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp"),
                    "context": conversations[i-1].get("content", "") if i > 0 else "",
                })

        return highlights[:5]  # Limit to 5 highlights

    def _empty_mapping(self) -> Dict[str, Dict]:
        """Return empty mapping structure."""
        return {
            "thesis_statement": {},
            "evidence_architecture": {},
            "narrative_arc": {},
            "coachs_perspective": {},
        }

    def get_retrospective_summary(self, pursuit_id: str) -> Dict:
        """
        Get a summary of retrospective data for ITD generation.

        Returns simplified data suitable for passing to ITDCompositionEngine.
        """
        retro_data = self._get_retrospective(pursuit_id)

        if not retro_data:
            return {}

        artifact = retro_data.get("artifact", {})

        return {
            "key_learnings": [
                l.get("learning", "") for l in artifact.get("key_learnings", [])
            ],
            "outcome_reflection": artifact.get("outcome_reflection", ""),
            "surprise_factors": artifact.get("surprise_factors", []),
            "future_recommendations": artifact.get("future_recommendations", []),
            "methodology_score": artifact.get("methodology_assessment", {}).get("effectiveness_score", 0),
            "outcome_state": artifact.get("outcome_state", "UNKNOWN"),
        }
