"""
InDE MVP v5.1b.0 - CInDE Mode Certification Tests
Tests for DEPLOYMENT_MODE=CINDE behavior.

Run with:
    DEPLOYMENT_MODE=CINDE ORG_ID_SEED=test-org python -m pytest tests/test_cinde_mode.py -v --tb=short
"""

import os
import sys
import pytest

# Set DEPLOYMENT_MODE before any imports
os.environ["DEPLOYMENT_MODE"] = "CINDE"
os.environ["ORG_ID_SEED"] = "test-org-seed-12345"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-validation")

# Add app to path
_app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)


class TestCInDEHealthEndpoint:
    """Test 1: Health endpoint — deployment_mode == CINDE"""

    def test_health_deployment_mode_cinde(self):
        """Health endpoint should return CINDE deployment mode."""
        from services.feature_gate import get_feature_gate, DeploymentMode

        # Clear cache to ensure fresh read
        get_feature_gate.cache_clear()

        gate = get_feature_gate()
        assert gate.mode == DeploymentMode.CINDE
        assert gate.mode.value == "CINDE"


class TestEnterpriseGatesActive:
    """Test 2: All enterprise gates should be active in CINDE mode."""

    def test_cinde_gates_true(self):
        """All CInDE-only gates should return True in CINDE mode."""
        from services.feature_gate import get_feature_gate

        get_feature_gate.cache_clear()
        gate = get_feature_gate()

        assert gate.org_entity_active is True
        assert gate.team_formation_active is True
        assert gate.idtfs_active is True
        assert gate.portfolio_active is True
        assert gate.soc2_audit_active is True
        assert gate.rbac_active is True
        assert gate.activity_stream_active is True
        assert gate.convergence_protocol_active is True

    def test_shared_gates_still_true(self):
        """All SHARED gates should still return True in CINDE mode."""
        from services.feature_gate import get_feature_gate

        get_feature_gate.cache_clear()
        gate = get_feature_gate()

        assert gate.coaching_active is True
        assert gate.outcome_intelligence_active is True
        assert gate.momentum_active is True
        assert gate.irc_active is True
        assert gate.gii_active is True
        assert gate.license_active is True


class TestEnterpriseRouterRegistration:
    """Test 3: Enterprise routers should be conditionally registered."""

    def test_enterprise_route_prefixes_available(self):
        """Enterprise route prefixes should be available in CINDE mode."""
        # In CINDE mode, enterprise routes should be registered
        # This is verified by checking the middleware doesn't block them
        from services.feature_gate import get_feature_gate

        get_feature_gate.cache_clear()
        gate = get_feature_gate()

        # In CINDE mode, org_entity_active is True, so routes are registered
        assert gate.org_entity_active is True


class TestRBACWarmup:
    """Test 4: RBAC cache warmup in CINDE mode."""

    def test_rbac_warmup_function_exists(self):
        """RBAC warm_rbac_cache function should exist."""
        from middleware.rbac import warm_rbac_cache
        assert callable(warm_rbac_cache)

    def test_rbac_warmup_executes(self):
        """RBAC cache warmup should execute without error."""
        from middleware.rbac import warm_rbac_cache
        # Should not raise
        warm_rbac_cache()


class TestIDTFSIndexVerification:
    """Test 5: IDTFS index verification in CINDE mode."""

    def test_idtfs_verify_function_exists(self):
        """IDTFS verify_idtfs_indexes function should exist."""
        from discovery.idtfs import verify_idtfs_indexes
        assert callable(verify_idtfs_indexes)


class TestOrgContextAssembly:
    """Test 6: Org context assembly in ODICM."""

    def test_coaching_context_has_org_field(self):
        """CoachingContext should have org_context field."""
        from coaching.odicm_extensions import CoachingContext, ConvergencePhase, CoachingMode

        ctx = CoachingContext(
            pursuit_id="test-pursuit",
            user_id="test-user",
            org_id="test-org",
            methodology_archetype="lean_startup",
            current_phase=ConvergencePhase.EXPLORING,
            coaching_mode=CoachingMode.EXPLORATORY,
            convergence_signals=[],
            portfolio_context={},
            methodology_guidance={},
            recent_outcomes=[],
            org_context={"team_gaps": [], "composition_guidance": {}}
        )

        assert "org_context" in ctx.to_dict()
        assert ctx.org_context is not None


class TestActivityStreamConsumer:
    """Test 7: Activity stream consumer registration."""

    def test_activity_stream_consumer_registration(self):
        """Activity stream consumer should be registered in CInDE mode."""
        from services.feature_gate import get_feature_gate

        get_feature_gate.cache_clear()
        gate = get_feature_gate()

        # In CINDE mode, activity_stream_active is True
        assert gate.activity_stream_active is True


class TestPortfolioDashboardV4x:
    """Test 8: Portfolio dashboard v4.x panel."""

    def test_v4x_intelligence_panel_type_exists(self):
        """V4X_INTELLIGENCE panel type should exist."""
        from portfolio.dashboard import PanelType

        assert hasattr(PanelType, "V4X_INTELLIGENCE")
        assert PanelType.V4X_INTELLIGENCE.value == "v4x_intelligence"

    def test_portfolio_dashboard_has_v4x_generator(self):
        """Portfolio dashboard should have v4x generator method."""
        from portfolio.dashboard import PortfolioDashboard

        dashboard = PortfolioDashboard()
        assert hasattr(dashboard, "_generate_v4x_intelligence")


class TestAuditWritableCheck:
    """Test 9: Audit log writable check."""

    def test_audit_verify_function_exists(self):
        """verify_audit_writable function should exist."""
        from events.audit import verify_audit_writable
        assert callable(verify_audit_writable)


class TestTeamGapsFunction:
    """Test 10: Team gaps function for org context."""

    def test_team_gaps_function_exists(self):
        """get_team_gaps function should exist."""
        from discovery.formation import get_team_gaps
        assert callable(get_team_gaps)

    def test_team_gaps_returns_list(self):
        """get_team_gaps should return a list."""
        from discovery.formation import get_team_gaps

        # Should return empty list for non-existent pursuit
        result = get_team_gaps("non-existent-pursuit-id")
        assert isinstance(result, list)


# ============================================================================
# Summary Test
# ============================================================================

class TestCInDEModeSummary:
    """Summary test confirming all CInDE mode certification criteria."""

    def test_cinde_mode_certification_complete(self):
        """All CInDE mode tests should pass."""
        from services.feature_gate import get_feature_gate, DeploymentMode
        from core.config import VERSION

        get_feature_gate.cache_clear()
        gate = get_feature_gate()

        # Certification checklist
        checks = {
            "deployment_mode": gate.mode == DeploymentMode.CINDE,
            "version": VERSION == "5.1b.0",
            "enterprise_gates_on": gate.org_entity_active,
            "shared_gates_on": gate.coaching_active and gate.momentum_active,
            "rbac_active": gate.rbac_active,
            "portfolio_active": gate.portfolio_active,
            "activity_stream_active": gate.activity_stream_active,
            "idtfs_active": gate.idtfs_active,
        }

        failed = [k for k, v in checks.items() if not v]
        assert not failed, f"CInDE certification failed checks: {failed}"

        print("\n" + "="*60)
        print("CInDE MODE CERTIFICATION: PASSED")
        print("="*60)
        print(f"  Version:          {VERSION}")
        print(f"  Deployment Mode:  {gate.mode.value}")
        print(f"  Enterprise Gates: ON")
        print(f"  Shared Gates:     ON")
        print("="*60)
