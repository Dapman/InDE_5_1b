"""
InDE MVP v5.1b.0 - Enterprise Connectors API

Routes for managing enterprise connector integrations.
ALL routes are CINDE-only. In LINDE mode, all routes return 404 Not Found.

Routes:
- GET    /api/v1/connectors/                    List available connectors and status
- GET    /api/v1/connectors/{slug}/status       Health for installed connector
- POST   /api/v1/connectors/{slug}/install      Initiate OAuth flow
- GET    /api/v1/connectors/{slug}/callback     OAuth callback (exchanges code)
- DELETE /api/v1/connectors/{slug}/uninstall    Revoke installation
- GET    /api/v1/connectors/{slug}/events       Recent webhook events (admin only)
- POST   /api/v1/webhooks/github                GitHub webhook receiver (unauthenticated)
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth.middleware import get_current_user
from services.feature_gate import get_feature_gate
from connectors.base import HealthStatus

logger = logging.getLogger("inde.api.connectors")

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class ConnectorInfo(BaseModel):
    """Information about an available connector."""
    slug: str
    display_name: str
    description: str
    required_scopes: List[str]
    webhook_events: List[str]
    is_stub: bool
    is_installed: bool = False
    installation_status: Optional[str] = None


class ConnectorListResponse(BaseModel):
    """Response for listing connectors."""
    connectors: List[ConnectorInfo]


class ConnectorStatusResponse(BaseModel):
    """Response for connector health status."""
    slug: str
    status: str  # HEALTHY | DEGRADED | DISCONNECTED
    last_checked: str
    message: Optional[str] = None


class InstallResponse(BaseModel):
    """Response for install initiation."""
    redirect_url: str


class WebhookEventInfo(BaseModel):
    """Information about a webhook event."""
    delivery_id: str
    event_type: str
    received_at: str
    processed: bool
    processing_result: Optional[str] = None


class WebhookEventsResponse(BaseModel):
    """Response for webhook events listing."""
    events: List[WebhookEventInfo]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Check CINDE mode (returns 404 in LINDE)
# ─────────────────────────────────────────────────────────────────────────────

def require_cinde_mode(request: Request):
    """Dependency that checks for CINDE mode, returns 404 if LINDE."""
    gate = get_feature_gate()
    if not gate.enterprise_connectors:
        raise HTTPException(status_code=404, detail="Not found")
    return gate


def get_connector_registry(request: Request):
    """Get the connector registry from app state."""
    if not hasattr(request.app.state, 'connector_registry'):
        raise HTTPException(status_code=503, detail="Connector registry not initialized")
    return request.app.state.connector_registry


def get_user_org_id(current_user) -> str:
    """Get the organization ID for the current user."""
    # In CINDE mode, users are associated with an organization
    org_id = current_user.get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="User not associated with an organization")
    return org_id


def require_org_admin(current_user):
    """Check if user has org_admin role."""
    role = current_user.get("role", "")
    org_role = current_user.get("org_role", "")
    if role != "admin" and org_role not in ["admin", "owner"]:
        raise HTTPException(status_code=403, detail="Organization admin access required")


# ─────────────────────────────────────────────────────────────────────────────
# Connector Management Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/connectors/", response_model=ConnectorListResponse)
async def list_connectors(
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    List all available connectors and their installation status.

    Requires: org_admin or org_member role
    """
    registry = get_connector_registry(request)
    org_id = get_user_org_id(current_user)

    # Get all available connectors
    available = registry.list_available()

    # Get installed connectors for this org
    installed = registry.list_installed(org_id)
    installed_slugs = {i.connector_slug: i for i in installed}

    connectors = []
    for meta in available:
        installation = installed_slugs.get(meta.slug)
        connectors.append(ConnectorInfo(
            slug=meta.slug,
            display_name=meta.display_name,
            description=meta.description,
            required_scopes=meta.required_scopes,
            webhook_events=meta.webhook_events,
            is_stub=meta.is_stub,
            is_installed=installation is not None,
            installation_status=installation.status.value if installation else None
        ))

    return ConnectorListResponse(connectors=connectors)


