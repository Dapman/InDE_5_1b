"""
InDE MVP v5.1b.0 - ITD Narrative Style Engine

Applies audience-specific narrative styles to the ITD's six-layer
architecture. The underlying intelligence does not change; the voice,
ordering, and emphasis adapt to the audience.

6 Narrative Styles:
1. investor   - Traction, validation evidence, forward projection
2. academic   - Discovery process, methodology learnings, evidence rigor
3. commercial - Value proposition, customer validation, implementation
4. grant      - Problem framing, innovation approach, expected outcomes
5. internal   - Coaching intelligence, organizational learning, IML patterns
6. standard   - Balanced default, no audience weighting

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger("inde.export.narrative_style")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NarrativeStyle:
    """Specification for an audience narrative style."""
    style_key: str
    display_name: str
    layer_ordering: List[str]           # Which ITD layers appear first
    layer_emphasis: Dict[str, float]    # layer_key -> word-count weighting (0.0-2.0)
    opening_frame: str                  # LLM system prompt modifier for style voice
    coach_explanation: str              # What the coach says about this style


# =============================================================================
# STYLE DEFINITIONS
# =============================================================================

NARRATIVE_STYLES: Dict[str, NarrativeStyle] = {
    "investor": NarrativeStyle(
        style_key="investor",
        display_name="Investor Narrative",
        layer_ordering=[
            "forward_projection",
            "thesis_statement",
            "evidence_architecture",
            "narrative_arc",
            "coachs_perspective",
            "pattern_connections",
        ],
        layer_emphasis={
            "forward_projection": 1.8,
            "evidence_architecture": 1.5,
            "thesis_statement": 1.2,
            "narrative_arc": 0.8,
            "coachs_perspective": 0.6,
            "pattern_connections": 0.4,
        },
        opening_frame=(
            "Frame the innovation as a validated market opportunity. "
            "Lead with traction evidence and forward trajectory. "
            "De-emphasize process; emphasize validated outcomes and "
            "next-stage readiness. Use declarative, confident language."
        ),
        coach_explanation=(
            "Leads with your validation evidence and trajectory - the "
            "format that investment conversations typically expect."
        ),
    ),

    "academic": NarrativeStyle(
        style_key="academic",
        display_name="Research Narrative",
        layer_ordering=[
            "narrative_arc",
            "evidence_architecture",
            "thesis_statement",
            "coachs_perspective",
            "pattern_connections",
            "forward_projection",
        ],
        layer_emphasis={
            "narrative_arc": 1.8,
            "evidence_architecture": 1.6,
            "coachs_perspective": 1.4,
            "pattern_connections": 1.2,
            "thesis_statement": 1.0,
            "forward_projection": 0.6,
        },
        opening_frame=(
            "Frame the innovation as a discovery process. Lead with "
            "methodology of inquiry and evidence quality. Emphasize "
            "how assumptions were surfaced, tested, and refined. "
            "Analytical, precise, reproducible-sounding language."
        ),
        coach_explanation=(
            "Leads with your discovery process and evidence quality - "
            "the format that research and conference audiences expect."
        ),
    ),

    "commercial": NarrativeStyle(
        style_key="commercial",
        display_name="Commercial Narrative",
        layer_ordering=[
            "thesis_statement",
            "evidence_architecture",
            "forward_projection",
            "narrative_arc",
            "pattern_connections",
            "coachs_perspective",
        ],
        layer_emphasis={
            "thesis_statement": 1.8,
            "evidence_architecture": 1.5,
            "forward_projection": 1.3,
            "narrative_arc": 0.9,
            "pattern_connections": 0.7,
            "coachs_perspective": 0.5,
        },
        opening_frame=(
            "Frame the innovation as a market-ready solution. Lead with "
            "value proposition clarity and customer validation evidence. "
            "Emphasize implementation readiness and path to adoption. "
            "Action-oriented, benefit-focused language."
        ),
        coach_explanation=(
            "Leads with your value proposition and customer evidence - "
            "the format that commercial partnerships expect."
        ),
    ),

    "grant": NarrativeStyle(
        style_key="grant",
        display_name="Grant Narrative",
        layer_ordering=[
            "narrative_arc",
            "thesis_statement",
            "evidence_architecture",
            "forward_projection",
            "coachs_perspective",
            "pattern_connections",
        ],
        layer_emphasis={
            "narrative_arc": 1.6,
            "thesis_statement": 1.5,
            "evidence_architecture": 1.4,
            "forward_projection": 1.2,
            "coachs_perspective": 0.8,
            "pattern_connections": 0.6,
        },
        opening_frame=(
            "Frame the innovation as addressing a significant problem "
            "or opportunity. Lead with clear problem framing and your "
            "innovative approach. Emphasize expected outcomes and "
            "evaluation criteria. Systematic, outcome-focused language."
        ),
        coach_explanation=(
            "Leads with problem framing and your innovative approach - "
            "the format that grant committees typically expect."
        ),
    ),

    "internal": NarrativeStyle(
        style_key="internal",
        display_name="Team Learning Narrative",
        layer_ordering=[
            "coachs_perspective",
            "pattern_connections",
            "narrative_arc",
            "evidence_architecture",
            "thesis_statement",
            "forward_projection",
        ],
        layer_emphasis={
            "coachs_perspective": 1.8,
            "pattern_connections": 1.6,
            "narrative_arc": 1.4,
            "evidence_architecture": 1.0,
            "thesis_statement": 0.8,
            "forward_projection": 0.7,
        },
        opening_frame=(
            "Frame the innovation as an organizational learning journey. "
            "Lead with coaching insights and pattern connections across "
            "pursuits. Emphasize what the team learned and how it applies "
            "to future work. Reflective, growth-oriented language."
        ),
        coach_explanation=(
            "Leads with coaching insights and organizational learning - "
            "the format that internal teams and leadership appreciate."
        ),
    ),

    "standard": NarrativeStyle(
        style_key="standard",
        display_name="Standard Narrative",
        layer_ordering=[
            "thesis_statement",
            "narrative_arc",
            "evidence_architecture",
            "coachs_perspective",
            "pattern_connections",
            "forward_projection",
        ],
        layer_emphasis={
            "thesis_statement": 1.0,
            "narrative_arc": 1.0,
            "evidence_architecture": 1.0,
            "coachs_perspective": 1.0,
            "pattern_connections": 1.0,
            "forward_projection": 1.0,
        },
        opening_frame=(
            "Present the innovation thesis as a balanced narrative. "
            "No particular audience emphasis - let the content speak "
            "for itself. Clear, accessible language."
        ),
        coach_explanation=(
            "The complete Innovation Thesis as generated - balanced "
            "and comprehensive for any audience."
        ),
    ),
}


# =============================================================================
# NARRATIVE STYLE ENGINE
# =============================================================================

class NarrativeStyleEngine:
    """
    Applies audience-specific narrative styles to ITD documents.

    The styled ITD has:
    - Reordered layers per style specification
    - A style bridge opening paragraph (generated via LLM)
    - Style metadata for tracking
    """

    def __init__(self):
        self._styles = NARRATIVE_STYLES

    def get_style(self, style_key: str) -> Optional[NarrativeStyle]:
        """Get a narrative style by key."""
        return self._styles.get(style_key)

    def get_all_styles(self) -> List[NarrativeStyle]:
        """Get all registered styles."""
        return list(self._styles.values())

    def apply_style(
        self,
        itd: Dict[str, Any],
        style_key: str,
        llm_client: Any = None,  # ExportLLMClient
        audience_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply a narrative style to an ITD document.

        Args:
            itd: The ITD document (as dict)
            style_key: The style to apply
            llm_client: ExportLLMClient for style bridge generation
            audience_context: Optional free-text audience description

        Returns:
            styled_itd: ITD with reordered layers and style metadata
        """
        style = self._styles.get(style_key)
        if not style:
            logger.warning(f"Style '{style_key}' not found, using 'standard'")
            style = self._styles["standard"]

        # Create a copy of the ITD
        styled_itd = dict(itd)

        # Reorder layers according to style
        styled_itd["layer_ordering"] = style.layer_ordering
        styled_itd["layer_emphasis"] = style.layer_emphasis

        # Generate style bridge if LLM client provided
        if llm_client:
            thesis_summary = self._extract_thesis_summary(itd)
            style_bridge = llm_client.generate_style_bridge(
                style=style,
                itd_thesis_summary=thesis_summary,
                audience_context=audience_context,
            )
            styled_itd["style_opening"] = style_bridge
        else:
            # Fallback: use style's opening frame as bridge
            styled_itd["style_opening"] = self._generate_fallback_bridge(
                style, itd, audience_context
            )

        # Add style metadata
        styled_itd["style_metadata"] = {
            "style_key": style.style_key,
            "display_name": style.display_name,
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "coach_explanation": style.coach_explanation,
        }

        logger.info(f"Applied style '{style_key}' to ITD {itd.get('itd_id', 'unknown')}")
        return styled_itd

    def _extract_thesis_summary(self, itd: Dict[str, Any]) -> str:
        """Extract a short thesis summary for style bridge generation."""
        thesis = itd.get("thesis_statement", {})
        if isinstance(thesis, dict):
            text = thesis.get("thesis_text", "")
        else:
            # Might be a dataclass
            text = getattr(thesis, "thesis_text", str(thesis))

        # Truncate to ~200 chars
        if len(text) > 200:
            text = text[:197] + "..."
        return text

    def _generate_fallback_bridge(
        self,
        style: NarrativeStyle,
        itd: Dict[str, Any],
        audience_context: Optional[str],
    ) -> str:
        """
        Generate a fallback style bridge without LLM.

        Used when LLM client is not available or to save tokens.
        """
        thesis_text = self._extract_thesis_summary(itd)
        pursuit_title = itd.get("pursuit_title", "this innovation pursuit")

        if style.style_key == "investor":
            return (
                f"This Innovation Thesis presents {pursuit_title} as a validated "
                f"opportunity with clear market signals and a defined trajectory "
                f"for growth and scale."
            )
        elif style.style_key == "academic":
            return (
                f"This Innovation Thesis documents the discovery process behind "
                f"{pursuit_title}, presenting the evidence architecture and "
                f"methodology learnings that emerged."
            )
        elif style.style_key == "commercial":
            return (
                f"This Innovation Thesis articulates the value proposition and "
                f"customer validation behind {pursuit_title}, demonstrating "
                f"market readiness and implementation path."
            )
        elif style.style_key == "grant":
            return (
                f"This Innovation Thesis addresses a significant opportunity "
                f"through {pursuit_title}, presenting the innovative approach "
                f"and expected outcomes of this initiative."
            )
        elif style.style_key == "internal":
            return (
                f"This Innovation Thesis captures the organizational learning "
                f"from {pursuit_title}, highlighting coaching insights and "
                f"patterns applicable to future work."
            )
        else:  # standard
            return (
                f"This Innovation Thesis presents the complete narrative of "
                f"{pursuit_title}, from initial discovery through validated "
                f"outcomes and forward trajectory."
            )

    def get_ordered_layers(
        self,
        itd: Dict[str, Any],
        style_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Get ITD layers in style-specific order.

        Returns list of layer dicts with name, content, and emphasis.
        """
        style = self._styles.get(style_key, self._styles["standard"])
        ordered = []

        # Layer key to display name mapping
        layer_names = {
            "thesis_statement": "Your Innovation Thesis",
            "evidence_architecture": "Evidence Architecture",
            "narrative_arc": "Narrative Arc",
            "coachs_perspective": "Coach's Perspective",
            "pattern_connections": "Pattern Connections",
            "forward_projection": "Forward Projection",
        }

        for layer_key in style.layer_ordering:
            content = itd.get(layer_key, {})
            if content:
                ordered.append({
                    "key": layer_key,
                    "name": layer_names.get(layer_key, layer_key),
                    "content": content,
                    "emphasis": style.layer_emphasis.get(layer_key, 1.0),
                })

        return ordered
