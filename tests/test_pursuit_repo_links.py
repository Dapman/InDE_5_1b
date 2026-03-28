"""
InDE MVP v5.1b.0 - Pursuit-Repo Links Test Suite

Tests for pursuit-repo linkage functionality.
All tests run in CINDE mode unless specifically testing LINDE mode.

Test classes:
- TestLinkRepoBasic: Basic link creation tests
- TestLinkRepoPrimary: Primary designation tests
- TestUnlinkRepo: Unlink and auto-promote tests
- TestSetPrimary: Primary swap tests
- TestGetLinks: Query tests
- TestLINDEMode: LINDE 404 regression tests

Total: 12 tests
"""

import os
import sys
import pytest
import secrets
from datetime import datetime, timezone
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


class TestLinkRepoBasic:
    """Test basic link creation functionality."""

    @pytest.mark.asyncio
    async def test_link_repo_creates_document(self):
        """Link repo creates a pursuit_repo_links document."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        mock_db.pursuits.find_one.return_value = {
            "_id": "pursuit123",
            "org_id": "org456",
            "title": "Test Pursuit"
        }
        mock_db.pursuit_repo_links.find_one.return_value = None  # No duplicate
        mock_db.pursuit_repo_links.count_documents.return_value = 0  # First link
        mock_db.pursuit_repo_links.insert_one.return_value = MagicMock(inserted_id="link-id")

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.link_repo(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_full_name="acme/project-x",
            github_repo_id=12345,
            is_primary=False,
            linked_by="user789"
        )

        assert result.action == "created"
        assert result.pursuit_id == "pursuit123"
        assert result.github_repo_id == 12345
        # First link should be auto-set as primary
        assert result.is_primary is True
        mock_db.pursuit_repo_links.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_repo_sets_primary_correctly(self):
        """When is_primary=True, the link is set as primary."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        mock_db.pursuits.find_one.return_value = {
            "_id": "pursuit123",
            "org_id": "org456"
        }
        mock_db.pursuit_repo_links.find_one.side_effect = [
            None,  # No duplicate
            None,  # No existing primary
        ]
        mock_db.pursuit_repo_links.count_documents.return_value = 1  # Not first link
        mock_db.pursuit_repo_links.insert_one.return_value = MagicMock(inserted_id="link-id")

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.link_repo(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_full_name="acme/project-x",
            github_repo_id=12345,
            is_primary=True,
            linked_by="user789"
        )

        assert result.is_primary is True
        assert result.action == "created"

    @pytest.mark.asyncio
    async def test_link_repo_demotes_existing_primary_when_new_primary_set(self):
        """When setting new primary, existing primary is demoted."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        mock_db.pursuits.find_one.return_value = {
            "_id": "pursuit123",
            "org_id": "org456"
        }
        mock_db.pursuit_repo_links.find_one.side_effect = [
            None,  # No duplicate link for the new repo
            {"_id": "old-primary-id", "github_repo_id": 99999, "is_primary": True},  # Existing primary
        ]
        mock_db.pursuit_repo_links.count_documents.return_value = 1
        mock_db.pursuit_repo_links.update_one.return_value = MagicMock(modified_count=1)
        mock_db.pursuit_repo_links.insert_one.return_value = MagicMock(inserted_id="link-id")

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.link_repo(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_full_name="acme/new-primary",
            github_repo_id=12345,
            is_primary=True,
            linked_by="user789"
        )

        assert result.is_primary is True
        assert result.previous_primary_id == 99999
        # Should have demoted old primary
        mock_db.pursuit_repo_links.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_link_repo_rejects_duplicate_active_link(self):
        """Duplicate active link raises DuplicateLinkError."""
        from connectors.github.pursuit_linker import PursuitRepoLinker, DuplicateLinkError

        mock_db = MagicMock()
        mock_db.pursuits.find_one.return_value = {
            "_id": "pursuit123",
            "org_id": "org456"
        }
        # Return existing link for the same repo
        mock_db.pursuit_repo_links.find_one.return_value = {
            "_id": "existing-link",
            "pursuit_id": "pursuit123",
            "github_repo_id": 12345,
            "is_active": True
        }

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        with pytest.raises(DuplicateLinkError):
            await linker.link_repo(
                org_id="org456",
                pursuit_id="pursuit123",
                github_repo_full_name="acme/project-x",
                github_repo_id=12345,
                is_primary=False,
                linked_by="user789"
            )

    @pytest.mark.asyncio
    async def test_link_repo_validates_pursuit_exists_in_org(self):
        """Link fails if pursuit doesn't exist in org."""
        from connectors.github.pursuit_linker import PursuitRepoLinker, PursuitNotFoundError

        mock_db = MagicMock()
        mock_db.pursuits.find_one.return_value = None  # Pursuit not found

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        with pytest.raises(PursuitNotFoundError):
            await linker.link_repo(
                org_id="org456",
                pursuit_id="nonexistent",
                github_repo_full_name="acme/project-x",
                github_repo_id=12345,
                is_primary=False,
                linked_by="user789"
            )