@router.get("/connectors/{slug}/status", response_model=ConnectorStatusResponse)
async def get_connector_status(
    slug: str,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Get health status for an installed connector.

    Requires: org_admin or org_member role
    """
    registry = get_connector_registry(request)
    org_id = get_user_org_id(current_user)

    health = await registry.get_status(slug, org_id)

    if not health:
        raise HTTPException(status_code=404, detail=f"Connector '{slug}' not found")

    return ConnectorStatusResponse(
        slug=slug,
        status=health.status.value,
        last_checked=health.last_checked.isoformat(),
        message=health.message
    )


@router.post("/connectors/{slug}/install", response_model=InstallResponse)
async def install_connector(
    slug: str,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Initiate connector installation via OAuth flow.

    Requires: org_admin role
    Returns: Redirect URL for OAuth authorization
    """
    require_org_admin(current_user)
    registry = get_connector_registry(request)
    org_id = get_user_org_id(current_user)
    user_id = current_user.get("user_id", current_user.get("id", ""))

    try:
        redirect_url = await registry.install(slug, org_id, user_id)
        return InstallResponse(redirect_url=redirect_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{slug}/callback")
async def oauth_callback(
    slug: str,
    code: str,
    state: str,
    request: Request,
    gate=Depends(require_cinde_mode)
):
    """
    Handle OAuth callback from connector provider.

    Exchanges authorization code for access token.
    Redirects to connector settings page on completion.
    """
    registry = get_connector_registry(request)
    connector = registry.get(slug)

    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{slug}' not found")

    try:
        installation = await connector.handle_oauth_callback(code, state)

        # Redirect to settings page with success message
        # The frontend will show a success notification
        return RedirectResponse(
            url="/settings/connectors?installed=" + slug,
            status_code=302
        )
    except ValueError as e:
        logger.error(f"OAuth callback failed for {slug}: {e}")
        return RedirectResponse(
            url="/settings/connectors?error=" + str(e),
            status_code=302
        )


@router.delete("/connectors/{slug}/uninstall")
async def uninstall_connector(
    slug: str,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Uninstall a connector from the organization.

    Requires: org_admin role
    """
    require_org_admin(current_user)
    registry = get_connector_registry(request)
    org_id = get_user_org_id(current_user)
    user_id = current_user.get("user_id", current_user.get("id", ""))

    try:
        await registry.uninstall(slug, org_id, user_id)
        return {"status": "uninstalled", "slug": slug}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/connectors/{slug}/events", response_model=WebhookEventsResponse)
async def list_webhook_events(
    slug: str,
    request: Request,
    limit: int = 50,
    offset: int = 0,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    List recent webhook events for a connector.

    Requires: org_admin role (for audit/debugging)
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)

    db = request.app.state.db.db

    # Query webhook events
    cursor = db.webhook_events.find(
        {"org_id": org_id, "connector_slug": slug}
    ).sort("received_at", -1).skip(offset).limit(limit)

    events = []
    for doc in cursor:
        events.append(WebhookEventInfo(
            delivery_id=doc["delivery_id"],
            event_type=doc["event_type"],
            received_at=doc["received_at"].isoformat(),
            processed=doc.get("processed", False),
            processing_result=doc.get("processing_result")
        ))

    # Get total count
    total = db.webhook_events.count_documents(
        {"org_id": org_id, "connector_slug": slug}
    )

    return WebhookEventsResponse(events=events, total=total)


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Receiver (Unauthenticated - signature verified)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/webhooks/github")
async def github_webhook_receiver(
    request: Request,
    background_tasks: BackgroundTasks,
    gate=Depends(require_cinde_mode)
):
    """
    Receive GitHub webhook events.

    This endpoint is unauthenticated but signature-verified.
    Must respond within 500ms - processing is done in background.

    Security:
    - Verifies X-Hub-Signature-256 header
    - Returns 403 on invalid signature
    - Idempotent via X-GitHub-Delivery header
    - Payload is NOT stored, only its hash
    """
    from connectors.github.webhooks import (
        verify_webhook_signature,
        compute_payload_hash,
        store_webhook_event,
        mark_webhook_processed,
        get_org_id_from_installation,
    )
    from connectors.github.events import process_github_webhook

    # Read raw body for signature verification
    payload = await request.body()

    # Get required headers
    signature = request.headers.get("X-Hub-Signature-256", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    event_type = request.headers.get("X-GitHub-Event", "")

    if not delivery_id:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Delivery header")

    if not event_type:
        raise HTTPException(status_code=400, detail="Missing X-GitHub-Event header")

    # Verify signature immediately
    if not verify_webhook_signature(payload, signature):
        logger.warning(f"Invalid webhook signature for delivery {delivery_id}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse payload
    import json
    try:
        payload_data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Compute payload hash (we store hash, not payload)
    payload_hash = compute_payload_hash(payload)

    # Get database
    db = request.app.state.db.db

    # Get org_id from installation ID
    installation = payload_data.get("installation", {})
    installation_id = installation.get("id") if installation else None
    org_id = None

    if installation_id:
        org_id = get_org_id_from_installation(db, installation_id)

    # Store event metadata (idempotency check)
    is_new = await store_webhook_event(
        db=db,
        org_id=org_id or "",
        connector_slug="github",
        delivery_id=delivery_id,
        event_type=event_type,
        payload_hash=payload_hash
    )

    if not is_new:
        # Duplicate delivery - return 200 but don't process
        logger.debug(f"Duplicate webhook delivery: {delivery_id}")
        return {"status": "ok", "duplicate": True}

    # Get event publisher
    event_publisher = None
    if hasattr(request.app.state, 'publisher'):
        event_publisher = request.app.state.publisher

    # Get RBAC bridge and sync service (v5.1a)
    bridge = getattr(request.app.state, 'github_rbac_bridge', None)
    sync_service = getattr(request.app.state, 'github_sync_service', None)

    # Process in background
    async def process_webhook():
        try:
            result = await process_github_webhook(
                db=db,
                event_publisher=event_publisher,
                org_id=org_id,
                event_type=event_type,
                payload=payload_data,
                delivery_id=delivery_id,
                bridge=bridge,
                sync_service=sync_service
            )
            await mark_webhook_processed(db, delivery_id, result)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            await mark_webhook_processed(db, delivery_id, "ERROR", str(e))

    background_tasks.add_task(process_webhook)

    # Return 200 immediately (processing continues in background)
    return {"status": "ok", "delivery_id": delivery_id}


# ─────────────────────────────────────────────────────────────────────────────
# v5.1a: GitHub RBAC Sync Routes
# ─────────────────────────────────────────────────────────────────────────────

class SyncStatusResponse(BaseModel):
    """Response for GitHub sync status."""
    org_id: str
    status: str  # IDLE | IN_PROGRESS | COMPLETED | FAILED
    last_sync_id: Optional[str] = None
    last_sync_at: Optional[str] = None
    synced_count: int = 0
    pending_count: int = 0
    floor_applied_count: int = 0
    error_count: int = 0
    message: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    """Response for triggering a sync."""
    sync_id: str
    status: str
    message: str


class SyncLogEntry(BaseModel):
    """Entry in the sync log."""
    event_type: str
    action: str
    github_login: Optional[str] = None
    affected_user_id: Optional[str] = None
    role_before: Optional[str] = None
    role_after: Optional[str] = None
    human_floor_applied: bool = False
    created_at: str
    delivery_id: Optional[str] = None


class SyncLogResponse(BaseModel):
    """Response for sync log listing."""
    entries: List[SyncLogEntry]
    total: int
    page: int
    page_size: int


class MemberSyncInfo(BaseModel):
    """Member with GitHub sync information."""
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    github_login: Optional[str] = None
    github_org_role: Optional[str] = None
    github_derived_role: Optional[str] = None
    human_set_role: Optional[str] = None
    effective_role: str
    github_synced_at: Optional[str] = None
    github_unlinked: bool = False


class MembersListResponse(BaseModel):
    """Response for members listing with sync info."""
    members: List[MemberSyncInfo]
    total: int


class MemberRoleResponse(BaseModel):
    """Response for member role info."""
    user_id: str
    github_login: Optional[str] = None
    github_org_role: Optional[str] = None
    github_derived_role: Optional[str] = None
    human_set_role: Optional[str] = None
    effective_role: str
    human_set_at: Optional[str] = None
    human_set_by: Optional[str] = None


class SetRoleRequest(BaseModel):
    """Request to set human role override."""
    role: str  # org_admin | org_member | org_viewer


class SetRoleResponse(BaseModel):
    """Response for setting human role override."""
    user_id: str
    role_before: str
    role_after: str
    human_floor_applied: bool
    message: str


def get_github_sync_service(request: Request):
    """Get GitHub sync service from app state."""
    sync_service = getattr(request.app.state, 'github_sync_service', None)
    if not sync_service:
        raise HTTPException(status_code=503, detail="GitHub sync service not initialized")
    return sync_service


def get_github_rbac_bridge(request: Request):
    """Get GitHub RBAC bridge from app state."""
    bridge = getattr(request.app.state, 'github_rbac_bridge', None)
    if not bridge:
        raise HTTPException(status_code=503, detail="GitHub RBAC bridge not initialized")
    return bridge


@router.get("/connectors/github/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Get the current GitHub sync status for the organization.

    Returns last sync timestamp, counts, and any floor_applied events.
    Requires: org_admin or org_member role
    """
    org_id = get_user_org_id(current_user)
    sync_service = get_github_sync_service(request)

    status = sync_service.get_sync_status(org_id)

    # Determine display status
    display_status = "IN_PROGRESS" if status.sync_in_progress else (status.last_sync_status or "IDLE")

    # Get error message if any
    db = request.app.state.db.db
    status_doc = db.github_sync_status.find_one({"org_id": org_id})
    message = status_doc.get("error_message") if status_doc else None

    return SyncStatusResponse(
        org_id=org_id,
        status=display_status,
        last_sync_id=status.current_sync_id or status.last_sync_id,
        last_sync_at=status.last_sync_at.isoformat() if status.last_sync_at else None,
        synced_count=status.synced_count,
        pending_count=status.pending_count,
        floor_applied_count=status.floor_applied_count,
        error_count=status.error_count,
        message=message
    )


@router.post("/connectors/github/sync/trigger", response_model=SyncTriggerResponse, status_code=202)
async def trigger_sync(
    request: Request,
    background_tasks: BackgroundTasks,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Trigger a manual GitHub RBAC sync for the organization.

    Returns 202 Accepted immediately with a sync_id.
    Poll GET /sync/status for completion.
    Returns 409 Conflict if a sync is already in progress.

    Requires: org_admin role
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)
    sync_service = get_github_sync_service(request)

    # Check for in-progress sync
    if sync_service.is_sync_in_progress(org_id):
        raise HTTPException(
            status_code=409,
            detail="Sync already in progress for this organization"
        )

    # Trigger sync
    sync_id = sync_service.trigger_initial_sync(org_id)

    # Run sync in background
    background_tasks.add_task(sync_service.run_initial_sync, org_id, sync_id)

    return SyncTriggerResponse(
        sync_id=sync_id,
        status="IN_PROGRESS",
        message="Sync initiated. Poll GET /sync/status for completion."
    )


@router.get("/connectors/github/sync/log", response_model=SyncLogResponse)
async def get_sync_log(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Get paginated GitHub sync log for the organization.

    Requires: org_admin role
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)
    db = request.app.state.db.db

    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 50

    skip = (page - 1) * page_size

    # Query sync log
    cursor = db.github_sync_log.find(
        {"org_id": org_id}
    ).sort("created_at", -1).skip(skip).limit(page_size)

    entries = []
    for doc in cursor:
        entries.append(SyncLogEntry(
            event_type=doc.get("event_type", ""),
            action=doc.get("action", ""),
            github_login=doc.get("github_login"),
            affected_user_id=doc.get("affected_user_id"),
            role_before=doc.get("role_before"),
            role_after=doc.get("role_after"),
            human_floor_applied=doc.get("human_floor_applied", False),
            created_at=doc.get("created_at", datetime.now(timezone.utc)).isoformat(),
            delivery_id=doc.get("github_delivery_id")
        ))

    # Get total count
    total = db.github_sync_log.count_documents({"org_id": org_id})

    return SyncLogResponse(
        entries=entries,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/connectors/github/members", response_model=MembersListResponse)
async def list_members_with_sync_info(
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    List organization members with GitHub sync information.

    Requires: org_admin or org_member role
    """
    org_id = get_user_org_id(current_user)
    db = request.app.state.db.db

    # Query memberships with GitHub sync fields
    cursor = db.memberships.find(
        {"org_id": org_id, "status": "ACTIVE"}
    ).sort("created_at", -1)

    members = []
    for doc in cursor:
        # Get user info
        user_id = doc.get("user_id", "")
        user = db.users.find_one({"_id": user_id}) or {}

        members.append(MemberSyncInfo(
            user_id=user_id,
            email=user.get("email"),
            display_name=user.get("display_name") or user.get("name"),
            github_login=doc.get("github_login"),
            github_org_role=doc.get("github_org_role"),
            github_derived_role=doc.get("github_derived_role"),
            human_set_role=doc.get("human_set_role"),
            effective_role=doc.get("effective_role") or doc.get("role", "org_viewer"),
            github_synced_at=doc.get("github_synced_at").isoformat() if doc.get("github_synced_at") else None,
            github_unlinked=doc.get("github_unlinked", False)
        ))

    return MembersListResponse(
        members=members,
        total=len(members)
    )


@router.get("/connectors/github/members/{user_id}/role", response_model=MemberRoleResponse)
async def get_member_role(
    user_id: str,
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Get a member's role information including GitHub sync data.

    Requires: org_admin or org_member role
    """
    org_id = get_user_org_id(current_user)
    db = request.app.state.db.db

    # Find membership
    membership = db.memberships.find_one({
        "org_id": org_id,
        "user_id": user_id,
        "status": "ACTIVE"
    })

    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")

    return MemberRoleResponse(
        user_id=user_id,
        github_login=membership.get("github_login"),
        github_org_role=membership.get("github_org_role"),
        github_derived_role=membership.get("github_derived_role"),
        human_set_role=membership.get("human_set_role"),
        effective_role=membership.get("effective_role") or membership.get("role", "org_viewer"),
        human_set_at=membership.get("human_set_at").isoformat() if membership.get("human_set_at") else None,
        human_set_by=membership.get("human_set_by")
    )


@router.post("/connectors/github/members/{user_id}/role", response_model=SetRoleResponse)
async def set_member_role(
    user_id: str,
    request: Request,
    body: SetRoleRequest,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Set a human role override for a member.

    This sets the human_set_role floor. The effective_role will be
    max(github_derived_role, human_set_role).

    Requires: org_admin role
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)
    admin_user_id = current_user.get("user_id", current_user.get("id", ""))

    bridge = get_github_rbac_bridge(request)

    # Validate role
    valid_roles = ["org_admin", "org_member", "org_viewer"]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    try:
        result = await bridge.apply_human_override(
            org_id=org_id,
            user_id=user_id,
            new_role=body.role,
            admin_user_id=admin_user_id
        )

        return SetRoleResponse(
            user_id=user_id,
            role_before=result.role_before or "none",
            role_after=result.role_after,
            human_floor_applied=result.human_floor_applied,
            message=f"Role override applied. Effective role is now {result.role_after}."
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# v5.1b: Admin Confirmation UI for github_unlinked Users
# ─────────────────────────────────────────────────────────────────────────────

class UnlinkedMemberInfo(BaseModel):
    """Member marked as github_unlinked awaiting admin action."""
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    github_login: Optional[str] = None
    effective_role: str
    github_unlinked_at: Optional[str] = None
    github_last_synced_at: Optional[str] = None


class UnlinkedMembersResponse(BaseModel):
    """Response for listing github_unlinked members."""
    members: List[UnlinkedMemberInfo]
    total: int


class ConfirmUnlinkRequest(BaseModel):
    """Request to confirm removal of unlinked member."""
    action: str  # "remove" | "retain"


class ConfirmUnlinkResponse(BaseModel):
    """Response for confirming unlink action."""
    user_id: str
    action: str
    message: str
    membership_status: str


@router.get("/connectors/github/members/unlinked", response_model=UnlinkedMembersResponse)
async def list_unlinked_members(
    request: Request,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    List members marked as github_unlinked awaiting admin review.

    These are members who were previously synced from GitHub but no longer
    appear in the GitHub organization. Admin must confirm whether to remove
    their access or retain them manually.

    Requires: org_admin role
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)
    db = request.app.state.db.db

    # Query memberships with github_unlinked=True
    cursor = db.memberships.find({
        "org_id": org_id,
        "status": "ACTIVE",
        "github_unlinked": True
    }).sort("github_unlinked_at", -1)

    members = []
    for doc in cursor:
        user_id = doc.get("user_id", "")
        user = db.users.find_one({"_id": user_id}) or {}

        members.append(UnlinkedMemberInfo(
            user_id=user_id,
            email=user.get("email"),
            display_name=user.get("display_name") or user.get("name"),
            github_login=doc.get("github_login"),
            effective_role=doc.get("effective_role") or doc.get("role", "org_viewer"),
            github_unlinked_at=doc.get("github_unlinked_at").isoformat() if doc.get("github_unlinked_at") else None,
            github_last_synced_at=doc.get("github_synced_at").isoformat() if doc.get("github_synced_at") else None
        ))

    return UnlinkedMembersResponse(
        members=members,
        total=len(members)
    )


@router.post("/connectors/github/members/{user_id}/confirm-unlink", response_model=ConfirmUnlinkResponse)
async def confirm_unlink_member(
    user_id: str,
    request: Request,
    body: ConfirmUnlinkRequest,
    gate=Depends(require_cinde_mode),
    current_user=Depends(get_current_user)
):
    """
    Confirm action for a github_unlinked member.

    Actions:
    - "remove": Revoke membership (status -> REVOKED)
    - "retain": Clear github_unlinked flag and convert to human-managed membership

    Requires: org_admin role
    """
    require_org_admin(current_user)
    org_id = get_user_org_id(current_user)
    admin_user_id = current_user.get("user_id", current_user.get("id", ""))
    db = request.app.state.db.db

    # Validate action
    if body.action not in ["remove", "retain"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Must be 'remove' or 'retain'."
        )

    # Find the membership
    membership = db.memberships.find_one({
        "org_id": org_id,
        "user_id": user_id,
        "status": "ACTIVE",
        "github_unlinked": True
    })

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="Unlinked member not found"
        )

    if body.action == "remove":
        # Revoke membership
        db.memberships.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "status": "REVOKED",
                    "revoked_at": datetime.now(timezone.utc),
                    "revoked_by": admin_user_id,
                    "revoke_reason": "github_unlinked_confirmed"
                }
            }
        )

        # Log the action
        db.github_sync_log.insert_one({
            "org_id": org_id,
            "event_type": "admin_confirm_unlink",
            "action": "remove",
            "github_login": membership.get("github_login"),
            "affected_user_id": user_id,
            "admin_user_id": admin_user_id,
            "created_at": datetime.now(timezone.utc)
        })

        return ConfirmUnlinkResponse(
            user_id=user_id,
            action="remove",
            message="Membership revoked. User no longer has access.",
            membership_status="REVOKED"
        )

    else:  # retain
        # Clear github_unlinked flag and convert to human-managed
        db.memberships.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "github_unlinked": False,
                    "github_unlinked_at": None,
                    "github_login": None,
                    "github_org_role": None,
                    "github_derived_role": None,
                    "human_set_role": membership.get("effective_role", "org_viewer"),
                    "human_set_at": datetime.now(timezone.utc),
                    "human_set_by": admin_user_id
                }
            }
        )

        # Log the action
        db.github_sync_log.insert_one({
            "org_id": org_id,
            "event_type": "admin_confirm_unlink",
            "action": "retain",
            "github_login": membership.get("github_login"),
            "affected_user_id": user_id,
            "admin_user_id": admin_user_id,
            "retained_role": membership.get("effective_role", "org_viewer"),
            "created_at": datetime.now(timezone.utc)
        })

        return ConfirmUnlinkResponse(
            user_id=user_id,
            action="retain",
            message="Member retained with human-managed role. GitHub link cleared.",
            membership_status="ACTIVE"
        )
