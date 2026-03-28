"""
InDE MVP v4.7.0 - Thesis Statement Generator

Layer 1 of the ITD Composition Engine.
Synthesizes vision, concerns, and archetype into a compelling thesis statement.

Input Sources:
- Vision artifact content
- Concerns (fear) artifact content
- Pursuit archetype/methodology

Output:
- A 2-3 sentence thesis that captures the innovation's essence
- Confidence score based on input quality
- Token usage tracking

2026 Yul Williams | InDEVerse, Incorporated
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

import httpx

from core.config import LLM_GATEWAY_URL
from modules.itd.itd_schemas import ThesisStatementLayer

logger = logging.getLogger("inde.itd.thesis_statement")


# =============================================================================
# THESIS GENERATION PROMPT
# =============================================================================

THESIS_SYNTHESIS_PROMPT = """You are synthesizing an innovation thesis statement.

INNOVATION CONTEXT:
Title: {pursuit_title}
Methodology: {archetype}

VISION SUMMARY:
{vision_content}

CONCERNS SUMMARY:
{concerns_content}

ARCHETYPE CONTEXT:
{archetype_guidance}

TASK:
Write a compelling thesis statement that:
1. Captures the core innovation opportunity in 2-3 sentences
2. Acknowledges the key challenges being addressed
3. Reflects the methodology approach naturally (without jargon)
4. Could stand alone as an executive summary

The thesis should be written in third person, professional tone.
Do NOT use bullet points or headers - write flowing prose.

