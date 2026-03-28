"""
Cohort Presence Signals API

InDE MVP v4.5.0 — The Engagement Engine

REST endpoint for retrieving anonymized cohort presence signals.

GET /api/v1/cohort/signals — authenticated, cached

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
import logging

from auth.middleware import get_current_user
from modules.cohort_signals import CohortAggregator

logger = logging.getLogger(__name__)

router = APIRouter()


class CohortSignalsResponse(BaseModel):
    """Cohort signals API response."""
    active_24h: int
    active_7d: int
    artifacts_7d: int
    pursuits_advancing_7d: int
    cohort_momentum_signal: str
    signal_label: str
    computed_at: str


@router.get("/cohort/signals", response_model=CohortSignalsResponse)
async def get_cohort_signals(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get anonymized cohort presence signals.

    Returns aggregate metrics about the innovator community:
    - Active users (24h, 7d)
    - Artifacts generated (7d)
    - Pursuits advancing (7d)
    - Cohort momentum signal (buzzing, active, warming_up, getting_started)

    All data is anonymized — no PII, no user identifiers.
    Results are cached for 15 minutes.
    """
    db = request.app.state.db

    aggregator = CohortAggregator(db)
    signals = aggregator.get_signals()

    return CohortSignalsResponse(
        active_24h=signals.active_24h,
        active_7d=signals.active_7d,
        artifacts_7d=signals.artifacts_7d,
        pursuits_advancing_7d=signals.pursuits_advancing_7d,
        cohort_momentum_signal=signals.cohort_momentum_signal,
        signal_label=signals.signal_label,
        computed_at=signals.computed_at,
    )