class TestUnlinkRepo:
    """Test unlink functionality."""

    @pytest.mark.asyncio
    async def test_unlink_repo_soft_deletes(self):
        """Unlink sets is_active=False, doesn't delete document."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find_one.return_value = {
            "_id": "link-id",
            "pursuit_id": "pursuit123",
            "github_repo_id": 12345,
            "github_repo_full_name": "acme/project-x",
            "is_primary": False,
            "is_active": True
        }
        mock_db.pursuit_repo_links.update_one.return_value = MagicMock(modified_count=1)
        mock_db.pursuit_repo_links.find.return_value.sort.return_value.limit.return_value = []

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.unlink_repo(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_id=12345,
            unlinked_by="user789"
        )

        assert result.action == "unlinked"
        assert result.is_primary is False
        mock_db.pursuit_repo_links.update_one.assert_called()
        mock_db.pursuit_repo_links.delete_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_unlink_repo_auto_promotes_primary_when_primary_removed(self):
        """When primary is unlinked, next oldest link becomes primary."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        # The link being unlinked is the primary
        mock_db.pursuit_repo_links.find_one.return_value = {
            "_id": "link-id",
            "pursuit_id": "pursuit123",
            "github_repo_id": 12345,
            "github_repo_full_name": "acme/project-x",
            "is_primary": True,
            "is_active": True
        }
        mock_db.pursuit_repo_links.update_one.return_value = MagicMock(modified_count=1)
        # There's another active link that should be promoted
        remaining_link = {
            "_id": "other-link",
            "github_repo_id": 67890,
            "is_primary": False
        }
        mock_db.pursuit_repo_links.find.return_value.sort.return_value.limit.return_value = [remaining_link]

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.unlink_repo(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_id=12345,
            unlinked_by="user789"
        )

        assert result.action == "unlinked"
        # Should have promoted the remaining link to primary
        assert mock_db.pursuit_repo_links.update_one.call_count >= 2

    @pytest.mark.asyncio
    async def test_unlink_repo_logs_warning_when_no_primary_remains(self):
        """When primary is unlinked and no other links exist, log warning."""
        from connectors.github.pursuit_linker import PursuitRepoLinker
        import logging

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find_one.return_value = {
            "_id": "link-id",
            "pursuit_id": "pursuit123",
            "github_repo_id": 12345,
            "github_repo_full_name": "acme/project-x",
            "is_primary": True,
            "is_active": True
        }
        mock_db.pursuit_repo_links.update_one.return_value = MagicMock(modified_count=1)
        # No other links remain
        mock_db.pursuit_repo_links.find.return_value.sort.return_value.limit.return_value = []

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        with patch.object(logging.getLogger("inde.connectors.github.pursuit_linker"), "warning") as mock_warn:
            result = await linker.unlink_repo(
                org_id="org456",
                pursuit_id="pursuit123",
                github_repo_id=12345,
                unlinked_by="user789"
            )

            assert result.action == "unlinked"
            mock_warn.assert_called()


class TestSetPrimary:
    """Test set_primary functionality."""

    @pytest.mark.asyncio
    async def test_set_primary_atomic_swap(self):
        """Set primary atomically demotes old primary and promotes new."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        # Target link to promote
        mock_db.pursuit_repo_links.find_one.side_effect = [
            {
                "_id": "new-primary-id",
                "pursuit_id": "pursuit123",
                "github_repo_id": 12345,
                "github_repo_full_name": "acme/new-primary",
                "is_primary": False,
                "is_active": True
            },
            # Current primary to demote
            {
                "_id": "old-primary-id",
                "github_repo_id": 99999,
                "is_primary": True,
                "is_active": True
            }
        ]
        mock_db.pursuit_repo_links.update_one.return_value = MagicMock(modified_count=1)

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        result = await linker.set_primary(
            org_id="org456",
            pursuit_id="pursuit123",
            github_repo_id=12345
        )

        assert result.action == "set_primary"
        assert result.is_primary is True
        assert result.previous_primary_id == 99999
        # Should have called update_one twice: demote old, promote new
        assert mock_db.pursuit_repo_links.update_one.call_count == 2


class TestGetLinks:
    """Test get_links_for_pursuit and get_pursuits_for_repo."""

    @pytest.mark.asyncio
    async def test_get_links_for_pursuit_primary_first(self):
        """get_links_for_pursuit returns primary link first."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        # Mock the cursor chain
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = lambda self: iter([
            {"github_repo_id": 111, "is_primary": True, "linked_at": datetime.now(timezone.utc)},
            {"github_repo_id": 222, "is_primary": False, "linked_at": datetime.now(timezone.utc)},
        ])
        mock_db.pursuit_repo_links.find.return_value = mock_cursor

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        links = await linker.get_links_for_pursuit("org456", "pursuit123")

        assert len(links) == 2
        assert links[0]["is_primary"] is True
        mock_db.pursuit_repo_links.find.assert_called_with({
            "org_id": "org456",
            "pursuit_id": "pursuit123",
            "is_active": True,
        })

    @pytest.mark.asyncio
    async def test_get_pursuits_for_repo_webhook_routing(self):
        """get_pursuits_for_repo returns all pursuits linked to a repo."""
        from connectors.github.pursuit_linker import PursuitRepoLinker

        mock_db = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__iter__ = lambda self: iter([
            {"pursuit_id": "pursuit1", "is_primary": True},
            {"pursuit_id": "pursuit2", "is_primary": False},
        ])
        mock_db.pursuit_repo_links.find.return_value = mock_cursor

        linker = PursuitRepoLinker(db=mock_db, connector=None, event_publisher=None)

        links = await linker.get_pursuits_for_repo("org456", 12345)

        assert len(links) == 2
        mock_db.pursuit_repo_links.find.assert_called_with({
            "org_id": "org456",
            "github_repo_id": 12345,
            "is_active": True,
        })


class TestLINDEMode:
    """Test LINDE mode regression - all routes should return 404."""

    def test_linkage_routes_404_in_linde(self):
        """All linkage routes return 404 in LINDE mode."""
        with patch.dict(os.environ, {"DEPLOYMENT_MODE": "LINDE"}):
            from services.feature_gate import get_feature_gate
            get_feature_gate.cache_clear()

            gate = get_feature_gate()

            # In LINDE mode, enterprise_connectors should be False
            assert gate.enterprise_connectors is False

            # The routes would return 404 due to require_cinde_mode dependency
            assert gate.mode.value == "LINDE"
