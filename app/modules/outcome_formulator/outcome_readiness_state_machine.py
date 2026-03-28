"""
Outcome Readiness State Machine

InDE MVP v4.6.0 - The Outcome Engine

Manages per-artifact readiness states for outcome artifacts, mirroring the
architectural pattern of the Scaffolding Readiness State Machine but operating
on back-end outcome deliverables rather than front-end scaffolding elements.

Each outcome artifact passes through five states:
  UNTRACKED   -> EMERGING -> PARTIAL -> SUBSTANTIAL -> READY

State transitions are forward-only. Confidence adjustments are allowed within
a state; state downgrade is not permitted.

Persists to MongoDB: outcome_readiness collection.
Emits events on state transition for IML capture (v4.7 ITD engine consumes these).

This module writes to the outcome_readiness collection and reads from it.
It does NOT write to any other MongoDB collection.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class OutcomeReadinessState(str, Enum):
    UNTRACKED = "UNTRACKED"
    EMERGING = "EMERGING"
    PARTIAL = "PARTIAL"
    SUBSTANTIAL = "SUBSTANTIAL"
    READY = "READY"


STATE_ORDER = [
    OutcomeReadinessState.UNTRACKED,
    OutcomeReadinessState.EMERGING,
    OutcomeReadinessState.PARTIAL,
    OutcomeReadinessState.SUBSTANTIAL,
    OutcomeReadinessState.READY,
]


# Score thresholds for state transitions
# (readiness_score must reach threshold to enter this state)
STATE_THRESHOLDS = {
    OutcomeReadinessState.EMERGING: 0.10,
    OutcomeReadinessState.PARTIAL: 0.25,
    OutcomeReadinessState.SUBSTANTIAL: 0.55,
    OutcomeReadinessState.READY: 0.80,
}


@dataclass
class OutcomeFieldRecord:
    """Persisted record of a single outcome artifact field value."""
    field_key: str
    value: str
    confidence: float
    source_event_id: str
    source_event_type: str
    source_artifact_id: Optional[str] = None
    captured_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.captured_at:
            self.captured_at = now
        if not self.updated_at:
            self.updated_at = now


@dataclass
class StateTransitionRecord:
    """Record of a state transition."""
    from_state: str
    to_state: str
    readiness_score: float
    timestamp: str


@dataclass
class OutcomeReadinessRecord:
    """Full readiness record for one artifact in one pursuit."""
    pursuit_id: str
    archetype: str
    artifact_type: str
    state: OutcomeReadinessState
    readiness_score: float
    fields: List[OutcomeFieldRecord] = field(default_factory=list)
    state_history: List[StateTransitionRecord] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class OutcomeReadinessStateMachine:
    """
    Manages outcome readiness state transitions and persistence.

    Constructor dependencies:
      - db: MongoDB database client (motor or pymongo)
      - event_bus: InDE event bus (for emitting transition events)
    """

    COLLECTION = "outcome_readiness"

    def __init__(self, db, event_bus=None):
        self.db = db
        self.collection = db[self.COLLECTION] if db else None
        self.event_bus = event_bus

    async def update_field(
        self,
        pursuit_id: str,
        archetype: str,
        artifact_type: str,
        field_record: OutcomeFieldRecord,
        archetype_mapping: Optional[Dict] = None,
    ) -> OutcomeReadinessState:
        """
        Update a single field value in the readiness record.
        Recompute readiness score. Transition state if threshold crossed.
        Returns the new state.
        """
        record = await self.get_record(pursuit_id, archetype, artifact_type)

        if record is None:
            record = OutcomeReadinessRecord(
                pursuit_id=pursuit_id,
                archetype=archetype,
                artifact_type=artifact_type,
                state=OutcomeReadinessState.UNTRACKED,
                readiness_score=0.0,
            )

        field_found = False
        for i, existing_field in enumerate(record.fields):
            if existing_field.field_key == field_record.field_key:
                if field_record.confidence > existing_field.confidence:
                    record.fields[i] = field_record
                field_found = True
                break

        if not field_found:
            record.fields.append(field_record)

        old_score = record.readiness_score
        record.readiness_score = self._compute_readiness_score(
            record.fields, archetype_mapping
        )

        old_state = record.state
        new_state = self._evaluate_state_transition(record, record.readiness_score)

        if new_state and new_state != old_state:
            record.state = new_state
            record.state_history.append(StateTransitionRecord(
                from_state=old_state.value,
                to_state=new_state.value,
                readiness_score=record.readiness_score,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            await self._emit_transition_event(
                pursuit_id, archetype, artifact_type, old_state, new_state
            )

        record.updated_at = datetime.now(timezone.utc).isoformat()
        await self._persist_record(record)

        return record.state

    async def get_record(
        self, pursuit_id: str, archetype: str, artifact_type: str
    ) -> Optional[OutcomeReadinessRecord]:
        """
        Retrieve the current readiness record for a specific artifact.
        Returns None if no data has been tracked yet (UNTRACKED).
        """
        if not self.collection:
            return None

        doc = await self.collection.find_one({
            "pursuit_id": pursuit_id,
            "archetype": archetype,
            "artifact_type": artifact_type,
        })

        if not doc:
            return None

        return self._doc_to_record(doc)

    async def get_all_records_for_pursuit(
        self, pursuit_id: str
    ) -> List[OutcomeReadinessRecord]:
        """
        Retrieve readiness records for all tracked artifacts in a pursuit.
        """
        if not self.collection:
            return []

        cursor = self.collection.find({"pursuit_id": pursuit_id})
        records = []
        async for doc in cursor:
            records.append(self._doc_to_record(doc))
        return records

    def _compute_readiness_score(
        self, fields: List[OutcomeFieldRecord], archetype_mapping: Optional[Dict] = None
    ) -> float:
        """
        Compute weighted readiness score from field values and confidence scores.
        If no archetype_mapping provided, uses equal weights.
        """
        if not fields:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for field_record in fields:
            weight = 1.0
            if archetype_mapping:
                mapping = archetype_mapping.get(field_record.field_key)
                if mapping:
                    weight = mapping.get("weight", 1.0)

            if field_record.confidence >= 0.30:
                weighted_sum += field_record.confidence * weight
                total_weight += weight

        if total_weight == 0.0:
            return 0.0

        return min(1.0, weighted_sum / total_weight)

    def _evaluate_state_transition(
        self, record: OutcomeReadinessRecord, new_score: float
    ) -> Optional[OutcomeReadinessState]:
        """
        Determine if a state transition should occur given the new score.
        Transition only moves forward. Returns new state or None if no change.
        """
        current_idx = STATE_ORDER.index(record.state)

        for next_state in STATE_ORDER[current_idx + 1:]:
            threshold = STATE_THRESHOLDS.get(next_state, 1.0)
            if new_score >= threshold:
                return next_state

        return None

    async def _emit_transition_event(
        self,
        pursuit_id: str,
        archetype: str,
        artifact_type: str,
        from_state: OutcomeReadinessState,
        to_state: OutcomeReadinessState,
    ) -> None:
        """
        Emit outcome.readiness.state_transition event on the event bus.
        """
        if self.event_bus:
            try:
                from events.schemas import DomainEvent
                event = DomainEvent(
                    event_type="outcome.readiness.state_transition",
                    payload={
                        "pursuit_id": pursuit_id,
                        "archetype": archetype,
                        "artifact_type": artifact_type,
                        "from_state": from_state.value,
                        "to_state": to_state.value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                self.event_bus.emit(event)
                logger.info(
                    f"Outcome readiness transition: {artifact_type} "
                    f"{from_state.value}->{to_state.value} for pursuit {pursuit_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to emit transition event: {e}")

    async def _persist_record(self, record: OutcomeReadinessRecord) -> None:
        """Persist record to MongoDB."""
        if not self.collection:
            return

        doc = {
            "pursuit_id": record.pursuit_id,
            "archetype": record.archetype,
            "artifact_type": record.artifact_type,
            "state": record.state.value,
            "readiness_score": record.readiness_score,
            "fields": [asdict(f) for f in record.fields],
            "state_history": [asdict(h) for h in record.state_history],
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

        await self.collection.update_one(
            {
                "pursuit_id": record.pursuit_id,
                "archetype": record.archetype,
                "artifact_type": record.artifact_type,
            },
            {"$set": doc},
            upsert=True,
        )

    def _doc_to_record(self, doc: Dict[str, Any]) -> OutcomeReadinessRecord:
        """Convert MongoDB document to OutcomeReadinessRecord."""
        fields = [
            OutcomeFieldRecord(
                field_key=f["field_key"],
                value=f["value"],
                confidence=f["confidence"],
                source_event_id=f["source_event_id"],
                source_event_type=f["source_event_type"],
                source_artifact_id=f.get("source_artifact_id"),
                captured_at=f.get("captured_at", ""),
                updated_at=f.get("updated_at", ""),
            )
            for f in doc.get("fields", [])
        ]

        state_history = [
            StateTransitionRecord(
                from_state=h["from_state"],
                to_state=h["to_state"],
                readiness_score=h["readiness_score"],
                timestamp=h["timestamp"],
            )
            for h in doc.get("state_history", [])
        ]

        return OutcomeReadinessRecord(
            pursuit_id=doc["pursuit_id"],
            archetype=doc["archetype"],
            artifact_type=doc["artifact_type"],
            state=OutcomeReadinessState(doc["state"]),
            readiness_score=doc["readiness_score"],
            fields=fields,
            state_history=state_history,
            created_at=doc.get("created_at", ""),
            updated_at=doc.get("updated_at", ""),
        )
