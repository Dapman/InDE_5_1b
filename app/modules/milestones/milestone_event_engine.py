"""
Milestone Event Engine

InDE MVP v4.5.0 — The Engagement Engine

Generates milestone events when artifacts are finalized.
The milestone event contains:
1. Achievement narrative — celebration text
2. Health Card refresh flag — trigger frontend refresh
3. Pathway teaser flag — trigger teaser generation

This engine is called AFTER artifact finalization completes.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .milestone_templates import MilestoneTemplates

logger = logging.getLogger(__name__)


@dataclass
class MilestoneEvent:
    """Milestone achievement event."""
    pursuit_id: str
    artifact_type: str
    headline: str
    narrative: str
    next_hint: str
    growth_stage_before: Optional[str]
    growth_stage_after: Optional[str]
    health_card_refresh: bool
    pathway_teaser_trigger: bool
    created_at: str


class MilestoneEventEngine:
    """
    Generates milestone events on artifact finalization.

    The milestone event is a coordination point:
    - Generates achievement narrative
    - Triggers Health Card refresh
    - Triggers Pathway Teaser generation
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access
        """
        self.db = db

    def generate_milestone(self, pursuit_id: str, artifact_type: str,
                           growth_stage_before: Optional[str] = None) -> MilestoneEvent:
        """
        Generate a milestone event for artifact finalization.

        Args:
            pursuit_id: The pursuit that finalized an artifact
            artifact_type: Type of artifact finalized
            growth_stage_before: Growth stage before finalization (optional)

        Returns:
            MilestoneEvent with narrative and refresh triggers
        """
        # Get pursuit context for template rendering
        pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})
        idea_domain = ""
        if pursuit:
            # Extract domain from title
            title = pursuit.get("title", "")
            idea_domain = title[:50] if title else "your innovation"

        # Render milestone template
        rendered = MilestoneTemplates.render(
            artifact_type=artifact_type,
            idea_domain=idea_domain,
        )

        # Compute new growth stage (Health Card will recompute)
        growth_stage_after = self._estimate_growth_stage(pursuit_id, artifact_type)

        milestone = MilestoneEvent(
            pursuit_id=pursuit_id,
            artifact_type=artifact_type,
            headline=rendered["headline"],
            narrative=rendered["narrative"],
            next_hint=rendered["next_hint"],
            growth_stage_before=growth_stage_before,
            growth_stage_after=growth_stage_after,
            health_card_refresh=True,
            pathway_teaser_trigger=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Milestone generated: {artifact_type} for {pursuit_id}")
        return milestone

    def _estimate_growth_stage(self, pursuit_id: str, artifact_type: str) -> str:
        """
        Estimate the new growth stage after artifact finalization.

        This is a rough estimate; the Health Card engine will compute the actual stage.
        """
        # Count artifacts
        artifact_count = self.db.db.artifacts.count_documents({
            "pursuit_id": pursuit_id
        })

        if artifact_count >= 4:
            return "branches"
        elif artifact_count >= 3:
            return "stem"
        elif artifact_count >= 2:
            return "roots"
        else:
            return "seed"
