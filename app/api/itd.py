"""
InDE MVP v4.7.0 - ITD Composition Engine API

REST endpoints for Innovation Thesis Document generation and management.

Endpoints:
- POST /api/v1/pursuits/{pursuit_id}/itd/generate - Generate ITD
- GET /api/v1/pursuits/{pursuit_id}/itd - Get ITD for pursuit
- GET /api/v1/itd/{itd_id} - Get ITD by ID
- POST /api/v1/pursuits/{pursuit_id}/itd/{layer}/regenerate - Regenerate layer
- POST /api/v1/pursuits/{pursuit_id}/exit/start - Start exit flow
- POST /api/v1/pursuits/{pursuit_id}/exit/{session_id}/process - Process exit phase

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("inde.api.itd")

router = APIRouter(prefix="/api/v1", tags=["ITD"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ITDGenerateRequest(BaseModel):
    """Request to generate an ITD."""
    retrospective_data: Optional[Dict] = None


class ITDLayerRegenerateRequest(BaseModel):
    """Request to regenerate a specific ITD layer."""
    layer_type: str  # thesis_statement, evidence_architecture, narrative_arc, coachs_perspective


class ExitPhaseProcessRequest(BaseModel):
    """Request to process an exit phase."""
    phase_data: Optional[Dict] = None


class ITDResponse(BaseModel):
    """ITD API response."""
    itd_id: str
    pursuit_id: str
    status: str
    layers_completed: List[str]
    layers_failed: List[str]
    thesis_preview: Optional[str] = None
    created_at: Optional[str] = None


class ExitSessionResponse(BaseModel):
    """Exit session API response."""
    session_id: str
    pursuit_id: str
    current_phase: str
    phase_history: List[Dict]
    itd_id: Optional[str] = None


# =============================================================================
# DEPENDENCIES
# =============================================================================

def get_itd_engine(request: Request):
    """Get ITD engine from app state."""
    engine = getattr(request.app.state, "itd_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="ITD engine not available")
    return engine


def get_exit_orchestrator(request: Request):
    """Get exit orchestrator from app state."""
    orchestrator = getattr(request.app.state, "exit_orchestrator", None)
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Exit orchestrator not available")
    return orchestrator


def get_current_user(request: Request):
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# =============================================================================
# ITD ENDPOINTS
# =============================================================================

@router.post("/pursuits/{pursuit_id}/itd/generate", response_model=ITDResponse)
async def generate_itd(
    pursuit_id: str,
    body: ITDGenerateRequest = ITDGenerateRequest(),
    itd_engine=Depends(get_itd_engine),
    user=Depends(get_current_user),
):
    """
    Generate an Innovation Thesis Document for a pursuit.

    This triggers the full ITD Composition Engine to generate
    all six layers of the document.
    """
    logger.info(f"[ITD API] Generate ITD for pursuit: {pursuit_id}")

    try:
        itd = itd_engine.generate(
            pursuit_id=pursuit_id,
            retrospective_data=body.retrospective_data,
        )

        return ITDResponse(
            itd_id=itd.itd_id,
            pursuit_id=itd.pursuit_id,
            status=itd.status.value,
            layers_completed=itd.layers_completed,
            layers_failed=itd.layers_failed,
            thesis_preview=itd.thesis_statement.thesis_text[:200] if itd.thesis_statement else None,
            created_at=itd.created_at.isoformat() if itd.created_at else None,
        )
    except Exception as e:
        logger.error(f"[ITD API] Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pursuits/{pursuit_id}/itd", response_model=ITDResponse)
async def get_itd_for_pursuit(
    pursuit_id: str,
    itd_engine=Depends(get_itd_engine),
    user=Depends(get_current_user),
):
    """
    Get the ITD for a pursuit.

    Returns the most recent ITD generated for the pursuit.
    """
    itd = itd_engine.get_itd(pursuit_id)

    if not itd:
        raise HTTPException(status_code=404, detail="ITD not found for pursuit")

    return ITDResponse(
        itd_id=itd.itd_id,
        pursuit_id=itd.pursuit_id,
        status=itd.status.value,
        layers_completed=itd.layers_completed,
        layers_failed=itd.layers_failed,
        thesis_preview=itd.thesis_statement.thesis_text[:200] if itd.thesis_statement else None,
        created_at=itd.created_at.isoformat() if itd.created_at else None,
    )


@router.get("/itd/{itd_id}")
async def get_itd_by_id(
    itd_id: str,
    itd_engine=Depends(get_itd_engine),
    user=Depends(get_current_user),
):
    """
    Get an ITD by its ID.

    Returns the full ITD document.
    """
    itd = itd_engine.assembler.load(itd_id)

    if not itd:
        raise HTTPException(status_code=404, detail="ITD not found")

    return itd.to_dict()


@router.post("/pursuits/{pursuit_id}/itd/{layer}/regenerate", response_model=ITDResponse)
async def regenerate_itd_layer(
    pursuit_id: str,
    layer: str,
    itd_engine=Depends(get_itd_engine),
    user=Depends(get_current_user),
):
    """
    Regenerate a specific layer of an ITD.

    Valid layers: thesis_statement, evidence_architecture, narrative_arc, coachs_perspective
    """
    from modules.itd.itd_schemas import ITDLayerType

    # Validate layer type
    try:
        layer_type = ITDLayerType(layer)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer type. Valid options: {[l.value for l in ITDLayerType]}"
        )

    # Get existing ITD
    itd = itd_engine.get_itd(pursuit_id)
    if not itd:
        raise HTTPException(status_code=404, detail="ITD not found for pursuit")

    # Regenerate layer
    updated_itd = itd_engine.regenerate_layer(itd.itd_id, layer_type)

    if not updated_itd:
        raise HTTPException(status_code=500, detail="Failed to regenerate layer")

    return ITDResponse(
        itd_id=updated_itd.itd_id,
        pursuit_id=updated_itd.pursuit_id,
        status=updated_itd.status.value,
        layers_completed=updated_itd.layers_completed,
        layers_failed=updated_itd.layers_failed,
        thesis_preview=updated_itd.thesis_statement.thesis_text[:200] if updated_itd.thesis_statement else None,
        created_at=updated_itd.created_at.isoformat() if updated_itd.created_at else None,
    )


# =============================================================================
# EXIT FLOW ENDPOINTS
# =============================================================================

@router.post("/pursuits/{pursuit_id}/exit/start", response_model=ExitSessionResponse)
async def start_exit_flow(
    pursuit_id: str,
    exit_orchestrator=Depends(get_exit_orchestrator),
    user=Depends(get_current_user),
):
    """
    Start the four-phase exit flow for a pursuit.

    Initiates the guided exit experience:
    1. Retrospective
    2. ITD Preview
    3. Artifact Packaging
    4. Transition Guidance
    """
    logger.info(f"[ITD API] Starting exit flow for pursuit: {pursuit_id}")

    session = exit_orchestrator.start_exit(pursuit_id, user.get("user_id"))

    return ExitSessionResponse(
        session_id=session.session_id,
        pursuit_id=session.pursuit_id,
        current_phase=session.current_phase.value,
        phase_history=session.phase_history,
        itd_id=session.itd_id,
    )


@router.post("/pursuits/{pursuit_id}/exit/{session_id}/process")
async def process_exit_phase(
    pursuit_id: str,
    session_id: str,
    body: ExitPhaseProcessRequest = ExitPhaseProcessRequest(),
    exit_orchestrator=Depends(get_exit_orchestrator),
    user=Depends(get_current_user),
):
    """
    Process the current exit phase.

    Handles phase-specific data and advances to next phase when ready.
    """
    logger.info(f"[ITD API] Processing exit phase for session: {session_id}")

    result = exit_orchestrator.process_phase(
        session_id=session_id,
        phase_data=body.phase_data,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/pursuits/{pursuit_id}/exit/status")
async def get_exit_status(
    pursuit_id: str,
    exit_orchestrator=Depends(get_exit_orchestrator),
    user=Depends(get_current_user),
):
    """
    Get the current exit session status for a pursuit.
    """
    session = exit_orchestrator.get_session_for_pursuit(pursuit_id)

    if not session:
        return {"status": "no_active_session", "pursuit_id": pursuit_id}

    return {
        "status": "active",
        "session": session.to_dict(),
    }
