"""
InDE MVP v5.1b.0 - Export Template Registry

Defines 6 audience-targeted export template families, each with:
- Field mappings to ITD, Outcome Formulator, and coaching sources
- Minimum readiness thresholds
- Display names (methodology-brand-free for Language Sovereignty)

Template Families:
1. business_model_canvas    -> "Business Model Summary"
2. empathy_journey_map      -> "Customer Discovery Map"
3. gate_review_package      -> "Stage Review Package"
4. strategy_canvas          -> "Competitive Landscape Canvas"
5. contradiction_resolution -> "Constraint Resolution Record"
6. investment_readiness     -> "Investment Readiness Summary"

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FieldMapping:
    """Maps a template field to InDE data sources."""
    field_name: str              # Template field name (e.g., "value_proposition")
    itd_source: Optional[str]    # Dot-path into ITD layers
    outcome_source: Optional[str]  # Field key from Outcome Formulator
    coaching_source: Optional[str]  # Event type from coaching history
    fallback_text: str           # Used when source data is below threshold
    required: bool               # If True and fallback used, export is PARTIAL


@dataclass
class ExportTemplateSpec:
    """Specification for an export template family."""
    template_key: str               # Internal identifier
    display_name: str               # Innovator-facing, methodology-brand-free
    description: str                # Coach-facing description (language-sovereign)
    source_archetypes: List[str]    # Which archetypes produce this naturally
    available_to_all: bool          # True = always offered; False = archetype-gated
    min_outcome_readiness: float    # 0.0–1.0 threshold from Outcome Formulator
    field_mappings: List[FieldMapping]
    output_formats: List[str]       # ["markdown", "html", "pdf", "docx"]
    irc_integration: bool = False   # v4.10: True = include IRC resource appendix


@dataclass
class ExportAvailability:
    """Availability status for a specific template."""
    template_key: str
    display_name: str
    description: str
    available: bool
    readiness_score: float
    min_required: float
    missing_required_fields: List[str]
    output_formats: List[str]
    readiness_note: str  # Coach-friendly explanation


@dataclass
class TemplateReadinessResult:
    """Result of checking template readiness."""
    template_key: str
    status: str  # "READY", "PARTIAL", "BLOCKED"
    readiness_score: float
    missing_required_fields: List[str]
    missing_optional_fields: List[str]
    blocking_reason: Optional[str]


# =============================================================================
# TEMPLATE DEFINITIONS
# =============================================================================

# Business Model Summary (Lean Startup derivative)
BUSINESS_MODEL_CANVAS = ExportTemplateSpec(
    template_key="business_model_canvas",
    display_name="Business Model Summary",
    description="A structured overview of your business model components - value proposition, customer segments, channels, and validation evidence.",
    source_archetypes=["lean_startup", "incubation"],
    available_to_all=True,
    min_outcome_readiness=0.65,
    field_mappings=[
        FieldMapping(
            field_name="value_proposition",
            itd_source="thesis_statement.thesis_text",
            outcome_source="value_proposition_readiness",
            coaching_source="vision_artifact_finalized",
            fallback_text="[Value proposition still forming - revisit after customer validation]",
            required=True,
        ),
        FieldMapping(
            field_name="customer_segments",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="customer_segment_readiness",
            coaching_source="persona_artifact_finalized",
            fallback_text="[Customer segments under development]",
            required=True,
        ),
        FieldMapping(
            field_name="channels",
            itd_source="forward_projection.horizons.day_90.success_correlated_actions",
            outcome_source="channel_readiness",
            coaching_source=None,
            fallback_text="[Distribution channels being explored]",
            required=False,
        ),
        FieldMapping(
            field_name="revenue_streams",
            itd_source="forward_projection.horizons.day_180.narrative",
            outcome_source="revenue_model_readiness",
            coaching_source=None,
            fallback_text="[Revenue model under development]",
            required=False,
        ),
        FieldMapping(
            field_name="key_resources",
            itd_source="evidence_architecture.pivots",
            outcome_source="resource_requirements_readiness",
            coaching_source=None,
            fallback_text="[Key resources being identified]",
            required=False,
        ),
        FieldMapping(
            field_name="key_activities",
            itd_source="narrative_arc.acts",
            outcome_source="key_activities_readiness",
            coaching_source=None,
            fallback_text="[Key activities emerging from validation]",
            required=False,
        ),
        FieldMapping(
            field_name="key_partnerships",
            itd_source="pattern_connections.cross_pursuit.narrative",
            outcome_source="partnership_readiness",
            coaching_source=None,
            fallback_text="[Partnership strategy forming]",
            required=False,
        ),
        FieldMapping(
            field_name="cost_structure",
            itd_source="forward_projection.horizons.day_365.narrative",
            outcome_source="cost_structure_readiness",
            coaching_source=None,
            fallback_text="[Cost structure under analysis]",
            required=False,
        ),
        FieldMapping(
            field_name="validation_evidence",
            itd_source="evidence_architecture.confidence_trajectory",
            outcome_source="validation_evidence_readiness",
            coaching_source=None,
            fallback_text="[Validation evidence being assembled]",
            required=True,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
)

# Customer Discovery Map (Design Thinking derivative)
EMPATHY_JOURNEY_MAP = ExportTemplateSpec(
    template_key="empathy_journey_map",
    display_name="Customer Discovery Map",
    description="A visual journey through your customer understanding - who they are, what they need, and how you validated your assumptions.",
    source_archetypes=["design_thinking"],
    available_to_all=True,
    min_outcome_readiness=0.60,
    field_mappings=[
        FieldMapping(
            field_name="customer_profile",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="persona_readiness",
            coaching_source="persona_artifact_finalized",
            fallback_text="[Customer profile being developed through discovery]",
            required=True,
        ),
        FieldMapping(
            field_name="customer_goals",
            itd_source="thesis_statement.thesis_text",
            outcome_source="customer_goals_readiness",
            coaching_source="vision_artifact_finalized",
            fallback_text="[Customer goals emerging from research]",
            required=True,
        ),
        FieldMapping(
            field_name="customer_challenges",
            itd_source="narrative_arc.acts",
            outcome_source="customer_challenges_readiness",
            coaching_source="concerns_artifact_finalized",
            fallback_text="[Customer challenges being identified]",
            required=True,
        ),
        FieldMapping(
            field_name="touchpoints",
            itd_source="coachs_perspective.moments",
            outcome_source="touchpoint_readiness",
            coaching_source=None,
            fallback_text="[Customer touchpoints under exploration]",
            required=False,
        ),
        FieldMapping(
            field_name="insights",
            itd_source="pattern_connections.within_pursuit.narrative",
            outcome_source="insight_readiness",
            coaching_source=None,
            fallback_text="[Key insights still forming]",
            required=False,
        ),
        FieldMapping(
            field_name="opportunities",
            itd_source="forward_projection.synthesis_statement",
            outcome_source="opportunity_readiness",
            coaching_source=None,
            fallback_text="[Opportunity areas being validated]",
            required=False,
        ),
        FieldMapping(
            field_name="validation_methods",
            itd_source="evidence_architecture.pivots",
            outcome_source="validation_method_readiness",
            coaching_source=None,
            fallback_text="[Validation approaches documented in pursuit history]",
            required=False,
        ),
        FieldMapping(
            field_name="next_experiments",
            itd_source="forward_projection.horizons.day_90.success_correlated_actions",
            outcome_source="experiment_readiness",
            coaching_source=None,
            fallback_text="[Next experiments to be designed]",
            required=False,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
)

# Stage Review Package (Stage-Gate derivative)
GATE_REVIEW_PACKAGE = ExportTemplateSpec(
    template_key="gate_review_package",
    display_name="Stage Review Package",
    description="A comprehensive review package for stage advancement decisions - milestones achieved, evidence gathered, and readiness assessment.",
    source_archetypes=["stage_gate", "pim"],
    available_to_all=False,
    min_outcome_readiness=0.70,
    field_mappings=[
        FieldMapping(
            field_name="executive_summary",
            itd_source="thesis_statement.thesis_text",
            outcome_source="executive_summary_readiness",
            coaching_source=None,
            fallback_text="[Executive summary to be finalized]",
            required=True,
        ),
        FieldMapping(
            field_name="stage_objectives",
            itd_source="narrative_arc.opening_hook",
            outcome_source="stage_objectives_readiness",
            coaching_source=None,
            fallback_text="[Stage objectives documented in pursuit]",
            required=True,
        ),
        FieldMapping(
            field_name="deliverables_completed",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="deliverables_readiness",
            coaching_source=None,
            fallback_text="[Deliverables checklist in progress]",
            required=True,
        ),
        FieldMapping(
            field_name="evidence_quality",
            itd_source="evidence_architecture.confidence_trajectory",
            outcome_source="evidence_quality_readiness",
            coaching_source=None,
            fallback_text="[Evidence quality assessment pending]",
            required=True,
        ),
        FieldMapping(
            field_name="risk_assessment",
            itd_source="coachs_perspective.overall_reflection",
            outcome_source="risk_assessment_readiness",
            coaching_source=None,
            fallback_text="[Open considerations documented in coaching history]",
            required=False,
        ),
        FieldMapping(
            field_name="resource_requirements",
            itd_source="forward_projection.horizons.day_180.narrative",
            outcome_source="resource_requirements_readiness",
            coaching_source=None,
            fallback_text="[Resource planning in development]",
            required=False,
        ),
        FieldMapping(
            field_name="timeline_projection",
            itd_source="forward_projection.horizons",
            outcome_source="timeline_readiness",
            coaching_source=None,
            fallback_text="[Timeline projections forming]",
            required=False,
        ),
        FieldMapping(
            field_name="go_no_go_recommendation",
            itd_source="forward_projection.synthesis_statement",
            outcome_source="recommendation_readiness",
            coaching_source=None,
            fallback_text="[Recommendation pending full evidence review]",
            required=True,
        ),
        FieldMapping(
            field_name="next_stage_plan",
            itd_source="forward_projection.horizons.day_90.success_correlated_actions",
            outcome_source="next_stage_readiness",
            coaching_source=None,
            fallback_text="[Next stage planning to commence after review]",
            required=False,
        ),
        FieldMapping(
            field_name="lessons_learned",
            itd_source="coachs_perspective.moments",
            outcome_source="lessons_readiness",
            coaching_source=None,
            fallback_text="[Lessons captured in coaching history]",
            required=False,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
    irc_integration=True,  # v4.10: Include resource appendix
)

# Competitive Landscape Canvas (Blue Ocean derivative)
STRATEGY_CANVAS = ExportTemplateSpec(
    template_key="strategy_canvas",
    display_name="Competitive Landscape Canvas",
    description="A strategic view of your competitive positioning - where you compete differently and where you create new value.",
    source_archetypes=["blue_ocean"],
    available_to_all=False,
    min_outcome_readiness=0.65,
    field_mappings=[
        FieldMapping(
            field_name="value_curve_positioning",
            itd_source="thesis_statement.thesis_text",
            outcome_source="positioning_readiness",
            coaching_source="vision_artifact_finalized",
            fallback_text="[Value positioning under development]",
            required=True,
        ),
        FieldMapping(
            field_name="factors_to_eliminate",
            itd_source="evidence_architecture.pivots",
            outcome_source="eliminate_factors_readiness",
            coaching_source=None,
            fallback_text="[Elimination factors being identified]",
            required=False,
        ),
        FieldMapping(
            field_name="factors_to_reduce",
            itd_source="narrative_arc.acts",
            outcome_source="reduce_factors_readiness",
            coaching_source=None,
            fallback_text="[Reduction factors being analyzed]",
            required=False,
        ),
        FieldMapping(
            field_name="factors_to_raise",
            itd_source="forward_projection.horizons.day_90.narrative",
            outcome_source="raise_factors_readiness",
            coaching_source=None,
            fallback_text="[Elevation factors being validated]",
            required=False,
        ),
        FieldMapping(
            field_name="factors_to_create",
            itd_source="pattern_connections.within_pursuit.narrative",
            outcome_source="create_factors_readiness",
            coaching_source=None,
            fallback_text="[Creation factors emerging from discovery]",
            required=True,
        ),
        FieldMapping(
            field_name="competitive_differentiation",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="differentiation_readiness",
            coaching_source=None,
            fallback_text="[Differentiation strategy forming]",
            required=True,
        ),
        FieldMapping(
            field_name="new_market_opportunity",
            itd_source="forward_projection.synthesis_statement",
            outcome_source="market_opportunity_readiness",
            coaching_source=None,
            fallback_text="[Market opportunity being validated]",
            required=False,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
)

# Constraint Resolution Record (TRIZ derivative)
CONTRADICTION_RESOLUTION = ExportTemplateSpec(
    template_key="contradiction_resolution",
    display_name="Constraint Resolution Record",
    description="A systematic record of technical or business constraints and how they were resolved without compromise.",
    source_archetypes=["triz"],
    available_to_all=False,
    min_outcome_readiness=0.55,
    field_mappings=[
        FieldMapping(
            field_name="initial_constraint",
            itd_source="narrative_arc.opening_hook",
            outcome_source="constraint_definition_readiness",
            coaching_source="concerns_artifact_finalized",
            fallback_text="[Initial constraint definition in progress]",
            required=True,
        ),
        FieldMapping(
            field_name="constraint_analysis",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="constraint_analysis_readiness",
            coaching_source=None,
            fallback_text="[Constraint analysis documented in pursuit]",
            required=True,
        ),
        FieldMapping(
            field_name="resolution_approach",
            itd_source="thesis_statement.thesis_text",
            outcome_source="resolution_approach_readiness",
            coaching_source=None,
            fallback_text="[Resolution approach being developed]",
            required=True,
        ),
        FieldMapping(
            field_name="validation_results",
            itd_source="evidence_architecture.confidence_trajectory",
            outcome_source="validation_results_readiness",
            coaching_source=None,
            fallback_text="[Validation results pending]",
            required=False,
        ),
        FieldMapping(
            field_name="implementation_guidance",
            itd_source="forward_projection.horizons.day_90.success_correlated_actions",
            outcome_source="implementation_readiness",
            coaching_source=None,
            fallback_text="[Implementation guidance to follow validation]",
            required=False,
        ),
        FieldMapping(
            field_name="lessons_for_future",
            itd_source="coachs_perspective.overall_reflection",
            outcome_source="lessons_readiness",
            coaching_source=None,
            fallback_text="[Lessons captured in coaching reflections]",
            required=False,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
)

# Investment Readiness Summary (Incubation derivative)
INVESTMENT_READINESS = ExportTemplateSpec(
    template_key="investment_readiness",
    display_name="Investment Readiness Summary",
    description="A comprehensive assessment of investment readiness - traction, validation, team, and growth trajectory.",
    source_archetypes=["incubation", "lean_startup"],
    available_to_all=True,
    min_outcome_readiness=0.75,
    field_mappings=[
        FieldMapping(
            field_name="executive_pitch",
            itd_source="thesis_statement.thesis_text",
            outcome_source="pitch_readiness",
            coaching_source="vision_artifact_finalized",
            fallback_text="[Executive pitch being refined]",
            required=True,
        ),
        FieldMapping(
            field_name="traction_evidence",
            itd_source="evidence_architecture.confidence_trajectory",
            outcome_source="traction_readiness",
            coaching_source=None,
            fallback_text="[Traction metrics being established]",
            required=True,
        ),
        FieldMapping(
            field_name="market_validation",
            itd_source="evidence_architecture.tested_assumptions",
            outcome_source="market_validation_readiness",
            coaching_source=None,
            fallback_text="[Market validation in progress]",
            required=True,
        ),
        FieldMapping(
            field_name="competitive_advantage",
            itd_source="pattern_connections.within_pursuit.narrative",
            outcome_source="competitive_advantage_readiness",
            coaching_source=None,
            fallback_text="[Competitive positioning being established]",
            required=False,
        ),
        FieldMapping(
            field_name="growth_trajectory",
            itd_source="forward_projection.synthesis_statement",
            outcome_source="growth_trajectory_readiness",
            coaching_source=None,
            fallback_text="[Growth trajectory projections forming]",
            required=True,
        ),
        FieldMapping(
            field_name="financial_projections",
            itd_source="forward_projection.horizons.day_365.narrative",
            outcome_source="financial_projections_readiness",
            coaching_source=None,
            fallback_text="[Financial projections under development]",
            required=False,
        ),
        FieldMapping(
            field_name="use_of_funds",
            itd_source="forward_projection.horizons.day_180.success_correlated_actions",
            outcome_source="use_of_funds_readiness",
            coaching_source=None,
            fallback_text="[Use of funds planning in progress]",
            required=False,
        ),
        FieldMapping(
            field_name="key_milestones",
            itd_source="forward_projection.horizons",
            outcome_source="milestones_readiness",
            coaching_source=None,
            fallback_text="[Key milestones to be defined]",
            required=False,
        ),
    ],
    output_formats=["markdown", "html", "pdf", "docx"],
    irc_integration=True,  # v4.10: Include resource appendix
)


# =============================================================================
# REGISTRY
# =============================================================================

class ExportTemplateRegistry:
    """
    Central registry for all export template families.

    Provides:
    - Template lookup by key
    - Available templates for a pursuit based on archetype and readiness
    - Readiness checking for specific templates
    """

    def __init__(self):
        self._templates: Dict[str, ExportTemplateSpec] = {
            "business_model_canvas": BUSINESS_MODEL_CANVAS,
            "empathy_journey_map": EMPATHY_JOURNEY_MAP,
            "gate_review_package": GATE_REVIEW_PACKAGE,
            "strategy_canvas": STRATEGY_CANVAS,
            "contradiction_resolution": CONTRADICTION_RESOLUTION,
            "investment_readiness": INVESTMENT_READINESS,
        }

    def get_template(self, key: str) -> Optional[ExportTemplateSpec]:
        """Get a template specification by key."""
        return self._templates.get(key)

    def get_all_templates(self) -> List[ExportTemplateSpec]:
        """Get all registered templates."""
        return list(self._templates.values())

    def get_available_templates(
        self,
        archetype: str,
        readiness_scores: Dict[str, float],
        overall_readiness: float,
    ) -> List[ExportAvailability]:
        """
        Get available export templates for a pursuit.

        Args:
            archetype: The pursuit's methodology archetype
            readiness_scores: Field-level readiness from Outcome Formulator
            overall_readiness: Overall outcome readiness score (0.0-1.0)

        Returns:
            List of ExportAvailability with status and notes
        """
        results = []

        for template in self._templates.values():
            # Check archetype gating
            if not template.available_to_all:
                if archetype not in template.source_archetypes:
                    continue

            # Check readiness
            meets_threshold = overall_readiness >= template.min_outcome_readiness
            check_result = self.check_readiness(
                template.template_key,
                readiness_scores,
                overall_readiness,
            )

            # Determine readiness note
            if check_result.status == "READY":
                readiness_note = "Ready to generate"
            elif check_result.status == "PARTIAL":
                missing_count = len(check_result.missing_required_fields)
                readiness_note = f"Ready with {missing_count} dimension(s) still forming"
            else:
                readiness_note = f"Needs more development ({check_result.blocking_reason})"

            results.append(ExportAvailability(
                template_key=template.template_key,
                display_name=template.display_name,
                description=template.description,
                available=check_result.status != "BLOCKED",
                readiness_score=overall_readiness,
                min_required=template.min_outcome_readiness,
                missing_required_fields=check_result.missing_required_fields,
                output_formats=template.output_formats,
                readiness_note=readiness_note,
            ))

        # Sort by readiness (highest first)
        results.sort(key=lambda x: (-x.readiness_score, x.template_key))
        return results

    def check_readiness(
        self,
        template_key: str,
        readiness_scores: Dict[str, float],
        overall_readiness: float,
    ) -> TemplateReadinessResult:
        """
        Check readiness for a specific template.

        Args:
            template_key: Template to check
            readiness_scores: Field-level readiness from Outcome Formulator
            overall_readiness: Overall outcome readiness score

        Returns:
            TemplateReadinessResult with status and missing fields
        """
        template = self._templates.get(template_key)
        if not template:
            return TemplateReadinessResult(
                template_key=template_key,
                status="BLOCKED",
                readiness_score=0.0,
                missing_required_fields=[],
                missing_optional_fields=[],
                blocking_reason="Template not found",
            )

        # Check overall threshold
        if overall_readiness < template.min_outcome_readiness:
            return TemplateReadinessResult(
                template_key=template_key,
                status="BLOCKED",
                readiness_score=overall_readiness,
                missing_required_fields=[],
                missing_optional_fields=[],
                blocking_reason=f"Overall readiness {overall_readiness:.0%} below {template.min_outcome_readiness:.0%} threshold",
            )

        # Check individual field readiness
        missing_required = []
        missing_optional = []
        field_threshold = 0.5  # Field is considered "available" at 50%+

        for mapping in template.field_mappings:
            field_readiness = readiness_scores.get(mapping.outcome_source, 0.0) if mapping.outcome_source else 0.0

            # Also check if ITD source might provide data (assume available if ITD exists)
            if mapping.itd_source and field_readiness < field_threshold:
                # ITD source might still provide data - don't mark as missing
                continue

            if field_readiness < field_threshold:
                if mapping.required:
                    missing_required.append(mapping.field_name)
                else:
                    missing_optional.append(mapping.field_name)

        # Determine status
        if missing_required and any(
            not self._has_fallback(template_key, f) for f in missing_required
        ):
            return TemplateReadinessResult(
                template_key=template_key,
                status="BLOCKED",
                readiness_score=overall_readiness,
                missing_required_fields=missing_required,
                missing_optional_fields=missing_optional,
                blocking_reason=f"Required fields missing without fallback: {', '.join(missing_required)}",
            )
        elif missing_required:
            return TemplateReadinessResult(
                template_key=template_key,
                status="PARTIAL",
                readiness_score=overall_readiness,
                missing_required_fields=missing_required,
                missing_optional_fields=missing_optional,
                blocking_reason=None,
            )
        else:
            return TemplateReadinessResult(
                template_key=template_key,
                status="READY",
                readiness_score=overall_readiness,
                missing_required_fields=[],
                missing_optional_fields=missing_optional,
                blocking_reason=None,
            )

    def _has_fallback(self, template_key: str, field_name: str) -> bool:
        """Check if a field has fallback text defined."""
        template = self._templates.get(template_key)
        if not template:
            return False

        for mapping in template.field_mappings:
            if mapping.field_name == field_name:
                return bool(mapping.fallback_text)
        return False
