"""
InDE MVP v5.1b.0 - Pursuit-Repo Linker Service

Manages the formal linkage between InDE pursuits and GitHub repositories.
Supports 1:N linking with primary designation for Layer 2 RBAC activation.

Design invariants:
- Linkage is always explicit (no heuristic or auto-link)
- One active primary repo per pursuit at all times (enforced transactionally)
- Linkage records are soft-deleted (is_active=False), never hard-deleted
- Never reads coaching, maturity, fear, or pursuit content — validation only
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("inde.connectors.github.pursuit_linker")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class PursuitNotFoundError(Exception):
    """Raised when pursuit_id does not exist or does not belong to org."""
    pass


class RepoNotFoundError(Exception):
    """Raised when GitHub repo cannot be validated via connector."""
    pass


class DuplicateLinkError(Exception):
    """Raised when an active link already exists for pursuit+repo combination."""
    pass


class LinkNotFoundError(Exception):
    """Raised when the requested link does not exist."""
    pass


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class LinkResult:
    """Result of link/unlink/set_primary operations."""
    org_id: str
    pursuit_id: str
    github_repo_id: int
    github_repo_full_name: str
    is_primary: bool
    action: str  # "created" | "unlinked" | "set_primary" | "demoted"
    previous_primary_id: Optional[int] = None
    message: Optional[str] = None


# =============================================================================
# PURSUIT REPO LINKER
# =============================================================================

class PursuitRepoLinker:
    """
    Manages the formal linkage between InDE pursuits and GitHub repositories.

    Design invariants:
    - Linkage is always explicit (no heuristic or auto-link)
    - One active primary repo per pursuit at all times (enforced transactionally)
    - Linkage records are soft-deleted (is_active=False), never hard-deleted
    - Reads pursuit metadata from inde-db to validate pursuit_id exists
    - Never reads coaching, maturity, fear, or pursuit content
    """

    def __init__(self, db, connector=None, event_publisher=None):
        """
        Initialize the linker.

        Args:
            db: MongoDB database instance
            connector: GitHubAppConnector instance (optional, for repo validation)
            event_publisher: Event publisher for audit events
        """
        self.db = db
        self.connector = connector
        self.event_publisher = event_publisher

    async def link_repo(
        self,
        org_id: str,
        pursuit_id: str,
        github_repo_full_name: str,
        github_repo_id: int,
        is_primary: bool,
        linked_by: str
    ) -> LinkResult:
        """
        Create a new pursuit-repo link.

        Validation:
        1. pursuit_id exists and belongs to org_id
        2. No active link already exists for this pursuit+repo combination
        3. If is_primary=True and a primary already exists: demote existing primary

        Args:
            org_id: Organization ID
            pursuit_id: InDE pursuit ID
            github_repo_full_name: "{owner}/{repo}"
            github_repo_id: GitHub numeric repo ID
            is_primary: Whether this is the primary repo for the pursuit
            linked_by: User ID who created the link

        Returns:
            LinkResult with link details

        Raises:
            PursuitNotFoundError: If pursuit doesn't exist in org
            DuplicateLinkError: If active link already exists
        """
        now = datetime.utcnow()

        # Validate pursuit exists in org
        pursuit = self.db.pursuits.find_one({
            "_id": pursuit_id,
            "org_id": org_id,
        })
        if not pursuit:
            # Try with ObjectId
            from bson import ObjectId
            try:
                pursuit = self.db.pursuits.find_one({
                    "_id": ObjectId(pursuit_id),
                    "org_id": org_id,
                })
            except Exception:
                pass

        if not pursuit:
            raise PursuitNotFoundError(f"Pursuit {pursuit_id} not found in org {org_id}")

        # Check for duplicate active link
        existing_link = self.db.pursuit_repo_links.find_one({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        })
        if existing_link:
            raise DuplicateLinkError(
                f"Active link already exists for pursuit {pursuit_id} "
                f"and repo {github_repo_full_name}"
            )

        previous_primary_id = None

        # If setting as primary, demote existing primary first
        if is_primary:
            existing_primary = self.db.pursuit_repo_links.find_one({
                "org_id": org_id,
                "pursuit_id": pursuit_id,
                "is_primary": True,
                "is_active": True,
            })
            if existing_primary:
                previous_primary_id = existing_primary.get("github_repo_id")
                self.db.pursuit_repo_links.update_one(
                    {"_id": existing_primary["_id"]},
                    {
                        "$set": {
                            "is_primary": False,
                            "updated_at": now,
                        }
                    }
                )
                logger.info(
                    f"Demoted previous primary repo {previous_primary_id} "
                    f"for pursuit {pursuit_id}"
                )

        # If this is the first link and not explicitly set as primary, make it primary
        existing_links_count = self.db.pursuit_repo_links.count_documents({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "is_active": True,
        })
        if existing_links_count == 0 and not is_primary:
            is_primary = True
            logger.info(f"Auto-setting first link as primary for pursuit {pursuit_id}")

        # Create the link
        link_doc = {
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "github_repo_full_name": github_repo_full_name,
            "github_repo_id": github_repo_id,
            "is_primary": is_primary,
            "linked_by": linked_by,
            "linked_at": now,
            "is_active": True,
            "signal_capture_enabled": True,
            "unlinked_at": None,
            "unlinked_by": None,
            "created_at": now,
            "updated_at": now,
        }

        result = self.db.pursuit_repo_links.insert_one(link_doc)
        logger.info(
            f"Created pursuit-repo link: pursuit={pursuit_id} "
            f"repo={github_repo_full_name} primary={is_primary}"
        )

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("pursuit_repo_links.created", {
                "org_id": org_id,
                "pursuit_id": pursuit_id,
                "github_repo_full_name": github_repo_full_name,
                "github_repo_id": github_repo_id,
                "is_primary": is_primary,
                "linked_by": linked_by,
                "previous_primary_id": previous_primary_id,
                "timestamp": now.isoformat(),
            })

        return LinkResult(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_id=github_repo_id,
            github_repo_full_name=github_repo_full_name,
            is_primary=is_primary,
            action="created",
            previous_primary_id=previous_primary_id,
            message=f"Link created. Primary={is_primary}.",
        )

    async def unlink_repo(
        self,
        org_id: str,
        pursuit_id: str,
        github_repo_id: int,
        unlinked_by: str
    ) -> LinkResult:
        """
        Soft-delete a pursuit-repo link (set is_active=False).

        If the unlinked repo was primary and other active links exist:
        - Auto-promote the oldest remaining active link to primary
        - Emit pursuit_repo_links.primary_auto_reassigned audit event

        Args:
            org_id: Organization ID
            pursuit_id: InDE pursuit ID
            github_repo_id: GitHub numeric repo ID
            unlinked_by: User ID who unlinked

        Returns:
            LinkResult with unlink details

        Raises:
            LinkNotFoundError: If link doesn't exist
        """
        now = datetime.utcnow()

        # Find the link
        link = self.db.pursuit_repo_links.find_one({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        })

        if not link:
            raise LinkNotFoundError(
                f"No active link found for pursuit {pursuit_id} "
                f"and repo {github_repo_id}"
            )

        was_primary = link.get("is_primary", False)
        github_repo_full_name = link.get("github_repo_full_name", "")

        # Soft delete the link
        self.db.pursuit_repo_links.update_one(
            {"_id": link["_id"]},
            {
                "$set": {
                    "is_active": False,
                    "is_primary": False,
                    "unlinked_at": now,
                    "unlinked_by": unlinked_by,
                    "updated_at": now,
                }
            }
        )
        logger.info(
            f"Unlinked pursuit-repo: pursuit={pursuit_id} "
            f"repo={github_repo_full_name}"
        )

        # If was primary, auto-promote another link
        new_primary_id = None
        if was_primary:
            remaining_links = list(self.db.pursuit_repo_links.find({
                "org_id": org_id,
                "pursuit_id": pursuit_id,
                "is_active": True,
            }).sort("linked_at", 1).limit(1))

            if remaining_links:
                new_primary = remaining_links[0]
                new_primary_id = new_primary.get("github_repo_id")
                self.db.pursuit_repo_links.update_one(
                    {"_id": new_primary["_id"]},
                    {
                        "$set": {
                            "is_primary": True,
                            "updated_at": now,
                        }
                    }
                )
                logger.info(
                    f"Auto-promoted repo {new_primary_id} to primary "
                    f"for pursuit {pursuit_id}"
                )

                # Emit auto-reassign event
                if self.event_publisher:
                    await self.event_publisher.publish(
                        "pursuit_repo_links.primary_auto_reassigned",
                        {
                            "org_id": org_id,
                            "pursuit_id": pursuit_id,
                            "old_primary_repo_id": github_repo_id,
                            "new_primary_repo_id": new_primary_id,
                            "timestamp": now.isoformat(),
                        }
                    )
            else:
                logger.warning(
                    f"Pursuit {pursuit_id} has no remaining linked repos - "
                    f"Layer 2 RBAC will fall back to org-level role only"
                )

        # Emit unlink event
        if self.event_publisher:
            await self.event_publisher.publish("pursuit_repo_links.unlinked", {
                "org_id": org_id,
                "pursuit_id": pursuit_id,
                "github_repo_full_name": github_repo_full_name,
                "github_repo_id": github_repo_id,
                "was_primary": was_primary,
                "new_primary_id": new_primary_id,
                "unlinked_by": unlinked_by,
                "timestamp": now.isoformat(),
            })

        return LinkResult(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_id=github_repo_id,
            github_repo_full_name=github_repo_full_name,
            is_primary=False,
            action="unlinked",
            previous_primary_id=github_repo_id if was_primary else None,
            message=f"Link removed. {'New primary assigned.' if new_primary_id else 'No primary repo remaining.'}",
        )

    async def set_primary(
        self,
        org_id: str,
        pursuit_id: str,
        github_repo_id: int
    ) -> LinkResult:
        """
        Designate a specific linked repo as the primary for a pursuit.
        Atomically demotes the current primary (if any) to is_primary=False.

        Args:
            org_id: Organization ID
            pursuit_id: InDE pursuit ID
            github_repo_id: GitHub repo ID to set as primary

        Returns:
            LinkResult with update details

        Raises:
            LinkNotFoundError: If link doesn't exist
        """
        now = datetime.utcnow()

        # Find the target link
        target_link = self.db.pursuit_repo_links.find_one({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        })

        if not target_link:
            raise LinkNotFoundError(
                f"No active link found for pursuit {pursuit_id} "
                f"and repo {github_repo_id}"
            )

        # Already primary?
        if target_link.get("is_primary"):
            return LinkResult(
                org_id=org_id,
                pursuit_id=pursuit_id,
                github_repo_id=github_repo_id,
                github_repo_full_name=target_link.get("github_repo_full_name", ""),
                is_primary=True,
                action="no_change",
                message="Repo is already the primary.",
            )

        # Demote current primary
        previous_primary_id = None
        existing_primary = self.db.pursuit_repo_links.find_one({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "is_primary": True,
            "is_active": True,
        })
        if existing_primary:
            previous_primary_id = existing_primary.get("github_repo_id")
            self.db.pursuit_repo_links.update_one(
                {"_id": existing_primary["_id"]},
                {
                    "$set": {
                        "is_primary": False,
                        "updated_at": now,
                    }
                }
            )

        # Promote target link
        self.db.pursuit_repo_links.update_one(
            {"_id": target_link["_id"]},
            {
                "$set": {
                    "is_primary": True,
                    "updated_at": now,
                }
            }
        )

        logger.info(
            f"Set primary repo for pursuit {pursuit_id}: "
            f"repo={github_repo_id} (previous={previous_primary_id})"
        )

        # Emit event
        if self.event_publisher:
            await self.event_publisher.publish("pursuit_repo_links.primary_changed", {
                "org_id": org_id,
                "pursuit_id": pursuit_id,
                "github_repo_id": github_repo_id,
                "previous_primary_id": previous_primary_id,
                "timestamp": now.isoformat(),
            })

        return LinkResult(
            org_id=org_id,
            pursuit_id=pursuit_id,
            github_repo_id=github_repo_id,
            github_repo_full_name=target_link.get("github_repo_full_name", ""),
            is_primary=True,
            action="set_primary",
            previous_primary_id=previous_primary_id,
            message=f"Repo set as primary. Previous primary: {previous_primary_id}.",
        )

    async def get_links_for_pursuit(
        self,
        org_id: str,
        pursuit_id: str
    ) -> List[dict]:
        """
        Get all active links for a pursuit, primary first.

        Args:
            org_id: Organization ID
            pursuit_id: InDE pursuit ID

        Returns:
            List of link documents, sorted by is_primary (desc), linked_at (asc)
        """
        cursor = self.db.pursuit_repo_links.find({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "is_active": True,
        }).sort([("is_primary", -1), ("linked_at", 1)])

        return list(cursor)

    async def get_pursuits_for_repo(
        self,
        org_id: str,
        github_repo_id: int
    ) -> List[dict]:
        """
        Webhook routing: given a GitHub repo, return all active pursuit links.

        Used by signal ingestion to attribute activity to the correct pursuits.

        Args:
            org_id: Organization ID
            github_repo_id: GitHub numeric repo ID

        Returns:
            List of link documents
        """
        cursor = self.db.pursuit_repo_links.find({
            "org_id": org_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        })

        return list(cursor)

    async def get_primary_for_pursuit(
        self,
        org_id: str,
        pursuit_id: str
    ) -> Optional[dict]:
        """
        Get the primary repo link for a pursuit.

        Args:
            org_id: Organization ID
            pursuit_id: InDE pursuit ID

        Returns:
            Primary link document, or None if no primary
        """
        return self.db.pursuit_repo_links.find_one({
            "org_id": org_id,
            "pursuit_id": pursuit_id,
            "is_primary": True,
            "is_active": True,
        })
