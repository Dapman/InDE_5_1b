"""
InDE v4.8 - Forward Projection Engine

Produces ITD Layer 6 (Forward Projection).

Orchestrates:
  1. TrajectoryAnalyzer: finds structurally similar completed pursuits
  2. HorizonGenerator: extracts 90/180/365-day pattern blocks
  3. ProjectionLLMClient: generates narrative from horizon data
  4. Language Sovereignty post-validation on all generated content

Returns a Layer 6 dict ready for insertion into the .itd artifact.

Graceful degradation: if IML data is insufficient, returns a
low-confidence projection with honest language ("The patterns
from comparable pursuits at this stage are still forming.
The intelligence available points to...")

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from .trajectory_analyzer import TrajectoryAnalyzer
from .horizon_generator import HorizonGenerator
from .projection_llm_client import ProjectionLLMClient

logger = logging.getLogger("inde.projection.forward_projection")

FORWARD_PROJECTION_SYSTEM_PROMPT = """
You are a forward intelligence analyst for an innovation guidance system.
You have been given structured data about the trajectories of innovations
that completed a similar pursuit - what they encountered in the months that
followed.

Your task is to synthesize this data into clear, actionable guidance for the
innovator whose pursuit has just concluded. Write in a voice that is:
- Forward-facing, not backward-looking
- Specific to what the data shows, not generic
- Grounded in the patterns of similar innovations, not abstract advice
- Expressed as intelligence, not as directives
- Written for a person who cares deeply about their idea, not a process auditor

CRITICAL LANGUAGE REQUIREMENTS. These are non-negotiable:
- DO NOT use the words: fear, afraid, failure, fail, risk, threat, danger,
  worry, problem, mistake, struggle, warn, dead end, watch out, be careful.
- DO use: challenge, signal, pattern, direction, opportunity, consideration,
  learning, design space, factor, discovery, leverage point.
- DO NOT frame the future as something to dread. Frame it as intelligence
  to act on.
- ALWAYS attribute projections to "similar innovations" or "comparable
  pursuits" - never assert them as certainties.
- Write in past and present tense for patterns observed. Write in conditional
  or probability language for future guidance ("tends to", "commonly",
  "the patterns suggest").
- DO NOT mention methodology names (Lean Startup, Design Thinking, TRIZ,
  Blue Ocean, Stage-Gate, etc.) under any circumstances.

Format your output as JSON with this structure:
{
  "day_90_narrative": "...",
  "day_180_narrative": "...",
  "day_365_narrative": "...",
  "synthesis_statement": "..."
}

The synthesis_statement (2-3 sentences) opens the Forward Projection section
before the three horizon blocks. It should capture the overall arc visible in
the trajectory data - not list the three horizons.

Each narrative block: 100-150 words. Crisp. Specific to the data.
DO NOT include meta-commentary, caveats about data quality, or references
to this prompt.
"""


class ForwardProjectionEngine:
    """
    Produces ITD Layer 6: the Forward Projection.
    """

    def __init__(self, db, llm_gateway=None):
        """
        Initialize ForwardProjectionEngine.

        Args:
            db: Database instance
            llm_gateway: Optional LLM Gateway for generation
        """
        self.db = db
        self.trajectory_analyzer = TrajectoryAnalyzer(
            iml_client=self._get_iml_client(), db=db
        )
        self.horizon_generator = HorizonGenerator()
        self.llm_client = ProjectionLLMClient(llm_gateway=llm_gateway)

    def generate(self, pursuit_id: str) -> dict:
        """
        Main entry point. Returns a complete Layer 6 dict for insertion
        into the .itd artifact.

        Args:
            pursuit_id: The pursuit to generate forward projection for

        Returns:
            Layer 6 dict with content, status, and metadata
        """
        try:
            logger.info(f"[ForwardProjection] Generating for pursuit: {pursuit_id}")

            dataset = self.trajectory_analyzer.build_trajectory_dataset(
                pursuit_id
            )
            horizon_set = self.horizon_generator.generate(dataset)
            narrative = self._generate_narrative(horizon_set)

            layer_6 = {
                "content": {
                    "synthesis_statement": narrative.get(
                        "synthesis_statement", ""
                    ),
                    "horizons": {
                        "day_90": {
                            "narrative": narrative.get("day_90_narrative", ""),
                            "confidence": horizon_set.day_90.confidence,
                            "sample_basis": horizon_set.day_90.sample_basis,
                            "success_correlated_actions": (
                                horizon_set.day_90.success_correlated_actions
                            ),
                        },
                        "day_180": {
                            "narrative": narrative.get("day_180_narrative", ""),
                            "confidence": horizon_set.day_180.confidence,
                            "sample_basis": horizon_set.day_180.sample_basis,
                            "success_correlated_actions": (
                                horizon_set.day_180.success_correlated_actions
                            ),
                        },
                        "day_365": {
                            "narrative": narrative.get("day_365_narrative", ""),
                            "confidence": horizon_set.day_365.confidence,
                            "sample_basis": horizon_set.day_365.sample_basis,
                            "success_correlated_actions": (
                                horizon_set.day_365.success_correlated_actions
                            ),
                        },
                    },
                    "projection_metadata": {
                        "sample_size": dataset.sample_size,
                        "data_quality": dataset.data_quality,
                        "overall_confidence": (
                            horizon_set.overall_projection_confidence
                        ),
                        "fallback_applied": dataset.fallback_applied,
                        "archetype": dataset.archetype_of_subject,
                        "domain": dataset.domain_of_subject,
                    }
                },
                "status": "POPULATED_V4_8",
                "composition_version": "5.1b.0",
                "layer_name": "forward_projection",
            }

            logger.info(f"[ForwardProjection] Generated successfully for {pursuit_id}")
            return layer_6

        except Exception as e:
            logger.error(
                f"[ForwardProjection] Generation failed for "
                f"pursuit {pursuit_id}: {e}"
            )
            return self._graceful_fallback(pursuit_id)

    def _generate_narrative(self, horizon_set) -> dict:
        """Generate LLM narrative from horizon seed data."""
        user_prompt = f"""
