"""
InDE MVP v5.1b.0 - IRC API Endpoints

Primary Deliverable I: REST API for the Innovation Resource Canvas module.

Endpoints:
GET  /api/pursuits/{id}/irc/resources     → List resource entries
GET  /api/pursuits/{id}/irc/resources/{rid} → Get single resource
PATCH /api/pursuits/{id}/irc/resources/{rid} → Update resource fields
GET  /api/pursuits/{id}/irc/canvas        → Get IRC canvas
POST /api/pursuits/{id}/irc/consolidate   → Trigger consolidation
GET  /api/pursuits/{id}/irc/status        → Get IRC status indicator

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth.middleware import get_current_user
from core.database import db

logger = logging.getLogger("inde.api.irc")

router = APIRouter(tags=["IRC - Resource Canvas"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ResourceUpdateRequest(BaseModel):
    """Request to update a resource entry."""
    resource_name: Optional[str] = None
    category: Optional[str] = None
    phase_alignment: Optional[list] = None
    availability_status: Optional[str] = None
    availability_notes: Optional[str] = None
    cost_estimate_low: Optional[float] = None
    cost_estimate_high: Optional[float] = None
    cost_type: Optional[str] = None
    cost_confidence: Optional[str] = None
    criticality: Optional[str] = None
    duration_type: Optional[str] = None
    duration_description: Optional[str] = None


class ConsolidationRequest(BaseModel):
    """Request to trigger consolidation."""
    include_resource_ids: Optional[list] = Field(
        None,
        description="Specific resource IDs to include. If None, includes all."
    )


class ResourceResponse(BaseModel):
    """Response containing a resource entry."""
    artifact_id: str
    pursuit_id: str
    resource_name: str
    category: str
    phase_alignment: list
    availability_status: str
    availability_notes: str
    cost_estimate_low: Optional[float]
    cost_estimate_high: Optional[float]
    cost_type: str
    cost_confidence: str
    criticality: str
    duration_type: str
    duration_description: str
    challenge_registered: bool
    irc_included: bool
    created_at: str
    modified_at: str


class CanvasResponse(BaseModel):
    """Response containing an IRC canvas."""
    artifact_id: str
    pursuit_id: str
    generated_at: str
    consolidation_count: int
    resources_by_phase: dict
    resources_by_category: dict
    total_cost_low: float
    total_cost_high: float
    cost_by_phase: dict
    secured_count: int
    unresolved_count: int
    unknown_cost_count: int
    canvas_completeness: float
    coach_synthesis_notes: str
    itd_ready: bool


class IRCStatusResponse(BaseModel):
    """Response containing IRC status indicator."""
    pursuit_id: str
    has_canvas: bool
    resource_count: int
    secured_count: int
    unresolved_count: int
    canvas_completeness: float
    consolidation_eligible: bool
    status_label: str
    status_description: str


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get(
    "/pursuits/{pursuit_id}/irc/resources",
    response_model=list[ResourceResponse],
    summary="List resource entries for a pursuit",
)
async def list_resources(
    pursuit_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    List all .resource entries for a pursuit.

    Returns resources organized by creation date (newest first).
    """
    from modules.irc.resource_entry_manager import ResourceEntryManager

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    # Check ownership
    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    manager = ResourceEntryManager(db)
    resources = manager.get_resources_for_pursuit(pursuit_id)

    return resources


@router.get(
    "/pursuits/{pursuit_id}/irc/resources/{resource_id}",
    response_model=ResourceResponse,
    summary="Get a single resource entry",
)
async def get_resource(
    pursuit_id: str,
    resource_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a single .resource entry by ID."""
    from modules.irc.resource_entry_manager import ResourceEntryManager

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    manager = ResourceEntryManager(db)
    resource = manager.get_resource(resource_id)

    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Verify resource belongs to pursuit
    if resource.get("pursuit_id") != pursuit_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found in this pursuit"
        )

    return resource


@router.patch(
    "/pursuits/{pursuit_id}/irc/resources/{resource_id}",
    response_model=ResourceResponse,
    summary="Update a resource entry",
)
async def update_resource(
    pursuit_id: str,
    resource_id: str,
    request: ResourceUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Update fields on an existing .resource entry.

    Only provided fields are updated. Omitted fields are unchanged.
    """
    from bson import ObjectId
    from modules.irc.resource_entry_manager import ResourceEntryManager

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    manager = ResourceEntryManager(db)

    # Verify resource exists and belongs to pursuit
    resource = manager.get_resource(resource_id)
    if not resource or resource.get("pursuit_id") != pursuit_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found"
        )

    # Build update
    update_data = request.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    update_data["modified_at"] = datetime.now(timezone.utc)

    # Update in database
    db.db.resource_entries.update_one(
        {"_id": ObjectId(resource_id)},
        {"$set": update_data}
    )

    # Return updated resource
    return manager.get_resource(resource_id)


