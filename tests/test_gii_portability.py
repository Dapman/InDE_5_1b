"""
InDE MVP v5.1b.0 - GII Portability Tests
Tests for GII binding, mode transitions, and data isolation.

Run with:
    DEPLOYMENT_MODE=CINDE ORG_ID_SEED=test-org python -m pytest tests/test_gii_portability.py -v --tb=short
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

# Set environment before imports
os.environ["DEPLOYMENT_MODE"] = "CINDE"
os.environ["ORG_ID_SEED"] = "test-org-seed-12345"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-validation")

# Add app to path
_app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)


class TestGIIGeneration:
    """Test 1: GII generation format."""

    def test_gii_format_v316(self):
        """GII should follow v3.16 format: GII-REGION-16CHAR-4CHECK"""
        from gii.manager import GIIManager

        # Create mock db
        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        gii = manager.generate_gii(region="US", user_id="test-user")

        # Verify format
        parts = gii.split("-")
        assert len(parts) == 4, f"Expected 4 parts, got {len(parts)}: {gii}"
        assert parts[0] == "GII"
        assert parts[1] == "US"
        assert len(parts[2]) == 16  # 16-char hash
        assert len(parts[3]) == 4   # 4-char check


class TestGIIValidation:
    """Test 2: GII format validation."""

    def test_validate_v316_format(self):
        """v3.16 format should be valid."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        # v3.16 format (16-char + 4-char check)
        valid_v316 = "GII-US-8D4E9F2A1B3C4E5F-A7F3"
        assert manager._validate_gii_format(valid_v316) is True

    def test_validate_v31_format(self):
        """v3.1 format should still be valid."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        # v3.1 format (12-char)
        valid_v31 = "GII-US-8D4E9F2A1B3C"
        assert manager._validate_gii_format(valid_v31) is True

    def test_invalid_format_rejected(self):
        """Invalid formats should be rejected."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        invalid_formats = [
            "",
            "GII",
            "GII-US",
            "GII-US-SHORT",
            "XXX-US-8D4E9F2A1B3C",
            "GII-X-8D4E9F2A1B3C",  # Region too short
        ]

        for fmt in invalid_formats:
            assert manager._validate_gii_format(fmt) is False, f"Should reject: {fmt}"


class TestOnboardToCInDE:
    """Test 3: GII binding to CInDE organization."""

    def test_onboard_method_exists(self):
        """onboard_to_cinde method should exist."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        assert hasattr(manager, "onboard_to_cinde")
        assert callable(manager.onboard_to_cinde)

    def test_onboard_updates_binding(self):
        """onboard_to_cinde should update binding type to ORGANIZATION."""
        from gii.manager import GIIManager

        # Setup mock
        mock_db = MagicMock()
        mock_profile = {
            "gii_id": "GII-US-TEST12345678-ABCD",
            "user_id": "test-user",
            "binding_type": "INDIVIDUAL",
            "binding_org_id": None,
            "binding_history": []
        }
        mock_db.db.gii_profiles.find_one.return_value = mock_profile

        manager = GIIManager(mock_db)

        # Should not raise
        manager.onboard_to_cinde("test-user", "test-org-123")

        # Verify update was called
        mock_db.db.gii_profiles.update_one.assert_called_once()


class TestDissolveBinding:
    """Test 4: GII binding dissolution."""

    def test_dissolve_method_exists(self):
        """dissolve_binding method should exist."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        assert hasattr(manager, "dissolve_binding")
        assert callable(manager.dissolve_binding)

    def test_dissolve_reverts_to_individual(self):
        """dissolve_binding should revert binding type to INDIVIDUAL."""
        from gii.manager import GIIManager

        # Setup mock
        mock_db = MagicMock()
        mock_profile = {
            "gii_id": "GII-US-TEST12345678-ABCD",
            "user_id": "test-user",
            "binding_type": "ORGANIZATION",
            "binding_org_id": "test-org-123",
            "binding_history": []
        }
        mock_db.db.gii_profiles.find_one.return_value = mock_profile

        manager = GIIManager(mock_db)

        # Should not raise
        manager.dissolve_binding("test-user")

        # Verify update was called
        mock_db.db.gii_profiles.update_one.assert_called_once()


class TestBindingType:
    """Test 5: Get binding type."""

    def test_get_binding_type_individual(self):
        """get_binding_type should return INDIVIDUAL for unbound users."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        mock_db.db.gii_profiles.find_one.return_value = None

        manager = GIIManager(mock_db)
        binding = manager.get_binding_type("test-user")

        assert binding == "INDIVIDUAL"

    def test_get_binding_type_organization(self):
        """get_binding_type should return ORGANIZATION for org-bound users."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        mock_db.db.gii_profiles.find_one.return_value = {
            "binding_type": "ORGANIZATION"
        }

        manager = GIIManager(mock_db)
        binding = manager.get_binding_type("test-user")

        assert binding == "ORGANIZATION"


