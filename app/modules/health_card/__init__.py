"""
Innovation Health Card Module

InDE MVP v4.5.0 — The Engagement Engine

Provides organic, depth-framed visualization of how developed an idea is
across five growth dimensions: Clarity, Resilience, Evidence, Direction,
and Momentum.

The Health Card is computed on demand — never stored — to ensure it always
reflects real-time pursuit state.
"""

from .health_card_engine import (
    HealthCardEngine,
    InnovationHealthCard,
    HealthCardDimension,
    GROWTH_STAGES,
)
from .health_card_renderer import HealthCardRenderer

__all__ = [
    "HealthCardEngine",
    "InnovationHealthCard",
    "HealthCardDimension",
    "HealthCardRenderer",
    "GROWTH_STAGES",
]
