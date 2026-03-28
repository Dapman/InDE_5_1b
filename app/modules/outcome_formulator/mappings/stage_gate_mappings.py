"""
Stage-Gate Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for Stage-Gate outcome artifacts:
  - Gate Review Package (6 gate sections)

Total: 6 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # GATE REVIEW PACKAGE (6 sections)
    # ===================================
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="innovation_brief",
        source_event_types=["vision_artifact_finalized"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Executive summary of the innovation",
    ),
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="business_case",
        source_event_types=["hypothesis_artifact_validated", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Business case and financial projections",
    ),
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="technical_assessment",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.15,
        mandatory=False,
        confidence_floor=0.30,
        description="Technical feasibility assessment",
    ),
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="risk_assessment",
        source_event_types=["fear_artifact_resolved", "fear_artifact_created"],
        extractor_fn="extract_from_fear_artifact",
        weight=0.15,
        mandatory=False,
        confidence_floor=0.30,
        description="Risk identification and mitigation",
    ),
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="resource_requirements",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Resource and budget requirements",
    ),
    OutcomeFieldMapping(
        archetype="stage_gate",
        artifact_type="gate_review_package",
        field_key="launch_readiness_assessment",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Launch readiness and go/no-go criteria",
    ),
]
