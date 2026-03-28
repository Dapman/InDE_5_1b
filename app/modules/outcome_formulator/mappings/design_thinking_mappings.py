"""
Design Thinking Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for Design Thinking outcome artifacts:
  - Empathy Map (4 quadrants)
  - Journey Map (5 stages)
  - Prototype Testing Report (4 sections)

Total: 12 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # EMPATHY MAP (4 quadrants)
    # ===================================
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="empathy_map",
        field_key="thinks_feels",
        source_event_types=["persona_artifact_created", "persona_artifact_updated"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="What user thinks and feels",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="empathy_map",
        field_key="sees",
        source_event_types=["persona_artifact_created", "vision_artifact_finalized"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="What user sees in their environment",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="empathy_map",
        field_key="hears",
        source_event_types=["persona_artifact_created"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="What user hears from others",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="empathy_map",
        field_key="says_does",
        source_event_types=["persona_artifact_created", "hypothesis_artifact_validated"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="What user says and does",
    ),

    # ===================================
    # JOURNEY MAP (5 stages)
    # ===================================
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="journey_map",
        field_key="awareness_stage",
        source_event_types=["vision_artifact_finalized", "persona_artifact_created"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="User awareness stage",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="journey_map",
        field_key="consideration_stage",
        source_event_types=["persona_artifact_created"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="User consideration stage",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="journey_map",
        field_key="decision_stage",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="User decision stage",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="journey_map",
        field_key="use_stage",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="User use stage",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="journey_map",
        field_key="advocacy_stage",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="User advocacy stage",
    ),

    # ===================================
    # PROTOTYPE TESTING REPORT (4 sections)
    # ===================================
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="prototype_testing_report",
        field_key="what_we_tested",
        source_event_types=["hypothesis_artifact_created"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="What was tested",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="prototype_testing_report",
        field_key="what_we_found",
        source_event_types=["hypothesis_artifact_validated", "hypothesis_artifact_invalidated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.35,
        mandatory=True,
        confidence_floor=0.30,
        description="Key findings from testing",
    ),
    OutcomeFieldMapping(
        archetype="design_thinking",
        artifact_type="prototype_testing_report",
        field_key="iterations_made",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="Iterations based on feedback",
    ),
]
