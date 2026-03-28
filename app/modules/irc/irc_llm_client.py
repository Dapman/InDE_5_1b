"""
InDE MVP v5.1b.0 - IRC LLM Client

LLM wrapper with Language Sovereignty post-validation for all IRC
module interactions. All LLM-generated text passes through the validator
before being returned to ensure compliance.

2026 Yul Williams | InDEVerse, Incorporated
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("inde.irc.llm")


# =============================================================================
# LANGUAGE SOVEREIGNTY VALIDATOR
# =============================================================================

# Prohibited terms that must NEVER appear in innovator-facing output
PROHIBITED_TERMS = [
    # Fear/concern language
    r"\bfear\b", r"\bfears\b", r"\bfearful\b", r"\bafraid\b", r"\bscared\b",
    r"\bfrightened\b", r"\bthreat\b", r"\bthreatens?\b", r"\bthreatening\b",
    r"\bdread\b", r"\bworry\b", r"\bworried\b", r"\bworries\b",
    r"\banxious\b", r"\banxiety\b",
    # Failure language
    r"\bfailure\b", r"\bfailed\b", r"\bfailing\b",
    # Risk/danger language
    r"\brisk\b", r"\brisky\b", r"\bat risk\b",
    r"\bdanger\b", r"\bdangerous\b",
    # Problem/gap language
    r"\bserious gap\b", r"\bserious gaps\b",
    r"\byour plan has problems\b",
    # Warning language
    r"\bwarn\b", r"\bwarning\b",
    # Internal terms that should never be exposed
    r"\bIRC\b", r"\.resource\b", r"\.irc\b",
    r"\bchallenge_registered\b", r"\bUNRESOLVED\b",
    r"\bIRC_CONSOLIDATION\b", r"\bRESOURCE_SIGNAL\b",
    r"\bInnovation Resource Canvas\b",
]

# Compile for performance
PROHIBITED_PATTERNS = [re.compile(term, re.IGNORECASE) for term in PROHIBITED_TERMS]


def validate_language_sovereignty(text: str) -> tuple[bool, List[str]]:
    """
    Validate text for Language Sovereignty compliance.

    Args:
        text: Text to validate

    Returns:
        Tuple of (is_valid, list of violations found)
    """
    violations = []

    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(text):
            violations.append(pattern.pattern)

    return len(violations) == 0, violations


def sanitize_output(text: str) -> str:
    """
    Sanitize LLM output to remove any prohibited terms.
    Used as a fallback when retries are exhausted.
    """
    result = text

    # Replace common violations with acceptable alternatives
    replacements = [
        (r"\brisk(s|y)?\b", "consideration"),
        (r"\bfear(s|ful)?\b", "concern"),
        (r"\bfailure\b", "learning opportunity"),
        (r"\bfailed\b", "didn't work out"),
        (r"\bthreat(s|ening)?\b", "challenge"),
        (r"\bdanger(ous)?\b", "complexity"),
        (r"\bworr(y|ied|ies)\b", "thinking about"),
        (r"\bserious gap(s)?\b", "open question"),
        (r"\bUNRESOLVED\b", "still open"),
        (r"\bat risk\b", "to work through"),
    ]

    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


# =============================================================================
# IRC LLM CLIENT
# =============================================================================

class IRCLLMClient:
    """
    LLM client specialized for IRC module operations.
    All outputs pass through Language Sovereignty validation.
    """

    def __init__(self, llm_gateway_client):
        """
        Initialize IRC LLM Client.

        Args:
            llm_gateway_client: The InDE LLM Gateway client for API calls
        """
        self.llm_client = llm_gateway_client
        self._max_retries = 2

    async def extract_resource_signal(
        self,
        text: str,
        matched_families: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract resource details from signal text using LLM.

        Args:
            text: The coaching turn text containing the signal
            matched_families: List of matched signal family names
            context: Optional coaching context

        Returns:
            Dict with: resource_name, category, confidence, uncertainty_flag
        """
        from .irc_prompt_library import RESOURCE_EXTRACTION_PROMPT

        prompt = RESOURCE_EXTRACTION_PROMPT.format(
            text=text[:500],
            families=", ".join(matched_families),
            context_hint=self._format_context_hint(context),
        )

        try:
            response = await self._call_with_validation(
                prompt=prompt,
                max_tokens=150,
                purpose="resource_extraction",
            )

            if not response:
                return None

            # Parse JSON response
            return self._parse_extraction_response(response)

        except Exception as e:
            logger.error(f"[IRCLLM] Extraction error: {e}")
            return None

    async def generate_coaching_probe(
        self,
        signal_family: str,
        resource_name: Optional[str],
        pursuit_phase: str,
        coaching_context: Dict[str, Any],
    ) -> str:
        """
        Generate a coaching probe to extend resource signal exploration.

        Args:
            signal_family: The detected signal family
            resource_name: Extracted resource name (if available)
            pursuit_phase: Current pursuit phase
            coaching_context: Full coaching context

        Returns:
            Coaching probe text (Language Sovereignty validated)
        """
        from .irc_prompt_library import COACHING_PROBE_PROMPT

        prompt = COACHING_PROBE_PROMPT.format(
            signal_family=signal_family,
            resource_name=resource_name or "the resource mentioned",
            pursuit_phase=pursuit_phase,
            context_summary=self._summarize_context(coaching_context),
        )

        response = await self._call_with_validation(
            prompt=prompt,
            max_tokens=200,
            purpose="coaching_probe",
        )

        return response or ""

    async def generate_consolidation_offer(
        self,
        resource_summary: str,
        pursuit_context: Dict[str, Any],
    ) -> str:
        """
        Generate the consolidation offer coaching text.

        Args:
            resource_summary: Summary of accumulated resources
            pursuit_context: Pursuit context

        Returns:
            Consolidation offer text (Language Sovereignty validated)
        """
        from .irc_prompt_library import CONSOLIDATION_OFFER_PROMPT

        prompt = CONSOLIDATION_OFFER_PROMPT.format(
            resource_summary=resource_summary,
            pursuit_name=pursuit_context.get("title", "your pursuit"),
        )

        response = await self._call_with_validation(
            prompt=prompt,
            max_tokens=250,
            purpose="consolidation_offer",
        )

        return response or ""

    async def generate_synthesis_notes(
        self,
        canvas_snapshot: Dict[str, Any],
    ) -> str:
        """
        Generate synthesis notes for the IRC canvas.

        Args:
            canvas_snapshot: The computed canvas data

        Returns:
            Synthesis notes text (Language Sovereignty validated)
        """
        from .irc_prompt_library import SYNTHESIS_NOTES_PROMPT

        prompt = SYNTHESIS_NOTES_PROMPT.format(
            secured_count=canvas_snapshot.get("secured_count", 0),
            open_count=canvas_snapshot.get("unresolved_count", 0),
            total_cost_low=canvas_snapshot.get("total_cost_low", 0),
            total_cost_high=canvas_snapshot.get("total_cost_high", 0),
            completeness=canvas_snapshot.get("canvas_completeness", 0),
        )

        response = await self._call_with_validation(
            prompt=prompt,
            max_tokens=200,
            purpose="synthesis_notes",
        )

        return response or ""

    async def _call_with_validation(
        self,
        prompt: str,
        max_tokens: int,
        purpose: str,
    ) -> Optional[str]:
        """
        Call LLM and validate response for Language Sovereignty.
        Retries up to max_retries if violations found.
        """
        from .irc_prompt_library import IRC_SYSTEM_PROMPT_BASE

        for attempt in range(self._max_retries + 1):
            try:
                # Make LLM call
                response = await self.llm_client.complete(
                    system_prompt=IRC_SYSTEM_PROMPT_BASE,
                    user_prompt=prompt,
                    max_tokens=max_tokens,
                )

                if not response:
                    return None

                # Validate Language Sovereignty
                is_valid, violations = validate_language_sovereignty(response)

                if is_valid:
                    return response

                logger.warning(
                    f"[IRCLLM] Language Sovereignty violation in {purpose} "
                    f"(attempt {attempt + 1}): {violations}"
                )

                if attempt < self._max_retries:
                    # Add correction instruction and retry
                    prompt = self._add_correction_instruction(prompt, violations)
                else:
                    # Exhausted retries — sanitize and return
                    logger.warning(f"[IRCLLM] Sanitizing output after {self._max_retries} retries")
                    return sanitize_output(response)

            except Exception as e:
                logger.error(f"[IRCLLM] LLM call error: {e}")
                return None

        return None

    def _add_correction_instruction(self, prompt: str, violations: List[str]) -> str:
        """Add correction instruction for retry."""
        correction = (
            "\n\nIMPORTANT CORRECTION: Your previous response contained "
            "prohibited language. DO NOT use these terms: "
            f"{', '.join(v for v in violations[:5])}. "
            "Use neutral, constructive language instead."
        )
        return prompt + correction

    def _format_context_hint(self, context: Optional[Dict[str, Any]]) -> str:
        """Format context for extraction prompt."""
        if not context:
            return ""

        hints = []
        if context.get("pursuit_phase"):
            hints.append(f"Phase: {context['pursuit_phase']}")
        if context.get("archetype"):
            hints.append(f"Methodology: {context['archetype']}")

        return " | ".join(hints) if hints else ""

    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Create a brief context summary for prompts."""
        parts = []

        if context.get("pursuit_title"):
            parts.append(f"working on: {context['pursuit_title']}")
        if context.get("current_phase"):
            parts.append(f"in phase: {context['current_phase']}")
        if context.get("recent_topic"):
            parts.append(f"discussing: {context['recent_topic']}")

        return ", ".join(parts) if parts else "general coaching session"

    def _parse_extraction_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from extraction LLM call."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "resource_name": data.get("resource_name"),
                    "category": data.get("category"),
                    "confidence": float(data.get("confidence", 0.7)),
                    "uncertainty_flag": data.get("uncertainty_flag", False),
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[IRCLLM] Failed to parse extraction response: {e}")

        return None
