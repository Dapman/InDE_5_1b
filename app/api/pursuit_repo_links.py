"""
InDE MVP v5.1b.0 - Pursuit-Repo Links API

Routes for managing pursuit-repo linkage.
ALL routes are CINDE-only. In LINDE mode, all routes return 404 Not Found.

Routes:
- POST   /api/v1/pursuits/{pursuit_id}/repos                    Link a repo
- GET    /api/v1/pursuits/{pursuit_id}/repos                    List active links
- DELETE /api/v1/pursuits/{pursuit_id}/repos/{github_repo_id}   Unlink (soft delete)
- PATCH  /api/v1/pursuits/{pursuit_id}/repos/{github_repo_id}/primary   Set as primary
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel

from auth.middleware import get_current_user
from services.feature_gate import get_feature_gate

logger = logging.getLogger("inde.api.pursuit_repo_links")

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class LinkRepoRequest(BaseModel):
    """Request to link a GitHub repo to a pursuit."""
    github_repo_full_name: str  # "{owner}/{repo}"
    github_repo_id: int  # GitHub numeric repo ID
    is_primary: bool = False


class RepoLinkResponse(BaseModel):
    """Response for a single repo link."""
    pursuit_id: str
    github_repo_full_name: str
    github_repo_id: int
    is_primary: bool
    signal_capture_enabled: bool
    linked_by: str
    linked_at: str


class LinkListResponse(BaseModel):
    """Response for listing repo links."""
    pursuit_id: str
    links: List[RepoLinkResponse]
    total: int


class LinkResultResponse(BaseModel):
    """Response for link/unlink/set_primary operations."""
    pursuit_id: str
    github_repo_id: int
    github_repo_full_name: str
    is_primary: bool
    action: str
    message: str


# =============================================================================
# DEPENDENCIES
# =============================================================================

def require_cinde_mode(request: Request):
    """Dependency that checks for CINDE mode, returns 404 if LINDE."""
    gate = get_feature_gate()
    if not gate.enterprise_connectors:
        raise HTTPException(status_code=404, detail="Not found")
    return gate


def get_pursuit_linker(request: Request):
    """Get PursuitRepoLinker from app state."""
    linker = getattr(request.app.state, 'pursuit_linker', None)
    if not linker:
        raise HTTPException(status_code=503, detail="Pursuit linker not initialized")
    return linker


def get_user_org_id(current_user) -> str:
    """Get the organization ID for the current user."""
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="User not associated with an organization")
    return org_id


def require_pursuit_access(current_user, pursuit_id: str, db):
    """
    Check if user has admin or owner access to the pursuit.
    org_admin can link repos to any pursuit in the org.
    pursuit_owner can link repos to their own pursuit.
    """
    role = current_user.get("role", "")
    org_role = current_user.get("org_role", "")

    # Org admin can link to any pursuit
    if role == "admin" or org_role in ["admin", "owner", "org_admin"]:
        return True

    # Check if user is pursuit owner
    user_id = current_user.get("user_id", current_user.get("id", ""))
    org_id = current_user.get("org_id", "")

    pursuit = db.pursuits.find_one({"_id": pursuit_id, "org_id": org_id})
    if not pursuit:
        from bson import ObjectId
        try:
            pursuit = db.pursuits.find_one({"_id": ObjectId(pursuit_id), "org_id": org_id})
        except Exception:
            pass

    if pursuit and pursuit.get("owner_id") == user_id:
        return True

    raise HTTPException(
        status_code=403,
        detail="Organization admin or pursuit owner access required"
    )


# =============================================================================
# ROUTES
# =============================================================================

@router.post("/pursuits/{pursuit_id}/repos", response_model=LinkResultResponse)
async def link_repo(
    pursuit_id: str,
    request: Request,
    body: LinkRepoRequest,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Link a GitHub repository to a pursuit.

    Requires: org_admin or pursuit_owner role.
    If is_primary=True and a primary already exists, the existing primary is demoted.
    If this is the first link and is_primary=False, it's auto-set as primary.
    """
    org_id = get_user_org_id(current_user)
    user_id = current_user.get("user_id", current_user.get("id", ""))
    db = request.app.state.db.db

    require_pursuit_access(current_user, pursuit_id, db)

    linker = get_pursuit_linker(request)

    try:
        result = await linker.link_repo(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_full_name=body.github_repo_full_name,
            github_repo_id=body.github_repo_id,
            is_primary=body.is_primary,
            linked_by=user_id
        )

        return LinkResultResponse(
            pursuit_id=result.pursuit_id,
            github_repo_id=result.github_repo_id,
            github_repo_full_name=result.github_repo_full_name,
            is_primary=result.is_primary,
            action=result.action,
            message=result.message or "Link created."
        )

    except Exception as e:
        error_name = type(e).__name__
        if error_name == "PursuitNotFoundError":
            raise HTTPException(status_code=404, detail=str(e))
        elif error_name == "DuplicateLinkError":
            raise HTTPException(status_code=409, detail=str(e))
        else:
            logger.error(f"Link repo error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/pursuits/{pursuit_id}/repos", response_model=LinkListResponse)
