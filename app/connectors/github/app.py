"""
InDE MVP v5.1b.0 - GitHub App Connector Implementation

Implements BaseConnector for GitHub App OAuth integration.
Full implementation with OAuth flow, token management, and health checks.
"""

import logging
from typing import Optional
from datetime import datetime

from ..base import (
    BaseConnector,
    ConnectorInstallation,
    ConnectorHealth,
    ConnectorStatus,
    HealthStatus
)
from ..crypto import encrypt_token, decrypt_token
from .auth import (
    generate_oauth_state,
    store_oauth_state,
    validate_oauth_state,
    get_github_app_installation_url,
)
from .client import exchange_code_for_installation, GitHubAPIClient

logger = logging.getLogger("inde.connectors.github")


class GitHubAppConnector(BaseConnector):
    """
    GitHub App connector for enterprise integration.

    Provides:
    - OAuth App installation flow
    - Webhook signature verification
    - Organization membership data access
    - Team and repository metadata
    """

    slug = "github"
    display_name = "GitHub"
    description = "Connect your GitHub organization to sync team memberships and roles"
    required_scopes = [
        "members:read",
        "organization_administration:read",
        "metadata:read"
    ]
    webhook_events = [
        "membership",
        "organization",
        "team",
        "team_add",
        "repository"
    ]

    def __init__(self, db, event_publisher=None, config=None):
        """
        Initialize the GitHub connector.

        Args:
            db: MongoDB database instance
            event_publisher: Optional event publisher for audit events
            config: Optional configuration dict
        """
        super().__init__(db, event_publisher)
        self.config = config or {}

    async def initiate_oauth(self, org_id: str, admin_user_id: str) -> str:
        """
        Initiate GitHub App OAuth flow.

        1. Generates a cryptographically random state parameter
        2. Stores state with org_id and admin_user_id in ephemeral collection
        3. Returns GitHub App installation URL with state

        Args:
            org_id: InDE organization ID
            admin_user_id: User ID of admin initiating installation

        Returns:
            GitHub App installation URL
        """
        # Generate secure state
        state = generate_oauth_state()

        # Store state for callback validation
        await store_oauth_state(self.db, state, org_id, admin_user_id)

        # Build installation URL
        install_url = get_github_app_installation_url(state)

        logger.info(f"Initiated GitHub OAuth for org {org_id}")

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("connector.oauth_initiated", {
                "connector_slug": self.slug,
                "org_id": org_id,
                "initiated_by": admin_user_id,
                "timestamp": datetime.utcnow().isoformat()
            })

        return install_url

    async def handle_oauth_callback(self, code: str, state: str) -> ConnectorInstallation:
        """
        Handle GitHub OAuth callback.

        1. Validates state (must exist, not expired, one-time use)
        2. Exchanges code for installation access token
        3. Reads org login from installation payload
        4. Encrypts and stores access token
        5. Creates/updates connector_installations record
        6. Emits audit event

        Args:
            code: OAuth authorization code from GitHub
            state: State parameter for validation

        Returns:
            ConnectorInstallation record

        Raises:
            ValueError: If state is invalid/expired or token exchange fails
        """
        # Validate state
        state_data = await validate_oauth_state(self.db, state)
        if not state_data:
            raise ValueError("Invalid or expired OAuth state")

        org_id, admin_user_id = state_data

        # Exchange code for installation token
        installation_data = await exchange_code_for_installation(code)

        installation_id = installation_data["installation_id"]
        org_login = installation_data["org_login"]
        access_token = installation_data["access_token"]
        token_expires_at = installation_data["expires_at"]

        # Encrypt access token for storage
        encrypted_token = encrypt_token(access_token)

        now = datetime.utcnow()

        # Upsert installation record
        self.db.connector_installations.update_one(
            {
                "org_id": org_id,
                "connector_slug": self.slug,
                "status": {"$ne": ConnectorStatus.UNINSTALLED.value}
            },
            {
                "$set": {
                    "org_id": org_id,
                    "connector_slug": self.slug,
                    "status": ConnectorStatus.ACTIVE.value,
                    "installed_at": now,
                    "installed_by": admin_user_id,
                    "last_active": now,
                    "github_installation_id": installation_id,
                    "github_org_login": org_login,
                    "github_access_token_enc": encrypted_token,
                    "github_token_expires_at": token_expires_at,
                }
            },
            upsert=True
        )

        logger.info(f"GitHub connector installed for org {org_id} (GitHub org: {org_login})")

        # Emit audit event
        if self.event_publisher:
            await self.event_publisher.publish("connector.installed", {
                "connector_slug": self.slug,
                "org_id": org_id,
                "github_org_login": org_login,
                "installed_by": admin_user_id,
                "timestamp": now.isoformat()
            })

        # Return the installation record
        return ConnectorInstallation(
            id="",  # Will be filled by get_installation
            org_id=org_id,
            connector_slug=self.slug,
            status=ConnectorStatus.ACTIVE,
            installed_at=now,
            installed_by=admin_user_id,
            last_active=now,
            metadata={
                "github_installation_id": installation_id,
                "github_org_login": org_login,
            }
        )

    async def handle_webhook(self, event_type: str, payload: dict, delivery_id: str, org_id: str = None) -> str:
        """
        Process a verified GitHub webhook event.

        Routes event to appropriate handler and logs to audit pipeline.

        Args:
            event_type: The webhook event type (e.g., "membership")
            payload: The webhook payload (already verified)
            delivery_id: Unique delivery ID for idempotency
            org_id: Optional InDE organization ID (looked up from installation if not provided)

        Returns:
            Processing result (SUCCESS, SKIPPED, ERROR)
        """
        from .events import process_github_webhook

        return await process_github_webhook(
            db=self.db,
            event_publisher=self.event_publisher,
            org_id=org_id,
            event_type=event_type,
            payload=payload,
            delivery_id=delivery_id
        )

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature using HMAC-SHA256.

        Args:
            payload: Raw webhook payload bytes
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        from .webhooks import verify_webhook_signature
        return verify_webhook_signature(payload, signature)

    async def health_check(self, org_id: str) -> ConnectorHealth:
        """
        Check GitHub connection health.

        Attempts a lightweight API call to verify the installation is still valid.

        Args:
            org_id: InDE organization ID

        Returns:
            ConnectorHealth with current status
        """
        now = datetime.utcnow()

        # Get installation record
        installation = await self.get_installation(org_id)

        if not installation:
            return ConnectorHealth(
                status=HealthStatus.DISCONNECTED,
                last_checked=now,
                message="GitHub connector not installed"
            )

        # Get installation details from DB
        doc = self.db.connector_installations.find_one({
            "org_id": org_id,
            "connector_slug": self.slug,
            "status": ConnectorStatus.ACTIVE.value
        })

        if not doc:
            return ConnectorHealth(
                status=HealthStatus.DISCONNECTED,
                last_checked=now,
                message="Installation record not found"
            )

        installation_id = doc.get("github_installation_id")
        if not installation_id:
            return ConnectorHealth(
                status=HealthStatus.DEGRADED,
                last_checked=now,
                message="Installation ID missing"
            )

        # Try to get installation info from GitHub
        try:
            client = GitHubAPIClient(installation_id)
            try:
                install_info = await client.get_installation()

                # Update last_active
                self.db.connector_installations.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"last_active": now}}
                )

                return ConnectorHealth(
                    status=HealthStatus.HEALTHY,
                    last_checked=now,
                    message=f"Connected to {install_info.get('account', {}).get('login', 'unknown')}",
                    last_successful_call=now
                )
            finally:
                await client.close()

        except Exception as e:
            logger.warning(f"GitHub health check failed for org {org_id}: {e}")
            return ConnectorHealth(
                status=HealthStatus.DEGRADED,
                last_checked=now,
                message=f"API call failed: {str(e)}",
                error_count=1
            )

    async def get_decrypted_token(self, org_id: str) -> Optional[str]:
        """
        Get decrypted access token for an organization's installation.

        Args:
            org_id: InDE organization ID

        Returns:
            Decrypted access token, or None if not installed
        """
        doc = self.db.connector_installations.find_one({
            "org_id": org_id,
            "connector_slug": self.slug,
            "status": ConnectorStatus.ACTIVE.value
        })

        if not doc or not doc.get("github_access_token_enc"):
            return None

        return decrypt_token(doc["github_access_token_enc"])

    async def get_api_client(self, org_id: str) -> Optional[GitHubAPIClient]:
        """
        Get an authenticated API client for an organization.

        Args:
            org_id: InDE organization ID

        Returns:
            GitHubAPIClient instance, or None if not installed
        """
        doc = self.db.connector_installations.find_one({
            "org_id": org_id,
            "connector_slug": self.slug,
            "status": ConnectorStatus.ACTIVE.value
        })

        if not doc:
            return None

        installation_id = doc.get("github_installation_id")
        if not installation_id:
            return None

        # Decrypt token if available
        token = None
        token_expires = None
        if doc.get("github_access_token_enc"):
            token = decrypt_token(doc["github_access_token_enc"])
            token_expires = doc.get("github_token_expires_at")

        return GitHubAPIClient(
            installation_id=installation_id,
            access_token=token,
            token_expires_at=token_expires
        )
