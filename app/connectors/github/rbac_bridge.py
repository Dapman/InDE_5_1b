"""
InDE MVP v5.1b.0 - GitHub RBAC Bridge

Translates GitHub org/repo roles into InDE RBAC memberships.
Implements the GitHub → InDE role synchronization with human floor enforcement.

Design invariants:
- Reads GitHub org data via GitHubAppConnector.get_api_client()
- Writes only to memberships and github_sync_log collections
- Never reads or writes coaching, pursuit content, maturity, or fear data
- Human floor: effective_role = max(github_derived, human_set)
- Removal is advisory: sets github_unlinked flag, does not delete membership
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .role_mapper import GitHubRoleMapper

logger = logging.getLogger("inde.connectors.github.rbac_bridge")


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class InitialSyncResult:
    """Result of initial sync operation."""
    org_id: str
    sync_id: str
    synced_count: int           # Members successfully synced
    pending_count: int          # GitHub members not yet in InDE
    unchanged_count: int        # Members with no role change
    floor_applied_count: int    # Members where human floor prevented demotion
    error_count: int            # Members that failed to sync
    started_at: datetime
    completed_at: datetime
    status: str                 # "SUCCESS" | "PARTIAL" | "FAILED"
    error_message: Optional[str] = None


@dataclass
class MembershipSyncResult:
    """Result of single membership sync operation."""
    org_id: str
    user_id: Optional[str]      # InDE user ID (None if pending)
    github_login: str
    action: str                 # "created" | "elevated" | "floor_applied" | "unlinked_flagged" | "no_change" | "pending" | "skipped" | "error"
    role_before: Optional[str]
    role_after: Optional[str]
    human_floor_applied: bool
    reason: Optional[str] = None


@dataclass
class TeamSyncResult:
    """Result of team_add sync operation."""
    org_id: str
    team_name: str
    team_slug: str
    action: str                 # "captured" | "skipped"
    reason: Optional[str] = None


@dataclass
class OrgSyncResult:
    """Result of organization event sync operation."""
    org_id: str
    action: str                 # "member_added" | "member_removed" | "renamed" | "no_change"
    affected_user_id: Optional[str] = None
    github_login: Optional[str] = None
    new_org_login: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class OverrideResult:
    """Result of human role override operation."""
    org_id: str
    user_id: str
    role_before: str
    role_after: str
    human_set_role: str
    github_derived_role: Optional[str]
    admin_user_id: str
    timestamp: datetime


@dataclass
class PursuitRoleSyncResult:
    """Result of pursuit role sync from repository collaborators (Layer 2)."""
    org_id: str
    pursuit_id: str
    github_repo_id: int
    is_primary_repo: bool
    synced_count: int           # Members with role changes
    unchanged_count: int        # Members with no role change
    floor_applied_count: int    # Members where human floor prevented demotion
    error_count: int            # Members that failed to sync
    action: str                 # "synced" | "secondary_repo_signal_only" | "no_links" | "error"
    delivery_id: Optional[str] = None
    error_message: Optional[str] = None


# =============================================================================
# GITHUB RBAC BRIDGE
# =============================================================================

class GitHubRBACBridge:
    """
    Translates GitHub org/repo roles into InDE RBAC memberships.

    Design invariants:
    - Reads GitHub org data via GitHubAppConnector.get_org_members()
    - Writes only to memberships and github_sync_log collections
    - Never reads or writes coaching, maturity, fear, or pursuit content modules
    - Human floor: effective_role = max(github_derived, human_set)
    - Removal is advisory: sets github_unlinked flag, does not delete membership
    """

    def __init__(self, db, connector=None, event_publisher=None):
        """
        Initialize the RBAC bridge.

        Args:
            db: MongoDB database instance
            connector: GitHubAppConnector instance (optional, for API calls)
            event_publisher: Event publisher for audit events
        """
        self.db = db
        self.connector = connector
        self.event_publisher = event_publisher
        self.role_mapper = GitHubRoleMapper()

    async def initial_sync(self, org_id: str) -> InitialSyncResult:
        """
        Perform initial sync of GitHub org members to InDE RBAC.

        Called at connector installation. Reads full GitHub org roster and syncs.

        Flow:
        1. Read connector_installations record for org_id
        2. Get API client and fetch org members from GitHub
        3. For each GitHub member:
           a. Look up InDE user by github_login or email
           b. If found: compute effective_role, apply human floor, update membership
           c. If not found: create pending_github_member record
        4. Emit audit events and return result

        Args:
            org_id: InDE organization ID

        Returns:
            InitialSyncResult with sync statistics
        """
        import uuid
        sync_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        synced_count = 0
        pending_count = 0
        unchanged_count = 0
        floor_applied_count = 0
        error_count = 0

        try:
            # Get installation details
            installation = self.db.connector_installations.find_one({
                "org_id": org_id,
                "connector_slug": "github",
                "status": "ACTIVE"
            })

            if not installation:
                return InitialSyncResult(
                    org_id=org_id,
                    sync_id=sync_id,
                    synced_count=0,
                    pending_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    status="FAILED",
                    error_message="GitHub connector not installed"
                )

            github_org_login = installation.get("github_org_login")

            # Get API client
            if not self.connector:
                return InitialSyncResult(
                    org_id=org_id,
                    sync_id=sync_id,
                    synced_count=0,
                    pending_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    status="FAILED",
                    error_message="Connector not available"
                )

            client = await self.connector.get_api_client(org_id)
            if not client:
                return InitialSyncResult(
                    org_id=org_id,
                    sync_id=sync_id,
                    synced_count=0,
                    pending_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    status="FAILED",
                    error_message="Failed to get API client"
                )

            try:
                # Fetch GitHub org members
                github_members = await client.get_org_members(github_org_login)

                for member in github_members:
                    try:
                        result = await self._sync_single_member(
                            org_id=org_id,
                            github_login=member.get("login"),
                            github_role=member.get("role", "member"),
                            sync_source="initial_sync"
                        )

                        if result.action == "pending":
                            pending_count += 1
                        elif result.action == "no_change":
                            unchanged_count += 1
                        elif result.action == "floor_applied":
                            floor_applied_count += 1
                            synced_count += 1
                        elif result.action in ["created", "elevated"]:
                            synced_count += 1
                        elif result.action == "error":
                            error_count += 1

                    except Exception as e:
                        logger.error(f"Failed to sync member {member.get('login')}: {e}")
                        error_count += 1

            finally:
                await client.close()

            # Log to github_sync_log
            self._log_sync_event(
                org_id=org_id,
                event_type="initial_sync",
                action="completed",
                details={
                    "sync_id": sync_id,
                    "synced_count": synced_count,
                    "pending_count": pending_count,
                    "unchanged_count": unchanged_count,
                    "floor_applied_count": floor_applied_count,
                    "error_count": error_count
                }
            )

            # Emit audit event
            if self.event_publisher:
                await self.event_publisher.publish("rbac.github_sync.initial_sync_complete", {
                    "org_id": org_id,
                    "sync_id": sync_id,
                    "synced_count": synced_count,
                    "pending_count": pending_count,
                    "floor_applied_count": floor_applied_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            status = "SUCCESS"
            if error_count > 0:
                status = "PARTIAL" if synced_count > 0 else "FAILED"

            return InitialSyncResult(
                org_id=org_id,
                sync_id=sync_id,
                synced_count=synced_count,
                pending_count=pending_count,
                unchanged_count=unchanged_count,
                floor_applied_count=floor_applied_count,
                error_count=error_count,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status=status
            )

        except Exception as e:
            logger.error(f"Initial sync failed for org {org_id}: {e}")
            return InitialSyncResult(
                org_id=org_id,
                sync_id=sync_id,
                synced_count=synced_count,
                pending_count=pending_count,
                unchanged_count=unchanged_count,
                floor_applied_count=floor_applied_count,
                error_count=error_count,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                status="FAILED",
                error_message=str(e)
            )

    async def handle_membership_event(
        self,
        org_id: str,
        event_payload: dict,
        delivery_id: str
    ) -> MembershipSyncResult:
        """
        Handle GitHub membership webhook: member added/removed/role changed.

        Args:
            org_id: InDE organization ID
            event_payload: Webhook payload
            delivery_id: Delivery ID for idempotency

        Returns:
            MembershipSyncResult
        """
        action = event_payload.get("action")
        member = event_payload.get("member", {})
        github_login = member.get("login")
        scope = event_payload.get("scope")

        # Only handle org-scope events
        if scope != "organization":
            return MembershipSyncResult(
                org_id=org_id,
                user_id=None,
                github_login=github_login or "",
                action="skipped",
                role_before=None,
                role_after=None,
                human_floor_applied=False,
                reason="team_scope_deferred_to_team_add_handler"
            )

        if action == "added":
            github_role = event_payload.get("role", "member")
            return await self._sync_single_member(
                org_id=org_id,
                github_login=github_login,
                github_role=github_role,
                sync_source="webhook",
                delivery_id=delivery_id
            )

        elif action == "removed":
            return await self._handle_member_removed(
                org_id=org_id,
                github_login=github_login,
                delivery_id=delivery_id
            )

        return MembershipSyncResult(
            org_id=org_id,
            user_id=None,
            github_login=github_login or "",
            action="skipped",
            role_before=None,
            role_after=None,
            human_floor_applied=False,
            reason=f"unknown_action_{action}"
        )

    async def handle_team_add_event(
        self,
        org_id: str,
        event_payload: dict,
        delivery_id: str
    ) -> TeamSyncResult:
        """
        Handle GitHub team_add webhook: member added to a GitHub team.

        In v5.1a: record the team membership signal in github_sync_log for
        future IDTFS use. Do NOT yet map teams to pursuits - that is v5.1b.

        Args:
            org_id: InDE organization ID
            event_payload: Webhook payload
            delivery_id: Delivery ID

        Returns:
            TeamSyncResult
        """
        team = event_payload.get("team", {})
        team_name = team.get("name", "")
        team_slug = team.get("slug", "")

        # Log team add signal for v5.1b backfill
        self._log_sync_event(
            org_id=org_id,
            event_type="webhook_team_add",
            github_delivery_id=delivery_id,
            action="captured",
            details={
                "team_name": team_name,
                "team_slug": team_slug,
                "team_id": team.get("id")
            }
        )

        return TeamSyncResult(
            org_id=org_id,
            team_name=team_name,
            team_slug=team_slug,
            action="captured",
            reason="signal_captured_for_v5.1b"
        )

    async def handle_organization_event(
        self,
        org_id: str,
        event_payload: dict,
        delivery_id: str
    ) -> OrgSyncResult:
        """
        Handle GitHub organization webhook: org renamed, member_added, member_removed.

        Args:
            org_id: InDE organization ID
            event_payload: Webhook payload
            delivery_id: Delivery ID

        Returns:
            OrgSyncResult
        """
        action = event_payload.get("action")
        org = event_payload.get("organization", {})

        if action == "member_added":
            membership = event_payload.get("membership", {})
            member = membership.get("user", {})
            github_login = member.get("login")
            github_role = membership.get("role", "member")

            result = await self._sync_single_member(
                org_id=org_id,
                github_login=github_login,
                github_role=github_role,
                sync_source="webhook",
                delivery_id=delivery_id
            )

            return OrgSyncResult(
                org_id=org_id,
                action="member_added",
                affected_user_id=result.user_id,
                github_login=github_login
            )

        elif action == "member_removed":
            membership = event_payload.get("membership", {})
            member = membership.get("user", {})
            github_login = member.get("login")

            result = await self._handle_member_removed(
                org_id=org_id,
                github_login=github_login,
                delivery_id=delivery_id
            )

            return OrgSyncResult(
                org_id=org_id,
                action="member_removed",
                affected_user_id=result.user_id,
                github_login=github_login
            )

        elif action == "renamed":
            new_login = org.get("login")

            # Update connector_installations.github_org_login
            self.db.connector_installations.update_one(
                {"org_id": org_id, "connector_slug": "github"},
                {"$set": {"github_org_login": new_login}}
            )

            self._log_sync_event(
                org_id=org_id,
                event_type="webhook_org",
                github_delivery_id=delivery_id,
                action="renamed",
                details={"new_login": new_login}
            )

            return OrgSyncResult(
                org_id=org_id,
                action="renamed",
                new_org_login=new_login
            )

        # Other actions: log and mark as no_change
        self._log_sync_event(
            org_id=org_id,
            event_type="webhook_org",
            github_delivery_id=delivery_id,
            action="no_change",
            details={"github_action": action}
        )

        return OrgSyncResult(
            org_id=org_id,
            action="no_change",
            reason=f"action_{action}_not_handled"
        )

    async def apply_human_override(
        self,
        org_id: str,
        user_id: str,
        new_role: str,
        admin_user_id: str
    ) -> OverrideResult:
        """
        Admin explicitly sets a role. Sets human_set_role floor.

        Args:
            org_id: Organization ID
            user_id: Target user ID
            new_role: New role to set (org_admin, org_member, org_viewer)
            admin_user_id: Admin user ID performing the override

        Returns:
            OverrideResult
        """
        now = datetime.now(timezone.utc)

        # Find existing membership
        membership = self.db.memberships.find_one({
            "org_id": org_id,
            "user_id": user_id,
            "status": "active"
        })

        if not membership:
            raise ValueError(f"No active membership found for user {user_id} in org {org_id}")

        role_before = membership.get("effective_role") or membership.get("role")
        github_derived_role = membership.get("github_derived_role")

        # Set human_set_role and recompute effective_role
        effective_role, floor_applied = self.role_mapper.compute_effective_role(
            github_derived_role=github_derived_role,
            human_set_role=new_role,
            current_role=role_before
        )

        # Update membership
        self.db.memberships.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "role": effective_role,
                    "effective_role": effective_role,
                    "human_set_role": new_role,
                    "human_set_at": now,
                    "human_set_by": admin_user_id,
                    "github_sync_source": "manual"
                }
            }
        )

        # Log to github_sync_log
        self._log_sync_event(
            org_id=org_id,
            event_type="manual_override",
            affected_user_id=user_id,
            action="human_override",
            role_before=role_before,
            role_after=effective_role,
            human_floor_applied=floor_applied,
            details={
                "admin_user_id": admin_user_id,
                "human_set_role": new_role
            }
        )

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("rbac.github_sync.human_override", {
                "org_id": org_id,
                "user_id": user_id,
                "admin_user_id": admin_user_id,
                "role_before": role_before,
                "role_after": effective_role,
                "human_set_role": new_role,
                "timestamp": now.isoformat()
            })

        return OverrideResult(
            org_id=org_id,
            user_id=user_id,
            role_before=role_before,
            role_after=effective_role,
            human_set_role=new_role,
            github_derived_role=github_derived_role,
            admin_user_id=admin_user_id,
            timestamp=now
        )

    async def sync_pursuit_roles_from_repo(
        self,
        org_id: str,
        github_repo_id: int,
        delivery_id: str
    ) -> List[PursuitRoleSyncResult]:
        """
        Layer 2 Live Activation: Sync GitHub repo roles to InDE pursuit roles.

        Called when a repository collaborator event fires (member added/removed/changed).

        Flow:
        1. Look up all active pursuit_repo_links for this github_repo_id
        2. For each linked pursuit:
           a. Only apply Layer 2 roles if this repo is the primary repo for the pursuit
           b. Fetch current GitHub collaborators for the repo via GitHubAppConnector
           c. For each collaborator: map GitHub role → InDE pursuit role
           d. Apply human floor: effective_pursuit_role = max(github_derived, human_set)
           e. Update pursuit memberships with new effective_pursuit_role
           f. Write to github_sync_log with event_type="webhook_repo_collab"
        3. Secondary repos: log signal only, do NOT modify pursuit roles

        Two-layer independence invariant:
        This method MUST NOT read or modify org_role. It reads and writes pursuit_role
        only. The org_role layer remains completely independent.

        Args:
            org_id: InDE organization ID
            github_repo_id: GitHub numeric repo ID
            delivery_id: Webhook delivery ID for idempotency

        Returns:
            List of PursuitRoleSyncResult for each linked pursuit
        """
        results = []

        # Look up all pursuit links for this repo
        links = list(self.db.pursuit_repo_links.find({
            "org_id": org_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        }))

        if not links:
            # No pursuits linked to this repo
            self._log_sync_event(
                org_id=org_id,
                event_type="webhook_repo_collab",
                github_delivery_id=delivery_id,
                action="no_links",
                details={"github_repo_id": github_repo_id}
            )
            return [PursuitRoleSyncResult(
                org_id=org_id,
                pursuit_id="",
                github_repo_id=github_repo_id,
                is_primary_repo=False,
                synced_count=0,
                unchanged_count=0,
                floor_applied_count=0,
                error_count=0,
                action="no_links",
                delivery_id=delivery_id
            )]

        for link in links:
            pursuit_id = link.get("pursuit_id")
            is_primary = link.get("is_primary", False)
            github_repo_full_name = link.get("github_repo_full_name", "")

            if not is_primary:
                # Secondary repo: log signal only, no role mutation
                self._log_sync_event(
                    org_id=org_id,
                    event_type="webhook_repo_collab",
                    github_delivery_id=delivery_id,
                    action="secondary_repo_signal_only",
                    details={
                        "pursuit_id": pursuit_id,
                        "github_repo_id": github_repo_id,
                        "github_repo_full_name": github_repo_full_name,
                        "reason": "not_primary_repo"
                    }
                )
                results.append(PursuitRoleSyncResult(
                    org_id=org_id,
                    pursuit_id=pursuit_id,
                    github_repo_id=github_repo_id,
                    is_primary_repo=False,
                    synced_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    action="secondary_repo_signal_only",
                    delivery_id=delivery_id
                ))
                continue

            # Primary repo: sync pursuit roles
            result = await self._sync_pursuit_roles_from_primary_repo(
                org_id=org_id,
                pursuit_id=pursuit_id,
                github_repo_id=github_repo_id,
                github_repo_full_name=github_repo_full_name,
                delivery_id=delivery_id
            )
            results.append(result)

        return results

    async def _sync_pursuit_roles_from_primary_repo(
        self,
        org_id: str,
        pursuit_id: str,
        github_repo_id: int,
        github_repo_full_name: str,
        delivery_id: str
    ) -> PursuitRoleSyncResult:
        """
        Sync pursuit roles from primary repo collaborators.

        Two-layer independence: This method only modifies pursuit_role,
        never touches org_role.
        """
        now = datetime.now(timezone.utc)
        synced_count = 0
        unchanged_count = 0
        floor_applied_count = 0
        error_count = 0

        try:
            # Get API client
            if not self.connector:
                return PursuitRoleSyncResult(
                    org_id=org_id,
                    pursuit_id=pursuit_id,
                    github_repo_id=github_repo_id,
                    is_primary_repo=True,
                    synced_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    action="error",
                    delivery_id=delivery_id,
                    error_message="Connector not available"
                )

            client = await self.connector.get_api_client(org_id)
            if not client:
                return PursuitRoleSyncResult(
                    org_id=org_id,
                    pursuit_id=pursuit_id,
                    github_repo_id=github_repo_id,
                    is_primary_repo=True,
                    synced_count=0,
                    unchanged_count=0,
                    floor_applied_count=0,
                    error_count=0,
                    action="error",
                    delivery_id=delivery_id,
                    error_message="Failed to get API client"
                )

            try:
                # Fetch repo collaborators from GitHub
                collaborators = await client.get_repo_collaborators(github_repo_full_name)

                for collab in collaborators:
                    try:
                        github_login = collab.get("login")
                        github_repo_role = collab.get("permissions", {})

                        # Determine highest role from permissions
                        if github_repo_role.get("admin"):
                            role_key = "admin"
                        elif github_repo_role.get("maintain"):
                            role_key = "maintain"
                        elif github_repo_role.get("push"):
                            role_key = "write"
                        elif github_repo_role.get("triage"):
                            role_key = "triage"
                        else:
                            role_key = "read"

                        # Map to InDE pursuit role
                        github_derived_pursuit_role = self.role_mapper.map_repo_role(role_key)

                        # Find user's membership in org
                        membership = self.db.memberships.find_one({
                            "org_id": org_id,
                            "github_login": github_login,
                            "status": "active"
                        })

                        if not membership:
                            # Try to find by user record
                            user = self.db.users.find_one({"github_login": github_login})
                            if user:
                                membership = self.db.memberships.find_one({
                                    "org_id": org_id,
                                    "user_id": str(user["_id"]),
                                    "status": "active"
                                })

                        if not membership:
                            # User not in InDE - skip
                            continue

                        user_id = membership.get("user_id")

                        # Find pursuit membership
                        pursuit_membership = self.db.pursuit_memberships.find_one({
                            "pursuit_id": pursuit_id,
                            "user_id": user_id,
                        })

                        pursuit_role_before = None
                        human_set_pursuit_role = None

                        if pursuit_membership:
                            pursuit_role_before = pursuit_membership.get("pursuit_role") or pursuit_membership.get("role")
                            human_set_pursuit_role = pursuit_membership.get("human_set_pursuit_role")

                        # Compute effective pursuit role with human floor
                        effective_pursuit_role, floor_applied = self.role_mapper.compute_effective_pursuit_role(
                            github_derived_pursuit_role=github_derived_pursuit_role,
                            human_set_pursuit_role=human_set_pursuit_role,
                            current_pursuit_role=pursuit_role_before
                        )

                        # Determine if role changed
                        if pursuit_role_before == effective_pursuit_role:
                            unchanged_count += 1
                        elif floor_applied:
                            floor_applied_count += 1
                            synced_count += 1
                        else:
                            synced_count += 1

                        # Update or create pursuit membership
                        if pursuit_membership:
                            self.db.pursuit_memberships.update_one(
                                {"_id": pursuit_membership["_id"]},
                                {
                                    "$set": {
                                        "pursuit_role": effective_pursuit_role,
                                        "role": effective_pursuit_role,
                                        "github_derived_pursuit_role": github_derived_pursuit_role,
                                        "github_repo_role": role_key,
                                        "github_synced_at": now,
                                    }
                                }
                            )
                        else:
                            # Create new pursuit membership
                            self.db.pursuit_memberships.insert_one({
                                "pursuit_id": pursuit_id,
                                "user_id": user_id,
                                "org_id": org_id,
                                "pursuit_role": effective_pursuit_role,
                                "role": effective_pursuit_role,
                                "github_login": github_login,
                                "github_derived_pursuit_role": github_derived_pursuit_role,
                                "github_repo_role": role_key,
                                "github_synced_at": now,
                                "created_at": now,
                            })
                            synced_count += 1

                    except Exception as e:
                        logger.error(f"Failed to sync pursuit role for {collab.get('login')}: {e}")
                        error_count += 1

            finally:
                await client.close()

            # Log sync event
            self._log_sync_event(
                org_id=org_id,
                event_type="webhook_repo_collab",
                github_delivery_id=delivery_id,
                action="synced",
                details={
                    "pursuit_id": pursuit_id,
                    "github_repo_id": github_repo_id,
                    "github_repo_full_name": github_repo_full_name,
                    "is_primary_repo": True,
                    "synced_count": synced_count,
                    "unchanged_count": unchanged_count,
                    "floor_applied_count": floor_applied_count,
                    "error_count": error_count
                }
            )

            return PursuitRoleSyncResult(
                org_id=org_id,
                pursuit_id=pursuit_id,
                github_repo_id=github_repo_id,
                is_primary_repo=True,
                synced_count=synced_count,
                unchanged_count=unchanged_count,
                floor_applied_count=floor_applied_count,
                error_count=error_count,
                action="synced",
                delivery_id=delivery_id
            )

        except Exception as e:
            logger.error(f"Failed to sync pursuit roles from repo {github_repo_id}: {e}")
            return PursuitRoleSyncResult(
                org_id=org_id,
                pursuit_id=pursuit_id,
                github_repo_id=github_repo_id,
                is_primary_repo=True,
                synced_count=synced_count,
                unchanged_count=unchanged_count,
                floor_applied_count=floor_applied_count,
                error_count=error_count,
                action="error",
                delivery_id=delivery_id,
                error_message=str(e)
            )

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _sync_single_member(
        self,
        org_id: str,
        github_login: str,
        github_role: str,
        sync_source: str,
        delivery_id: str = None
    ) -> MembershipSyncResult:
        """
        Sync a single GitHub member to InDE membership.

        Args:
            org_id: InDE organization ID
            github_login: GitHub username
            github_role: GitHub org role (owner, member, outside_collaborator)
            sync_source: "initial_sync" | "webhook"
            delivery_id: Optional delivery ID for webhooks

        Returns:
            MembershipSyncResult
        """
        now = datetime.now(timezone.utc)
        github_derived_role = self.role_mapper.map_org_role(github_role)

        # Find InDE user by github_login
        membership = self.db.memberships.find_one({
            "org_id": org_id,
            "github_login": github_login,
            "status": "active"
        })

        # If not found by github_login, try to find by user record with matching github_login
        if not membership:
            user = self.db.users.find_one({"github_login": github_login})
            if user:
                membership = self.db.memberships.find_one({
                    "org_id": org_id,
                    "user_id": str(user["_id"]),
                    "status": "active"
                })

        if not membership:
            # User not in InDE - create pending record in sync log
            self._log_sync_event(
                org_id=org_id,
                event_type=sync_source,
                github_delivery_id=delivery_id,
                github_login=github_login,
                action="pending",
                details={
                    "github_role": github_role,
                    "github_derived_role": github_derived_role,
                    "reason": "user_not_found_in_inde"
                }
            )

            return MembershipSyncResult(
                org_id=org_id,
                user_id=None,
                github_login=github_login,
                action="pending",
                role_before=None,
                role_after=None,
                human_floor_applied=False,
                reason="user_not_found_in_inde"
            )

        user_id = membership.get("user_id")
        role_before = membership.get("effective_role") or membership.get("role")
        human_set_role = membership.get("human_set_role")

        # Compute effective role with human floor
        effective_role, floor_applied = self.role_mapper.compute_effective_role(
            github_derived_role=github_derived_role,
            human_set_role=human_set_role,
            current_role=role_before
        )

        # Determine action
        if role_before == effective_role:
            action = "no_change"
        elif floor_applied:
            action = "floor_applied"
        elif self.role_mapper.role_index(effective_role) > self.role_mapper.role_index(role_before):
            action = "elevated"
        else:
            action = "created"

        # Update membership
        update_fields = {
            "github_login": github_login,
            "github_org_role": github_role,
            "github_derived_role": github_derived_role,
            "github_sync_source": sync_source,
            "github_synced_at": now,
            "github_unlinked": False,
            "effective_role": effective_role,
        }

        # Only update role if not floor_applied (floor_applied keeps human_set_role)
        if not floor_applied:
            update_fields["role"] = effective_role

        self.db.memberships.update_one(
            {"_id": membership["_id"]},
            {"$set": update_fields}
        )

        # Log to github_sync_log
        self._log_sync_event(
            org_id=org_id,
            event_type=sync_source,
            github_delivery_id=delivery_id,
            affected_user_id=user_id,
            github_login=github_login,
            action=action,
            role_before=role_before,
            role_after=effective_role,
            human_floor_applied=floor_applied
        )

        return MembershipSyncResult(
            org_id=org_id,
            user_id=user_id,
            github_login=github_login,
            action=action,
            role_before=role_before,
            role_after=effective_role,
            human_floor_applied=floor_applied
        )

    async def _handle_member_removed(
        self,
        org_id: str,
        github_login: str,
        delivery_id: str
    ) -> MembershipSyncResult:
        """
        Handle member removal from GitHub org.

        Sets github_unlinked=True flag - does NOT delete the membership.
        Human admin must confirm removal through InDE admin interface.

        Args:
            org_id: InDE organization ID
            github_login: GitHub username
            delivery_id: Delivery ID

        Returns:
            MembershipSyncResult
        """
        now = datetime.now(timezone.utc)

        # Find membership by github_login
        membership = self.db.memberships.find_one({
            "org_id": org_id,
            "github_login": github_login,
            "status": "active"
        })

        if not membership:
            return MembershipSyncResult(
                org_id=org_id,
                user_id=None,
                github_login=github_login,
                action="skipped",
                role_before=None,
                role_after=None,
                human_floor_applied=False,
                reason="membership_not_found"
            )

        user_id = membership.get("user_id")
        role_before = membership.get("effective_role") or membership.get("role")

        # Set unlinked flag - do NOT delete or change role
        self.db.memberships.update_one(
            {"_id": membership["_id"]},
            {
                "$set": {
                    "github_unlinked": True,
                    "github_unlinked_at": now,
                    "github_sync_source": "webhook"
                }
            }
        )

        # Log to github_sync_log
        self._log_sync_event(
            org_id=org_id,
            event_type="webhook_membership",
            github_delivery_id=delivery_id,
            affected_user_id=user_id,
            github_login=github_login,
            action="unlinked_flagged",
            role_before=role_before,
            role_after=role_before,  # Role unchanged
            human_floor_applied=False
        )

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("rbac.github_sync.member_unlinked", {
                "org_id": org_id,
                "user_id": user_id,
                "github_login": github_login,
                "delivery_id": delivery_id,
                "timestamp": now.isoformat()
            })

        return MembershipSyncResult(
            org_id=org_id,
            user_id=user_id,
            github_login=github_login,
            action="unlinked_flagged",
            role_before=role_before,
            role_after=role_before,  # Role unchanged
            human_floor_applied=False,
            reason="github_membership_removed_pending_admin_review"
        )

    def _log_sync_event(
        self,
        org_id: str,
        event_type: str,
        action: str,
        github_delivery_id: str = None,
        affected_user_id: str = None,
        github_login: str = None,
        role_before: str = None,
        role_after: str = None,
        human_floor_applied: bool = False,
        details: dict = None
    ):
        """
        Log sync event to github_sync_log collection.

        Args:
            org_id: Organization ID
            event_type: "initial_sync" | "webhook_membership" | "webhook_team_add" | "webhook_org" | "manual_override"
            action: "created" | "elevated" | "floor_applied" | "unlinked_flagged" | "no_change" | "pending" | etc.
            github_delivery_id: Optional delivery ID for webhook events
            affected_user_id: Optional InDE user ID
            github_login: Optional GitHub username
            role_before: Role before sync
            role_after: Role after sync
            human_floor_applied: Whether human floor prevented demotion
            details: Additional details dict
        """
        doc = {
            "org_id": org_id,
            "event_type": event_type,
            "action": action,
            "github_delivery_id": github_delivery_id,
            "affected_user_id": affected_user_id,
            "github_login": github_login,
            "role_before": role_before,
            "role_after": role_after,
            "human_floor_applied": human_floor_applied,
            "created_at": datetime.now(timezone.utc),
        }

        if details:
            doc["details"] = details

        try:
            self.db.github_sync_log.insert_one(doc)
        except Exception as e:
            logger.error(f"Failed to log sync event: {e}")
