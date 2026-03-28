"""
Milestone Narrative Hooks Module

InDE MVP v4.5.0 — The Engagement Engine

Generates achievement narratives when artifacts are finalized.
Works with pathway teasers to create continuity moments.

The milestone fires AFTER artifact finalization, generating:
1. Achievement narrative — celebration of progress
2. Health Card refresh trigger — update growth visualization
3. Pathway teaser trigger — preview of next coaching pathway

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""

from .milestone_event_engine import MilestoneEventEngine, MilestoneEvent
from .milestone_templates import MilestoneTemplates

__all__ = [
    "MilestoneEventEngine",
    "MilestoneEvent",
    "MilestoneTemplates",
]
