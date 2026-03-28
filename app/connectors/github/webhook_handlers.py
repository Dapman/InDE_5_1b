"""
InDE MVP v5.1b.0 - GitHub Webhook Handlers

Live handlers for GitHub webhook events that sync to InDE RBAC.
Replaces v5.1 stub handlers with real implementations.

Handler responsibilities:
1. Check idempotency via delivery_id
2. Extract relevant data from payload
3. Call RBAC bridge for sync
4. Log results and mark processed
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("inde.connectors.github.webhook_handlers")


async def handle_membership(
    db,
    bridge,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'membership' event: member added/removed/role changed.

    v5.1a: Full RBAC sync implementation.

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance
        event_publisher: Event publisher for audit
        org_id: InDE organization ID
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result (SUCCESS, SKIPPED, ERROR)
    """
    action = payload.get("action")  # added, removed
    member = payload.get("member", {})
    org = payload.get("organization", {})
    scope = payload.get("scope")

    github_login = member.get("login")

    logger.info(
        f"GitHub membership event: {action} - "
        f"user={github_login} org={org.get('login')} scope={scope}"
    )

    # Only handle org-scope events
    if scope != "organization":
        logger.debug(f"Skipping team-scope membership event for {github_login}")
        # Emit audit event for visibility
        if event_publisher:
            await event_publisher.publish("github.membership", {
                "action": action,
                "github_user_login": github_login,
                "github_org_login": org.get("login"),
                "org_id": org_id,
                "delivery_id": delivery_id,
                "skipped": True,
                "reason": "team_scope",
                "timestamp": datetime.utcnow().isoformat()
            })
        return "SKIPPED"

    try:
        # Call RBAC bridge
        result = await bridge.handle_membership_event(
            org_id=org_id,
            event_payload=payload,
            delivery_id=delivery_id
        )

        # Emit audit event
        if event_publisher:
            await event_publisher.publish("github.membership", {
                "action": action,
                "github_user_login": github_login,
                "github_user_id": member.get("id"),
                "github_org_login": org.get("login"),
                "org_id": org_id,
                "delivery_id": delivery_id,
                "sync_result": result.action,
                "role_before": result.role_before,
                "role_after": result.role_after,
                "human_floor_applied": result.human_floor_applied,
                "timestamp": datetime.utcnow().isoformat()
            })

        return "SUCCESS"

    except Exception as e:
        logger.error(f"Membership handler error: {e}")
        return "ERROR"


