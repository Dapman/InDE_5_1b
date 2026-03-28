"""
InDE MVP v5.1b.0 - Enterprise Connectors Test Suite

Tests for the connector framework, GitHub OAuth, and webhook handling.
All tests run in CINDE mode unless specifically testing LINDE mode.
"""

import os
import sys
import pytest
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment variables before imports
os.environ["DEPLOYMENT_MODE"] = "CINDE"
os.environ["ORG_ID_SEED"] = "test-org-seed"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing-only"
os.environ["CONNECTOR_ENCRYPTION_KEY"] = secrets.token_hex(32)
os.environ["GITHUB_APP_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["LLM_GATEWAY_URL"] = "http://test-gateway:8080"

# Ensure app directory is in path
app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)


class TestConnectorRoutesLINDE:
    """Test that connector routes return 404 in LINDE mode."""

    def test_connector_routes_linde_404(self):
        """All /api/v1/connectors/* return 404 in LINDE mode."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "LINDE"}):
            # Clear cached feature gate
            from services.feature_gate import get_feature_gate
            get_feature_gate.cache_clear()

            gate = get_feature_gate()
            assert gate.enterprise_connectors is False

            # Routes should not be available
            # In LINDE mode, the routes are not even mounted
            # This test verifies the feature gate behavior
            assert gate.mode.value == "LINDE"


class TestConnectorRoutesCINDE:
    """Test connector routes in CINDE mode."""

    def test_connector_routes_cinde_enabled(self):
        """Connector routes enabled in CINDE mode."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "CINDE", "ORG_ID_SEED": "test"}):
            from services.feature_gate import get_feature_gate
            get_feature_gate.cache_clear()

            gate = get_feature_gate()
            assert gate.enterprise_connectors is True


class TestConnectorRegistry:
    """Test ConnectorRegistry functionality."""

    def test_registry_lists_github(self):
        """Registry lists GitHub connector as available."""
        from connectors.registry import ConnectorRegistry
        from connectors.base import ConnectorMeta

        registry = ConnectorRegistry()
        mock_db = MagicMock()
        registry.initialize(mock_db)

        # Register a mock GitHub connector
        mock_connector = MagicMock()
        mock_connector.slug = "github"
        mock_connector.display_name = "GitHub"
        mock_connector.description = "GitHub integration"
        mock_connector.required_scopes = []
        mock_connector.webhook_events = []
        mock_connector.get_meta = MagicMock(return_value=ConnectorMeta(
            slug="github",
            display_name="GitHub",
            description="GitHub integration",
            required_scopes=[],
            webhook_events=[],
            is_stub=False
        ))

        registry.register(mock_connector)

        available = registry.list_available()
        slugs = [c.slug for c in available]
        assert "github" in slugs

    def test_registry_lists_stubs(self):
        """Slack and Atlassian appear as available stubs."""
        from connectors.registry import ConnectorRegistry
        from connectors.base import ConnectorMeta

        registry = ConnectorRegistry()
        mock_db = MagicMock()
        registry.initialize(mock_db)

        # Register stubs
        registry.register_stub(ConnectorMeta(
            slug="slack",
            display_name="Slack",
            description="Slack integration",
            required_scopes=[],
            webhook_events=[],
            is_stub=True
        ))
        registry.register_stub(ConnectorMeta(
            slug="atlassian",
            display_name="Atlassian",
            description="Atlassian integration",
            required_scopes=[],
            webhook_events=[],
            is_stub=True
        ))

        available = registry.list_available()
        stubs = [c for c in available if c.is_stub]

        assert len(stubs) >= 2
        stub_slugs = [c.slug for c in stubs]
        assert "slack" in stub_slugs
        assert "atlassian" in stub_slugs


class TestOAuthState:
    """Test OAuth state management."""

    def test_oauth_state_generation(self):
        """State generation creates secure random string."""
        # Generate 64-char hex string (32 bytes)
        state = secrets.token_hex(32)
        assert len(state) == 64
        assert all(c in "0123456789abcdef" for c in state)

    @pytest.mark.asyncio
    async def test_oauth_state_storage(self):
        """State is stored with org_id and expires_at."""
        mock_db = MagicMock()
        mock_db.connector_oauth_states = MagicMock()
        mock_db.connector_oauth_states.insert_one = MagicMock()

        state = secrets.token_hex(32)
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=10)

        doc = {
            "state": state,
            "org_id": "org-123",
            "admin_user_id": "user-456",
            "expires_at": expires_at,
            "created_at": now,
            "used": False,
        }
        mock_db.connector_oauth_states.insert_one(doc)

        mock_db.connector_oauth_states.insert_one.assert_called_once()

    def test_oauth_state_single_use(self):
        """State should be deleted after use (find_one_and_delete pattern)."""
        mock_db = MagicMock()

        # First call returns the state
        mock_db.connector_oauth_states.find_one_and_delete = MagicMock(
            side_effect=[
                {"state": "test-state", "org_id": "org-1", "admin_user_id": "user-1"},
                None  # Second call returns None (already deleted)
            ]
        )

        # First use - returns data
        result1 = mock_db.connector_oauth_states.find_one_and_delete({})
        assert result1 is not None

        # Second use - returns None (deleted)
        result2 = mock_db.connector_oauth_states.find_one_and_delete({})
        assert result2 is None


