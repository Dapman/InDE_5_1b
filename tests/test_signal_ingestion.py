"""
InDE MVP v5.1b.0 - Signal Ingestion Test Suite

Tests for GitHub activity signal ingestion (Pillar 1/2).
All tests run in CINDE mode unless specifically testing LINDE mode.

Test classes:
- TestPushSignalIngestion: Push event signal tests
- TestPRSignalIngestion: Pull request signal tests
- TestTeamSignalIngestion: Team activity signal tests
- TestSignalIdempotency: Duplicate signal handling
- TestActivitySummary: 90-day signal count and strength
- TestSignalPursuitAttribution: Pursuit link attribution

Total: 13 tests
"""

import os
import sys
import pytest
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


class TestPushSignalIngestion:
    """Test push event signal ingestion."""

    @pytest.mark.asyncio
    async def test_push_creates_signal_per_commit(self):
        """Push event creates one signal per commit."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None  # No duplicate
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()
        mock_db.users.find_one.return_value = {"_id": "user123", "github_login": "dev1"}

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "repository": {"id": 12345, "full_name": "acme/project"},
            "pusher": {"name": "pusher1"},
            "commits": [
                {"id": "abc123", "author": {"username": "dev1"}, "message": "Fix bug"},
                {"id": "def456", "author": {"username": "dev2"}, "message": "Add feature"},
            ]
        }

        results = await ingester.ingest_push(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-001"
        )

        assert len(results) == 2
        assert all(r.signal_type == "push_commit" for r in results)
        assert results[0].github_login == "dev1"
        assert results[1].github_login == "dev2"

    @pytest.mark.asyncio
    async def test_push_signal_includes_commit_metadata(self):
        """Push signal includes commit SHA and message in metadata."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = None
        mock_db.memberships.find_one.return_value = None

        # Capture the inserted document
        inserted_doc = None
        def capture_insert(doc):
            nonlocal inserted_doc
            inserted_doc = doc
            return MagicMock()
        mock_db.github_activity_signals.insert_one.side_effect = capture_insert

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "repository": {"id": 12345, "full_name": "acme/project"},
            "ref": "refs/heads/main",
            "pusher": {"name": "pusher1"},
            "commits": [
                {"id": "abc123def456", "author": {"username": "dev1"}, "message": "Fix critical bug"},
            ]
        }

        results = await ingester.ingest_push(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-002"
        )

        assert len(results) == 1
        assert results[0].action == "ingested"
        assert inserted_doc is not None
        assert "commit_sha" in inserted_doc.get("event_metadata", {})
        assert inserted_doc["event_metadata"]["commit_sha"] == "abc123def456"[:12]


class TestPRSignalIngestion:
    """Test pull request signal ingestion."""

    @pytest.mark.asyncio
    async def test_pr_opened_creates_pr_opened_signal(self):
        """PR opened action creates pr_opened signal."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "state": "open",
                "merged": False,
                "user": {"login": "contributor1"}
            },
            "repository": {"id": 12345, "full_name": "acme/project"}
        }

        result = await ingester.ingest_pull_request(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-003"
        )

        assert result.signal_type == "pr_opened"
        assert result.github_login == "contributor1"
        assert result.action == "ingested"

    @pytest.mark.asyncio
    async def test_pr_closed_merged_creates_pr_merged_signal(self):
        """PR closed with merged=True creates pr_merged signal."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "action": "closed",
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "state": "closed",
                "merged": True,
                "user": {"login": "contributor1"}
            },
            "repository": {"id": 12345, "full_name": "acme/project"}
        }

        result = await ingester.ingest_pull_request(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-004"
        )

        assert result.signal_type == "pr_merged"
        assert result.github_login == "contributor1"
        assert result.action == "ingested"

    @pytest.mark.asyncio
    async def test_pr_review_submitted_creates_pr_reviewed_signal(self):
        """PR review submitted creates pr_reviewed signal."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "action": "submitted",
            "review": {
                "state": "approved",
                "user": {"login": "reviewer1"}
            },
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "state": "open",
                "merged": False,
                "user": {"login": "contributor1"}
            },
            "repository": {"id": 12345, "full_name": "acme/project"}
        }

        result = await ingester.ingest_pull_request(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-005"
        )

        assert result.signal_type == "pr_reviewed"
        assert result.github_login == "reviewer1"
        assert result.action == "ingested"


class TestTeamSignalIngestion:
    """Test team activity signal ingestion."""

    @pytest.mark.asyncio
    async def test_team_added_creates_team_added_signal(self):
        """Team member added creates team_added signal."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "member": {"login": "newmember"},
            "team": {"name": "Engineering", "slug": "engineering", "id": 111},
            "organization": {"login": "acme"}
        }

        result = await ingester.ingest_team_activity(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-006",
            signal_type="team_added"
        )

        assert result.signal_type == "team_added"
        assert result.github_login == "newmember"
        assert result.action == "ingested"

    @pytest.mark.asyncio
    async def test_team_removed_creates_team_removed_signal(self):
        """Team member removed creates team_removed signal."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "member": {"login": "oldmember"},
            "team": {"name": "Engineering", "slug": "engineering", "id": 111},
            "organization": {"login": "acme"}
        }

        result = await ingester.ingest_team_activity(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-007",
            signal_type="team_removed"
        )

        assert result.signal_type == "team_removed"
        assert result.github_login == "oldmember"
        assert result.action == "ingested"


class TestSignalIdempotency:
    """Test duplicate signal handling."""

    @pytest.mark.asyncio
    async def test_duplicate_signal_returns_duplicate_action(self):
        """Processing same delivery_id twice returns 'duplicate' action."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.pursuit_repo_links.find.return_value = []
        # First call returns None (no duplicate), second call returns existing
        mock_db.github_activity_signals.find_one.side_effect = [
            None,
            {"_id": "existing-signal"}
        ]
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "repository": {"id": 12345, "full_name": "acme/project"},
            "pusher": {"name": "dev1"},
            "commits": [{"id": "abc123", "author": {"username": "dev1"}, "message": "Fix"}]
        }

        # First ingestion
        results1 = await ingester.ingest_push(
            org_id="org456",
            payload=payload,
            delivery_id="same-delivery-id"
        )
        assert results1[0].action == "ingested"

        # Second ingestion with same delivery_id
        results2 = await ingester.ingest_push(
            org_id="org456",
            payload=payload,
            delivery_id="same-delivery-id"
        )
        assert results2[0].action == "duplicate"


