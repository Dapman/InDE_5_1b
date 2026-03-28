"""
InDE MVP v5.1b.0 - Pursuit-Repo Link and Activity Signal Models

Schema definitions for pursuit-repo linkage and GitHub activity signals.
Supports IDTFS Pillar 1/2 signal ingestion and Layer 2 RBAC activation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


# =============================================================================
# PURSUIT-REPO LINK SCHEMA
# =============================================================================

@dataclass
class PursuitRepoLink:
    """
    Represents a formal link between an InDE pursuit and a GitHub repository.

    Design invariants:
    - Linkage is always explicit (no heuristic or auto-link)
    - One active primary repo per pursuit (enforced by PursuitRepoLinker)
    - Soft delete only (is_active=False), never hard delete
    """
    org_id: str
    pursuit_id: str
    github_repo_full_name: str  # "{owner}/{repo}"
    github_repo_id: int  # GitHub numeric repo ID (stable across renames)
    is_primary: bool  # True = drives Layer 2 RBAC
    linked_by: str  # user_id who created the link
    linked_at: datetime
    is_active: bool = True
    signal_capture_enabled: bool = True
    unlinked_at: Optional[datetime] = None
    unlinked_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document."""
        doc = {
            "org_id": self.org_id,
            "pursuit_id": self.pursuit_id,
            "github_repo_full_name": self.github_repo_full_name,
            "github_repo_id": self.github_repo_id,
            "is_primary": self.is_primary,
            "linked_by": self.linked_by,
            "linked_at": self.linked_at,
            "is_active": self.is_active,
            "signal_capture_enabled": self.signal_capture_enabled,
            "unlinked_at": self.unlinked_at,
            "unlinked_by": self.unlinked_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self._id:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, doc: Dict[str, Any]) -> "PursuitRepoLink":
        """Create from MongoDB document."""
        return cls(
            _id=str(doc.get("_id")) if doc.get("_id") else None,
            org_id=doc["org_id"],
            pursuit_id=doc["pursuit_id"],
            github_repo_full_name=doc["github_repo_full_name"],
            github_repo_id=doc["github_repo_id"],
            is_primary=doc.get("is_primary", False),
            linked_by=doc["linked_by"],
            linked_at=doc["linked_at"],
            is_active=doc.get("is_active", True),
            signal_capture_enabled=doc.get("signal_capture_enabled", True),
            unlinked_at=doc.get("unlinked_at"),
            unlinked_by=doc.get("unlinked_by"),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )


# =============================================================================
# GITHUB ACTIVITY SIGNAL SCHEMA
# =============================================================================