async def list_repo_links(
    pursuit_id: str,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    List all active GitHub repo links for a pursuit.

    Requires: org membership (any role).
    Returns links sorted by is_primary (desc), linked_at (asc).
    """
    org_id = get_user_org_id(current_user)
    linker = get_pursuit_linker(request)

    links = await linker.get_links_for_pursuit(org_id, pursuit_id)

    link_responses = []
    for link in links:
        link_responses.append(RepoLinkResponse(
            pursuit_id=link["pursuit_id"],
            github_repo_full_name=link["github_repo_full_name"],
            github_repo_id=link["github_repo_id"],
            is_primary=link.get("is_primary", False),
            signal_capture_enabled=link.get("signal_capture_enabled", True),
            linked_by=link["linked_by"],
            linked_at=link["linked_at"].isoformat()
        ))

    return LinkListResponse(
        pursuit_id=pursuit_id,
        links=link_responses,
        total=len(link_responses)
    )


@router.delete("/pursuits/{pursuit_id}/repos/{github_repo_id}", response_model=LinkResultResponse)
async def unlink_repo(
    pursuit_id: str,
    github_repo_id: int,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Unlink (soft delete) a GitHub repository from a pursuit.

    Requires: org_admin or pursuit_owner role.
    If the unlinked repo was primary and other links exist, a new primary is auto-assigned.
    """
    org_id = get_user_org_id(current_user)
    user_id = current_user.get("user_id", current_user.get("id", ""))
    db = request.app.state.db.db

    require_pursuit_access(current_user, pursuit_id, db)

    linker = get_pursuit_linker(request)

    try:
        result = await linker.unlink_repo(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_id=github_repo_id,
            unlinked_by=user_id
        )

        return LinkResultResponse(
            pursuit_id=result.pursuit_id,
            github_repo_id=result.github_repo_id,
            github_repo_full_name=result.github_repo_full_name,
            is_primary=result.is_primary,
            action=result.action,
            message=result.message or "Link removed."
        )

    except Exception as e:
        error_name = type(e).__name__
        if error_name == "LinkNotFoundError":
            raise HTTPException(status_code=404, detail=str(e))
        else:
            logger.error(f"Unlink repo error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.patch("/pursuits/{pursuit_id}/repos/{github_repo_id}/primary", response_model=LinkResultResponse)
async def set_primary_repo(
    pursuit_id: str,
    github_repo_id: int,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Set a linked repository as the primary for a pursuit.

    Requires: org_admin or pursuit_owner role.
    Atomically demotes the current primary (if any).
    """
    org_id = get_user_org_id(current_user)
    db = request.app.state.db.db

    require_pursuit_access(current_user, pursuit_id, db)

    linker = get_pursuit_linker(request)

    try:
        result = await linker.set_primary(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_id=github_repo_id
        )

        return LinkResultResponse(
            pursuit_id=result.pursuit_id,
            github_repo_id=result.github_repo_id,
            github_repo_full_name=result.github_repo_full_name,
            is_primary=result.is_primary,
            action=result.action,
            message=result.message or "Primary set."
        )

    except Exception as e:
        error_name = type(e).__name__
        if error_name == "LinkNotFoundError":
            raise HTTPException(status_code=404, detail=str(e))
        else:
            logger.error(f"Set primary error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