class TestActivitySummary:
    """Test 90-day signal count and strength calculation."""

    @pytest.mark.asyncio
    async def test_activity_summary_strong_strength(self):
        """10+ signals in 90 days = 'strong' strength."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.github_activity_signals.count_documents.return_value = 15
        mock_db.innovator_profiles.update_one.return_value = MagicMock(
            modified_count=1,
            upserted_id=None
        )

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        result = await ingester.recompute_activity_summary(
            org_id="org456",
            user_id="user123"
        )

        assert result.signal_count_90d == 15
        assert result.pillar_1_signal_strength == "strong"
        assert result.updated is True

    @pytest.mark.asyncio
    async def test_activity_summary_moderate_strength(self):
        """4-9 signals in 90 days = 'moderate' strength."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.github_activity_signals.count_documents.return_value = 6
        mock_db.innovator_profiles.update_one.return_value = MagicMock(
            modified_count=1,
            upserted_id=None
        )

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        result = await ingester.recompute_activity_summary(
            org_id="org456",
            user_id="user123"
        )

        assert result.signal_count_90d == 6
        assert result.pillar_1_signal_strength == "moderate"

    @pytest.mark.asyncio
    async def test_activity_summary_weak_strength(self):
        """1-3 signals in 90 days = 'weak' strength."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.github_activity_signals.count_documents.return_value = 2
        mock_db.innovator_profiles.update_one.return_value = MagicMock(
            modified_count=1,
            upserted_id=None
        )

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        result = await ingester.recompute_activity_summary(
            org_id="org456",
            user_id="user123"
        )

        assert result.signal_count_90d == 2
        assert result.pillar_1_signal_strength == "weak"

    @pytest.mark.asyncio
    async def test_activity_summary_none_strength(self):
        """0 signals in 90 days = 'none' strength."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        mock_db.github_activity_signals.count_documents.return_value = 0
        mock_db.innovator_profiles.update_one.return_value = MagicMock(
            modified_count=0,
            upserted_id="new-profile"
        )

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        result = await ingester.recompute_activity_summary(
            org_id="org456",
            user_id="user123"
        )

        assert result.signal_count_90d == 0
        assert result.pillar_1_signal_strength == "none"


class TestSignalPursuitAttribution:
    """Test pursuit link attribution in signals."""

    @pytest.mark.asyncio
    async def test_signal_attributed_to_primary_pursuit(self):
        """Signal is attributed to primary linked pursuit."""
        from connectors.github.signal_ingester import GitHubSignalIngester

        mock_db = MagicMock()
        # Repo is linked to two pursuits, one primary
        mock_db.pursuit_repo_links.find.return_value = [
            {"pursuit_id": "pursuit1", "is_primary": True, "github_repo_id": 12345},
            {"pursuit_id": "pursuit2", "is_primary": False, "github_repo_id": 12345},
        ]
        mock_db.github_activity_signals.find_one.return_value = None
        mock_db.users.find_one.return_value = {"_id": "user123"}
        mock_db.github_activity_signals.insert_one.return_value = MagicMock()

        ingester = GitHubSignalIngester(db=mock_db, event_publisher=None)

        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add feature",
                "state": "open",
                "merged": False,
                "user": {"login": "dev1"}
            },
            "repository": {"id": 12345, "full_name": "acme/project"}
        }

        result = await ingester.ingest_pull_request(
            org_id="org456",
            payload=payload,
            delivery_id="delivery-010"
        )

        assert result.pursuit_id == "pursuit1"
        assert result.is_primary_repo is True
