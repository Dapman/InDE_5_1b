"""
Share Link Service

InDE MVP v4.5.0 — The Engagement Engine

Manages time-limited shareable artifact links with view tracking.
Uses a new MongoDB collection: shared_artifact_links.

The shared view contains ONLY the artifact content — no coaching context,
no system state, no internal metadata. The viewer sees a clean, branded
read-only page.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ShareLinkService:
    """
    Creates, retrieves, and tracks shareable artifact links.

    The shared view contains ONLY the artifact content — no coaching context,
    no system state, no internal metadata. The viewer sees a clean, branded
    read-only page.
    """

    COLLECTION = "shared_artifact_links"

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access
        """
        self.db = db
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create TTL index for automatic link expiration and token index."""
        try:
            collection = self.db.db[self.COLLECTION]
            # TTL index for automatic expiration
            collection.create_index("expires_at", expireAfterSeconds=0)
            # Unique index on token for fast lookup
            collection.create_index("token", unique=True)
            logger.debug("shared_artifact_links indexes created")
        except Exception as e:
            logger.warning(f"Index creation skipped: {e}")

    def create(self, token: str, pursuit_id: str, artifact_type: str,
               artifact_content: str, artifact_title: str,
               pursuit_title: str, artifact_label: str,
               innovator_name: str, expires_at: datetime) -> None:
        """
        Store a new shareable link.

        Args:
            token: Unique URL-safe token for this share link
            pursuit_id: Source pursuit ID (for analytics only)
            artifact_type: Type of artifact being shared
            artifact_content: The actual content to display
            artifact_title: Title of the artifact
            pursuit_title: Title of the pursuit
            artifact_label: Innovator-facing label for the artifact type
            innovator_name: Name of the creator (optional)
            expires_at: When this link expires
        """
        self.db.db[self.COLLECTION].insert_one({
            "token": token,
            "pursuit_id": pursuit_id,
            "artifact_type": artifact_type,
            "artifact_content": artifact_content,
            "artifact_title": artifact_title,
            "pursuit_title": pursuit_title,
            "artifact_label": artifact_label,
            "innovator_name": innovator_name,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "view_count": 0,
            "unique_viewers": [],
            "last_viewed_at": None,
        })
        logger.info(f"Share link created: {token[:8]}... for {artifact_type}")

    def get_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve shared artifact by token and increment view count.

        Args:
            token: The share link token

        Returns:
            dict with artifact data if found, None if expired or invalid
        """
        result = self.db.db[self.COLLECTION].find_one_and_update(
            {"token": token},
            {
                "$inc": {"view_count": 1},
                "$set": {"last_viewed_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )

        if result:
            logger.debug(f"Share link viewed: {token[:8]}... (count: {result.get('view_count')})")

        return result

    def get_link_analytics(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get view analytics for a shared link (for the link creator).

        Args:
            token: The share link token

        Returns:
            dict with analytics or None if not found
        """
        doc = self.db.db[self.COLLECTION].find_one({"token": token})
        if not doc:
            return None

        return {
            "token": token,
            "artifact_type": doc.get("artifact_type"),
            "pursuit_title": doc.get("pursuit_title"),
            "view_count": doc.get("view_count", 0),
            "created_at": doc.get("created_at"),
            "expires_at": doc.get("expires_at"),
            "last_viewed_at": doc.get("last_viewed_at"),
        }

    def get_links_for_pursuit(self, pursuit_id: str) -> list:
        """
        Get all active share links for a pursuit.

        Args:
            pursuit_id: The pursuit ID

        Returns:
            List of share link analytics dicts
        """
        docs = self.db.db[self.COLLECTION].find({"pursuit_id": pursuit_id})
        return [
            {
                "token": doc.get("token"),
                "artifact_type": doc.get("artifact_type"),
                "view_count": doc.get("view_count", 0),
                "created_at": doc.get("created_at"),
                "expires_at": doc.get("expires_at"),
                "last_viewed_at": doc.get("last_viewed_at"),
            }
            for doc in docs
        ]

    def revoke_link(self, token: str) -> bool:
        """
        Revoke (delete) a share link before its expiration.

        Args:
            token: The share link token

        Returns:
            True if link was deleted, False if not found
        """
        result = self.db.db[self.COLLECTION].delete_one({"token": token})
        if result.deleted_count > 0:
            logger.info(f"Share link revoked: {token[:8]}...")
            return True
        return False
