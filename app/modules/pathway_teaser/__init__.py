"""
Post-Vision Pathway Teaser Module

InDE MVP v4.5.0 — The Engagement Engine

Generates forward-leaning teasers that preview the next pathway after
an artifact is finalized. Works with the milestone hooks to create
continuity moments after achievement.

The teaser uses IML pattern data first (if available), with a static
fallback based on pursuit context.

Example:
  Vision finalized → "What risks might ambush this vision? Explore 2-3
  anonymized patterns from innovators who traveled this path..."

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""

from .pathway_teaser_engine import PathwayTeaserEngine, PathwayTeaser

__all__ = [
    "PathwayTeaserEngine",
    "PathwayTeaser",
]
