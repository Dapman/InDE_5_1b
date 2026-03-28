"""
InDE MVP v5.1b.0 - Connector Registry

Central registry for all enterprise connectors.
Singleton pattern - initialized at startup in CINDE mode.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .base import (
    BaseConnector,
    ConnectorMeta,
    ConnectorInstallation,
    ConnectorHealth,
    ConnectorStatus,
    HealthStatus
)

logger = logging.getLogger("inde.connectors.registry")


class ConnectorRegistry:
    """
    Central registry for enterprise connectors.

    Manages connector registration, installation, and status.
    Only active in CINDE deployment mode.
    """

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._stubs: Dict[str, ConnectorMeta] = {}
        self._initialized = False
        self.db = None

    def initialize(self, db, event_publisher=None):
        """
        Initialize the registry with database access.

        Args:
            db: MongoDB database instance
            event_publisher: Optional event publisher for audit events
        """
        self.db = db
        self.event_publisher = event_publisher
        self._initialized = True
        logger.info("Connector registry initialized")

    def register(self, connector: BaseConnector) -> None:
        """
        Register a connector with the registry.

        Args:
            connector: The connector instance to register
        """
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize() first.")

        self._connectors[connector.slug] = connector
        logger.info(f"Registered connector: {connector.slug} ({connector.display_name})")

    def register_stub(self, meta: ConnectorMeta) -> None:
        """
        Register a stub connector (placeholder for future implementation).

        Args:
            meta: Connector metadata
        """
        meta.is_stub = True
        self._stubs[meta.slug] = meta
        logger.info(f"Registered stub connector: {meta.slug}")

    def get(self, slug: str) -> Optional[BaseConnector]:
        """
        Get a connector by slug.

        Args:
            slug: The connector slug (e.g., "github")

        Returns:
            The connector instance, or None if not found
        """
        return self._connectors.get(slug)

    def list_available(self) -> List[ConnectorMeta]:
        """
        List all available connectors (both implemented and stubs).

        Returns:
            List of connector metadata
        """
        available = []

        # Add implemented connectors
        for connector in self._connectors.values():
            available.append(connector.get_meta())

        # Add stub connectors
        for meta in self._stubs.values():
            available.append(meta)

        return available

    def list_installed(self, org_id: str) -> List[ConnectorInstallation]:
        """
        List all installed connectors for an organization.

        Args:
            org_id: The InDE organization ID

        Returns:
            List of connector installations
        """
        if not self.db:
            return []

        cursor = self.db.connector_installations.find({
            "org_id": org_id,
            "status": {"$ne": ConnectorStatus.UNINSTALLED.value}
        })

        installations = []
        for doc in cursor:
            installations.append(ConnectorInstallation(
                id=str(doc["_id"]),
                org_id=doc["org_id"],
                connector_slug=doc["connector_slug"],
                status=ConnectorStatus(doc["status"]),
                installed_at=doc["installed_at"],
                installed_by=doc["installed_by"],
                last_active=doc.get("last_active"),
                metadata=doc.get("metadata", {})
            ))

        return installations

    async def install(
        self,
        slug: str,
        org_id: str,
        initiated_by: str
    ) -> str:
        """
        Initiate connector installation.

        Args:
            slug: The connector slug
            org_id: The InDE organization ID
            initiated_by: User ID of the admin initiating installation

        Returns:
            OAuth redirect URL

        Raises:
            ValueError: If connector not found or is a stub
        """
        connector = self.get(slug)

        if not connector:
            if slug in self._stubs:
                raise ValueError(f"Connector '{slug}' is not yet implemented")
            raise ValueError(f"Connector '{slug}' not found")

        # Check if already installed
        existing = await connector.get_installation(org_id)
        if existing and existing.status == ConnectorStatus.ACTIVE:
            raise ValueError(f"Connector '{slug}' is already installed for this organization")

        return await connector.initiate_oauth(org_id, initiated_by)

    async def uninstall(
        self,
        slug: str,
        org_id: str,
        initiated_by: str
    ) -> None:
        """
        Uninstall a connector.

        Args:
            slug: The connector slug
            org_id: The InDE organization ID
            initiated_by: User ID of the admin uninstalling

        Raises:
            ValueError: If connector not found or not installed
        """
        connector = self.get(slug)

        if not connector:
            raise ValueError(f"Connector '{slug}' not found")

        existing = await connector.get_installation(org_id)
        if not existing:
            raise ValueError(f"Connector '{slug}' is not installed for this organization")

        await connector.uninstall(org_id, initiated_by)

    async def get_status(self, slug: str, org_id: str) -> Optional[ConnectorHealth]:
        """
        Get health status for an installed connector.

        Args:
            slug: The connector slug
            org_id: The InDE organization ID

        Returns:
            ConnectorHealth if installed, None otherwise
        """
        connector = self.get(slug)

        if not connector:
            return None

        existing = await connector.get_installation(org_id)
        if not existing:
            return ConnectorHealth(
                status=HealthStatus.DISCONNECTED,
                last_checked=datetime.utcnow(),
                message="Connector not installed"
            )

        return await connector.health_check(org_id)

    def is_stub(self, slug: str) -> bool:
        """Check if a connector slug is a stub."""
        return slug in self._stubs


# Singleton instance
connector_registry = ConnectorRegistry()
