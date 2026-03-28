"""
InDE MVP v4.6.0 - Outcome Formulator Tests

Unit tests for the Outcome Formulator Engine:
- OutcomeReadinessStateMachine: State transitions and persistence
- OutcomeScaffoldingMapper: Field extraction from artifacts
- OutcomeFormulatorEngine: Event handling and orchestration
- Mapping Registry: Archetype mapping loading and lookup

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


# =============================================================================
# Test: OutcomeReadinessState Enum
# =============================================================================

class TestOutcomeReadinessState:
    """Tests for the OutcomeReadinessState enum and thresholds."""

    def test_state_enum_values(self):
        """Verify all five readiness states exist."""
        from modules.outcome_formulator.outcome_readiness_state_machine import OutcomeReadinessState

        states = list(OutcomeReadinessState)
        assert len(states) == 5
        assert OutcomeReadinessState.UNTRACKED in states
        assert OutcomeReadinessState.EMERGING in states
        assert OutcomeReadinessState.PARTIAL in states
        assert OutcomeReadinessState.SUBSTANTIAL in states
        assert OutcomeReadinessState.READY in states

    def test_state_thresholds(self):
        """Verify state thresholds are correctly defined."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessState,
            STATE_THRESHOLDS,
        )

        assert STATE_THRESHOLDS[OutcomeReadinessState.EMERGING] == 0.10
        assert STATE_THRESHOLDS[OutcomeReadinessState.PARTIAL] == 0.25
        assert STATE_THRESHOLDS[OutcomeReadinessState.SUBSTANTIAL] == 0.55
        assert STATE_THRESHOLDS[OutcomeReadinessState.READY] == 0.80

    def test_state_order(self):
        """Verify STATE_ORDER defines forward transitions."""
        from modules.outcome_formulator.outcome_readiness_state_machine import STATE_ORDER

        assert len(STATE_ORDER) == 5
        assert STATE_ORDER[0] == "UNTRACKED"
        assert STATE_ORDER[4] == "READY"


# =============================================================================
# Test: OutcomeReadinessStateMachine
# =============================================================================

class TestOutcomeReadinessStateMachine:
    """Tests for the Outcome Readiness State Machine."""

    def test_machine_initialization(self):
        """Machine initializes with db and event_bus."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessStateMachine,
        )

        machine = OutcomeReadinessStateMachine(db=None, event_bus=None)
        assert machine is not None
        assert machine.db is None
        assert machine.event_bus is None

    def test_machine_collection_name(self):
        """Machine uses correct collection name."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessStateMachine,
        )

        assert OutcomeReadinessStateMachine.COLLECTION == "outcome_readiness"

    def test_readiness_score_computation_empty(self):
        """Empty fields list returns 0.0 score."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessStateMachine,
        )

        machine = OutcomeReadinessStateMachine(db=None, event_bus=None)
        score = machine._compute_readiness_score([], None)
        assert score == 0.0

    def test_readiness_score_computation_with_fields(self):
        """Fields with confidence above floor contribute to score."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessStateMachine,
            OutcomeFieldRecord,
        )

        machine = OutcomeReadinessStateMachine(db=None, event_bus=None)

        fields = [
            OutcomeFieldRecord(
                field_key="field1",
                value="test",
                confidence=0.80,
                source_event_id="evt1",
                source_event_type="vision_artifact_finalized",
            ),
            OutcomeFieldRecord(
                field_key="field2",
                value="test2",
                confidence=0.60,
                source_event_id="evt2",
                source_event_type="vision_artifact_finalized",
            ),
        ]

        score = machine._compute_readiness_score(fields, None)
        # (0.80 + 0.60) / 2 = 0.70
        assert score == 0.70

    def test_readiness_score_ignores_low_confidence(self):
        """Fields with confidence below 0.30 floor are ignored."""
        from modules.outcome_formulator.outcome_readiness_state_machine import (
            OutcomeReadinessStateMachine,
            OutcomeFieldRecord,
        )

        machine = OutcomeReadinessStateMachine(db=None, event_bus=None)

        fields = [
            OutcomeFieldRecord(
                field_key="field1",
                value="test",
                confidence=0.80,
                source_event_id="evt1",
                source_event_type="vision_artifact_finalized",
            ),
            OutcomeFieldRecord(
                field_key="field2",
                value="test2",
                confidence=0.20,  # Below 0.30 floor
                source_event_id="evt2",
                source_event_type="vision_artifact_finalized",
            ),
        ]

        score = machine._compute_readiness_score(fields, None)
        # Only field1 contributes, so score = 0.80
        assert score == 0.80


# =============================================================================
# Test: OutcomeScaffoldingMapper
# =============================================================================

