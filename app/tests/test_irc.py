"""
InDE MVP v5.1b.0 - IRC Module Tests

Tests for the Innovation Resource Canvas module.

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
from datetime import datetime, timezone

# =============================================================================
# SIGNAL DETECTION TESTS
# =============================================================================

class TestSignalDetectionEngine:
    """Tests for IRCSignalDetectionEngine."""

    def test_identification_signal_detection(self):
        """Test detection of IDENTIFICATION signals."""
        from app.modules.irc.signal_detection_engine import IRCSignalDetectionEngine

        engine = IRCSignalDetectionEngine()

        # Should detect
        signal = engine.detect_sync(
            text="We would need a data scientist for this phase",
            turn_id="turn_001",
            pursuit_id="pursuit_001",
        )
        assert signal is not None
        assert signal.family.value == "IDENTIFICATION"

    def test_cost_signal_detection(self):
        """Test detection of COST signals."""
        from app.modules.irc.signal_detection_engine import IRCSignalDetectionEngine

        engine = IRCSignalDetectionEngine()

        signal = engine.detect_sync(
            text="Budget-wise, I think that's going to be expensive",
            turn_id="turn_002",
            pursuit_id="pursuit_001",
        )
        assert signal is not None
        assert signal.family.value == "COST"

    def test_uncertainty_signal_detection(self):
        """Test detection of UNCERTAINTY signals."""
        from app.modules.irc.signal_detection_engine import IRCSignalDetectionEngine

        engine = IRCSignalDetectionEngine()

        signal = engine.detect_sync(
            text="I think we can get that, hopefully by next month",
            turn_id="turn_003",
            pursuit_id="pursuit_001",
        )
        assert signal is not None
        assert signal.uncertainty_flag == True

    def test_no_signal_for_short_text(self):
        """Test that very short text doesn't trigger signals."""
        from app.modules.irc.signal_detection_engine import IRCSignalDetectionEngine

        engine = IRCSignalDetectionEngine()

        signal = engine.detect_sync(
            text="Yes",
            turn_id="turn_004",
            pursuit_id="pursuit_001",
        )
        assert signal is None


# =============================================================================
# DISPLAY LABELS TESTS
# =============================================================================

class TestDisplayLabels:
    """Tests for IRC display labels (Language Sovereignty compliance)."""

    def test_category_labels_exist(self):
        """Test that all category display labels are defined."""
        from app.modules.irc.irc_display_labels import IRC_DISPLAY_LABELS

        categories = IRC_DISPLAY_LABELS.get("category_display", {})
        assert "HUMAN_CAPITAL" in categories
        assert "CAPITAL_EQUIPMENT" in categories
        assert "DATA_AND_IP" in categories
        assert "SERVICES" in categories
        assert "FINANCIAL" in categories

    def test_availability_labels_no_risk_language(self):
        """Test that availability labels don't use prohibited language."""
        from app.modules.irc.irc_display_labels import IRC_DISPLAY_LABELS

        availability = IRC_DISPLAY_LABELS.get("availability_display", {})

        prohibited = ["risk", "fear", "danger", "warning", "fail"]
        for label in availability.values():
            label_lower = label.lower()
            for term in prohibited:
                assert term not in label_lower, f"Prohibited term '{term}' in '{label}'"

    def test_get_display_label_function(self):
        """Test the get_display_label helper function."""
        from app.modules.irc.irc_display_labels import get_display_label

        label = get_display_label("category_display", "HUMAN_CAPITAL")
        assert label == "People & Expertise"

        # Unknown value should return the value itself
        label = get_display_label("category_display", "UNKNOWN_CAT")
        assert label == "UNKNOWN_CAT"


# =============================================================================
# LANGUAGE SOVEREIGNTY TESTS
# =============================================================================

class TestLanguageSovereignty:
    """Tests for Language Sovereignty compliance."""

    def test_validate_language_sovereignty_clean_text(self):
        """Test that clean text passes validation."""
        from app.modules.irc.irc_llm_client import validate_language_sovereignty

        is_valid, violations = validate_language_sovereignty(
            "We need to work through some open questions about resources."
        )
        assert is_valid == True
        assert len(violations) == 0

    def test_validate_language_sovereignty_catches_violations(self):
        """Test that prohibited terms are caught."""
        from app.modules.irc.irc_llm_client import validate_language_sovereignty

        is_valid, violations = validate_language_sovereignty(
            "Your fears about this resource are at risk of becoming problems."
        )
        assert is_valid == False
        assert len(violations) > 0

    def test_sanitize_output(self):
        """Test that sanitize_output replaces prohibited terms."""
        from app.modules.irc.irc_llm_client import sanitize_output

        result = sanitize_output("This resource is at risk.")
        assert "at risk" not in result.lower()

    def test_coaching_scripts_clean(self):
        """Test that coaching scripts in irc_coach_bridge are clean."""
        from app.modules.irc.irc_coach_bridge import (
            CONSOLIDATION_OFFER,
            CONSOLIDATION_DECLINE_ACK,
            CANVAS_SYNTHESIS_TEMPLATE,
            PHASE_APPROACH_NUDGE,
        )
        from app.modules.irc.irc_llm_client import validate_language_sovereignty

        scripts = [
            CONSOLIDATION_OFFER,
            CONSOLIDATION_DECLINE_ACK,
            CANVAS_SYNTHESIS_TEMPLATE,
            PHASE_APPROACH_NUDGE,
        ]

        for script in scripts:
            is_valid, violations = validate_language_sovereignty(script)
            assert is_valid, f"Coaching script contains violations: {violations}"


