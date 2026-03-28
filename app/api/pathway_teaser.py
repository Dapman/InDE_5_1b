"""
Pathway Teaser API

InDE MVP v4.5.0 — The Engagement Engine

REST endpoint for retrieving pathway teasers.

GET /api/v1/pursuits/{pursuit_id}/pathway-teaser

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import logging

from auth.middleware import get_current_user
from modules.pathway_teaser import PathwayTeaserEngine

logger = logging.getLogger(__name__)

router = APIRouter()


class PathwayTeaserResponse(BaseModel):
    """Pathway teaser API response."""
    teaser_type: str
    headline: str
    body: str
    cta: str
    target_pathway: str
    source: str
    pattern_previews: Optional[List[str]] = None


@router.get("/pursuits/{pursuit_id}/pathway-teaser",
            response_model=Optional[PathwayTeaserResponse])
async def get_pathway_teaser(
    pursuit_id: str,
    artifact_type: Optional[str] = None,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the pathway teaser for the next coaching pathway.

    If artifact_type is not provided, uses the most recently finalized artifact.
    Returns null if all pathways have been explored.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({"pursuit_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("user_id") != current_user["user_id"]:
        is_team_member = db.db.team_members.find_one({
            "pursuit_id": pursuit_id,
            "user_id": current_user["user_id"]
        })
        if not is_team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Determine the completed artifact type
    if artifact_type:
        completed_type = artifact_type
    else:
        # Find most recently finalized artifact
        latest_artifact = db.db.artifacts.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("created_at", -1)]
        )
        if not latest_artifact:
            return None
        # Support both 'type' and 'artifact_type' field names
        completed_type = latest_artifact.get("type") or latest_artifact.get("artifact_type")

    # Generate teaser
    engine = PathwayTeaserEngine(db)
    teaser = engine.get_teaser(pursuit_id, completed_type)

    if not teaser:
        return None

    return PathwayTeaserResponse(
        teaser_type=teaser.teaser_type,
        headline=teaser.headline,
        body=teaser.body,
        cta=teaser.cta,
        target_pathway=teaser.target_pathway,
        source=teaser.source,
        pattern_previews=teaser.pattern_previews,
    )
