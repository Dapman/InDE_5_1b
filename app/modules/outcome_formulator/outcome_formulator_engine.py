"""
Outcome Formulator Engine

InDE MVP v4.6.0 - The Outcome Engine

Architecturally parallel to the Vision Formulator. The Vision Formulator scaffolds
the front end of an innovation pursuit - generating the innovator's story through
coached conversation. The Outcome Formulator prepares the back end - tracking how
ready the pursuit's characteristic deliverables are as the pursuit progresses.

The engine:
  1. Registers as a subscriber on the InDE event bus (via OutcomeEventBusAdapter).
  2. On each qualifying event, calls OutcomeScaffoldingMapper to extract field values.
  3. Writes extracted values to the OutcomeReadinessStateMachine for persistence.
  4. Tracks per-pursuit, per-archetype outcome readiness context.

The engine is silent: it does not modify coaching behavior, scaffolding state,
session logic, or any user-facing interface. It reads from the event stream and
writes to the outcome_readiness collection. That is all.

Constructor dependencies (injected):
  - state_machine: OutcomeReadinessStateMachine
  - mapper: OutcomeScaffoldingMapper
  - pursuit_service: access to pursuit archetype and metadata
  - db: MongoDB database client
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


TRACKED_EVENT_TYPES = [
    "vision_artifact_finalized",
    "vision_artifact_updated",
    "fear_artifact_resolved",
    "fear_artifact_created",
    "hypothesis_artifact_created",
    "hypothesis_artifact_validated",
    "hypothesis_artifact_invalidated",
    "validation_artifact_completed",
    "coaching_convergence_decision_recorded",
    "persona_artifact_created",
    "persona_artifact_updated",
    "pursuit_phase_transitioned",
    # v4.6 additional artifact events
    "artifact.generated",
    "artifact.updated",
]


class OutcomeFormulatorEngine:
    """
    Tracks outcome artifact readiness throughout the pursuit lifecycle.
    Registered as an event bus subscriber. Processes qualifying events silently.
    """

    def __init__(self, state_machine, mapper, pursuit_service, event_bus):
        self.state_machine = state_machine
        self.mapper = mapper
        self.pursuit_service = pursuit_service
        self.event_bus = event_bus

    def initialize(self) -> None:
        """Register as a subscriber on the event bus for all tracked event types."""
        for event_type in TRACKED_EVENT_TYPES:
            self.event_bus.register(event_type, self.handle_event)
        logger.info(
            f"OutcomeFormulatorEngine registered for {len(TRACKED_EVENT_TYPES)} event types."
        )

    async def handle_event(self, event) -> None:
        """
        Process a single pursuit event. Called by the event bus on each qualifying event.
        Extracts field values from the event, persists to state machine.
        Silent on failure - never raises to the event bus.
        """
        try:
            # Handle both DomainEvent objects and raw dicts
            if hasattr(event, "event_type"):
                event_type = event.event_type
                payload = event.payload if hasattr(event, "payload") else {}
            else:
                event_type = event.get("event_type", "")
                payload = event.get("payload", event)

            pursuit_id = payload.get("pursuit_id")
            if not pursuit_id:
                return

            archetype = await self._get_archetype(pursuit_id)
            if not archetype:
                return

            extracted_fields = self.mapper.map_event(archetype, event_type, payload)

            for field_value in extracted_fields:
                from .outcome_readiness_state_machine import OutcomeFieldRecord

                field_record = OutcomeFieldRecord(
                    field_key=field_value.field_key,
                    value=field_value.value,
                    confidence=field_value.confidence,
                    source_event_id=field_value.source_event_id,
                    source_event_type=field_value.source_event_type,
                    source_artifact_id=field_value.source_artifact_id,
                    captured_at=datetime.now(timezone.utc).isoformat(),
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )

                # Determine artifact_type from field_key via mapping registry
                artifact_type = self.mapper.mapping_registry.get_artifact_type_for_field(
                    archetype, field_value.field_key
                )

                await self.state_machine.update_field(
                    pursuit_id=pursuit_id,
                    archetype=archetype,
                    artifact_type=artifact_type,
                    field_record=field_record,
                )

        except Exception as e:
            logger.error(
                f"OutcomeFormulatorEngine.handle_event failed silently: "
                f"event={getattr(event, 'event_type', 'unknown')}, error={e}"
            )

    async def get_outcome_readiness_context(self, pursuit_id: str) -> dict:
        """
        Return the full outcome readiness context for a pursuit.
        Used by the admin API and (in v4.7) by the ITD Composition Engine.
        """
        archetype = await self._get_archetype(pursuit_id)
        if not archetype:
            return {"pursuit_id": pursuit_id, "archetype": None, "outcome_artifacts": []}

        records = await self.state_machine.get_all_records_for_pursuit(pursuit_id)

        return {
            "pursuit_id": pursuit_id,
            "archetype": archetype,
            "outcome_artifacts": [
                {
                    "artifact_type": r.artifact_type,
                    "state": r.state.value,
                    "readiness_score": r.readiness_score,
                    "fields_populated": len([f for f in r.fields if f.confidence > 0.30]),
                    "fields_total": self._get_total_fields(archetype, r.artifact_type),
                    "last_updated": r.updated_at,
                }
                for r in records
            ],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _get_archetype(self, pursuit_id: str) -> Optional[str]:
        """Get the archetype for a pursuit."""
        if self.pursuit_service:
            try:
                pursuit = await self.pursuit_service.get_pursuit(pursuit_id)
                if pursuit:
                    return pursuit.get("archetype") or pursuit.get("methodology_archetype")
            except Exception as e:
                logger.warning(f"Failed to get archetype for {pursuit_id}: {e}")
        return None

    def _get_total_fields(self, archetype: str, artifact_type: str) -> int:
        """Get total number of fields for an artifact type."""
        mappings = self.mapper.mapping_registry.get_mappings_for_archetype(archetype)
        return len([m for m in mappings if m.artifact_type == artifact_type])
