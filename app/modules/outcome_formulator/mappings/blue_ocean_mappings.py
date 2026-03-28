"""
Blue Ocean Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for Blue Ocean outcome artifacts:
  - Strategy Canvas (5 fields)
  - ERRC Grid (4 quadrants)

Total: 10 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # STRATEGY CANVAS (5 fields)
    # ===================================
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="strategy_canvas",
        field_key="competitive_factors",
        source_event_types=["vision_artifact_finalized", "fear_artifact_created"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Key competitive factors in the industry",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="strategy_canvas",
        field_key="industry_curve",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="Current industry strategic profile",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="strategy_canvas",
        field_key="target_curve",
        source_event_types=["vision_artifact_finalized", "hypothesis_artifact_validated"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Target strategic profile",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="strategy_canvas",
        field_key="differentiation_points",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.15,
        mandatory=True,
        confidence_floor=0.30,
        description="Key differentiation points",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="strategy_canvas",
        field_key="market_space_definition",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.15,
        mandatory=False,
        confidence_floor=0.30,
        description="New market space definition",
    ),

    # ===================================
    # ERRC GRID (4 quadrants)
    # ===================================
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="errc_grid",
        field_key="eliminate",
        source_event_types=["fear_artifact_resolved", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_fear_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Factors to eliminate",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="errc_grid",
        field_key="reduce",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Factors to reduce below industry standard",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="errc_grid",
        field_key="raise",
        source_event_types=["vision_artifact_finalized", "hypothesis_artifact_validated"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Factors to raise above industry standard",
    ),
    OutcomeFieldMapping(
        archetype="blue_ocean",
        artifact_type="errc_grid",
        field_key="create",
        source_event_types=["vision_artifact_finalized", "hypothesis_artifact_validated"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Factors to create that industry never offered",
    ),
]