OUTPUT FORMAT:
Respond with ONLY the thesis text, no preamble or explanation."""


# Archetype-specific guidance for thesis framing
ARCHETYPE_GUIDANCE = {
    "lean_startup": (
        "This innovation follows a Lean Startup approach: rapid experimentation, "
        "customer validation, and iterative learning. Frame the thesis around "
        "hypotheses tested and validated insights."
    ),
    "design_thinking": (
        "This innovation follows Design Thinking: deep user empathy, iterative "
        "prototyping, and human-centered solutions. Frame the thesis around "
        "user needs understood and solutions shaped by feedback."
    ),
    "stage_gate": (
        "This innovation follows Stage-Gate: structured milestones, rigorous "
        "evaluation criteria, and disciplined progression. Frame the thesis around "
        "gates passed and evidence accumulated."
    ),
    "triz": (
        "This innovation follows TRIZ methodology: systematic problem-solving "
        "through contradiction resolution. Frame the thesis around "
        "the key contradictions identified and resolved."
    ),
    "blue_ocean": (
        "This innovation follows Blue Ocean Strategy: creating uncontested market "
        "space by eliminating, reducing, raising, and creating factors. Frame the "
        "thesis around the new value proposition and market differentiation."
    ),
    "incubation": (
        "This innovation is an incubation pursuit: exploratory, early-stage "
        "development with focus on investment readiness. Frame the thesis around "
        "the opportunity identified and investment potential."
    ),
}


# =============================================================================
# THESIS STATEMENT GENERATOR
# =============================================================================

class ThesisStatementGenerator:
    """
    Generates Layer 1: Thesis Statement.

    Pulls vision and concerns from pursuit artifacts, synthesizes
    with archetype context into a compelling narrative thesis.
    """

    def __init__(self, db, gateway_url: str = None):
        """
        Initialize ThesisStatementGenerator.

        Args:
            db: Database instance for artifact retrieval
            gateway_url: LLM Gateway URL (defaults to config)
        """
        self.db = db
        self._gateway_url = gateway_url or LLM_GATEWAY_URL
        self._http_client = httpx.Client(timeout=90.0)

    def generate(self, pursuit_id: str) -> ThesisStatementLayer:
        """
        Generate the thesis statement layer for a pursuit.

        Args:
            pursuit_id: The pursuit to generate thesis for

        Returns:
            ThesisStatementLayer with generated content
        """
        logger.info(f"[ThesisGenerator] Generating thesis for pursuit: {pursuit_id}")

        # Collect input data
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.error(f"[ThesisGenerator] Pursuit not found: {pursuit_id}")
            return self._empty_layer("Pursuit not found")

        # Get artifacts
        vision_content = self._get_artifact_content(pursuit_id, "vision")
        concerns_content = self._get_artifact_content(pursuit_id, "fears")

        # Get archetype
        archetype = pursuit.get("methodology", {}).get("archetype", "lean_startup")
        if isinstance(archetype, dict):
            archetype = archetype.get("id", "lean_startup")

        pursuit_title = pursuit.get("title", "Innovation Pursuit")

        # Calculate input confidence (based on available content)
        input_confidence = self._calculate_input_confidence(
            vision_content, concerns_content
        )

        if input_confidence < 0.3:
            logger.warning(f"[ThesisGenerator] Low input confidence: {input_confidence}")
            return self._empty_layer("Insufficient artifact content for thesis synthesis")

        # Generate thesis via LLM
        thesis_text, token_count = self._synthesize_thesis(
            pursuit_title=pursuit_title,
            archetype=archetype,
            vision_content=vision_content,
            concerns_content=concerns_content,
        )

        if not thesis_text:
            return self._empty_layer("LLM synthesis failed")

        # Build layer
        layer = ThesisStatementLayer(
            thesis_text=thesis_text,
            vision_summary=self._truncate(vision_content, 500),
            concerns_summary=self._truncate(concerns_content, 500),
            archetype_context=ARCHETYPE_GUIDANCE.get(archetype, ""),
            generated_at=datetime.now(timezone.utc),
            token_budget_used=token_count,
            confidence_score=input_confidence,
        )

        logger.info(f"[ThesisGenerator] Generated thesis ({token_count} tokens, {input_confidence:.2f} confidence)")
        return layer

    def _get_artifact_content(self, pursuit_id: str, artifact_type: str) -> str:
        """Get the content of an artifact by type."""
        artifacts = self.db.get_pursuit_artifacts(pursuit_id, artifact_type)
        if not artifacts:
            return ""

        # Get most recent artifact
        artifact = artifacts[0]
        content = artifact.get("content", "")

        # Handle structured content
        if isinstance(content, dict):
            # Flatten dict to text
            parts = []
            for key, value in content.items():
                if isinstance(value, str) and value:
                    parts.append(f"{key}: {value}")
                elif isinstance(value, dict) and value.get("text"):
                    parts.append(f"{key}: {value['text']}")
            return "\n".join(parts)

        return str(content) if content else ""

    def _calculate_input_confidence(self, vision: str, concerns: str) -> float:
        """
        Calculate confidence score based on input quality.

        Scores:
        - Vision present and substantial (>100 chars): 0.5
        - Concerns present and substantial (>50 chars): 0.3
        - Both present: 0.2 bonus
        """
        confidence = 0.0

        if vision and len(vision) > 100:
            confidence += 0.5
        elif vision and len(vision) > 50:
            confidence += 0.3
        elif vision:
            confidence += 0.1

        if concerns and len(concerns) > 50:
            confidence += 0.3
        elif concerns:
            confidence += 0.15

        # Bonus for having both
        if vision and concerns:
            confidence += 0.2

        return min(confidence, 1.0)

    def _synthesize_thesis(
        self,
        pursuit_title: str,
        archetype: str,
        vision_content: str,
        concerns_content: str,
    ) -> tuple:
        """
        Call LLM to synthesize thesis statement.

        Returns:
            (thesis_text, token_count) tuple
        """
        archetype_guidance = ARCHETYPE_GUIDANCE.get(archetype, "")

        prompt = THESIS_SYNTHESIS_PROMPT.format(
            pursuit_title=pursuit_title,
            archetype=archetype,
            vision_content=vision_content or "No vision artifact available.",
            concerns_content=concerns_content or "No concerns documented.",
            archetype_guidance=archetype_guidance,
        )

        try:
            response = self._http_client.post(
                f"{self._gateway_url}/llm/chat",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "system_prompt": "You are an expert innovation analyst creating thesis statements.",
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "preferred_provider": "auto"
                },
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("content", "")
            # Estimate token count (rough: 4 chars per token)
            token_count = len(prompt) // 4 + len(content) // 4

            return content.strip(), token_count

        except Exception as e:
            logger.error(f"[ThesisGenerator] LLM call failed: {e}")
            return "", 0

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _empty_layer(self, reason: str) -> ThesisStatementLayer:
        """Return an empty layer with error reason."""
        return ThesisStatementLayer(
            thesis_text=f"Unable to generate thesis: {reason}",
            generated_at=datetime.now(timezone.utc),
            confidence_score=0.0,
        )

    def close(self):
        """Close HTTP client."""
        self._http_client.close()
