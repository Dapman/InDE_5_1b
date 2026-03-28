"""
InDE MVP v5.1b.0 - Export Coach Bridge

Coach-assisted export discovery that integrates with the Pursuit Exit
Orchestrator to offer intelligent export suggestions during Phase 3.

The bridge:
- Evaluates export readiness for the pursuit
- Suggests most appropriate templates based on ITD/Outcome readiness
- Recommends narrative styles based on pursuit characteristics
- Provides coach-framed explanations for export options

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("inde.export.coach_bridge")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ExportSuggestion:
    """A single export suggestion from the coach."""
    template_key: str
    template_name: str
    narrative_style: str
    style_display_name: str
    readiness_score: float
    coach_rationale: str
    audience_hint: str
    recommended_format: str
    is_primary_suggestion: bool = False


@dataclass
class ExportDiscoveryResult:
    """Complete export discovery result for Phase 3."""
    pursuit_id: str
    pursuit_title: str
    itd_exists: bool
    overall_readiness: float
    suggestions: List[ExportSuggestion]
    coach_introduction: str
    coach_closing: str
    available_formats: List[str]


# =============================================================================
# EXPORT COACH BRIDGE
# =============================================================================

class ExportCoachBridge:
    """
    Bridge between coaching experience and export engine.

    Provides coach-framed export discovery during pursuit exit flow,
    making export options accessible and understandable for innovators.
    """

    def __init__(
        self,
        template_registry=None,
        style_engine=None,
        db=None,
    ):
        """
        Initialize the Export Coach Bridge.

        Args:
            template_registry: ExportTemplateRegistry instance
            style_engine: NarrativeStyleEngine instance
            db: Database instance
        """
        self.template_registry = template_registry
        self.style_engine = style_engine
        self.db = db

    def discover_exports(
        self,
        pursuit_id: str,
        session_context: Dict = None,
    ) -> ExportDiscoveryResult:
        """
        Discover available exports for a pursuit.

        Called during Phase 3 of the exit flow to present export options
        with coach-framed explanations.

        Args:
            pursuit_id: The pursuit ID
            session_context: Optional exit session context

        Returns:
            ExportDiscoveryResult with suggestions and coach framing
        """
        logger.info(f"[ExportCoachBridge] Discovering exports for pursuit: {pursuit_id}")

        # Get pursuit data
        pursuit_data = self._get_pursuit_data(pursuit_id)
        pursuit_title = pursuit_data.get("title", "Your Innovation")

        # Get ITD data
        itd_data = self._get_itd_data(pursuit_id)
        itd_exists = itd_data is not None

        # Get outcome readiness
        outcome_data = self._get_outcome_data(pursuit_id)

        # Build readiness context
        readiness_context = {
            "itd": itd_data.get("layers", {}) if itd_data else {},
            "outcome_state": outcome_data or {},
            "pursuit": pursuit_data,
        }

        # Generate suggestions
        suggestions = self._generate_suggestions(
            pursuit_id=pursuit_id,
            pursuit_title=pursuit_title,
            readiness_context=readiness_context,
        )

        # Calculate overall readiness
        if suggestions:
            overall_readiness = max(s.readiness_score for s in suggestions)
        else:
            overall_readiness = 0.0

        # Generate coach framing
        coach_intro = self._generate_introduction(
            pursuit_title=pursuit_title,
            overall_readiness=overall_readiness,
            itd_exists=itd_exists,
        )

        coach_closing = self._generate_closing(
            overall_readiness=overall_readiness,
            suggestion_count=len([s for s in suggestions if s.readiness_score >= 0.5]),
        )

        return ExportDiscoveryResult(
            pursuit_id=pursuit_id,
            pursuit_title=pursuit_title,
            itd_exists=itd_exists,
            overall_readiness=overall_readiness,
            suggestions=suggestions,
            coach_introduction=coach_intro,
            coach_closing=coach_closing,
            available_formats=["markdown", "html", "pdf", "docx"],
        )

    def get_suggestion_for_audience(
        self,
        pursuit_id: str,
        audience: str,
    ) -> Optional[ExportSuggestion]:
        """
        Get a specific suggestion for a target audience.

        Args:
            pursuit_id: The pursuit ID
            audience: Target audience (investor, academic, etc.)

        Returns:
            ExportSuggestion or None
        """
        result = self.discover_exports(pursuit_id)

        # Map audience to style
        audience_style_map = {
            "investor": "investor",
            "investors": "investor",
            "academic": "academic",
            "researcher": "academic",
            "commercial": "commercial",
            "business": "commercial",
            "grant": "grant",
            "funder": "grant",
            "internal": "internal",
            "team": "internal",
        }

        target_style = audience_style_map.get(audience.lower(), "standard")

        for suggestion in result.suggestions:
            if suggestion.narrative_style == target_style:
                return suggestion

        return None

    def _get_pursuit_data(self, pursuit_id: str) -> Dict:
        """Get pursuit data from database."""
        if not self.db:
            return {"title": "Innovation Pursuit"}

        try:
            pursuit = self.db.db.pursuits.find_one({"_id": pursuit_id})
            return pursuit or {"title": "Innovation Pursuit"}
        except Exception as e:
            logger.error(f"[ExportCoachBridge] Error fetching pursuit: {e}")
            return {"title": "Innovation Pursuit"}

    def _get_itd_data(self, pursuit_id: str) -> Optional[Dict]:
        """Get ITD data from database."""
        if not self.db:
            return None

        try:
            itd = self.db.db.innovation_thesis_documents.find_one(
                {"pursuit_id": pursuit_id},
                sort=[("created_at", -1)]
            )
            return itd
        except Exception as e:
            logger.error(f"[ExportCoachBridge] Error fetching ITD: {e}")
            return None

    def _get_outcome_data(self, pursuit_id: str) -> Optional[Dict]:
        """Get outcome readiness data from database."""
        if not self.db:
            return None

        try:
            outcome = self.db.db.outcome_readiness_states.find_one(
                {"pursuit_id": pursuit_id}
            )
            return outcome
        except Exception as e:
            logger.error(f"[ExportCoachBridge] Error fetching outcome data: {e}")
            return None

    def _generate_suggestions(
        self,
        pursuit_id: str,
        pursuit_title: str,
        readiness_context: Dict,
    ) -> List[ExportSuggestion]:
        """Generate export suggestions based on readiness."""
        suggestions = []

        # Template-style pairings with coach rationales
        template_style_pairings = [
            {
                "template_key": "investment_readiness",
                "style": "investor",
                "audience": "investors and stakeholders",
                "rationale_template": (
                    "Your {pursuit_title} has developed strong evidence foundations. "
                    "This export presents your innovation thesis in the language "
                    "that resonates with investment decision-makers."
                ),
            },
            {
                "template_key": "business_model_canvas",
                "style": "commercial",
                "audience": "business partners and customers",
                "rationale_template": (
                    "This format maps your innovation to the Business Model Canvas, "
                    "making it easy for commercial partners to understand your "
                    "value proposition and market approach."
                ),
            },
            {
                "template_key": "gate_review_package",
                "style": "internal",
                "audience": "internal review boards",
                "rationale_template": (
                    "Structured for stage-gate review processes, this export "
                    "presents your progress, evidence, and projections in a format "
                    "familiar to enterprise innovation governance."
                ),
            },
            {
                "template_key": "empathy_journey_map",
                "style": "standard",
                "audience": "design and product teams",
                "rationale_template": (
                    "This export captures your user understanding and empathy work, "
                    "perfect for sharing with design thinking practitioners and "
                    "product development teams."
                ),
            },
            {
                "template_key": "strategy_canvas",
                "style": "commercial",
                "audience": "strategic planners",
                "rationale_template": (
                    "Visualizes your competitive positioning and strategic choices, "
                    "ideal for strategy discussions and competitive analysis "
                    "presentations."
                ),
            },
            {
                "template_key": "contradiction_resolution",
                "style": "academic",
                "audience": "research and innovation theory audiences",
                "rationale_template": (
                    "Frames your innovation through the lens of contradiction "
                    "resolution, suitable for academic publications and "
                    "innovation research contexts."
                ),
            },
        ]

        # Check each pairing
        primary_selected = False
        for pairing in template_style_pairings:
            template_key = pairing["template_key"]

            # Get readiness if registry available
            readiness_score = 0.5  # Default
            if self.template_registry:
                try:
                    readiness_result = self.template_registry.check_template_readiness(
                        template_key=template_key,
                        pursuit_id=pursuit_id,
                        readiness_data=readiness_context,
                    )
                    readiness_score = readiness_result.readiness_score
                except Exception as e:
                    logger.warning(f"[ExportCoachBridge] Readiness check failed: {e}")

            # Get style display name
            style_display_name = self._get_style_display_name(pairing["style"])

            # Get template display name
            template_name = self._get_template_display_name(template_key)

            # Generate rationale
            rationale = pairing["rationale_template"].format(
                pursuit_title=pursuit_title
            )

            # Determine if primary (first one with readiness >= 0.6)
            is_primary = not primary_selected and readiness_score >= 0.6
            if is_primary:
                primary_selected = True

            # Recommended format based on audience
            recommended_format = self._get_recommended_format(pairing["audience"])

            suggestions.append(ExportSuggestion(
                template_key=template_key,
                template_name=template_name,
                narrative_style=pairing["style"],
                style_display_name=style_display_name,
                readiness_score=readiness_score,
                coach_rationale=rationale,
                audience_hint=pairing["audience"],
                recommended_format=recommended_format,
                is_primary_suggestion=is_primary,
            ))

        # Sort by readiness score descending
        suggestions.sort(key=lambda s: s.readiness_score, reverse=True)

        return suggestions

    def _get_style_display_name(self, style_key: str) -> str:
        """Get display name for a narrative style."""
        if self.style_engine:
            style = self.style_engine.get_style(style_key)
            if style:
                return style.display_name

        style_names = {
            "investor": "Investor Narrative",
            "academic": "Academic Narrative",
            "commercial": "Commercial Narrative",
            "grant": "Grant Application Narrative",
            "internal": "Internal Review Narrative",
            "standard": "Standard Narrative",
        }
        return style_names.get(style_key, "Standard Narrative")

    def _get_template_display_name(self, template_key: str) -> str:
        """Get display name for a template."""
        if self.template_registry:
            templates = self.template_registry.get_all_templates()
            if template_key in templates:
                return templates[template_key].display_name

        template_names = {
            "investment_readiness": "Investment Readiness Package",
            "business_model_canvas": "Business Model Canvas",
            "gate_review_package": "Gate Review Package",
            "empathy_journey_map": "Empathy Journey Map",
            "strategy_canvas": "Strategy Canvas",
            "contradiction_resolution": "Contradiction Resolution Brief",
        }
        return template_names.get(template_key, template_key.replace("_", " ").title())

    def _get_recommended_format(self, audience: str) -> str:
        """Get recommended format based on audience."""
        if "investor" in audience.lower() or "board" in audience.lower():
            return "pdf"
        if "academic" in audience.lower() or "research" in audience.lower():
            return "markdown"
        if "internal" in audience.lower() or "team" in audience.lower():
            return "docx"
        return "pdf"

    def _generate_introduction(
        self,
        pursuit_title: str,
        overall_readiness: float,
        itd_exists: bool,
    ) -> str:
        """Generate coach introduction for export discovery."""
        if not itd_exists:
            return (
                f"Your Innovation Thesis Document is still being prepared. "
                f"Once complete, you'll have several export options to share "
                f"your {pursuit_title} story with different audiences."
            )

        if overall_readiness >= 0.8:
            return (
                f"Excellent! Your {pursuit_title} has reached a strong point of "
                f"articulation. I've identified several export options that can "
                f"help you share your innovation thesis with different audiences."
            )
        elif overall_readiness >= 0.6:
            return (
                f"Your {pursuit_title} has developed nicely. While some dimensions "
                f"are still emerging, you have several solid options for sharing "
                f"your progress with stakeholders."
            )
        else:
            return (
                f"Your {pursuit_title} is taking shape. Some export options are "
                f"available now, and others will become stronger as your "
                f"innovation thesis continues to develop."
            )

    def _generate_closing(
        self,
        overall_readiness: float,
        suggestion_count: int,
    ) -> str:
        """Generate coach closing for export discovery."""
        if suggestion_count == 0:
            return (
                "Continue developing your pursuit, and more export options "
                "will become available as your innovation thesis matures."
            )

        if overall_readiness >= 0.8:
            return (
                f"You have {suggestion_count} strong export options ready. "
                f"Each format serves a different audience—choose the one that "
                f"best matches your immediate communication needs."
            )
        else:
            return (
                f"Select the export that best matches your current needs. "
                f"Partial fields will be noted in the document, giving you "
                f"transparent insight into areas still developing."
            )


# =============================================================================
# PHASE 3 INTEGRATION
# =============================================================================

def get_export_discovery_for_phase3(
    pursuit_id: str,
    db=None,
    template_registry=None,
    style_engine=None,
) -> Dict:
    """
    Get export discovery data for Phase 3 of exit flow.

    This is the integration point called by PursuitExitOrchestrator
    during the ARTIFACT_PACKAGING phase.

    Args:
        pursuit_id: The pursuit ID
        db: Database instance
        template_registry: ExportTemplateRegistry instance
        style_engine: NarrativeStyleEngine instance

    Returns:
        Dictionary with export discovery data for API response
    """
    bridge = ExportCoachBridge(
        template_registry=template_registry,
        style_engine=style_engine,
        db=db,
    )

    result = bridge.discover_exports(pursuit_id)

    # Convert to dict for API response
    return {
        "pursuit_id": result.pursuit_id,
        "pursuit_title": result.pursuit_title,
        "itd_exists": result.itd_exists,
        "overall_readiness": result.overall_readiness,
        "coach_introduction": result.coach_introduction,
        "coach_closing": result.coach_closing,
        "available_formats": result.available_formats,
        "suggestions": [
            {
                "template_key": s.template_key,
                "template_name": s.template_name,
                "narrative_style": s.narrative_style,
                "style_display_name": s.style_display_name,
                "readiness_score": s.readiness_score,
                "coach_rationale": s.coach_rationale,
                "audience_hint": s.audience_hint,
                "recommended_format": s.recommended_format,
                "is_primary_suggestion": s.is_primary_suggestion,
            }
            for s in result.suggestions
        ],
    }
