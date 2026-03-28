"""
Intelligence API

InDE MVP v4.5.0 — The Engagement Engine

REST endpoints for intelligence features including learning velocity.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from auth.middleware import get_current_user
from modules.learning_velocity import LearningVelocityEngine

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Models
class VelocityHistoryPoint(BaseModel):
    """Single point in velocity history."""
    date: str
    value: float


class LearningVelocityResponse(BaseModel):
    """Learning velocity API response."""
    score: float = Field(..., ge=0, le=100)
    trend: float = Field(..., ge=-1, le=1)
    history: List[VelocityHistoryPoint]
    conversion_rate: float = Field(..., ge=0, le=1)
    org_average: float = Field(..., ge=0, le=100)


@router.get("/learning-velocity/{user_id}", response_model=LearningVelocityResponse)
async def get_learning_velocity(
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get learning velocity metrics for a user.

    Learning velocity measures how actively a user is engaging with their
    innovation journey. Components include:
    - Conversation activity (coaching messages)
    - Artifact generation (vision, fears, hypothesis)
    - Scaffolding progress (element completion)
    - Pursuit momentum (session frequency, phase progression)

    The score is 0-100 where higher indicates more active engagement.
    Trend indicates whether velocity is improving (+) or declining (-).

    Users can only view their own velocity unless they have org admin role.
    """
    db = request.app.state.db

    # Security check: users can only view their own velocity
    # (org admins could view others, but not implemented yet)
    if user_id != current_user["user_id"]:
        # Check if current user is org admin (future feature)
        raise HTTPException(
            status_code=403,
            detail="You can only view your own learning velocity"
        )

    # Compute velocity
    engine = LearningVelocityEngine(db)
    velocity = engine.compute_velocity(user_id)

    return LearningVelocityResponse(
        score=velocity["score"],
        trend=velocity["trend"],
        history=[
            VelocityHistoryPoint(date=h["date"], value=h["value"])
            for h in velocity["history"]
        ],
        conversion_rate=velocity["conversion_rate"],
        org_average=velocity["org_average"],
    )


@router.get("/learning-velocity", response_model=LearningVelocityResponse)
async def get_my_learning_velocity(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get learning velocity for the current authenticated user.
    Convenience endpoint that doesn't require user_id in path.
    """
    db = request.app.state.db
    user_id = current_user["user_id"]

    engine = LearningVelocityEngine(db)
    velocity = engine.compute_velocity(user_id)

    return LearningVelocityResponse(
        score=velocity["score"],
        trend=velocity["trend"],
        history=[
            VelocityHistoryPoint(date=h["date"], value=h["value"])
            for h in velocity["history"]
        ],
        conversion_rate=velocity["conversion_rate"],
        org_average=velocity["org_average"],
    )
