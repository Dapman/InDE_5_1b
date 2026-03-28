"""
InDE MVP v4.7.0 - Narrative Arc Generator

Layer 3 of the ITD Composition Engine.
Creates an archetype-structured story in 5 acts.

5-Act Structure:
1. INCEPTION - How the idea began
2. EXPLORATION - Discovery and understanding
3. VALIDATION - Testing and learning
4. SYNTHESIS - Bringing it together
5. RESOLUTION - Where we landed

Each act is shaped by the pursuit's archetype, creating methodology-appropriate
narrative framing without surfacing methodology jargon.

2026 Yul Williams | InDEVerse, Incorporated
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

import httpx

from core.config import LLM_GATEWAY_URL
from modules.itd.itd_schemas import (
    NarrativeArcLayer,
    NarrativeAct,
    NarrativeActType,
)

logger = logging.getLogger("inde.itd.narrative_arc")


# =============================================================================
# NARRATIVE PROMPTS
# =============================================================================

NARRATIVE_SYSTEM_PROMPT = """You are an expert innovation storyteller.
You craft compelling narratives that capture the journey of innovation.
Your stories are professional, engaging, and insightful.
You never use methodology jargon - instead, you describe what happened in accessible terms."""

NARRATIVE_ARC_PROMPT = """Create a 5-act narrative for this innovation journey.

PURSUIT CONTEXT:
Title: {pursuit_title}
Duration: {duration_days} days
Terminal State: {terminal_state}

VISION SUMMARY:
{vision_summary}

KEY MILESTONES:
{milestones}

PIVOT POINTS:
{pivots}

RETROSPECTIVE INSIGHTS:
{retrospective_summary}

ARCHETYPE GUIDANCE:
{archetype_guidance}

Create a compelling 5-act narrative:
1. INCEPTION - How this idea began and what sparked it
2. EXPLORATION - The discovery phase, understanding the problem and solution space
3. VALIDATION - Testing assumptions, gathering evidence, learning from experiments
4. SYNTHESIS - Bringing learnings together, refining the approach
5. RESOLUTION - Where the journey landed and what was achieved

For each act, provide:
- A short title (2-5 words)
- Narrative content (3-5 sentences)
- Key moments (1-2 bullet points of specific events)

