"""
Outcome Formulator Module

InDE MVP v4.6.0 — The Outcome Engine

Tracks outcome artifact readiness throughout the pursuit lifecycle.
Operates silently in the background, registering as an event bus subscriber
and writing to the outcome_readiness MongoDB collection.

Components:
  - OutcomeReadinessStateMachine: 5-state machine (UNTRACKED→READY)
  - OutcomeScaffoldingMapper: Stateless field extractor
  - OutcomeFormulatorEngine: Event bus subscriber
  - OutcomeEventBusAdapter: Startup registration
"""

from .outcome_readiness_state_machine import (
    OutcomeReadinessState,
    OutcomeReadinessStateMachine,
    OutcomeFieldRecord,
    OutcomeReadinessRecord,
    STATE_THRESHOLDS,
)
from .outcome_scaffolding_mapper import (
    OutcomeScaffoldingMapper,
    OutcomeFieldMapping,
    ExtractedFieldValue,
)
from .outcome_formulator_engine import OutcomeFormulatorEngine
from .outcome_event_bus_adapter import OutcomeEventBusAdapter

__all__ = [
    "OutcomeReadinessState",
    "OutcomeReadinessStateMachine",
    "OutcomeFieldRecord",
    "OutcomeReadinessRecord",
    "STATE_THRESHOLDS",
    "OutcomeScaffoldingMapper",
    "OutcomeFieldMapping",
    "ExtractedFieldValue",
    "OutcomeFormulatorEngine",
    "OutcomeEventBusAdapter",
]