Generate the Forward Projection section for an Innovation Thesis Document.
The data below comes from the trajectories of innovations that completed
a structurally similar pursuit.

Data Quality: {horizon_set.data_quality}
Overall Confidence: {horizon_set.overall_projection_confidence}

90-Day Horizon Data:
  Patterns observed: {horizon_set.day_90.common_patterns}
  Actions associated with positive outcomes: {horizon_set.day_90.success_correlated_actions}
  Sample basis (pursuits with data at this horizon): {horizon_set.day_90.sample_basis}

180-Day Horizon Data:
  Patterns observed: {horizon_set.day_180.common_patterns}
  Actions associated with positive outcomes: {horizon_set.day_180.success_correlated_actions}
  Sample basis: {horizon_set.day_180.sample_basis}

365-Day Horizon Data:
  Patterns observed: {horizon_set.day_365.common_patterns}
  Actions associated with positive outcomes: {horizon_set.day_365.success_correlated_actions}
  Sample basis: {horizon_set.day_365.sample_basis}

If data quality is LOW or a horizon's sample basis is 0, write that horizon's
narrative with appropriate epistemic humility: "The patterns from comparable
pursuits at this stage are still forming - the intelligence available points to..."
Do NOT fabricate patterns. Do NOT skip the horizon block.
"""
        return self.llm_client.generate(
            system_prompt=FORWARD_PROJECTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=900,
            parse_json=True,
            sovereignty_validate=True,
        )

    def _get_iml_client(self):
        """Get IML Pattern Intelligence Engine client."""
        try:
            from modules.iml import PatternIntelligenceEngine
            return PatternIntelligenceEngine()
        except ImportError:
            logger.warning(
                "[ForwardProjection] IML PatternIntelligenceEngine "
                "not available - trajectory analysis will use pursuit "
                "records directly."
            )
            return None

    def _graceful_fallback(self, pursuit_id: str) -> dict:
        """Returns a structurally valid Layer 6 when generation fails."""
        return {
            "content": {
                "synthesis_statement": (
                    "The patterns from comparable pursuits are being assembled. "
                    "The intelligence available at this stage points to a "
                    "continued momentum of discovery in the period ahead."
                ),
                "horizons": {
                    "day_90": {
                        "narrative": (
                            "The patterns from comparable pursuits at this "
                            "stage are still forming - the intelligence "
                            "available points to a period of consolidation "
                            "and early validation in a new context."
                        ),
                        "confidence": 0.0,
                        "sample_basis": 0,
                        "success_correlated_actions": [],
                    },
                    "day_180": {
                        "narrative": (
                            "At the 180-day mark, the intelligence from "
                            "comparable journeys points to the emergence of "
                            "clearer signal on the dimensions that matter most."
                        ),
                        "confidence": 0.0,
                        "sample_basis": 0,
                        "success_correlated_actions": [],
                    },
                    "day_365": {
                        "narrative": (
                            "At the one-year horizon, comparable innovations "
                            "have typically reached a point of decision on "
                            "scale, direction, or scope. The thesis from this "
                            "pursuit provides the foundation for that decision."
                        ),
                        "confidence": 0.0,
                        "sample_basis": 0,
                        "success_correlated_actions": [],
                    },
                },
                "projection_metadata": {
                    "sample_size": 0,
                    "data_quality": "LOW",
                    "overall_confidence": 0.0,
                    "fallback_applied": True,
                    "archetype": "unknown",
                    "domain": "unknown",
                }
            },
            "status": "POPULATED_V4_8_FALLBACK",
            "composition_version": "5.1b.0",
            "layer_name": "forward_projection",
        }