class TestOutcomeScaffoldingMapper:
    """Tests for the Outcome Scaffolding Mapper."""

    def test_mapper_initialization(self):
        """Mapper initializes with mapping registry."""
        from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeScaffoldingMapper
        from modules.outcome_formulator.mappings import mapping_registry

        mapper = OutcomeScaffoldingMapper(mapping_registry=mapping_registry)
        assert mapper is not None
        assert mapper.mapping_registry is not None

    def test_map_event_returns_list(self):
        """map_event returns a list of extracted field values."""
        from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeScaffoldingMapper
        from modules.outcome_formulator.mappings import mapping_registry

        mapper = OutcomeScaffoldingMapper(mapping_registry=mapping_registry)

        # Mock vision finalization event payload
        payload = {
            "artifact_id": "artifact-123",
            "event_id": "evt-456",
            "artifact": {
                "problem_statement": "Users struggle to find innovation methodologies.",
                "target_user": "Innovation teams",
                "value_proposition": "AI-powered coaching",
            }
        }

        results = mapper.map_event(
            archetype="lean_startup",
            event_type="vision_artifact_finalized",
            event_payload=payload,
        )

        # Should return a list (possibly empty if extractors don't find matches)
        assert isinstance(results, list)


# =============================================================================
# Test: Mapping Registry
# =============================================================================