Respond in JSON format:
{{
    "opening_hook": "A compelling 1-sentence opening",
    "acts": [
        {{
            "act_type": "inception",
            "title": "...",
            "content": "...",
            "key_moments": ["...", "..."]
        }},
        ...
    ],
    "closing_reflection": "A thoughtful 1-2 sentence closing"
}}"""


# Archetype-specific narrative guidance
ARCHETYPE_NARRATIVE_GUIDANCE = {
    "lean_startup": (
        "Frame the narrative around hypotheses and experiments. "
        "Emphasize build-measure-learn cycles, customer interviews, and pivots. "
        "The story should highlight what was learned from each test."
    ),
    "design_thinking": (
        "Frame the narrative around user empathy and iteration. "
        "Emphasize deep understanding of users, prototyping, and feedback loops. "
        "The story should highlight insights gained from user engagement."
    ),
    "stage_gate": (
        "Frame the narrative around structured progression. "
        "Emphasize milestone achievements, gate reviews, and criteria met. "
        "The story should highlight disciplined decision-making."
    ),
    "triz": (
        "Frame the narrative around problem-solving and contradiction resolution. "
        "Emphasize the contradictions identified and how they were resolved. "
        "The story should highlight inventive solutions."
    ),
    "blue_ocean": (
        "Frame the narrative around value innovation and market creation. "
        "Emphasize what was eliminated, reduced, raised, and created. "
        "The story should highlight differentiation from competition."
    ),
    "incubation": (
        "Frame the narrative around exploration and opportunity assessment. "
        "Emphasize the investment thesis development and market validation. "
        "The story should highlight the opportunity's potential."
    ),
}


# =============================================================================
# NARRATIVE ARC GENERATOR
# =============================================================================

class NarrativeArcGenerator:
    """
    Generates Layer 3: Narrative Arc.

    Creates a 5-act story structure from pursuit history,
    shaped by the archetype's narrative style.
    """

    def __init__(self, db, gateway_url: str = None):
        """
        Initialize NarrativeArcGenerator.

        Args:
            db: Database instance
            gateway_url: LLM Gateway URL (defaults to config)
        """
        self.db = db
        self._gateway_url = gateway_url or LLM_GATEWAY_URL
        self._http_client = httpx.Client(timeout=120.0)

    def generate(
        self,
        pursuit_id: str,
        evidence_layer=None,
        retrospective_data: Dict = None
    ) -> NarrativeArcLayer:
        """
        Generate the narrative arc layer for a pursuit.

        Args:
            pursuit_id: The pursuit to generate narrative for
            evidence_layer: Optional EvidenceArchitectureLayer with pivot data
            retrospective_data: Optional retrospective artifact data

        Returns:
            NarrativeArcLayer with 5-act structure
        """
        logger.info(f"[NarrativeGenerator] Generating narrative for pursuit: {pursuit_id}")

        # Get pursuit
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.error(f"[NarrativeGenerator] Pursuit not found: {pursuit_id}")
            return self._empty_layer()

        # Gather context
        pursuit_title = pursuit.get("title", "Innovation Pursuit")
        archetype = pursuit.get("methodology", {}).get("archetype", "lean_startup")
        if isinstance(archetype, dict):
            archetype = archetype.get("id", "lean_startup")

        terminal_state = pursuit.get("state", "ACTIVE")
        created_at = pursuit.get("created_at", datetime.now(timezone.utc))
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        duration_days = (datetime.now(timezone.utc) - created_at).days

        # Get vision summary
        vision_summary = self._get_vision_summary(pursuit_id)

        # Get milestones
        milestones = self._get_milestones(pursuit_id)

        # Get pivots from evidence layer or detect fresh
        pivots = []
        if evidence_layer and evidence_layer.pivots:
            pivots = [f"{p.pivot_type}: {p.description}" for p in evidence_layer.pivots]

        # Get retrospective summary
        retro_summary = self._format_retrospective(retrospective_data)

        # Get archetype guidance
        archetype_guidance = ARCHETYPE_NARRATIVE_GUIDANCE.get(archetype, "")

        # Generate narrative via LLM
        narrative_data, token_count = self._generate_narrative(
            pursuit_title=pursuit_title,
            duration_days=duration_days,
            terminal_state=terminal_state,
            vision_summary=vision_summary,
            milestones=milestones,
            pivots=pivots,
            retrospective_summary=retro_summary,
            archetype_guidance=archetype_guidance,
        )

        if not narrative_data:
            return self._empty_layer()

        # Build layer from LLM response
        acts = self._build_acts(narrative_data.get("acts", []), duration_days)

        layer = NarrativeArcLayer(
            acts=acts,
            archetype=archetype,
            narrative_style=ARCHETYPE_NARRATIVE_GUIDANCE.get(archetype, "Standard narrative"),
            opening_hook=narrative_data.get("opening_hook", ""),
            closing_reflection=narrative_data.get("closing_reflection", ""),
            generated_at=datetime.now(timezone.utc),
            token_budget_used=token_count,
        )

        logger.info(f"[NarrativeGenerator] Generated {len(acts)} acts ({token_count} tokens)")
        return layer

    def _get_vision_summary(self, pursuit_id: str) -> str:
        """Get vision artifact summary."""
        artifacts = self.db.get_pursuit_artifacts(pursuit_id, "vision")
        if not artifacts:
            return "No vision documented."

        artifact = artifacts[0]
        content = artifact.get("content", "")

        if isinstance(content, dict):
            # Extract key fields
            parts = []
            for key in ["problem_statement", "solution_concept", "value_proposition"]:
                if key in content:
                    val = content[key]
                    if isinstance(val, dict):
                        val = val.get("text", "")
                    if val:
                        parts.append(val)
            return " ".join(parts)[:500] if parts else "Vision documented."

        return str(content)[:500] if content else "Vision documented."

    def _get_milestones(self, pursuit_id: str) -> str:
        """Get key milestones from pursuit."""
        milestones = []

        try:
            # Get pursuit milestones
            cursor = self.db.db.pursuit_milestones.find(
                {"pursuit_id": pursuit_id}
            ).sort("completed_at", 1).limit(10)

            for m in cursor:
                title = m.get("title") or m.get("milestone_type", "Milestone")
                completed = m.get("completed_at")
                if completed:
                    milestones.append(f"- {title}")

        except Exception as e:
            logger.warning(f"[NarrativeGenerator] Error getting milestones: {e}")

        return "\n".join(milestones) if milestones else "No formal milestones recorded."

    def _format_retrospective(self, retro_data: Dict) -> str:
        """Format retrospective data for narrative prompt."""
        if not retro_data:
            return "No retrospective conducted yet."

        parts = []

        # Key learnings
        learnings = retro_data.get("key_learnings", [])
        if learnings:
            parts.append("Key Learnings: " + "; ".join(learnings[:3]))

        # Outcome reflections
        outcome = retro_data.get("outcome_reflection", "")
        if outcome:
            parts.append(f"Outcome: {outcome[:200]}")

        return " ".join(parts) if parts else "Retrospective in progress."

    def _generate_narrative(
        self,
        pursuit_title: str,
        duration_days: int,
        terminal_state: str,
        vision_summary: str,
        milestones: str,
        pivots: List[str],
        retrospective_summary: str,
        archetype_guidance: str,
    ) -> tuple:
        """
        Call LLM to generate narrative arc.

        Returns:
            (narrative_data dict, token_count) tuple
        """
        prompt = NARRATIVE_ARC_PROMPT.format(
            pursuit_title=pursuit_title,
            duration_days=duration_days,
            terminal_state=terminal_state,
            vision_summary=vision_summary,
            milestones=milestones,
            pivots="\n".join(pivots) if pivots else "No major pivots recorded.",
            retrospective_summary=retrospective_summary,
            archetype_guidance=archetype_guidance,
        )

        try:
            response = self._http_client.post(
                f"{self._gateway_url}/llm/chat",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "system_prompt": NARRATIVE_SYSTEM_PROMPT,
                    "max_tokens": 2000,
                    "temperature": 0.7,
                    "preferred_provider": "auto"
                },
                timeout=90.0
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("content", "")
            token_count = len(prompt) // 4 + len(content) // 4

            # Parse JSON response
            try:
                # Try to extract JSON from response
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    narrative_data = json.loads(content[json_start:json_end])
                    return narrative_data, token_count
            except json.JSONDecodeError:
                logger.warning("[NarrativeGenerator] Failed to parse LLM JSON response")

            return None, token_count

        except Exception as e:
            logger.error(f"[NarrativeGenerator] LLM call failed: {e}")
            return None, 0

    def _build_acts(self, acts_data: List[Dict], total_days: int) -> List[NarrativeAct]:
        """Build NarrativeAct objects from LLM response."""
        acts = []
        days_per_act = max(1, total_days // 5)

        act_type_map = {
            "inception": NarrativeActType.INCEPTION,
            "exploration": NarrativeActType.EXPLORATION,
            "validation": NarrativeActType.VALIDATION,
            "synthesis": NarrativeActType.SYNTHESIS,
            "resolution": NarrativeActType.RESOLUTION,
        }

        for i, act_data in enumerate(acts_data):
            act_type_str = act_data.get("act_type", "").lower()
            act_type = act_type_map.get(act_type_str, list(NarrativeActType)[i] if i < 5 else NarrativeActType.RESOLUTION)

            acts.append(NarrativeAct(
                act_type=act_type,
                title=act_data.get("title", f"Act {i+1}"),
                content=act_data.get("content", ""),
                key_moments=act_data.get("key_moments", []),
                duration_days=days_per_act,
            ))

        # Ensure we have all 5 acts
        while len(acts) < 5:
            idx = len(acts)
            acts.append(NarrativeAct(
                act_type=list(NarrativeActType)[idx],
                title=f"Chapter {idx + 1}",
                content="This chapter of the journey awaits documentation.",
                key_moments=[],
                duration_days=days_per_act,
            ))

        return acts[:5]

    def _empty_layer(self) -> NarrativeArcLayer:
        """Return an empty layer."""
        return NarrativeArcLayer(
            acts=[
                NarrativeAct(act_type=act_type, title=act_type.value.title())
                for act_type in NarrativeActType
            ],
            generated_at=datetime.now(timezone.utc),
        )

    def close(self):
        """Close HTTP client."""
        self._http_client.close()