@router.get(
    "/pursuits/{pursuit_id}/irc/canvas",
    response_model=CanvasResponse,
    summary="Get the IRC canvas",
)
async def get_canvas(
    pursuit_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get the .irc canvas artifact for a pursuit.

    Returns 404 if no canvas has been consolidated yet.
    """
    from modules.irc.consolidation_engine import IRCConsolidationEngine

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    engine = IRCConsolidationEngine(db)
    canvas = engine.get_canvas(pursuit_id)

    if not canvas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No canvas has been created yet. Complete a consolidation first."
        )

    return canvas


@router.post(
    "/pursuits/{pursuit_id}/irc/consolidate",
    response_model=CanvasResponse,
    summary="Trigger canvas consolidation",
)
async def trigger_consolidation(
    pursuit_id: str,
    request: ConsolidationRequest = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger consolidation to create or update the .irc canvas.

    If include_resource_ids is provided, only those resources are included.
    Otherwise, all resources for the pursuit are included.
    """
    from modules.irc.consolidation_engine import IRCConsolidationEngine
    from modules.irc.resource_entry_manager import ResourceEntryManager

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check if there are resources to consolidate
    manager = ResourceEntryManager(db)
    resources = manager.get_resources_for_pursuit(pursuit_id)

    if not resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resources to consolidate. Resources must be identified through coaching first."
        )

    # Trigger consolidation
    engine = IRCConsolidationEngine(db)
    include_ids = request.include_resource_ids if request else None

    canvas = await engine.create_or_update_canvas(
        pursuit_id=pursuit_id,
        include_resource_ids=include_ids,
    )

    if not canvas:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create canvas"
        )

    return canvas


@router.get(
    "/pursuits/{pursuit_id}/irc/status",
    response_model=IRCStatusResponse,
    summary="Get IRC status indicator",
)
async def get_status(
    pursuit_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get the IRC status indicator for a pursuit.

    Used for sidebar/dashboard status displays.
    """
    from modules.irc.resource_entry_manager import ResourceEntryManager
    from modules.irc.consolidation_engine import IRCConsolidationEngine

    # Verify pursuit access
    pursuit = db.get_pursuit(pursuit_id)
    if not pursuit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pursuit not found"
        )

    if pursuit.get("user_id") != current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    manager = ResourceEntryManager(db)
    engine = IRCConsolidationEngine(db)

    # Get metrics
    density = manager.get_signal_density(pursuit_id)
    canvas = engine.get_canvas(pursuit_id)

    has_canvas = canvas is not None
    resource_count = density["total_entries"]
    unresolved = density["unresolved_count"]
    eligible = density["consolidation_eligible"]

    # Calculate status
    if resource_count == 0:
        status_label = "No resources yet"
        status_description = "Resources will appear as you discuss what you'll need"
    elif not has_canvas:
        status_label = "Building"
        status_description = f"{resource_count} resource{'s' if resource_count != 1 else ''} captured"
    else:
        completeness = canvas.get("canvas_completeness", 0)
        if completeness >= 0.8:
            status_label = "Complete"
            status_description = "Resource picture is well developed"
        elif completeness >= 0.5:
            status_label = "In progress"
            status_description = "Resource picture is taking shape"
        else:
            status_label = "Getting started"
            status_description = "Resource picture is emerging"

    secured = canvas.get("secured_count", 0) if canvas else 0
    completeness = canvas.get("canvas_completeness", 0) if canvas else 0

    return IRCStatusResponse(
        pursuit_id=pursuit_id,
        has_canvas=has_canvas,
        resource_count=resource_count,
        secured_count=secured,
        unresolved_count=unresolved,
        canvas_completeness=completeness,
        consolidation_eligible=eligible,
        status_label=status_label,
        status_description=status_description,
    )