class TestMappingRegistry:
    """Tests for the Outcome Mapping Registry."""

    def test_get_mappings_for_lean_startup(self):
        """Lean Startup archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("lean_startup")
        # 17 fields: BMC (9) + Growth Engine (5) + Experiment Board (3)
        assert len(mappings) == 17

    def test_get_mappings_for_design_thinking(self):
        """Design Thinking archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("design_thinking")
        # 12 fields: Empathy Map (4) + Journey Map (5) + Prototype Testing (3)
        assert len(mappings) == 12

    def test_get_mappings_for_stage_gate(self):
        """Stage-Gate archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("stage_gate")
        # 6 fields: Gate Review Package
        assert len(mappings) == 6

    def test_get_mappings_for_triz(self):
        """TRIZ archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("triz")
        # 4 fields: Contradiction Resolution Document
        assert len(mappings) == 4

    def test_get_mappings_for_blue_ocean(self):
        """Blue Ocean archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("blue_ocean")
        # 9 fields: Strategy Canvas (5) + ERRC Grid (4)
        assert len(mappings) == 9

    def test_get_mappings_for_incubation(self):
        """Incubation archetype returns correct number of mappings."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("incubation")
        # 5 fields: Investment Readiness Package
        assert len(mappings) == 5

    def test_total_mappings_count(self):
        """Total mappings across all archetypes is 53."""
        from modules.outcome_formulator.mappings import mapping_registry

        total = 0
        archetypes = [
            "lean_startup", "design_thinking", "stage_gate",
            "triz", "blue_ocean", "incubation"
        ]
        for archetype in archetypes:
            mappings = mapping_registry.get_mappings_for_archetype(archetype)
            total += len(mappings)

        # 17 + 12 + 6 + 4 + 9 + 5 = 53
        assert total == 53

    def test_unknown_archetype_returns_empty(self):
        """Unknown archetype returns empty list."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("unknown_archetype")
        assert mappings == []

    def test_mapping_structure(self):
        """Each mapping has required attributes."""
        from modules.outcome_formulator.mappings import mapping_registry

        mappings = mapping_registry.get_mappings_for_archetype("lean_startup")
        for mapping in mappings:
            assert hasattr(mapping, "archetype")
            assert hasattr(mapping, "artifact_type")
            assert hasattr(mapping, "field_key")
            assert hasattr(mapping, "source_event_types")
            assert hasattr(mapping, "extractor_fn")
            assert hasattr(mapping, "weight")
            assert hasattr(mapping, "mandatory")
            assert hasattr(mapping, "confidence_floor")


# =============================================================================
# Test: OutcomeFormulatorEngine
# =============================================================================

class TestOutcomeFormulatorEngine:
    """Tests for the Outcome Formulator Engine."""

    def test_engine_initialization(self):
        """Engine initializes with required components."""
        from modules.outcome_formulator.outcome_formulator_engine import OutcomeFormulatorEngine
        from modules.outcome_formulator.outcome_readiness_state_machine import OutcomeReadinessStateMachine
        from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeScaffoldingMapper
        from modules.outcome_formulator.mappings import mapping_registry

        state_machine = OutcomeReadinessStateMachine(db=None, event_bus=None)
        mapper = OutcomeScaffoldingMapper(mapping_registry=mapping_registry)

        engine = OutcomeFormulatorEngine(
            state_machine=state_machine,
            mapper=mapper,
            pursuit_service=None,
            event_bus=None,
        )

        assert engine is not None
        assert engine.state_machine is not None
        assert engine.mapper is not None

    def test_tracked_event_types(self):
        """Engine tracks the correct 14 event types."""
        from modules.outcome_formulator.outcome_formulator_engine import TRACKED_EVENT_TYPES

        assert len(TRACKED_EVENT_TYPES) == 14
        assert "vision_artifact_finalized" in TRACKED_EVENT_TYPES
        assert "fear_artifact_created" in TRACKED_EVENT_TYPES
        assert "hypothesis_artifact_validated" in TRACKED_EVENT_TYPES
        assert "coaching_convergence_decision_recorded" in TRACKED_EVENT_TYPES


# =============================================================================
# Test: Display Label Registry Extensions
# =============================================================================

class TestDisplayLabelExtensions:
    """Tests for v4.6 Display Label Registry categories."""

    def test_outcome_artifact_type_labels(self):
        """outcome_artifact_type category has 12 entries."""
        from shared.display_labels import DisplayLabels

        labels = DisplayLabels.get_all("outcome_artifact_type")
        assert len(labels) == 12

        # Check a few specific entries
        assert "business_model_canvas" in labels
        assert "strategy_canvas" in labels
        assert "investment_readiness_package" in labels

    def test_outcome_readiness_state_labels(self):
        """outcome_readiness_state category has 5 entries."""
        from shared.display_labels import DisplayLabels

        labels = DisplayLabels.get_all("outcome_readiness_state")
        assert len(labels) == 5

        assert "UNTRACKED" in labels
        assert "EMERGING" in labels
        assert "PARTIAL" in labels
        assert "SUBSTANTIAL" in labels
        assert "READY" in labels

    def test_outcome_readiness_hint_labels(self):
        """outcome_readiness_hint category has 4 entries."""
        from shared.display_labels import DisplayLabels

        labels = DisplayLabels.get_all("outcome_readiness_hint")
        assert len(labels) == 4

        # UNTRACKED has no hint (nothing to encourage yet)
        assert "EMERGING" in labels
        assert "PARTIAL" in labels
        assert "SUBSTANTIAL" in labels
        assert "READY" in labels

    def test_outcome_archetype_descriptor_labels(self):
        """outcome_archetype_descriptor category has 6 entries."""
        from shared.display_labels import DisplayLabels

        labels = DisplayLabels.get_all("outcome_archetype_descriptor")
        assert len(labels) == 6

        assert "lean_startup" in labels
        assert "design_thinking" in labels
        assert "stage_gate" in labels
        assert "triz" in labels
        assert "blue_ocean" in labels
        assert "incubation" in labels

    def test_label_get_method(self):
        """DisplayLabels.get() returns correct labels."""
        from shared.display_labels import DisplayLabels

        label = DisplayLabels.get("outcome_readiness_state", "READY")
        assert label == "Ready to review"

        label = DisplayLabels.get("outcome_artifact_type", "business_model_canvas")
        assert label == "Business Model"


# =============================================================================
# Test: Telemetry Events
# =============================================================================

class TestOutcomeTelemetry:
    """Tests for v4.6 Outcome Formulator telemetry."""

    def test_outcome_events_registered(self):
        """Outcome telemetry events are registered in EVENTS dict."""
        from services.telemetry import EVENTS

        outcome_events = [
            "outcome.field_captured",
            "outcome.field_updated",
            "outcome.state_transition",
            "outcome.artifact_tracking_started",
            "outcome.artifact_ready",
        ]

        for event in outcome_events:
            assert event in EVENTS, f"Event {event} not registered"

    def test_track_outcome_helper(self):
        """track_outcome() helper creates correct properties."""
        from services.telemetry import track_outcome, track

        with patch('services.telemetry.track') as mock_track:
            track_outcome(
                event_type="field_captured",
                archetype="lean_startup",
                artifact_type="business_model_canvas",
                field_key="customer_segments",
                confidence=0.85,
                pursuit_id="pursuit-123"
            )

            mock_track.assert_called_once()
            call_args = mock_track.call_args
            event_name = call_args[0][0]
            properties = call_args[0][2]

            assert event_name == "outcome.field_captured"
            assert properties["archetype"] == "lean_startup"
            assert properties["artifact_type"] == "business_model_canvas"
            assert properties["field_key"] == "customer_segments"
            assert properties["confidence"] == 0.85
            assert properties["pursuit_id"] == "pursuit-123"


# =============================================================================
# Test: Module Structure
# =============================================================================

class TestModuleStructure:
    """Tests for v4.6 module structure and imports."""

    def test_outcome_formulator_init_exports(self):
        """Outcome Formulator __init__ exports required classes."""
        from modules.outcome_formulator import (
            OutcomeReadinessState,
            OutcomeReadinessStateMachine,
            OutcomeScaffoldingMapper,
            OutcomeFormulatorEngine,
            OutcomeEventBusAdapter,
        )

        # All classes should be importable
        assert OutcomeReadinessState is not None
        assert OutcomeReadinessStateMachine is not None
        assert OutcomeScaffoldingMapper is not None
        assert OutcomeFormulatorEngine is not None
        assert OutcomeEventBusAdapter is not None

    def test_mappings_module_structure(self):
        """Mappings module has correct structure."""
        from modules.outcome_formulator.mappings import mapping_registry
        from modules.outcome_formulator.mappings.mapping_registry import (
            get_mappings_for_archetype,
            get_artifact_type_for_field,
        )

        # Registry and helper functions should be importable
        assert mapping_registry is not None
        assert callable(get_mappings_for_archetype)
        assert callable(get_artifact_type_for_field)