@dataclass
class GithubActivitySignal:
    """
    Append-only record of GitHub activity attributed to InDE innovators.

    This is the Pillar 1/2 data source for IDTFS discovery engine.

    Design invariants:
    - Append-only (never overwritten or deleted)
    - Idempotent (delivery_id + signal_type is unique)
    - user_id can be None if github_login not yet linked
    """
    org_id: str
    github_login: str
    signal_type: str  # push_commit | pr_opened | pr_merged | pr_reviewed | team_added | team_removed
    repo_full_name: str
    github_repo_id: int
    github_delivery_id: str
    occurred_at: datetime
    event_metadata: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    pursuit_id: Optional[str] = None
    is_primary_repo: Optional[bool] = None
    ingested_at: datetime = field(default_factory=datetime.utcnow)
    _id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document."""
        doc = {
            "org_id": self.org_id,
            "user_id": self.user_id,
            "github_login": self.github_login,
            "signal_type": self.signal_type,
            "repo_full_name": self.repo_full_name,
            "github_repo_id": self.github_repo_id,
            "pursuit_id": self.pursuit_id,
            "is_primary_repo": self.is_primary_repo,
            "github_delivery_id": self.github_delivery_id,
            "event_metadata": self.event_metadata,
            "occurred_at": self.occurred_at,
            "ingested_at": self.ingested_at,
        }
        if self._id:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, doc: Dict[str, Any]) -> "GithubActivitySignal":
        """Create from MongoDB document."""
        return cls(
            _id=str(doc.get("_id")) if doc.get("_id") else None,
            org_id=doc["org_id"],
            user_id=doc.get("user_id"),
            github_login=doc["github_login"],
            signal_type=doc["signal_type"],
            repo_full_name=doc["repo_full_name"],
            github_repo_id=doc["github_repo_id"],
            pursuit_id=doc.get("pursuit_id"),
            is_primary_repo=doc.get("is_primary_repo"),
            github_delivery_id=doc["github_delivery_id"],
            event_metadata=doc.get("event_metadata", {}),
            occurred_at=doc["occurred_at"],
            ingested_at=doc.get("ingested_at", datetime.utcnow()),
        )


# =============================================================================
# SIGNAL TYPES
# =============================================================================

SIGNAL_TYPES = [
    "push_commit",
    "pr_opened",
    "pr_merged",
    "pr_reviewed",
    "team_added",
    "team_removed",
]


# =============================================================================
# PILLAR 1 SIGNAL STRENGTH COMPUTATION
# =============================================================================

def compute_signal_strength(signal_count_90d: int) -> str:
    """
    Compute Pillar 1 signal strength from 90-day activity count.

    Returns: "strong" | "moderate" | "weak" | "none"
    """
    if signal_count_90d >= 10:
        return "strong"
    elif signal_count_90d >= 4:
        return "moderate"
    elif signal_count_90d >= 1:
        return "weak"
    else:
        return "none"


# =============================================================================
# INDEX DEFINITIONS
# =============================================================================

PURSUIT_REPO_LINKS_INDEXES = [
    # Primary lookup: find all active links for a pursuit
    {
        "keys": [("org_id", 1), ("pursuit_id", 1), ("is_active", 1)],
        "name": "idx_pursuit_links_active",
    },
    # Webhook routing: given a GitHub repo, find all linked pursuits
    {
        "keys": [("org_id", 1), ("github_repo_id", 1), ("is_active", 1)],
        "name": "idx_repo_pursuit_links",
    },
    # Idempotency: prevent duplicate active links for the same pursuit+repo
    {
        "keys": [("org_id", 1), ("pursuit_id", 1), ("github_repo_id", 1), ("is_active", 1)],
        "name": "idx_unique_active_link",
        "unique": True,
        "partialFilterExpression": {"is_active": True},
    },
]

GITHUB_ACTIVITY_SIGNALS_INDEXES = [
    # Idempotency: one signal record per delivery per event type
    {
        "keys": [("github_delivery_id", 1), ("signal_type", 1)],
        "name": "idx_signal_idempotency",
        "unique": True,
    },
    # IDTFS queries: activity by user within org
    {
        "keys": [("org_id", 1), ("user_id", 1), ("occurred_at", -1)],
        "name": "idx_user_activity",
    },
    # IDTFS queries: activity by pursuit
    {
        "keys": [("org_id", 1), ("pursuit_id", 1), ("signal_type", 1), ("occurred_at", -1)],
        "name": "idx_pursuit_activity",
    },
    # Unlinked signal resolution: when a GitHub login gets linked to an InDE user
    {
        "keys": [("org_id", 1), ("github_login", 1), ("user_id", 1)],
        "name": "idx_unlinked_signals",
        "partialFilterExpression": {"user_id": None},
    },
]


async def ensure_indexes(db):
    """
    Create indexes for pursuit_repo_links and github_activity_signals collections.
    Safe to call multiple times (idempotent).
    """
    # Pursuit-repo links indexes
    for idx_def in PURSUIT_REPO_LINKS_INDEXES:
        try:
            await db.pursuit_repo_links.create_index(
                idx_def["keys"],
                name=idx_def["name"],
                unique=idx_def.get("unique", False),
                partialFilterExpression=idx_def.get("partialFilterExpression"),
                background=True,
            )
        except Exception:
            # Index may already exist with same definition
            pass

    # GitHub activity signals indexes
    for idx_def in GITHUB_ACTIVITY_SIGNALS_INDEXES:
        try:
            await db.github_activity_signals.create_index(
                idx_def["keys"],
                name=idx_def["name"],
                unique=idx_def.get("unique", False),
                partialFilterExpression=idx_def.get("partialFilterExpression"),
                background=True,
            )
        except Exception:
            pass
