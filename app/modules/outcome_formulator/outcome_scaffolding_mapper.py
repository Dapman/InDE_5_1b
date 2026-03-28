"""
Outcome Scaffolding Mapper

InDE MVP v4.6.0 - The Outcome Engine

Maps pursuit event data to outcome artifact fields. Stateless - takes an event
and a set of field mappings, returns extracted field values with confidence scores.

Pattern: the mapper produces (field_key, value, confidence, source_event_id) tuples.
The engine calls the mapper on each qualifying event.
The state machine persists the results.

This module does NOT persist state. It does NOT modify any collection.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class OutcomeFieldMapping:
    """
    Declares how a single outcome artifact field is populated from pursuit data.
    """
    archetype: str
    artifact_type: str
    field_key: str
    source_event_types: List[str]   # Events that may contribute to this field
    extractor_fn: str               # Name of extraction function in this module
    weight: float                   # Contribution to artifact readiness (0.0-1.0)
    mandatory: bool                 # Mandatory fields gate READY state
    confidence_floor: float = 0.30  # Min confidence to count as contribution
    description: str = ""           # Optional: human-readable mapping description


@dataclass
class ExtractedFieldValue:
    """Result of a single field extraction."""
    field_key: str
    value: str
    confidence: float               # 0.0-1.0
    source_event_id: str
    source_event_type: str
    source_artifact_id: Optional[str] = None


class OutcomeScaffoldingMapper:
    """
    Applies field mappings to pursuit events to extract outcome artifact data.
    """

    def __init__(self, mapping_registry):
        self.mapping_registry = mapping_registry

    def map_event(
        self,
        archetype: str,
        event_type: str,
        event_payload: dict,
    ) -> List[ExtractedFieldValue]:
        """
        Process a single pursuit event against all registered mappings for
        the given archetype. Returns a list of extracted field values for any
        fields whose source_event_types match the incoming event_type.

        Returns an empty list if no mappings match.
        """
        mappings = self.mapping_registry.get_mappings_for_archetype(archetype)
        relevant = [m for m in mappings if event_type in m.source_event_types]
        results = []

        for mapping in relevant:
            extractor = getattr(self, mapping.extractor_fn, None)
            if extractor:
                try:
                    extracted = extractor(mapping, event_payload)
                    if extracted and extracted.confidence >= mapping.confidence_floor:
                        results.append(extracted)
                except Exception as e:
                    logger.warning(
                        f"Extractor {mapping.extractor_fn} failed for "
                        f"{mapping.artifact_type}.{mapping.field_key}: {e}"
                    )

        return results

    # ------------------------------------------
    # Extraction functions - one per source type
    # ------------------------------------------

    def extract_from_vision_artifact(
        self, mapping: OutcomeFieldMapping, payload: dict
    ) -> Optional[ExtractedFieldValue]:
        """
        Extract a field value from a vision artifact finalization event.
        The vision artifact content is the primary source for Value Proposition,
        Customer Segments summary, Innovation Intent, and similar fields.
        Confidence: 0.60 base, raised to 0.80 if artifact is in FINAL state.
        """
        artifact = payload.get("artifact", {})
        content = artifact.get("content", "")
        artifact_id = artifact.get("id", payload.get("artifact_id", ""))
        state = artifact.get("state", "")

        if not content:
            return None

        # Extract based on field_key
        value = self._extract_vision_field(mapping.field_key, content, artifact)

        if not value:
            return None

        confidence = 0.80 if state == "FINAL" else 0.60

        return ExtractedFieldValue(
            field_key=mapping.field_key,
            value=value,
            confidence=confidence,
            source_event_id=payload.get("event_id", ""),
            source_event_type=payload.get("event_type", "vision_artifact_finalized"),
            source_artifact_id=artifact_id,
        )

    def extract_from_fear_artifact(
        self, mapping: OutcomeFieldMapping, payload: dict
    ) -> Optional[ExtractedFieldValue]:
        """
        Extract a field value from a fear artifact resolved event.
        Resolved fears contribute to risk sections, Cost Structure (BMC),
        Contradiction Identification (TRIZ), and Key Uncertainties (Experiment Board).
        Confidence: 0.55 base, raised to 0.75 if fear has a resolution strategy.
        """
        artifact = payload.get("artifact", {})
        content = artifact.get("content", "")
        artifact_id = artifact.get("id", payload.get("artifact_id", ""))
        has_resolution = bool(artifact.get("resolution_strategy"))

        if not content:
            return None

        value = self._extract_fear_field(mapping.field_key, content, artifact)

        if not value:
            return None

        confidence = 0.75 if has_resolution else 0.55

        return ExtractedFieldValue(
            field_key=mapping.field_key,
            value=value,
            confidence=confidence,
            source_event_id=payload.get("event_id", ""),
            source_event_type=payload.get("event_type", "fear_artifact_resolved"),
            source_artifact_id=artifact_id,
        )

    def extract_from_hypothesis_artifact(
        self, mapping: OutcomeFieldMapping, payload: dict
    ) -> Optional[ExtractedFieldValue]:
        """
        Extract a field value from a hypothesis artifact state change.
        Validated hypotheses contribute high-confidence data to BMC Revenue Streams,
        Growth Engine experiments, Prototype Testing Report.
        Confidence: 0.40 (in progress), 0.75 (validated), 0.50 (invalidated - as
        negative evidence for alternative fields).
        """
        artifact = payload.get("artifact", {})
        content = artifact.get("content", "")
        artifact_id = artifact.get("id", payload.get("artifact_id", ""))
        state = artifact.get("state", "")

        if not content:
            return None

        value = self._extract_hypothesis_field(mapping.field_key, content, artifact)

        if not value:
            return None

        if state == "validated":
            confidence = 0.75
        elif state == "invalidated":
            confidence = 0.50
        else:
            confidence = 0.40

        return ExtractedFieldValue(
            field_key=mapping.field_key,
            value=value,
            confidence=confidence,
            source_event_id=payload.get("event_id", ""),
            source_event_type=payload.get("event_type", "hypothesis_artifact_validated"),
            source_artifact_id=artifact_id,
        )

    def extract_from_coaching_decision(
        self, mapping: OutcomeFieldMapping, payload: dict
    ) -> Optional[ExtractedFieldValue]:
        """
        Extract a field value from a coaching convergence decision event.
        Coaching decisions contribute to strategic rationale fields, pivot explanations,
        and TRIZ principle applications.
        Confidence: 0.50 base (coaching decision may evolve). Raised to 0.70 if the
        decision was made in a CONSOLIDATING convergence state.
        """
        decision = payload.get("decision", {})
        content = decision.get("rationale", "")
        convergence_state = payload.get("convergence_state", "")

        if not content:
            return None

        value = self._extract_decision_field(mapping.field_key, content, payload)

        if not value:
            return None

        confidence = 0.70 if convergence_state == "CONSOLIDATING" else 0.50

        return ExtractedFieldValue(
            field_key=mapping.field_key,
            value=value,
            confidence=confidence,
            source_event_id=payload.get("event_id", ""),
            source_event_type=payload.get("event_type", "coaching_convergence_decision_recorded"),
            source_artifact_id=None,
        )

    def extract_from_persona_artifact(
        self, mapping: OutcomeFieldMapping, payload: dict
    ) -> Optional[ExtractedFieldValue]:
        """
        Extract a field value from a persona artifact creation or update event.
        Persona data contributes to Empathy Map quadrants, Journey Map stages,
        and BMC Customer Segments.
        Confidence: 0.65 base.
        """
        artifact = payload.get("artifact", {})
        content = artifact.get("content", "")
        artifact_id = artifact.get("id", payload.get("artifact_id", ""))

        if not content:
            return None

        value = self._extract_persona_field(mapping.field_key, content, artifact)

        if not value:
            return None

        return ExtractedFieldValue(
            field_key=mapping.field_key,
            value=value,
            confidence=0.65,
            source_event_id=payload.get("event_id", ""),
            source_event_type=payload.get("event_type", "persona_artifact_created"),
            source_artifact_id=artifact_id,
        )

    # ------------------------------------------
    # Field extraction helpers
    # ------------------------------------------

    def _extract_vision_field(self, field_key: str, content: str, artifact: dict) -> Optional[str]:
        """Extract specific field from vision artifact content."""
        # For now, return content as-is; can be enhanced with NLP extraction
        if field_key in ["value_propositions", "innovation_intent", "problem_statement"]:
            return content[:500] if len(content) > 500 else content
        if field_key == "customer_segments":
            # Could extract from structured data in artifact
            return artifact.get("target_audience", content[:300])
        return content[:500] if content else None

    def _extract_fear_field(self, field_key: str, content: str, artifact: dict) -> Optional[str]:
        """Extract specific field from fear artifact content."""
        if field_key in ["key_risks", "cost_structure_risks", "contradictions"]:
            return content[:500] if len(content) > 500 else content
        return content[:500] if content else None

    def _extract_hypothesis_field(self, field_key: str, content: str, artifact: dict) -> Optional[str]:
        """Extract specific field from hypothesis artifact content."""
        if field_key in ["revenue_streams", "experiment_results", "validated_assumptions"]:
            return content[:500] if len(content) > 500 else content
        return content[:500] if content else None

    def _extract_decision_field(self, field_key: str, content: str, payload: dict) -> Optional[str]:
        """Extract specific field from coaching decision content."""
        if field_key in ["strategic_rationale", "pivot_explanation", "resolution_approach"]:
            return content[:500] if len(content) > 500 else content
        return content[:500] if content else None

    def _extract_persona_field(self, field_key: str, content: str, artifact: dict) -> Optional[str]:
        """Extract specific field from persona artifact content."""
        # Can extract specific quadrants for empathy map, stages for journey map
        return content[:500] if content else None
