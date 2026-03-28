"""
Outcome Formulator API

InDE MVP v4.6.0 - The Outcome Engine

REST endpoints for the Outcome Formulator. Admin-only in v4.6.
Outcome readiness data is not surfaced to innovators until v4.7.

Endpoints:
  GET  /api/v1/pursuits/{pursuit_id}/outcome-readiness
       - Returns outcome readiness context for a specific pursuit.
       - Admin authentication required.

  GET  /api/v1/admin/outcome-readiness/summary
       - Returns aggregate outcome readiness across all active pursuits.
       - Admin authentication required.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["outcome-readiness"])


# Response models
class OutcomeArtifactSummary(BaseModel):
    artifact_type: str
    state: str
    readiness_score: float
    fields_populated: int
    fields_total: int
    last_updated: str


class OutcomeReadinessResponse(BaseModel):
    pursuit_id: str
    archetype: Optional[str]
    outcome_artifacts: List[OutcomeArtifactSummary]
    computed_at: str


class ArchetypeReadinessSummary(BaseModel):
    archetype: str
    pursuits_tracked: int
    pursuits_with_ready: int
    avg_readiness_score: float
    artifacts_by_state: dict


class OutcomeReadinessSummaryResponse(BaseModel):
    total_pursuits_tracked: int
    pursuits_with_ready_artifacts: int
    artifacts_by_state: dict
    by_archetype: List[ArchetypeReadinessSummary]
    field_capture_rate_7d: int
    state_transitions_7d: int
    computed_at: str


def get_outcome_formulator_engine(request: Request):
    """Dependency to get the outcome formulator engine from app state."""
    engine = getattr(request.app.state, "outcome_formulator_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="Outcome Formulator not initialized")
    return engine


def get_db(request: Request):
    """Dependency to get database from app state."""
    db = getattr(request.app.state, "db", None)
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    return db.db  # Return underlying motor database for collection access


async def require_admin(request: Request):
    """Dependency to require admin authentication."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.get("is_admin", False) and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get(
    "/pursuits/{pursuit_id}/outcome-readiness",
    response_model=OutcomeReadinessResponse,
)
async def get_pursuit_outcome_readiness(
    pursuit_id: str,
    request: Request,
    engine=Depends(get_outcome_formulator_engine),
    admin=Depends(require_admin),
):
    """
    Get outcome readiness context for a specific pursuit.
    Admin-only in v4.6.
    """
    context = await engine.get_outcome_readiness_context(pursuit_id)

    return OutcomeReadinessResponse(
        pursuit_id=context["pursuit_id"],
        archetype=context["archetype"],
        outcome_artifacts=[
            OutcomeArtifactSummary(**artifact)
            for artifact in context.get("outcome_artifacts", [])
        ],
        computed_at=context.get("computed_at", datetime.now(timezone.utc).isoformat()),
    )


@router.get(
    "/admin/outcome-readiness/summary",
    response_model=OutcomeReadinessSummaryResponse,
)
async def get_outcome_readiness_summary(
    request: Request,
    db=Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Get aggregate outcome readiness summary across all active pursuits.
    Admin-only.
    """
    try:
        collection = db["outcome_readiness"]

        # Count total pursuits tracked
        pursuit_ids = await collection.distinct("pursuit_id")
        total_pursuits = len(pursuit_ids)

        # Count pursuits with at least one READY artifact
        ready_cursor = collection.find({"state": "READY"})
        ready_pursuit_ids = set()
        async for doc in ready_cursor:
            ready_pursuit_ids.add(doc["pursuit_id"])
        pursuits_with_ready = len(ready_pursuit_ids)

        # Count artifacts by state
        state_counts = {
            "UNTRACKED": 0,
            "EMERGING": 0,
            "PARTIAL": 0,
            "SUBSTANTIAL": 0,
            "READY": 0,
        }

        pipeline = [
            {"$group": {"_id": "$state", "count": {"$sum": 1}}}
        ]
        async for doc in collection.aggregate(pipeline):
            state = doc["_id"]
            if state in state_counts:
                state_counts[state] = doc["count"]

        # Count by archetype
        archetype_pipeline = [
            {
                "$group": {
                    "_id": "$archetype",
                    "pursuits": {"$addToSet": "$pursuit_id"},
                    "ready_count": {
                        "$sum": {"$cond": [{"$eq": ["$state", "READY"]}, 1, 0]}
                    },
                    "total_score": {"$sum": "$readiness_score"},
                    "count": {"$sum": 1},
                }
            }
        ]

        by_archetype = []
        async for doc in collection.aggregate(archetype_pipeline):
            archetype = doc["_id"]
            pursuit_count = len(doc["pursuits"])
            ready_count = doc["ready_count"]
            avg_score = doc["total_score"] / doc["count"] if doc["count"] > 0 else 0.0

            by_archetype.append(
                ArchetypeReadinessSummary(
                    archetype=archetype,
                    pursuits_tracked=pursuit_count,
                    pursuits_with_ready=ready_count,
                    avg_readiness_score=round(avg_score, 3),
                    artifacts_by_state={},  # Could be computed with more complex aggregation
                )
            )

        # Get 7-day event counts (simplified - would need telemetry collection)
        field_capture_rate_7d = 0
        state_transitions_7d = 0

        return OutcomeReadinessSummaryResponse(
            total_pursuits_tracked=total_pursuits,
            pursuits_with_ready_artifacts=pursuits_with_ready,
            artifacts_by_state=state_counts,
            by_archetype=by_archetype,
            field_capture_rate_7d=field_capture_rate_7d,
            state_transitions_7d=state_transitions_7d,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to compute outcome readiness summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute summary")
