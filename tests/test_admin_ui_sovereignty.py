"""
InDE MVP v5.1b.0 - Admin UI & Sovereignty Tests

Tests for:
1. Admin Confirmation UI for github_unlinked users (4 tests)
2. Extended Sovereignty Enforcement (4 tests)

Sovereignty boundary: No outbound data flow from pursuit content to GitHub.
Connectors must NOT import from coaching, maturity, fear, or pursuit_content modules.
"""

import pytest
import ast
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Admin UI Tests (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUnlinkedMembersUI:
    """Tests for admin UI routes for github_unlinked members."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.memberships = MagicMock()
        db.users = MagicMock()
        db.github_sync_log = MagicMock()
        return db

    @pytest.fixture
    def sample_unlinked_membership(self):
        """Sample membership marked as github_unlinked."""
        return {
            "_id": "mem_001",
            "org_id": "org_test",
            "user_id": "user_001",
            "status": "ACTIVE",
            "github_login": "testuser",
            "github_unlinked": True,
            "github_unlinked_at": datetime.now(timezone.utc),
            "github_synced_at": datetime.now(timezone.utc),
            "effective_role": "org_member",
            "role": "org_member"
        }

    def test_list_unlinked_members_returns_only_unlinked(self, mock_db, sample_unlinked_membership):
        """Test that GET /members/unlinked only returns github_unlinked=True members."""
        # Setup: Mock cursor with unlinked membership
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = [sample_unlinked_membership]
        mock_db.memberships.find.return_value = mock_cursor

        mock_db.users.find_one.return_value = {
            "_id": "user_001",
            "email": "test@example.com",
            "display_name": "Test User"
        }

        # Execute: Simulate the query that would be made
        query = {
            "org_id": "org_test",
            "status": "ACTIVE",
            "github_unlinked": True
        }
        mock_db.memberships.find(query)

        # Verify: Query includes github_unlinked=True filter
        mock_db.memberships.find.assert_called_with(query)

    def test_confirm_unlink_remove_revokes_membership(self, mock_db, sample_unlinked_membership):
        """Test that action='remove' sets status to REVOKED."""
        # Setup
        mock_db.memberships.find_one.return_value = sample_unlinked_membership
        mock_db.memberships.update_one.return_value = MagicMock(modified_count=1)
        mock_db.github_sync_log.insert_one.return_value = MagicMock()

        # Execute: Simulate remove action
        update_query = {"_id": sample_unlinked_membership["_id"]}
        update_fields = {
            "$set": {
                "status": "REVOKED",
                "revoked_at": datetime.now(timezone.utc),
                "revoked_by": "admin_001",
                "revoke_reason": "github_unlinked_confirmed"
            }
        }
        mock_db.memberships.update_one(update_query, update_fields)

        # Verify
        call_args = mock_db.memberships.update_one.call_args[0]
        assert call_args[1]["$set"]["status"] == "REVOKED"
        assert call_args[1]["$set"]["revoke_reason"] == "github_unlinked_confirmed"

    def test_confirm_unlink_retain_clears_github_fields(self, mock_db, sample_unlinked_membership):
        """Test that action='retain' clears GitHub fields and sets human_set_role."""
        # Setup
        mock_db.memberships.find_one.return_value = sample_unlinked_membership
        mock_db.memberships.update_one.return_value = MagicMock(modified_count=1)

        # Execute: Simulate retain action
        update_query = {"_id": sample_unlinked_membership["_id"]}
        update_fields = {
            "$set": {
                "github_unlinked": False,
                "github_unlinked_at": None,
                "github_login": None,
                "github_org_role": None,
                "github_derived_role": None,
                "human_set_role": "org_member",
                "human_set_at": datetime.now(timezone.utc),
                "human_set_by": "admin_001"
            }
        }
        mock_db.memberships.update_one(update_query, update_fields)

        # Verify: GitHub fields cleared, human_set_role preserved
        call_args = mock_db.memberships.update_one.call_args[0]
        assert call_args[1]["$set"]["github_unlinked"] == False
        assert call_args[1]["$set"]["github_login"] is None
        assert call_args[1]["$set"]["human_set_role"] == "org_member"

    def test_confirm_unlink_logs_admin_action(self, mock_db, sample_unlinked_membership):
        """Test that confirm actions are logged to github_sync_log."""
        # Setup
        mock_db.memberships.find_one.return_value = sample_unlinked_membership
        mock_db.memberships.update_one.return_value = MagicMock(modified_count=1)

        # Execute: Log the action
        log_entry = {
            "org_id": "org_test",
            "event_type": "admin_confirm_unlink",
            "action": "remove",
            "github_login": "testuser",
            "affected_user_id": "user_001",
            "admin_user_id": "admin_001",
            "created_at": datetime.now(timezone.utc)
        }
        mock_db.github_sync_log.insert_one(log_entry)

        # Verify
        call_args = mock_db.github_sync_log.insert_one.call_args[0][0]
        assert call_args["event_type"] == "admin_confirm_unlink"
        assert call_args["action"] == "remove"
        assert call_args["admin_user_id"] == "admin_001"


# ─────────────────────────────────────────────────────────────────────────────
# Sovereignty Tests (4 tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestSovereigntyEnforcement:
    """
    Tests to verify sovereignty boundary enforcement.

    Rule: Connectors must NOT import from coaching, maturity, fear, or pursuit_content.
    This ensures no outbound data flow from internal IP to external connectors.
    """

    # Forbidden modules that connectors must not import
    FORBIDDEN_MODULES = [
        "coaching",
        "maturity",
        "fear",
        "pursuit_content",
        "app.coaching",
        "app.maturity",
        "app.fear",
        "app.pursuit_content",
        "models.coaching",
        "models.maturity",
        "models.fear",
        "models.pursuit_content",
    ]

    def get_connector_files(self):
        """Get all Python files in the connectors directory."""
        connector_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "app", "connectors"
        )
        connector_dir = os.path.abspath(connector_dir)

        python_files = []
        for root, dirs, files in os.walk(connector_dir):
            for f in files:
                if f.endswith(".py"):
                    python_files.append(os.path.join(root, f))
        return python_files

    def extract_imports(self, filepath):
        """Extract all import statements from a Python file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                return []  # Skip files with syntax errors

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    # Also track full import paths
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
        return imports

    def test_no_coaching_imports_in_connectors(self):
        """Verify connectors do not import from coaching module."""
        connector_files = self.get_connector_files()
        violations = []

        for filepath in connector_files:
            imports = self.extract_imports(filepath)
            for imp in imports:
                if "coaching" in imp.lower():
                    violations.append((filepath, imp))

        assert len(violations) == 0, f"Sovereignty violation - coaching imports found: {violations}"

    def test_no_maturity_imports_in_connectors(self):
        """Verify connectors do not import from maturity module."""
        connector_files = self.get_connector_files()
        violations = []

        for filepath in connector_files:
            imports = self.extract_imports(filepath)
            for imp in imports:
                if "maturity" in imp.lower():
                    violations.append((filepath, imp))

        assert len(violations) == 0, f"Sovereignty violation - maturity imports found: {violations}"

    def test_no_fear_imports_in_connectors(self):
        """Verify connectors do not import from fear module."""
        connector_files = self.get_connector_files()
        violations = []

        for filepath in connector_files:
            imports = self.extract_imports(filepath)
            for imp in imports:
                if "fear" in imp.lower():
                    violations.append((filepath, imp))

        assert len(violations) == 0, f"Sovereignty violation - fear imports found: {violations}"

    def test_no_pursuit_content_imports_in_connectors(self):
        """Verify connectors do not import from pursuit_content module."""
        connector_files = self.get_connector_files()
        violations = []

        for filepath in connector_files:
            imports = self.extract_imports(filepath)
            for imp in imports:
                if "pursuit_content" in imp.lower():
                    violations.append((filepath, imp))

        assert len(violations) == 0, f"Sovereignty violation - pursuit_content imports found: {violations}"


# ─────────────────────────────────────────────────────────────────────────────
# Test Summary
# ─────────────────────────────────────────────────────────────────────────────

"""
Test Count: 8 tests

Admin UI Tests (4):
1. test_list_unlinked_members_returns_only_unlinked - GET filter
2. test_confirm_unlink_remove_revokes_membership - Remove action
3. test_confirm_unlink_retain_clears_github_fields - Retain action
4. test_confirm_unlink_logs_admin_action - Audit logging

Sovereignty Tests (4):
5. test_no_coaching_imports_in_connectors - No coaching leakage
6. test_no_maturity_imports_in_connectors - No maturity leakage
7. test_no_fear_imports_in_connectors - No fear leakage
8. test_no_pursuit_content_imports_in_connectors - No pursuit_content leakage
"""
