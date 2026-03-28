"""
InDE v4.8 - Projection LLM Client

Unified LLM client for all three projection module generators.
Mirrors ITDLLMClient from v4.7 but is projection-module scoped.

Enforces Language Sovereignty via post-generation validation.
Applies 2-retry logic with violation-correction prompt injection.

2026 Yul Williams | InDEVerse, Incorporated
"""

import json
import re
import logging
from typing import Optional

logger = logging.getLogger("inde.projection.llm_client")

# Language Sovereignty - prohibited terms (mirrors v4.7 ITDLLMClient)
PROHIBITED_TERMS = [
    r"\bfear\b", r"\bfears\b", r"\bfearful\b", r"\bafraid\b", r"\bscared\b",
    r"\bfailure\b", r"\bfailed\b", r"\bfailing\b", r"\bfail\b",
    r"\brisk\b", r"\brisky\b", r"\bthreat\b", r"\bthreatened\b",
    r"\bdanger\b", r"\bdangerous\b", r"\bwarn\b", r"\bwarning\b",
    r"\bstruggle\b", r"\bstruggled\b", r"\bproblem\b", r"\bmistake\b",
    r"\bdead[\s\-]end\b", r"\bwatch[\s\-]out\b", r"\bbe[\s\-]careful\b",
    r"\bworry\b", r"\bworries\b",
]

# Methodology name prohibition (additional to base sovereignty)
PROHIBITED_METHODOLOGY_NAMES = [
    r"\bLean Startup\b", r"\bDesign Thinking\b", r"\bTRIZ\b",
    r"\bBlue Ocean\b", r"\bStage-Gate\b", r"\bStage Gate\b",
    r"\bAgile\b", r"\bSix Sigma\b", r"\bIDEO\b", r"\bPIM\b",
    r"\bIncubation methodology\b",
]

ALL_PROHIBITED = PROHIBITED_TERMS + PROHIBITED_METHODOLOGY_NAMES

SOVEREIGNTY_CORRECTION_PROMPT = """
The previous response contained prohibited language. Please rewrite the
response, replacing ALL instances of prohibited terms with approved
alternatives:
  fear/afraid -> challenge/uncertainty
  failure/fail -> learning/course correction
  risk -> variable/design consideration
  threat/danger -> signal/factor
  struggle -> navigate/work through
  problem -> question/dimension
  methodology brand names -> analytical descriptions only

Rewrite the COMPLETE response in the same JSON format. No other changes.
"""


class ProjectionLLMClient:
    """
    LLM client for projection module generation.
    Uses the existing LLM Gateway infrastructure.
    """

    MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 700
    MAX_RETRIES = 2

    def __init__(self, llm_gateway=None):
        """
        Initialize ProjectionLLMClient.

        Args:
            llm_gateway: Optional LLM Gateway instance. If not provided,
                         will attempt to use the core LLM interface.
        """
        self.llm_gateway = llm_gateway
        self._client = None

    def _get_client(self):
        """Get or create LLM client."""
        if self._client:
            return self._client

        if self.llm_gateway:
            return self.llm_gateway

        # Try to use core LLM interface
        try:
            from core.llm_interface import LLMInterface
            self._client = LLMInterface()
            return self._client
        except ImportError:
            logger.warning("[ProjectionLLMClient] No LLM interface available")
            return None

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = None,
        parse_json: bool = False,
        sovereignty_validate: bool = True,
    ) -> dict | str:
        """
        Generate content with optional JSON parsing and sovereignty validation.

        Args:
            system_prompt: System prompt for the LLM
            user_prompt: User prompt with data
            max_tokens: Maximum tokens for response
            parse_json: Whether to parse response as JSON
            sovereignty_validate: Whether to validate against prohibited terms

        Returns:
            dict if parse_json=True, else string
        """
        max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        client = self._get_client()

        if not client:
            logger.error("[ProjectionLLMClient] No LLM client available")
            return {} if parse_json else ""

        messages = [{"role": "user", "content": user_prompt}]

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                # Use the LLM interface's generate method
                raw_text = client.generate(
                    system_prompt=system_prompt,
                    user_message=user_prompt if attempt == 0 else self._build_retry_message(messages),
                    max_tokens=max_tokens,
                )

                if not raw_text:
                    logger.warning("[ProjectionLLMClient] Empty response from LLM")
                    raw_text = ""

                if sovereignty_validate:
                    violations = self._find_violations(raw_text)
                    if violations and attempt < self.MAX_RETRIES:
                        logger.warning(
                            f"[ProjectionLLMClient] Sovereignty violations on "
                            f"attempt {attempt + 1}: {violations[:3]}. Retrying."
                        )
                        messages = [
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": raw_text},
                            {"role": "user", "content": SOVEREIGNTY_CORRECTION_PROMPT},
                        ]
                        continue
                    elif violations:
                        logger.error(
                            f"[ProjectionLLMClient] Sovereignty violations persist "
                            f"after {self.MAX_RETRIES} retries: {violations[:3]}. "
                            "Returning best available output."
                        )

                if parse_json:
                    return self._safe_parse_json(raw_text)
                return raw_text

            except Exception as e:
                logger.error(f"[ProjectionLLMClient] Generation error: {e}")
                if attempt == self.MAX_RETRIES:
                    return {} if parse_json else ""

        return {} if parse_json else ""

    def _build_retry_message(self, messages: list) -> str:
        """Build retry message from conversation history."""
        parts = []
        for msg in messages:
            if msg["role"] == "assistant":
                parts.append(f"Your previous response:\n{msg['content']}")
            elif msg["role"] == "user" and msg["content"] == SOVEREIGNTY_CORRECTION_PROMPT:
                parts.append(SOVEREIGNTY_CORRECTION_PROMPT)
        return "\n\n".join(parts)

    def _find_violations(self, text: str) -> list[str]:
        """Return list of prohibited terms found in text (case-insensitive)."""
        return [
            pattern for pattern in ALL_PROHIBITED
            if re.search(pattern, text, re.IGNORECASE)
        ]

    def _safe_parse_json(self, raw_text: str) -> dict:
        """Strip markdown fences and parse JSON safely."""
        if not raw_text:
            return {}

        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()
        cleaned = cleaned.rstrip("`").strip()

        # Try to find JSON object in the text
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"[ProjectionLLMClient] JSON parse failed: {e}")
            return {}