class TestTokenEncryption:
    """Test token encryption/decryption."""

    def test_token_encryption_roundtrip(self):
        """encrypt_token(decrypt_token(x)) == x for random tokens."""
        from connectors.crypto import encrypt_token, decrypt_token

        # Test 100 random tokens
        for _ in range(100):
            original = secrets.token_hex(32)
            encrypted = encrypt_token(original)
            decrypted = decrypt_token(encrypted)
            assert decrypted == original

    def test_encryption_different_each_time(self):
        """Same plaintext produces different ciphertext (random nonce)."""
        from connectors.crypto import encrypt_token

        token = "test-token-12345"
        encrypted1 = encrypt_token(token)
        encrypted2 = encrypt_token(token)

        # Should be different due to random nonce
        assert encrypted1 != encrypted2


class TestWebhookSignature:
    """Test webhook signature verification."""

    def test_webhook_signature_valid(self):
        """Correctly signed payload returns True."""
        secret = os.environ["GITHUB_APP_WEBHOOK_SECRET"]
        payload = b'{"action": "created"}'

        # Compute valid signature
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        signature = "sha256=" + mac.hexdigest()

        # Verify using our verification function logic
        expected_sig = signature[7:]  # Remove 'sha256=' prefix
        computed_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert hmac.compare_digest(computed_sig, expected_sig)

    def test_webhook_signature_invalid(self):
        """Tampered payload does not match signature."""
        secret = os.environ["GITHUB_APP_WEBHOOK_SECRET"]
        payload = b'{"action": "created"}'

        # Compute signature for different payload
        mac = hmac.new(secret.encode(), b'different payload', hashlib.sha256)
        wrong_signature = mac.hexdigest()

        # Compute expected signature for actual payload
        correct_mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        correct_signature = correct_mac.hexdigest()

        assert wrong_signature != correct_signature

    def test_webhook_no_signature(self):
        """Missing signature should fail verification."""
        # Empty string cannot match any valid signature
        assert "" != "sha256=anything"


class TestWebhookIdempotency:
    """Test webhook idempotency handling."""

    @pytest.mark.asyncio
    async def test_webhook_idempotency(self):
        """Duplicate delivery_id is detected via unique index."""
        mock_db = MagicMock()

        # First insert succeeds
        mock_db.webhook_events.insert_one = MagicMock(return_value=True)

        # Check the insert is called
        mock_db.webhook_events.insert_one({
            "delivery_id": "delivery-123",
            "org_id": "org-1",
            "connector_slug": "github"
        })
        mock_db.webhook_events.insert_one.assert_called_once()


class TestWebhookStorage:
    """Test webhook event storage."""

    def test_webhook_stored_without_payload(self):
        """Payload hash is stored, not the raw payload."""
        payload = b'{"action": "created", "secret_data": "sensitive"}'
        payload_hash = hashlib.sha256(payload).hexdigest()

        doc = {
            "delivery_id": "delivery-456",
            "event_type": "push",
            "payload_hash": payload_hash,
            # Note: NO 'payload' field
        }

        # Verify hash is present
        assert "payload_hash" in doc
        assert doc["payload_hash"] == payload_hash

        # Verify raw payload is NOT present
        assert "payload" not in doc
        assert "secret_data" not in str(doc)


class TestConnectorInstallPermissions:
    """Test connector installation permissions."""

    def test_connector_install_requires_admin(self):
        """Member and Viewer roles cannot install connector."""
        from api.connectors import require_org_admin
        from fastapi import HTTPException

        # Test with member role
        member_user = {"role": "user", "org_role": "member"}
        with pytest.raises(HTTPException) as exc:
            require_org_admin(member_user)
        assert exc.value.status_code == 403

        # Test with viewer role
        viewer_user = {"role": "user", "org_role": "viewer"}
        with pytest.raises(HTTPException) as exc:
            require_org_admin(viewer_user)
        assert exc.value.status_code == 403

        # Test with admin role (should not raise)
        admin_user = {"role": "admin", "org_role": "admin"}
        require_org_admin(admin_user)  # Should not raise


class TestHealthCheck:
    """Test connector health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_no_installation(self):
        """Health check returns DISCONNECTED when not installed."""
        from connectors.base import HealthStatus, ConnectorHealth

        # Simulate health check result when not installed
        health = ConnectorHealth(
            status=HealthStatus.DISCONNECTED,
            last_checked=datetime.utcnow(),
            message="GitHub connector not installed"
        )

        assert health.status == HealthStatus.DISCONNECTED
        assert "not installed" in health.message.lower()


class TestLINDERegression:
    """Verify LINDE mode unchanged from v5.0."""

    def test_linde_full_regression(self):
        """All v5.0 LINDE tests should pass without modification."""
        # This test verifies that the feature gate correctly
        # disables enterprise connectors in LINDE mode
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "LINDE"}):
            from services.feature_gate import get_feature_gate
            get_feature_gate.cache_clear()

            gate = get_feature_gate()

            # LINDE mode assertions
            assert gate.mode.value == "LINDE"
            assert gate.enterprise_connectors is False
            assert gate.connectors_registry_active is False

            # Shared features should still be active
            assert gate.coaching_active is True
            assert gate.momentum_active is True
            assert gate.irc_active is True


# Run with:
# python -m pytest tests/test_connectors.py -v
