"""
InDE MVP v5.1b.0 - Export LLM Client

Sovereignty-gated Anthropic API client for the export module.
Handles style bridge paragraph generation with Language Sovereignty
enforcement and methodology name prohibition.

LLM Budget: 350 tokens max per export (1 call for style bridge)

2026 Yul Williams | InDEVerse, Incorporated
"""

import re
import logging
from typing import Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("inde.export.llm_client")


# =============================================================================
# LANGUAGE SOVEREIGNTY - PROHIBITED TERMS
# =============================================================================

PROHIBITED_VOCABULARY = [
    r"\bfear\b", r"\bfears\b", r"\bfearful\b",
    r"\bafraid\b", r"\bscared\b", r"\bscare\b",
    r"\bfailure\b", r"\bfailed\b", r"\bfailing\b", r"\bfail\b",
    r"\bdanger\b", r"\bdangerous\b",
    r"\bthreat\b", r"\bthreatens\b", r"\bthreatening\b",
    r"\bwarn\b", r"\bwarning\b",
    r"\bstruggle\b", r"\bstruggles\b", r"\bstruggled\b",
    r"\bproblem\b", r"\bproblems\b",
    r"\bmistake\b", r"\bmistakes\b",
    r"\brisk\b", r"\brisky\b",
    r"\banxious\b", r"\banxiety\b",
    r"\bworry\b", r"\bworried\b", r"\bworries\b",
]

PROHIBITED_METHODOLOGY_NAMES = [
    r"\bLean Startup\b",
    r"\bDesign Thinking\b",
    r"\bTRIZ\b",
    r"\bBlue Ocean\b",
    r"\bStage[\s\-]Gate\b",
    r"\bPIM\b",
    r"\bAgile\b",
    r"\bSix Sigma\b",
    r"\bIDEO\b",
    r"\bIncubation methodology\b",
    r"\bBusiness Model Canvas\b",
    r"\bEmpathy Map\b",
    r"\bStrategy Canvas\b",
    r"\bERRC Grid\b",
    r"\bValue Proposition Canvas\b",
]

# Compile patterns for efficiency
_PROHIBITED_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in PROHIBITED_VOCABULARY + PROHIBITED_METHODOLOGY_NAMES
]


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

STYLE_BRIDGE_SYSTEM_PROMPT = """
You are writing the opening paragraph of an innovation document for a
specific audience. Your opening paragraph must:

1. Orient the reader to the pursuit's central discovery in 2-3 sentences
2. Frame what follows according to this audience perspective: {opening_frame}
3. Be entirely self-contained - this paragraph appears before the main
   document sections begin
4. Sound like compelling, clear prose - not a summary or a list

ABSOLUTE CONSTRAINTS:
- Do not use the following vocabulary: fear, afraid, failure, fail, risk,
  threat, danger, warning, struggle, problem, mistake, anxiety, worry
- Do not name any specific innovation methodologies or frameworks
- Do not use language that frames the innovation in terms of problems
  overcome or failures avoided
- The paragraph must work for someone reading it with no prior context

Write exactly one paragraph of 50-80 words.
"""

CORRECTION_PROMPT = """
Your previous response contained prohibited terms. Rewrite it without:
{violations}

Keep the same meaning and audience framing, but replace the prohibited
terms with neutral alternatives. Write exactly one paragraph of 50-80 words.
"""


# =============================================================================
# EXPORT LLM CLIENT
# =============================================================================

@dataclass
class StyleBridgeRequest:
    """Request for style bridge generation."""
    style_key: str
    style_display_name: str
    opening_frame: str
    itd_thesis_summary: str
    audience_context: Optional[str] = None