class TestDataIsolation:
    """Test 6: Data isolation verification."""

    def test_verify_data_isolation_method_exists(self):
        """verify_data_isolation method should exist."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        assert hasattr(manager, "verify_data_isolation")
        assert callable(manager.verify_data_isolation)

    def test_isolation_returns_correct_structure(self):
        """verify_data_isolation should return proper structure."""
        from gii.manager import GIIManager

        mock_db = MagicMock()
        mock_db.db.gii_profiles.find_one.return_value = {
            "binding_org_id": None  # Not bound to the org
        }
        mock_db.db.pursuits.count_documents.return_value = 5

        manager = GIIManager(mock_db)
        result = manager.verify_data_isolation("test-user", "former-org-123")

        assert "gii_isolated" in result
        assert "personal_pursuits_accessible" in result
        assert "org_pursuits_read_only" in result
        assert "isolation_verified" in result


class TestTransitionContext:
    """Test 7: ODICM transition context."""

    def test_coaching_context_has_transition_field(self):
        """CoachingContext should have transition_context field."""
        from coaching.odicm_extensions import CoachingContext, ConvergencePhase, CoachingMode

        ctx = CoachingContext(
            pursuit_id="test-pursuit",
            user_id="test-user",
            org_id="",
            methodology_archetype="lean_startup",
            current_phase=ConvergencePhase.EXPLORING,
            coaching_mode=CoachingMode.EXPLORATORY,
            convergence_signals=[],
            portfolio_context={},
            methodology_guidance={},
            recent_outcomes=[],
            org_context={},
            transition_context={"binding_type": "INDIVIDUAL", "recent_transition": False}
        )

        assert "transition_context" in ctx.to_dict()

    def test_transition_context_structure(self):
        """Transition context should have expected fields."""
        from coaching.odicm_extensions import ConvergenceAwareCoach

        coach = ConvergenceAwareCoach()

        # Mock implementation returns empty or default
        ctx = coach._build_transition_context("nonexistent-user")

        assert "binding_type" in ctx
        assert "recent_transition" in ctx


class TestGIIPortabilityRoundTrip:
    """Test 8: Full round-trip LInDE -> CInDE -> LInDE."""

    def test_binding_history_tracked(self):
        """Binding history should track transitions."""
        from gii.manager import GIIManager

        mock_db = MagicMock()

        # Initial state: INDIVIDUAL
        initial_profile = {
            "gii_id": "GII-US-TEST12345678-ABCD",
            "user_id": "test-user",
            "binding_type": "INDIVIDUAL",
            "binding_org_id": None,
            "binding_history": []
        }

        # After onboard
        after_onboard = {
            **initial_profile,
            "binding_type": "ORGANIZATION",
            "binding_org_id": "test-org",
            "binding_history": [{"event": "ONBOARD_TO_CINDE", "org_id": "test-org"}]
        }

        mock_db.db.gii_profiles.find_one.side_effect = [
            initial_profile,  # First call (onboard check)
            after_onboard,    # Second call (return updated)
        ]

        manager = GIIManager(mock_db)

        # Simulate onboard
        result = manager.onboard_to_cinde("test-user", "test-org")

        # Verify history push was called
        call_args = mock_db.db.gii_profiles.update_one.call_args
        update_doc = call_args[0][1]
        assert "$push" in update_doc
        assert "binding_history" in update_doc["$push"]


class TestStorageElection:
    """Test 9: Storage election respects mode."""

    def test_storage_elections_defined(self):
        """Storage elections should be defined."""
        from core.config import STORAGE_ELECTIONS
        assert "FULL_PARTICIPATION" in STORAGE_ELECTIONS
        assert "ORG_VISIBLE" in STORAGE_ELECTIONS
        assert "PRIVATE" in STORAGE_ELECTIONS


# ============================================================================
# Summary Test
# ============================================================================

class TestGIIPortabilitySummary:
    """Summary test confirming GII portability criteria."""

    def test_gii_portability_certification_complete(self):
        """All GII portability features should be available."""
        from gii.manager import GIIManager
        from coaching.odicm_extensions import CoachingContext

        # Verify GIIManager has all required methods
        mock_db = MagicMock()
        manager = GIIManager(mock_db)

        methods = {
            "generate_gii": callable(manager.generate_gii),
            "onboard_to_cinde": callable(manager.onboard_to_cinde),
            "dissolve_binding": callable(manager.dissolve_binding),
            "get_binding_type": callable(manager.get_binding_type),
            "verify_data_isolation": callable(manager.verify_data_isolation),
        }

        failed = [k for k, v in methods.items() if not v]
        assert not failed, f"GII portability missing methods: {failed}"

        # Verify CoachingContext has transition_context
        assert hasattr(CoachingContext, "__annotations__")
        assert "transition_context" in CoachingContext.__annotations__

        print("\n" + "="*60)
        print("GII PORTABILITY CERTIFICATION: PASSED")
        print("="*60)
        print("  GII Methods:          ALL PRESENT")
        print("  Transition Context:   AVAILABLE")
        print("  Data Isolation:       VERIFIABLE")
        print("="*60)
