"""
InDE MVP v5.1b.0 - GitHub Webhook Event Processing

Routes webhook events to appropriate handlers with RBAC bridge integration.
v5.1a: Live handlers that sync GitHub roles to InDE RBAC.
"""

import logging
from typing import Optional
from datetime import datetime

from .webhook_handlers import (
    handle_membership,
    handle_organization,
    handle_team,
    handle_team_add,
    handle_repository,
    handle_installation,
    handle_member,
    handle_push,
    handle_pull_request,
    handle_pull_request_review,
)

logger = logging.getLogger("inde.connectors.github.events")


# Event type to handler mapping
# These handlers are wrappers that call webhook_handlers with bridge
EVENT_HANDLERS = {
    "membership": "handle_membership",
    "organization": "handle_organization",
    "team": "handle_team",
    "team_add": "handle_team_add",
    "repository": "handle_repository",
    "member": "handle_member",  # v5.1b: Layer 2 RBAC activation
    "push": "handle_push",  # v5.1b: Pillar 1/2 signal ingestion
    "pull_request": "handle_pull_request",  # v5.1b: Pillar 1/2 signal ingestion
    "pull_request_review": "handle_pull_request_review",  # v5.1b: Pillar 1/2 signal ingestion
}


async def process_github_webhook(
    db,
    event_publisher,
    org_id: Optional[str],
    event_type: str,
    payload: dict,
    delivery_id: str,
    bridge=None,
    sync_service=None,
    signal_ingester=None
) -> str:
    """
    Route webhook event to appropriate handler.

    v5.1a: Integrates with GitHubRBACBridge for live RBAC sync.
    v5.1b: Integrates with GitHubSignalIngester for Pillar 1/2 signals.

    Args:
        db: MongoDB database
        event_publisher: Event publisher for audit
        org_id: InDE organization ID (may be None for installation events)
        event_type: X-GitHub-Event header value
        payload: Webhook payload
        delivery_id: Delivery ID
        bridge: GitHubRBACBridge instance (optional, from app.state)
        sync_service: GitHubSyncService instance (optional, from app.state)
        signal_ingester: GitHubSignalIngester instance (optional, from app.state)

    Returns:
        Processing result (SUCCESS, SKIPPED, ERROR)
    """
    try:
        # Handle installation events separately (no org_id)
        if event_type == "installation":
            return await handle_installation(
                db=db,
                bridge=bridge,
                sync_service=sync_service,
                event_publisher=event_publisher,
                payload=payload,
                delivery_id=delivery_id
            )

        # All other events require org_id
        if not org_id:
            logger.warning(f"No org_id for {event_type} event, skipping")
            return "SKIPPED"

        # Route to appropriate handler
        if event_type == "membership":
            return await handle_membership(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "organization":
            return await handle_organization(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "team":
            return await handle_team(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "team_add":
            return await handle_team_add(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "repository":
            return await handle_repository(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "member":
            # v5.1b: Layer 2 RBAC activation - repo collaborator events
            return await handle_member(
                db=db,
                bridge=bridge,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "push":
            # v5.1b: Pillar 1/2 signal ingestion - commit activity
            return await handle_push(
                db=db,
                signal_ingester=signal_ingester,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "pull_request":
            # v5.1b: Pillar 1/2 signal ingestion - PR activity
            return await handle_pull_request(
                db=db,
                signal_ingester=signal_ingester,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        elif event_type == "pull_request_review":
            # v5.1b: Pillar 1/2 signal ingestion - review activity
            return await handle_pull_request_review(
                db=db,
                signal_ingester=signal_ingester,
                event_publisher=event_publisher,
                org_id=org_id,
                payload=payload,
                delivery_id=delivery_id
            )

        else:
            logger.debug(f"No handler for event type: {event_type}")
            return "SKIPPED"

    except Exception as e:
        logger.error(f"Error processing {event_type} event: {e}")
        return "ERROR"


# Legacy handler functions for backward compatibility
# These are used by process_github_webhook and maintain the same signature

async def handle_membership_event(
    db,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_membership.

    Used when RBAC bridge is not available (fallback mode).
    """
    action = payload.get("action")
    member = payload.get("member", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub membership event: {action} - "
        f"user={member.get('login')} org={org.get('login')}"
    )

    # Emit audit event
    if event_publisher:
        await event_publisher.publish("github.membership", {
            "action": action,
            "github_user_login": member.get("login"),
            "github_user_id": member.get("id"),
            "github_org_login": org.get("login"),
            "org_id": org_id,
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    return "SUCCESS"


async def handle_organization_event(
    db,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_organization.
    """
    action = payload.get("action")
    org = payload.get("organization", {})

    logger.info(
        f"GitHub organization event: {action} - org={org.get('login')}"
    )

    if event_publisher:
        await event_publisher.publish("github.organization", {
            "action": action,
            "github_org_login": org.get("login"),
            "github_org_id": org.get("id"),
            "org_id": org_id,
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    return "SUCCESS"


async def handle_team_event(
    db,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_team.
    """
    action = payload.get("action")
    team = payload.get("team", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub team event: {action} - "
        f"team={team.get('name')} org={org.get('login')}"
    )

    if event_publisher:
        await event_publisher.publish("github.team", {
            "action": action,
            "github_team_name": team.get("name"),
            "github_team_slug": team.get("slug"),
            "github_team_id": team.get("id"),
            "github_org_login": org.get("login"),
            "org_id": org_id,
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    return "SUCCESS"


async def handle_team_add_event(
    db,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_team_add.
    """
    team = payload.get("team", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub team_add event: team={team.get('name')} org={org.get('login')}"
    )

    if event_publisher:
        await event_publisher.publish("github.team_add", {
            "github_team_name": team.get("name"),
            "github_team_slug": team.get("slug"),
            "github_team_id": team.get("id"),
            "github_org_login": org.get("login"),
            "org_id": org_id,
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    return "SUCCESS"


async def handle_repository_event(
    db,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_repository.
    """
    action = payload.get("action")
    repo = payload.get("repository", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub repository event: {action} - repo={repo.get('full_name')}"
    )

    if event_publisher:
        await event_publisher.publish("github.repository", {
            "action": action,
            "github_repo_name": repo.get("name"),
            "github_repo_full_name": repo.get("full_name"),
            "github_repo_id": repo.get("id"),
            "github_org_login": org.get("login") if org else None,
            "org_id": org_id,
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    return "SUCCESS"


async def handle_installation_event(
    db,
    event_publisher,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Legacy wrapper for handle_installation.
    """
    action = payload.get("action")
    installation = payload.get("installation", {})
    account = installation.get("account", {})

    logger.info(
        f"GitHub installation event: {action} - "
        f"installation_id={installation.get('id')} account={account.get('login')}"
    )

    if event_publisher:
        await event_publisher.publish("github.installation", {
            "action": action,
            "github_installation_id": installation.get("id"),
            "github_account_login": account.get("login"),
            "github_account_type": account.get("type"),
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Handle uninstallation
    if action == "deleted":
        result = db.connector_installations.update_one(
            {
                "github_installation_id": installation.get("id"),
                "connector_slug": "github",
                "status": "ACTIVE"
            },
            {
                "$set": {
                    "status": "SUSPENDED",
                    "uninstalled_at": datetime.utcnow()
                }
            }
        )
        if result.modified_count > 0:
            logger.info(f"GitHub connector suspended for installation {installation.get('id')}")

    return "SUCCESS"