class ExportLLMClient:
    """
    Sovereignty-gated Anthropic API client for export module.

    Features:
    - Style bridge generation (350 tokens max)
    - Language Sovereignty enforcement
    - 2-retry logic on sovereignty violations
    """

    MODEL = "claude-sonnet-4-20250514"
    STYLE_BRIDGE_MAX_TOKENS = 350
    MAX_RETRIES = 2

    def __init__(self, anthropic_client: Any = None, llm_gateway_url: Optional[str] = None):
        """
        Initialize the export LLM client.

        Args:
            anthropic_client: Pre-configured Anthropic client (optional)
            llm_gateway_url: URL for LLM gateway service (optional)
        """
        self._client = anthropic_client
        self._gateway_url = llm_gateway_url
        self._initialized = False

    def _ensure_client(self):
        """Ensure the Anthropic client is initialized."""
        if self._initialized:
            return

        if self._client is None:
            try:
                import anthropic
                from core.config import ANTHROPIC_API_KEY
                self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                logger.warning("Anthropic SDK not available")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")

        self._initialized = True

    def generate_style_bridge(
        self,
        style: Any,  # NarrativeStyle
        itd_thesis_summary: str,
        audience_context: Optional[str] = None,
    ) -> str:
        """
        Generate the audience-framing opening paragraph for a styled ITD.

        Args:
            style: NarrativeStyle object with opening_frame
            itd_thesis_summary: Brief summary of the thesis (max 200 chars)
            audience_context: Optional additional audience context

        Returns:
            Style bridge paragraph (plain prose string)
        """
        self._ensure_client()

        if not self._client:
            logger.warning("No LLM client available, using fallback bridge")
            return self._generate_fallback(style, itd_thesis_summary)

        # Build the prompt
        system_prompt = STYLE_BRIDGE_SYSTEM_PROMPT.format(
            opening_frame=style.opening_frame
        )

        user_message = f"Innovation thesis summary: {itd_thesis_summary}"
        if audience_context:
            user_message += f"\n\nAdditional audience context: {audience_context}"

        # Attempt generation with retries
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = self._client.messages.create(
                    model=self.MODEL,
                    max_tokens=self.STYLE_BRIDGE_MAX_TOKENS,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )

                content = response.content[0].text if response.content else ""

                # Check for sovereignty violations
                violations = self._check_violations(content)
                if not violations:
                    logger.info(f"Style bridge generated for {style.style_key}")
                    return content

                # Violations found - retry with correction prompt
                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"Sovereignty violations in style bridge (attempt {attempt + 1}): "
                        f"{violations}"
                    )
                    user_message = CORRECTION_PROMPT.format(
                        violations=", ".join(violations)
                    ) + f"\n\nOriginal: {content}"
                else:
                    # Final attempt failed - clean manually
                    logger.warning(
                        f"Max retries reached, cleaning violations manually: {violations}"
                    )
                    return self._clean_violations(content, violations)

            except Exception as e:
                logger.error(f"LLM API error in style bridge generation: {e}")
                return self._generate_fallback(style, itd_thesis_summary)

        return self._generate_fallback(style, itd_thesis_summary)

    def _check_violations(self, text: str) -> list:
        """Check text for sovereignty violations."""
        violations = []
        for pattern in _PROHIBITED_PATTERNS:
            if pattern.search(text):
                violations.append(pattern.pattern)
        return violations

    def _clean_violations(self, text: str, violations: list) -> str:
        """Remove or replace violations from text."""
        cleaned = text
        replacements = {
            "fear": "consideration",
            "afraid": "uncertain",
            "failure": "learning",
            "failed": "learned from",
            "fail": "explore",
            "danger": "complexity",
            "threat": "consideration",
            "warning": "signal",
            "struggle": "navigated",
            "problem": "opportunity",
            "mistake": "learning",
            "risk": "variable",
            "anxiety": "uncertainty",
            "worry": "consideration",
        }

        for term, replacement in replacements.items():
            pattern = re.compile(rf"\b{term}\b", re.IGNORECASE)
            cleaned = pattern.sub(replacement, cleaned)

        # Remove methodology names entirely
        for pattern in _PROHIBITED_PATTERNS:
            if "methodology" in pattern.pattern.lower() or any(
                m in pattern.pattern for m in ["Lean", "Design", "TRIZ", "Blue", "Stage"]
            ):
                cleaned = pattern.sub("", cleaned)

        return cleaned.strip()

    def _generate_fallback(self, style: Any, thesis_summary: str) -> str:
        """Generate a fallback bridge without LLM."""
        style_bridges = {
            "investor": (
                "This Innovation Thesis presents a validated market opportunity "
                "with demonstrated traction and a clear trajectory for growth. "
                "The evidence architecture and forward projections that follow "
                "outline the investment case."
            ),
            "academic": (
                "This Innovation Thesis documents a rigorous discovery process, "
                "presenting the methodology of inquiry and the evidence that "
                "emerged from systematic validation. The narrative captures "
                "how assumptions were tested and refined."
            ),
            "commercial": (
                "This Innovation Thesis articulates a clear value proposition "
                "validated through customer engagement. The evidence and "
                "trajectory that follow demonstrate market readiness and "
                "implementation pathway."
            ),
            "grant": (
                "This Innovation Thesis addresses a significant opportunity "
                "through a systematic approach to discovery and validation. "
                "The evidence architecture and expected outcomes presented "
                "demonstrate the initiative's merit."
            ),
            "internal": (
                "This Innovation Thesis captures the organizational learning "
                "from this pursuit, presenting coaching insights and patterns "
                "that inform future innovation work."
            ),
            "standard": (
                "This Innovation Thesis presents the complete narrative of "
                "discovery and validation, from initial exploration through "
                "validated outcomes and forward trajectory."
            ),
        }
        return style_bridges.get(style.style_key, style_bridges["standard"])
