"""
Cohort Presence Signals Module

InDE MVP v4.5.0 — The Engagement Engine

Provides anonymized aggregate metrics that give innovators a subtle sense
of community presence without revealing any personal information.

Metrics are computed on a 15-minute cache cycle and include:
- Active innovators (24h, 7d)
- Artifacts generated (7d)
- Pursuits advancing (7d)
- Cohort momentum signal (4-tier: buzzing, active, warming_up, getting_started)

All metrics are aggregate counts — no PII, no user identifiers, no pursuit
details. Consistent with Tenet XI (Abstract Sovereignty).

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""

from .cohort_aggregator import CohortAggregator, CohortSignals

__all__ = [
    "CohortAggregator",
    "CohortSignals",
]
