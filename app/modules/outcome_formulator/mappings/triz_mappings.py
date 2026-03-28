"""
TRIZ Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for TRIZ outcome artifacts:
  - Contradiction Resolution Document (4 sections)

Total: 4 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # CONTRADICTION RESOLUTION DOCUMENT (4 sections)
    # ===================================
    OutcomeFieldMapping(
        archetype="triz",
        artifact_type="contradiction_resolution_doc",
        field_key="problem_statement",
        source_event_types=["vision_artifact_finalized"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Clear statement of the problem to solve",
    ),
    OutcomeFieldMapping(
        archetype="triz",
        artifact_type="contradiction_resolution_doc",
        field_key="contradictions_identified",
        source_event_types=["fear_artifact_created", "fear_artifact_resolved"],
        extractor_fn="extract_from_fear_artifact",
        weight=0.30,
        mandatory=True,
        confidence_floor=0.30,
        description="Technical or physical contradictions identified",
    ),
    OutcomeFieldMapping(
        archetype="triz",
        artifact_type="contradiction_resolution_doc",
        field_key="principles_applied",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="TRIZ inventive principles applied",
    ),
    OutcomeFieldMapping(
        archetype="triz",
        artifact_type="contradiction_resolution_doc",
        field_key="resolution_outcome",
        source_event_types=["hypothesis_artifact_validated", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Resolution outcome and validation",
    ),
]