async def handle_organization(
    db,
    bridge,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'organization' event: renamed, member_added, member_removed.

    v5.1a: Routes member events through RBAC bridge.

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance
        event_publisher: Event publisher for audit
        org_id: InDE organization ID
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result
    """
    action = payload.get("action")  # renamed, member_added, member_removed, deleted
    org = payload.get("organization", {})

    logger.info(
        f"GitHub organization event: {action} - org={org.get('login')}"
    )

    try:
        # Call RBAC bridge
        result = await bridge.handle_organization_event(
            org_id=org_id,
            event_payload=payload,
            delivery_id=delivery_id
        )

        # Emit audit event
        if event_publisher:
            await event_publisher.publish("github.organization", {
                "action": action,
                "github_org_login": org.get("login"),
                "github_org_id": org.get("id"),
                "org_id": org_id,
                "delivery_id": delivery_id,
                "sync_result": result.action,
                "affected_user_id": result.affected_user_id,
                "new_org_login": result.new_org_login,
                "timestamp": datetime.utcnow().isoformat()
            })

        return "SUCCESS"

    except Exception as e:
        logger.error(f"Organization handler error: {e}")
        return "ERROR"


async def handle_team(
    db,
    bridge,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'team' event: team created/deleted/edited.

    v5.1a: Logs event but does not mutate RBAC.
    Team → pursuit mapping is v5.1b (IDTFS activation).

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance
        event_publisher: Event publisher for audit
        org_id: InDE organization ID
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result
    """
    action = payload.get("action")  # created, deleted, edited
    team = payload.get("team", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub team event: {action} - "
        f"team={team.get('name')} org={org.get('login')}"
    )

    # v5.1a: Log for future IDTFS use, no mutation
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


async def handle_team_add(
    db,
    bridge,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'team_add' event: member added to team.

    v5.1a: Captures team membership signal for v5.1b IDTFS backfill.
    Does NOT yet map teams to pursuits.

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance
        event_publisher: Event publisher for audit
        org_id: InDE organization ID
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result
    """
    team = payload.get("team", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub team_add event: team={team.get('name')} org={org.get('login')}"
    )

    try:
        # Call RBAC bridge (captures signal for v5.1b)
        result = await bridge.handle_team_add_event(
            org_id=org_id,
            event_payload=payload,
            delivery_id=delivery_id
        )

        # Emit audit event
        if event_publisher:
            await event_publisher.publish("github.team_add", {
                "github_team_name": team.get("name"),
                "github_team_slug": team.get("slug"),
                "github_team_id": team.get("id"),
                "github_org_login": org.get("login"),
                "org_id": org_id,
                "delivery_id": delivery_id,
                "sync_result": result.action,
                "timestamp": datetime.utcnow().isoformat()
            })

        return "SUCCESS"

    except Exception as e:
        logger.error(f"Team add handler error: {e}")
        return "ERROR"


async def handle_repository(
    db,
    bridge,
    event_publisher,
    org_id: str,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'repository' event: repo created/deleted/archived.

    v5.1a: Logs event but does not mutate RBAC.
    Reserved for v5.1b IDTFS activation (pursuit ↔ repo linking).

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance (unused in v5.1a)
        event_publisher: Event publisher for audit
        org_id: InDE organization ID
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result
    """
    action = payload.get("action")  # created, deleted, archived, unarchived
    repo = payload.get("repository", {})
    org = payload.get("organization", {})

    logger.info(
        f"GitHub repository event: {action} - repo={repo.get('full_name')}"
    )

    # v5.1a: Log for future IDTFS use, no mutation
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


async def handle_installation(
    db,
    bridge,
    sync_service,
    event_publisher,
    payload: dict,
    delivery_id: str
) -> str:
    """
    Handle GitHub 'installation' event: app installed/uninstalled.

    v5.1a: Triggers initial sync on installation.

    Args:
        db: MongoDB database
        bridge: GitHubRBACBridge instance
        sync_service: GitHubSyncService instance
        event_publisher: Event publisher for audit
        payload: Webhook payload
        delivery_id: Delivery ID

    Returns:
        Processing result
    """
    action = payload.get("action")  # created, deleted, suspend, unsuspend
    installation = payload.get("installation", {})
    account = installation.get("account", {})

    logger.info(
        f"GitHub installation event: {action} - "
        f"installation_id={installation.get('id')} account={account.get('login')}"
    )

    # Emit audit event
    if event_publisher:
        await event_publisher.publish("github.installation", {
            "action": action,
            "github_installation_id": installation.get("id"),
            "github_account_login": account.get("login"),
            "github_account_type": account.get("type"),
            "delivery_id": delivery_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Handle installation created - trigger initial sync
    if action == "created":
        # Find the org_id from the installation
        installation_id = installation.get("id")
        if installation_id:
            install_doc = db.connector_installations.find_one({
                "github_installation_id": installation_id,
                "connector_slug": "github",
                "status": "ACTIVE"
            })
            if install_doc and sync_service:
                org_id = install_doc.get("org_id")
                try:
                    await sync_service.handle_connector_installed(org_id)
                    logger.info(f"Initial sync triggered for org {org_id}")
                except Exception as e:
                    logger.warning(f"Could not trigger initial sync: {e}")

    # Handle uninstallation
    elif action == "deleted":
        # Mark the connector installation as suspended
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
