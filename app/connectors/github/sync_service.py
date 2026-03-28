"""
InDE MVP v5.1b.0 - GitHub Sync Service

Orchestrates initial sync and delta sync operations.
Provides sync status tracking and background task management.
"""

import logging
import uuid
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("inde.connectors.github.sync_service")


@dataclass
class SyncStatus:
    """Status of sync operations for an organization."""
    org_id: str
    last_sync_at: Optional[datetime]
    last_sync_id: Optional[str]
    last_sync_status: Optional[str]  # "SUCCESS" | "PARTIAL" | "FAILED" | "IN_PROGRESS"
    synced_count: int
    pending_count: int
    floor_applied_count: int
    error_count: int
    sync_in_progress: bool
    current_sync_id: Optional[str] = None


class GitHubSyncService:
    """
    Orchestrates GitHub → InDE RBAC synchronization.

    Manages:
    - Initial sync triggered on connector installation
    - Manual re-sync triggered by admin
    - Sync status tracking
    - Concurrent sync prevention (one sync per org at a time)
    """

    # Track in-progress syncs (org_id -> sync_id)
    _active_syncs: Dict[str, str] = {}

    def __init__(self, db, bridge=None, event_publisher=None):
        """
        Initialize the sync service.

        Args:
            db: MongoDB database instance
            bridge: GitHubRBACBridge instance
            event_publisher: Event publisher for audit events
        """
        self.db = db
        self.bridge = bridge
        self.event_publisher = event_publisher

    def trigger_initial_sync(self, org_id: str) -> str:
        """
        Trigger initial sync for an organization.

        Returns sync_id immediately; sync runs in background.
        Raises ValueError if sync already in progress.

        Args:
            org_id: Organization ID

        Returns:
            sync_id for tracking

        Raises:
            ValueError: If sync already in progress for this org
        """
        if self.is_sync_in_progress(org_id):
            raise ValueError(f"Sync already in progress for org {org_id}")

        sync_id = str(uuid.uuid4())
        self._active_syncs[org_id] = sync_id

        # Log sync started
        self.db.github_sync_log.insert_one({
            "org_id": org_id,
            "event_type": "initial_sync",
            "action": "started",
            "sync_id": sync_id,
            "created_at": datetime.now(timezone.utc)
        })

        logger.info(f"Triggered initial sync for org {org_id}, sync_id={sync_id}")

        return sync_id

    async def run_initial_sync(self, org_id: str, sync_id: str):
        """
        Execute the initial sync (called from background task).

        Args:
            org_id: Organization ID
            sync_id: Sync ID for tracking
        """
        try:
            if not self.bridge:
                raise ValueError("RBAC bridge not configured")

            result = await self.bridge.initial_sync(org_id)

            # Store result
            self.db.github_sync_status.update_one(
                {"org_id": org_id},
                {
                    "$set": {
                        "org_id": org_id,
                        "last_sync_at": result.completed_at,
                        "last_sync_id": sync_id,
                        "last_sync_status": result.status,
                        "synced_count": result.synced_count,
                        "pending_count": result.pending_count,
                        "floor_applied_count": result.floor_applied_count,
                        "error_count": result.error_count,
                        "error_message": result.error_message
                    }
                },
                upsert=True
            )

            logger.info(
                f"Initial sync completed for org {org_id}: "
                f"synced={result.synced_count}, pending={result.pending_count}, "
                f"status={result.status}"
            )

        except Exception as e:
            logger.error(f"Initial sync failed for org {org_id}: {e}")

            # Store failure
            self.db.github_sync_status.update_one(
                {"org_id": org_id},
                {
                    "$set": {
                        "org_id": org_id,
                        "last_sync_at": datetime.now(timezone.utc),
                        "last_sync_id": sync_id,
                        "last_sync_status": "FAILED",
                        "error_message": str(e)
                    }
                },
                upsert=True
            )

        finally:
            # Clear active sync
            self._active_syncs.pop(org_id, None)

    def get_sync_status(self, org_id: str) -> SyncStatus:
        """
        Get sync status for an organization.

        Args:
            org_id: Organization ID

        Returns:
            SyncStatus
        """
        doc = self.db.github_sync_status.find_one({"org_id": org_id})

        sync_in_progress = self.is_sync_in_progress(org_id)
        current_sync_id = self._active_syncs.get(org_id)

        if not doc:
            return SyncStatus(
                org_id=org_id,
                last_sync_at=None,
                last_sync_id=None,
                last_sync_status=None,
                synced_count=0,
                pending_count=0,
                floor_applied_count=0,
                error_count=0,
                sync_in_progress=sync_in_progress,
                current_sync_id=current_sync_id
            )

        return SyncStatus(
            org_id=org_id,
            last_sync_at=doc.get("last_sync_at"),
            last_sync_id=doc.get("last_sync_id"),
            last_sync_status=doc.get("last_sync_status"),
            synced_count=doc.get("synced_count", 0),
            pending_count=doc.get("pending_count", 0),
            floor_applied_count=doc.get("floor_applied_count", 0),
            error_count=doc.get("error_count", 0),
            sync_in_progress=sync_in_progress,
            current_sync_id=current_sync_id
        )

    def is_sync_in_progress(self, org_id: str) -> bool:
        """
        Check if a sync is currently in progress for an organization.

        Args:
            org_id: Organization ID

        Returns:
            True if sync in progress
        """
        return org_id in self._active_syncs

    def complete_sync(self, org_id: str):
        """
        Mark a sync as complete (called when background task finishes).

        Args:
            org_id: Organization ID
        """
        self._active_syncs.pop(org_id, None)

    def get_sync_log(
        self,
        org_id: str,
        limit: int = 50,
        offset: int = 0,
        event_type: str = None
    ) -> tuple[list[Dict[str, Any]], int]:
        """
        Get paginated sync log for an organization.

        Args:
            org_id: Organization ID
            limit: Max records to return
            offset: Records to skip
            event_type: Optional filter by event type

        Returns:
            Tuple of (log_entries, total_count)
        """
        query = {"org_id": org_id}
        if event_type:
            query["event_type"] = event_type

        cursor = self.db.github_sync_log.find(query).sort(
            "created_at", -1
        ).skip(offset).limit(limit)

        entries = list(cursor)
        total = self.db.github_sync_log.count_documents(query)

        # Convert ObjectId to string
        for entry in entries:
            entry["_id"] = str(entry["_id"])

        return entries, total

    async def handle_connector_installed(self, org_id: str):
        """
        Handle connector.installed event - trigger initial sync.

        Args:
            org_id: Organization ID
        """
        try:
            sync_id = self.trigger_initial_sync(org_id)

            # Run sync in background
            asyncio.create_task(self.run_initial_sync(org_id, sync_id))

            logger.info(f"Initial sync triggered on connector installation for org {org_id}")

        except ValueError as e:
            logger.warning(f"Could not trigger initial sync for org {org_id}: {e}")
