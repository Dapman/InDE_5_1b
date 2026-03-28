"""
InDE MVP v5.1b.0 - GitHub Sync Log Model

Audit trail for all RBAC sync operations.
Separate from the main audit pipeline to allow targeted querying.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class GithubSyncLog:
    """
    Audit log entry for GitHub → InDE RBAC sync operations.

    Attributes:
        org_id: Always present — all sync is org-scoped
        event_type: "initial_sync" | "webhook_membership" | "webhook_team_add" | "webhook_org" | "manual_override"
        github_delivery_id: Present for webhook-triggered syncs
        affected_user_id: InDE user_id if a specific user was affected
        github_login: GitHub username of affected user
        role_before: effective_role before sync
        role_after: effective_role after sync
        action: "created" | "elevated" | "floor_applied" | "unlinked_flagged" | "no_change" | "pending"
        human_floor_applied: True if human floor prevented a lower role from being set
        created_at: Timestamp of sync operation
        details: Additional context (sync_id, team info, etc.)
    """
    org_id: str
    event_type: str
    action: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    github_delivery_id: Optional[str] = None
    affected_user_id: Optional[str] = None
    github_login: Optional[str] = None
    role_before: Optional[str] = None
    role_after: Optional[str] = None
    human_floor_applied: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "org_id": self.org_id,
            "event_type": self.event_type,
            "github_delivery_id": self.github_delivery_id,
            "affected_user_id": self.affected_user_id,
            "github_login": self.github_login,
            "role_before": self.role_before,
            "role_after": self.role_after,
            "action": self.action,
            "human_floor_applied": self.human_floor_applied,
            "created_at": self.created_at,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GithubSyncLog":
        """Create from MongoDB document."""
        return cls(
            org_id=data["org_id"],
            event_type=data["event_type"],
            action=data["action"],
            created_at=data.get("created_at", datetime.utcnow()),
            github_delivery_id=data.get("github_delivery_id"),
            affected_user_id=data.get("affected_user_id"),
            github_login=data.get("github_login"),
            role_before=data.get("role_before"),
            role_after=data.get("role_after"),
            human_floor_applied=data.get("human_floor_applied", False),
            details=data.get("details", {}),
        )


# =============================================================================
# INDEX DEFINITIONS
# =============================================================================

GITHUB_SYNC_LOG_INDEXES = [
    # Idempotency — one sync log entry per delivery per affected user
    {
        "keys": [("org_id", 1), ("github_delivery_id", 1), ("affected_user_id", 1)],
        "unique": False,  # Not unique because same delivery can affect multiple users
        "sparse": True,
        "name": "github_sync_log_delivery_user"
    },
    # Admin queries — find recent sync history for an org
    {
        "keys": [("org_id", 1), ("created_at", -1)],
        "name": "github_sync_log_org_time"
    },
    # User queries — find sync history for a specific user
    {
        "keys": [("org_id", 1), ("affected_user_id", 1), ("created_at", -1)],
        "sparse": True,
        "name": "github_sync_log_user_time"
    },
    # Cleanup — TTL index for 90-day retention
    {
        "keys": [("created_at", 1)],
        "expireAfterSeconds": 90 * 24 * 60 * 60,  # 90 days
        "name": "github_sync_log_ttl"
    }
]


# =============================================================================
# MEMBERSHIP EXTENSION FIELDS (for documentation)
# =============================================================================

# These fields extend existing memberships collection documents.
# All fields are optional — existing documents without these fields continue to function.
MEMBERSHIP_GITHUB_SYNC_FIELDS = {
    "github_login": "str | None",           # GitHub username linked to this member
    "github_org_role": "str | None",        # Raw GitHub role ("owner", "member", "outside_collaborator")
    "github_derived_role": "str | None",    # Computed InDE role from GitHub (before human floor)
    "github_sync_source": "str | None",     # "initial_sync" | "webhook" | "manual"
    "github_synced_at": "datetime | None",  # Timestamp of last GitHub sync for this member
    "github_unlinked": "bool",              # True if removed from GitHub org (pending admin review)
    "github_unlinked_at": "datetime | None", # When unlink was detected
    "human_set_role": "str | None",         # Role explicitly set by human admin (the floor)
    "human_set_at": "datetime | None",      # When human admin last set the role
    "human_set_by": "str | None",           # Who set the human role
    "effective_role": "str",                # max(github_derived_role, human_set_role) — what RBAC uses
}


def ensure_github_sync_indexes(db):
    """
    Create indexes for github_sync_log collection.

    Called at startup in CINDE mode. Idempotent (safe to call multiple times).

    Args:
        db: MongoDB database instance
    """
    collection = db.github_sync_log

    for index_def in GITHUB_SYNC_LOG_INDEXES:
        keys = index_def["keys"]
        options = {k: v for k, v in index_def.items() if k != "keys"}
        try:
            collection.create_index(keys, **options, background=True)
        except Exception as e:
            # Index may already exist with different options
            import logging
            logging.getLogger("inde.models.github_sync_log").warning(
                f"Could not create index {index_def.get('name', keys)}: {e}"
            )


def ensure_github_sync_status_indexes(db):
    """
    Create indexes for github_sync_status collection.

    Args:
        db: MongoDB database instance
    """
    collection = db.github_sync_status

    try:
        collection.create_index([("org_id", 1)], unique=True, background=True)
    except Exception:
        pass
