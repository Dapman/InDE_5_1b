"""
InDE MVP v5.1b.0 - Base Connector Interface

Defines the abstract base class for all enterprise connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class ConnectorStatus(str, Enum):
    """Status of a connector installation."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    UNINSTALLED = "UNINSTALLED"


class HealthStatus(str, Enum):
    """Health status for connector connection."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class ConnectorMeta:
    """Metadata about an available connector."""
    slug: str
    display_name: str
    description: str
    required_scopes: List[str]
    webhook_events: List[str]
    is_stub: bool = False  # True for placeholder connectors (Slack, Atlassian)


@dataclass
class ConnectorInstallation:
    """Record of a connector installation for an org."""
    id: str
    org_id: str
    connector_slug: str
    status: ConnectorStatus
    installed_at: datetime
    installed_by: str
    last_active: Optional[datetime] = None
    uninstalled_at: Optional[datetime] = None
    uninstalled_by: Optional[str] = None
    # Connector-specific fields stored separately
    metadata: dict = field(default_factory=dict)


@dataclass
class ConnectorHealth:
    """Health check result for a connector."""
    status: HealthStatus
    last_checked: datetime
    message: Optional[str] = None
    last_successful_call: Optional[datetime] = None
    error_count: int = 0


class BaseConnector(ABC):
    """
    Abstract base class for all enterprise connectors.

    Each connector must implement OAuth flow, webhook handling,
    and health checking. Connectors are CINDE-only.
    """

    # Connector identification
    slug: str
    display_name: str
    description: str = ""
    required_scopes: List[str] = []
    webhook_events: List[str] = []

    def __init__(self, db, event_publisher=None):
        """
        Initialize the connector with database access.

        Args:
            db: MongoDB database instance
            event_publisher: Optional event publisher for audit events
        """
        self.db = db
        self.event_publisher = event_publisher

    def get_meta(self) -> ConnectorMeta:
        """Return connector metadata."""
        return ConnectorMeta(
            slug=self.slug,
            display_name=self.display_name,
            description=self.description,
            required_scopes=self.required_scopes,
            webhook_events=self.webhook_events,
            is_stub=False
        )

    @abstractmethod
    async def initiate_oauth(self, org_id: str, admin_user_id: str) -> str:
        """
        Initiate OAuth flow for connector installation.

        Args:
            org_id: The InDE organization ID
            admin_user_id: The user ID of the admin initiating installation

        Returns:
            The OAuth redirect URL
        """
        pass

    @abstractmethod
    async def handle_oauth_callback(self, code: str, state: str) -> ConnectorInstallation:
        """
        Handle OAuth callback and complete installation.

        Args:
            code: OAuth authorization code
            state: State parameter for validation

        Returns:
            The created ConnectorInstallation record

        Raises:
            ValueError: If state is invalid or expired
        """
        pass

    @abstractmethod
    async def handle_webhook(self, event_type: str, payload: dict, delivery_id: str) -> None:
        """
        Process a verified webhook event.

        Must be idempotent - duplicate delivery IDs should be silently handled.

        Args:
            event_type: The webhook event type
            payload: The webhook payload (already verified)
            delivery_id: Unique delivery ID for idempotency
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: Signature header value

        Returns:
            True if signature is valid
        """
        pass

    @abstractmethod
    async def health_check(self, org_id: str) -> ConnectorHealth:
        """
        Check connection health for an org's installation.

        Args:
            org_id: The InDE organization ID

        Returns:
            ConnectorHealth with current status
        """
        pass

    async def uninstall(self, org_id: str, admin_user_id: str) -> None:
        """
        Uninstall the connector for an organization.

        Args:
            org_id: The InDE organization ID
            admin_user_id: The user ID of the admin uninstalling
        """
        now = datetime.utcnow()
        self.db.connector_installations.update_one(
            {"org_id": org_id, "connector_slug": self.slug, "status": {"$ne": "UNINSTALLED"}},
            {
                "$set": {
                    "status": ConnectorStatus.UNINSTALLED.value,
                    "uninstalled_at": now,
                    "uninstalled_by": admin_user_id
                }
            }
        )

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("connector.uninstalled", {
                "connector_slug": self.slug,
                "org_id": org_id,
                "uninstalled_by": admin_user_id,
                "timestamp": now.isoformat()
            })

    async def get_installation(self, org_id: str) -> Optional[ConnectorInstallation]:
        """
        Get the current installation for an org.

        Args:
            org_id: The InDE organization ID

        Returns:
            ConnectorInstallation if installed, None otherwise
        """
        doc = self.db.connector_installations.find_one({
            "org_id": org_id,
            "connector_slug": self.slug,
            "status": {"$ne": ConnectorStatus.UNINSTALLED.value}
        })

        if not doc:
            return None

        return ConnectorInstallation(
            id=str(doc["_id"]),
            org_id=doc["org_id"],
            connector_slug=doc["connector_slug"],
            status=ConnectorStatus(doc["status"]),
            installed_at=doc["installed_at"],
            installed_by=doc["installed_by"],
            last_active=doc.get("last_active"),
            uninstalled_at=doc.get("uninstalled_at"),
            uninstalled_by=doc.get("uninstalled_by"),
            metadata=doc.get("metadata", {})
        )
