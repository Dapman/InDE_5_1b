"""
Innovation Health Card API

InDE MVP v4.5.0 — The Engagement Engine

REST endpoint for retrieving an Innovation Health Card.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from auth.middleware import get_current_user
from modules.health_card import HealthCardEngine, HealthCardRenderer

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class DimensionResponse(BaseModel):
    """Single dimension in Health Card response."""
    key: str
    label: str
    score: float = Field(..., ge=0.0, le=1.0)
    description: str
    icon: str
    color: str


class HealthCardResponse(BaseModel):
    """Full Health Card API response."""
    pursuit_id: str
    growth_stage: str
    growth_stage_label: str
    growth_stage_icon: str
    growth_stage_accent: str
    summary: str
    next_hint: str
    dimensions: Optional[List[DimensionResponse]] = None
    computed_at: str


@router.get("/pursuits/{pursuit_id}/health-card", response_model=HealthCardResponse)
async def get_health_card(
    pursuit_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Compute and return the Innovation Health Card for a pursuit.
    The card is computed on demand — never cached or stored.

    The response adapts to the user's experience level:
    - novice: Only growth stage, summary, and hint (no dimensions)
    - intermediate/expert: Full dimensions with scores

    Returns 404 if pursuit not found.
    Returns 403 if user lacks access to the pursuit.
    """
    db = request.app.state.db

    # Verify pursuit exists
    pursuit = db.db.pursuits.find_one({"pursuit_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Check ownership or team membership
    if pursuit.get("user_id") != current_user["user_id"]:
        is_team_member = db.db.team_members.find_one({
            "pursuit_id": pursuit_id,
            "user_id": current_user["user_id"]
        })
        if not is_team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get user's experience mode preference
    user = db.db.users.find_one({"user_id": current_user["user_id"]})
    experience_mode = (
        user.get("preferences", {}).get("experience_mode", "novice")
        if user else "novice"
    )

    # Compute Health Card
    engine = HealthCardEngine(db)
    health_card = engine.compute(pursuit_id)

    # Render based on experience level
    renderer = HealthCardRenderer()
    if experience_mode == "novice":
        result = renderer.render_minimal(health_card)
    else:
        result = renderer.render(health_card)

    return result
