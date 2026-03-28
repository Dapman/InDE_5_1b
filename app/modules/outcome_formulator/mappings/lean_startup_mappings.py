"""
Lean Startup Archetype Mappings

InDE MVP v4.6.0 - The Outcome Engine

Field mappings for Lean Startup outcome artifacts:
  - Business Model Canvas (9 fields)
  - Growth Engine Blueprint (5 fields)
  - Experiment Board (3 field groups)

Total: 17 OutcomeFieldMapping instances
"""

from modules.outcome_formulator.outcome_scaffolding_mapper import OutcomeFieldMapping

FIELD_MAPPINGS = [
    # ===================================
    # BUSINESS MODEL CANVAS (9 fields)
    # ===================================

    # Mandatory fields (3)
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="value_propositions",
        source_event_types=["vision_artifact_finalized", "vision_artifact_updated"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.15,
        mandatory=True,
        confidence_floor=0.30,
        description="Core value proposition from vision artifact",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="customer_segments",
        source_event_types=["vision_artifact_finalized", "persona_artifact_created"],
        extractor_fn="extract_from_vision_artifact",
        weight=0.15,
        mandatory=True,
        confidence_floor=0.30,
        description="Target customer segments from vision and persona",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="revenue_streams",
        source_event_types=["hypothesis_artifact_validated", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.15,
        mandatory=True,
        confidence_floor=0.30,
        description="Revenue model from validated hypotheses",
    ),

    # Non-mandatory fields (6)
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="channels",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Distribution and communication channels",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="customer_relationships",
        source_event_types=["persona_artifact_created", "vision_artifact_finalized"],
        extractor_fn="extract_from_persona_artifact",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Customer relationship strategy",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="key_activities",
        source_event_types=["vision_artifact_finalized", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Core activities required to deliver value",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="key_resources",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Key resources needed",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="key_partners",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.05,
        mandatory=False,
        confidence_floor=0.30,
        description="Strategic partnerships",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="business_model_canvas",
        field_key="cost_structure",
        source_event_types=["fear_artifact_resolved", "fear_artifact_created"],
        extractor_fn="extract_from_fear_artifact",
        weight=0.10,
        mandatory=False,
        confidence_floor=0.30,
        description="Cost drivers from risk analysis",
    ),

    # ===================================
    # GROWTH ENGINE BLUEPRINT (5 fields)
    # ===================================
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="growth_engine_blueprint",
        field_key="growth_model",
        source_event_types=["hypothesis_artifact_validated", "coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.25,
        mandatory=True,
        confidence_floor=0.30,
        description="Primary growth model (viral, sticky, paid)",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="growth_engine_blueprint",
        field_key="key_metrics",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=True,
        confidence_floor=0.30,
        description="North star and supporting metrics",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="growth_engine_blueprint",
        field_key="growth_levers",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="Actionable growth levers",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="growth_engine_blueprint",
        field_key="validated_experiments",
        source_event_types=["hypothesis_artifact_validated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.20,
        mandatory=False,
        confidence_floor=0.30,
        description="Summary of validated experiments",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="growth_engine_blueprint",
        field_key="scaling_blockers",
        source_event_types=["fear_artifact_resolved"],
        extractor_fn="extract_from_fear_artifact",
        weight=0.15,
        mandatory=False,
        confidence_floor=0.30,
        description="Identified scaling blockers",
    ),

    # ===================================
    # EXPERIMENT BOARD (3 field groups)
    # ===================================
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="experiment_board",
        field_key="key_assumptions",
        source_event_types=["hypothesis_artifact_created", "vision_artifact_finalized"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.35,
        mandatory=True,
        confidence_floor=0.30,
        description="Key assumptions to test",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="experiment_board",
        field_key="experiment_results",
        source_event_types=["hypothesis_artifact_validated", "hypothesis_artifact_invalidated"],
        extractor_fn="extract_from_hypothesis_artifact",
        weight=0.35,
        mandatory=True,
        confidence_floor=0.30,
        description="Experiment results and learnings",
    ),
    OutcomeFieldMapping(
        archetype="lean_startup",
        artifact_type="experiment_board",
        field_key="next_experiments",
        source_event_types=["coaching_convergence_decision_recorded"],
        extractor_fn="extract_from_coaching_decision",
        weight=0.30,
        mandatory=False,
        confidence_floor=0.30,
        description="Planned next experiments",
    ),
]
