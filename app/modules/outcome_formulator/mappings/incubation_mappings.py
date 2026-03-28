"""
Incubation Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for Incubation outcome artifacts:
  - Investment Readiness Package (5 sections)

Total: 5 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # INVESTMENT READINESS PACKAGE (5 sections)
    # ===================================
    OutcomeFieldMapping(
        archetype="incubation",
        artifact_type="investment_readiness_package",
        field_key="executive_summary",
        source_event_types=["vision_artifact_finalized"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Executive summary for investors",
    ),
    OutcomeFieldMapping(
        archetype="incubation",
        artifact_type="investment_readiness_package",
        field_key="problem_opportunity",
        source_event_types=["vision_artifact_finalized", "fear_artifact_created"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Problem statement and market opportunity",
    ),
    OutcomeFieldMapping(
        archetype="incubation",
        artifact_type="investment_readiness_package",
        field_key="solution_differentiation",
        source_event_types=["vision_artifact_finalized", "hypothesis_artifact_validated"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Solution and key differentiators",
    ),
    OutcomeFieldMapping(
        archetype="incubation",
        artifact_type="investment_readiness_package",
        field_key="traction_validation",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="Traction and validation evidence",
    ),
    OutcomeFieldMapping(
        archetype="incubation",
        artifact_type="investment_readiness_package",
        field_key="funding_ask",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.15,
        mandatory=False,
        confidence_floor=0.30,
        description="Funding requirements and use of funds",
    ),
]