# =============================================================================
# RESOURCE ENTRY TESTS
# =============================================================================

class TestResourceEntryManager:
    """Tests for ResourceEntryManager (requires mock database)."""

    def test_resource_schema_version(self):
        """Test that schema version is set correctly."""
        from app.modules.irc.resource_entry_manager import ResourceEntryManager

        assert ResourceEntryManager.SCHEMA_VERSION == "1.0"

    def test_resource_category_enum(self):
        """Test ResourceCategory enum values."""
        from app.modules.irc.resource_entry_manager import ResourceCategory

        assert ResourceCategory.HUMAN_CAPITAL.value == "HUMAN_CAPITAL"
        assert ResourceCategory.FINANCIAL.value == "FINANCIAL"

    def test_availability_status_enum(self):
        """Test AvailabilityStatus enum values."""
        from app.modules.irc.resource_entry_manager import AvailabilityStatus

        assert AvailabilityStatus.SECURED.value == "SECURED"
        assert AvailabilityStatus.UNRESOLVED.value == "UNRESOLVED"


# =============================================================================
# CONSOLIDATION TESTS
# =============================================================================

class TestConsolidationEngine:
    """Tests for IRCConsolidationEngine."""

    def test_canvas_computer_empty_resources(self):
        """Test canvas computation with empty resource list."""
        from app.modules.irc.consolidation_engine import CanvasComputer

        computer = CanvasComputer()
        result = computer.compute("pursuit_001", [])

        assert result["total_resources"] == 0
        assert result["canvas_completeness"] == 0.0
        assert result["itd_ready"] == False

    def test_canvas_computer_completeness(self):
        """Test canvas completeness calculation."""
        from app.modules.irc.consolidation_engine import CanvasComputer

        computer = CanvasComputer()

        # Resource with full data
        resources = [{
            "artifact_id": "res_001",
            "resource_name": "Data Scientist",
            "category": "HUMAN_CAPITAL",
            "phase_alignment": ["DE_RISK"],
            "availability_status": "SECURED",
            "cost_estimate_low": 50000,
            "cost_estimate_high": 60000,
            "cost_confidence": "ESTIMATED",
            "criticality": "ESSENTIAL",
            "duration_type": "SUSTAINED",
        }]

        result = computer.compute("pursuit_001", resources)

        assert result["total_resources"] == 1
        assert result["canvas_completeness"] > 0.5
        assert result["secured_count"] == 1

    def test_consolidation_trigger_density(self):
        """Test that consolidation trigger requires minimum resources."""
        from app.modules.irc.consolidation_engine import ConsolidationTriggerEvaluator

        # Would need mock database for full test
        # This tests that the class exists and has expected structure
        assert hasattr(ConsolidationTriggerEvaluator, 'PAUSE_PATTERNS')


# =============================================================================
# API RESPONSE MODEL TESTS
# =============================================================================

class TestAPIModels:
    """Tests for API response models."""

    def test_irc_status_response_model(self):
        """Test IRCStatusResponse model validation."""
        try:
            from app.api.irc import IRCStatusResponse

            response = IRCStatusResponse(
                pursuit_id="pursuit_001",
                has_canvas=True,
                resource_count=5,
                secured_count=2,
                unresolved_count=1,
                canvas_completeness=0.65,
                consolidation_eligible=True,
                status_label="In progress",
                status_description="Resource picture is taking shape",
            )

            assert response.pursuit_id == "pursuit_001"
            assert response.canvas_completeness == 0.65
        except ImportError:
            # API module requires full app context - skip in isolated test env
            pytest.skip("API module requires full app context")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestModuleIntegration:
    """Tests for IRC module integration points."""

    def test_irc_module_imports(self):
        """Test that all IRC module components can be imported."""
        from app.modules.irc import (
            IRCSignalDetectionEngine,
            ResourceSignal,
            ResourceSignalFamily,
            ResourceEntryManager,
            IRCConsolidationEngine,
            ConsolidationTriggerEvaluator,
            IRCCoachBridge,
        )

        assert IRCSignalDetectionEngine is not None
        assert ResourceSignal is not None
        assert ResourceSignalFamily is not None
        assert ResourceEntryManager is not None
        assert IRCConsolidationEngine is not None
        assert ConsolidationTriggerEvaluator is not None
        assert IRCCoachBridge is not None

    def test_moment_definitions_available(self):
        """Test that MDS moment definitions are available."""
        from app.modules.irc.signal_detection_engine import get_resource_signal_moment_definition
        from app.modules.irc.consolidation_engine import get_irc_consolidation_moment_definition

        signal_moment = get_resource_signal_moment_definition()
        assert signal_moment["moment_type"] == "RESOURCE_SIGNAL"
        assert "priority" in signal_moment

        consolidation_moment = get_irc_consolidation_moment_definition()
        assert consolidation_moment["moment_type"] == "IRC_CONSOLIDATION"
        assert "priority" in consolidation_moment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
