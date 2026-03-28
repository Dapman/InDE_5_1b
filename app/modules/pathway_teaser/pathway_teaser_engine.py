"""
Pathway Teaser Engine

InDE MVP v4.5.0 — The Engagement Engine

Generates forward-leaning teasers for the next coaching pathway after
an artifact is finalized. The teaser uses IML pattern data first,
with static fallback if IML data is insufficient.

Pathway progression:
  vision → risk_preview (What risks could ambush this?)
  risk → hypothesis_preview (What assumptions need testing?)
  hypothesis → validation_preview (How will you know if it works?)
  validation → reflection_preview (What have you learned?)

The teaser is meant to create continuity — a soft bridge from achievement
to next action. It supplements (not replaces) the momentum bridge.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


# Artifact type → next pathway mapping
PATHWAY_SEQUENCE = {
    "vision": "risk_preview",
    "fears": "hypothesis_preview",
    "hypothesis": "validation_preview",
    "validation": "reflection_preview",
}

# Static teaser templates (fallback when IML data insufficient)
STATIC_TEASERS = {
    "risk_preview": {
        "headline": "What could threaten this vision?",
        "body": "Strong ideas face hard questions. Exploring potential risks now can protect your momentum later.",
        "cta": "Explore risk patterns",
        "target_pathway": "fears",
    },
    "hypothesis_preview": {
        "headline": "What assumptions are you making?",
        "body": "Every idea rests on beliefs about the world. Surfacing them helps you test what matters most.",
        "cta": "Define key assumptions",
        "target_pathway": "hypothesis",
    },
    "validation_preview": {
        "headline": "How will you know if it works?",
        "body": "Evidence turns assumptions into confidence. Design a simple test for your most important belief.",
        "cta": "Design a test",
        "target_pathway": "validation",
    },
    "reflection_preview": {
        "headline": "What has this journey taught you?",
        "body": "The best innovators learn from every pursuit — wins, surprises, and pivots alike.",
        "cta": "Capture your learnings",
        "target_pathway": "retrospective",
    },
}


@dataclass
class PathwayTeaser:
    """Teaser content for the next coaching pathway."""
    teaser_type: str           # risk_preview | hypothesis_preview | etc.
    headline: str              # Attention-grabbing question
    body: str                  # 1-2 sentences of preview
    cta: str                   # Call-to-action button text
    target_pathway: str        # coaching pathway ID
    source: str                # "iml" | "fallback"
    pattern_previews: Optional[List[str]] = None  # IML pattern snippets


class PathwayTeaserEngine:
    """
    Generates pathway teasers based on artifact finalization.

    Uses IML momentum patterns first; falls back to static templates.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access
        """
        self.db = db

    def get_teaser(self, pursuit_id: str, completed_artifact_type: str) -> Optional[PathwayTeaser]:
        """
        Generate a teaser for the next pathway after artifact completion.

        Args:
            pursuit_id: The pursuit that completed an artifact
            completed_artifact_type: Type of artifact just finalized

        Returns:
            PathwayTeaser if a next pathway exists, None if all explored
        """
        # Determine next pathway
        teaser_type = PATHWAY_SEQUENCE.get(completed_artifact_type)
        if not teaser_type:
            logger.debug(f"No teaser for artifact type: {completed_artifact_type}")
            return None

        # Check if target artifact already exists (all explored)
        target_pathway = STATIC_TEASERS[teaser_type]["target_pathway"]
        # Support both 'type' and 'artifact_type' field names
        existing = self.db.db.artifacts.find_one({
            "pursuit_id": pursuit_id,
            "$or": [{"type": target_pathway}, {"artifact_type": target_pathway}]
        })
        if existing:
            logger.debug(f"Target pathway {target_pathway} already explored")
            return None

        # Try IML patterns first
        iml_teaser = self._try_iml_teaser(pursuit_id, teaser_type)
        if iml_teaser:
            return iml_teaser

        # Fallback to static template
        return self._static_teaser(teaser_type)

    def _try_iml_teaser(self, pursuit_id: str, teaser_type: str) -> Optional[PathwayTeaser]:
        """
        Try to generate a teaser from IML momentum patterns.

        Returns None if IML data is insufficient.
        """
        try:
            # Query momentum patterns for this context
            from modules.iml.momentum_pattern_persistence import get_patterns_for_context

            pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})
            if not pursuit:
                return None

            # Get patterns relevant to the target pathway
            target_artifact = STATIC_TEASERS[teaser_type]["target_pathway"]
            patterns = get_patterns_for_context(
                self.db,
                pursuit_stage=pursuit.get("current_phase", "VISION"),
                artifact_type=target_artifact,
                min_confidence=0.3,
                limit=3
            )

            if not patterns or len(patterns) < 2:
                return None

            # Extract anonymous previews
            previews = [
                p.get("insight_category", "Pattern insight")
                for p in patterns[:3]
            ]

            static = STATIC_TEASERS[teaser_type]
            return PathwayTeaser(
                teaser_type=teaser_type,
                headline=static["headline"],
                body=f"Innovators in similar pursuits explored these patterns: {', '.join(previews[:2])}...",
                cta=static["cta"],
                target_pathway=static["target_pathway"],
                source="iml",
                pattern_previews=previews,
            )

        except Exception as e:
            logger.debug(f"IML teaser generation failed: {e}")
            return None

    def _static_teaser(self, teaser_type: str) -> PathwayTeaser:
        """Generate a static fallback teaser."""
        template = STATIC_TEASERS[teaser_type]
        return PathwayTeaser(
            teaser_type=teaser_type,
            headline=template["headline"],
            body=template["body"],
            cta=template["cta"],
            target_pathway=template["target_pathway"],
            source="fallback",
            pattern_previews=None,
        )
