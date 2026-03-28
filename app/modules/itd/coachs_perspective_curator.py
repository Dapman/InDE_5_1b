"""
InDE MVP v4.7.0 - Coach's Perspective Curator

Layer 4 of the ITD Composition Engine.
Selects and curates the most impactful coaching moments.

Input Sources:
- Conversation history (coach messages)
- Coaching session metadata
- Breakthrough/reframe events

Output:
- 3-5 curated coaching moments
- Thematic summary of coaching approach
- Overall reflection on the coaching journey

2026 Yul Williams | InDEVerse, Incorporated
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

from core.config import LLM_GATEWAY_URL
from modules.itd.itd_schemas import (
    CoachsPerspectiveLayer,
    CoachingMoment,
)

logger = logging.getLogger("inde.itd.coachs_perspective")


# =============================================================================
# MOMENT SELECTION CRITERIA
# =============================================================================

# Keywords that indicate significant coaching moments
BREAKTHROUGH_INDICATORS = [
    "now i understand", "that makes sense", "i see",
    "i hadn't thought", "never considered", "great point",
    "you're right", "exactly what i needed", "aha",
    "this changes", "breakthrough", "clarity",
]

REFRAME_INDICATORS = [
    "another way", "different perspective", "what if",
    "consider", "alternatively", "flip", "reframe",
    "look at it", "think about", "instead of",
]

CHALLENGE_INDICATORS = [
    "push back", "challenge", "concern", "worry",
    "risky", "difficult", "obstacle", "barrier",
    "what about", "have you considered",
]

ENCOURAGEMENT_INDICATORS = [
    "well done", "great progress", "impressive",
    "strong", "on track", "proud", "achieving",
    "moving forward", "momentum", "success",
]


# =============================================================================
# CURATION PROMPTS
# =============================================================================

CURATION_SYSTEM_PROMPT = """You are summarizing the coaching perspective on an innovation journey.
Your summaries are insightful, warm, and professional.
Focus on the growth and learning that occurred."""

CURATION_PROMPT = """Analyze these coaching moments and create a summary.

COACHING MOMENTS:
{moments_text}

PURSUIT CONTEXT:
Title: {pursuit_title}
Duration: {duration_days} days
Outcome: {outcome}

Provide:
1. Identify 2-3 coaching themes that emerged
2. Write a brief overall reflection (2-3 sentences) on this coaching journey

Respond in JSON format:
{{
    "themes": ["theme1", "theme2", "theme3"],
    "overall_reflection": "..."
}}"""


# =============================================================================
# COACH'S PERSPECTIVE CURATOR
# =============================================================================

class CoachsPerspectiveCurator:
    """
    Curates Layer 4: Coach's Perspective.

    Selects the most impactful coaching moments from conversation
    history and summarizes the coaching themes.
    """

    def __init__(self, db, gateway_url: str = None):
        """
        Initialize CoachsPerspectiveCurator.

        Args:
            db: Database instance
            gateway_url: LLM Gateway URL (defaults to config)
        """
        self.db = db
        self._gateway_url = gateway_url or LLM_GATEWAY_URL
        self._http_client = httpx.Client(timeout=60.0)

    def curate(self, pursuit_id: str) -> CoachsPerspectiveLayer:
        """
        Curate the coach's perspective layer for a pursuit.

        Args:
            pursuit_id: The pursuit to curate perspective for

        Returns:
            CoachsPerspectiveLayer with selected moments
        """
        logger.info(f"[CoachCurator] Curating perspective for pursuit: {pursuit_id}")

        # Get pursuit
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.error(f"[CoachCurator] Pursuit not found: {pursuit_id}")
            return self._empty_layer()

        pursuit_title = pursuit.get("title", "Innovation Pursuit")
        terminal_state = pursuit.get("state", "ACTIVE")
        created_at = pursuit.get("created_at", datetime.now(timezone.utc))
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        duration_days = (datetime.now(timezone.utc) - created_at).days

        # Get conversation statistics
        total_sessions, total_messages = self._get_conversation_stats(pursuit_id)

        # Get conversation history
        conversations = self._get_conversations(pursuit_id)

        # Select top coaching moments
        moments, moments_considered = self._select_moments(conversations)

        # Generate themes and reflection via LLM
        themes, reflection = self._generate_summary(
            moments=moments,
            pursuit_title=pursuit_title,
            duration_days=duration_days,
            outcome=terminal_state,
        )

        layer = CoachsPerspectiveLayer(
            moments=moments[:5],  # Cap at 5 moments
            coaching_themes=themes,
            overall_reflection=reflection,
            total_sessions=total_sessions,
            total_messages=total_messages,
            moments_considered=moments_considered,
            generated_at=datetime.now(timezone.utc),
        )

        logger.info(
            f"[CoachCurator] Curated {len(moments)} moments from "
            f"{moments_considered} candidates, {len(themes)} themes"
        )
        return layer

    def _get_conversation_stats(self, pursuit_id: str) -> tuple:
        """Get conversation statistics."""
        try:
            # Count sessions
            sessions = self.db.db.coaching_sessions.count_documents(
                {"pursuit_id": pursuit_id}
            )

            # Count messages
            messages = self.db.db.conversation_history.count_documents(
                {"pursuit_id": pursuit_id}
            )

            return sessions, messages
        except Exception as e:
            logger.warning(f"[CoachCurator] Error getting stats: {e}")
            return 0, 0

    def _get_conversations(self, pursuit_id: str) -> List[Dict]:
        """Get conversation history for analysis."""
        try:
            cursor = self.db.db.conversation_history.find(
                {"pursuit_id": pursuit_id}
            ).sort("timestamp", 1).limit(500)

            return list(cursor)
        except Exception as e:
            logger.warning(f"[CoachCurator] Error getting conversations: {e}")
            return []

    def _select_moments(self, conversations: List[Dict]) -> tuple:
        """
        Select the most impactful coaching moments.

        Returns:
            (list of CoachingMoment, count of moments considered)
        """
        candidates = []

        # Build conversation pairs (coach message + user response)
        for i, msg in enumerate(conversations):
            if msg.get("role") != "assistant":
                continue

            coach_content = msg.get("content", "")
            timestamp = msg.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # Look for user response
            user_response = ""
            if i + 1 < len(conversations):
                next_msg = conversations[i + 1]
                if next_msg.get("role") == "user":
                    user_response = next_msg.get("content", "")

            # Score this moment
            moment_type, score = self._score_moment(coach_content, user_response)

            if score > 0:
                candidates.append({
                    "timestamp": timestamp,
                    "moment_type": moment_type,
                    "coach_quote": coach_content,
                    "user_response": user_response,
                    "score": score,
                })

        # Sort by score and select top moments
        candidates.sort(key=lambda x: x["score"], reverse=True)
        selected = candidates[:5]

        # Convert to CoachingMoment objects
        moments = []
        for c in selected:
            moments.append(CoachingMoment(
                timestamp=c["timestamp"],
                moment_type=c["moment_type"],
                coach_quote=self._truncate(c["coach_quote"], 300),
                innovator_response=self._truncate(c["user_response"], 200),
                impact=self._infer_impact(c["moment_type"]),
                session_context="",  # Could be enhanced with session metadata
            ))

        return moments, len(candidates)

    def _score_moment(self, coach_content: str, user_response: str) -> tuple:
        """
        Score a coaching moment for significance.

        Returns:
            (moment_type, score) tuple
        """
        coach_lower = coach_content.lower()
        response_lower = user_response.lower()

        # Check for breakthrough indicators in user response
        breakthrough_score = sum(
            1 for ind in BREAKTHROUGH_INDICATORS
            if ind in response_lower
        )
        if breakthrough_score > 0:
            return "breakthrough", breakthrough_score * 3

        # Check for reframe in coach message
        reframe_score = sum(
            1 for ind in REFRAME_INDICATORS
            if ind in coach_lower
        )
        if reframe_score > 0:
            return "reframe", reframe_score * 2

        # Check for challenge in coach message
        challenge_score = sum(
            1 for ind in CHALLENGE_INDICATORS
            if ind in coach_lower
        )
        if challenge_score > 0:
            return "challenge", challenge_score * 1.5

        # Check for encouragement in coach message
        encouragement_score = sum(
            1 for ind in ENCOURAGEMENT_INDICATORS
            if ind in coach_lower
        )
        if encouragement_score > 0:
            return "encouragement", encouragement_score

        return "general", 0

    def _infer_impact(self, moment_type: str) -> str:
        """Infer impact description from moment type."""
        impacts = {
            "breakthrough": "This insight shifted the innovator's perspective",
            "reframe": "A new way of looking at the challenge emerged",
            "challenge": "Prompted deeper thinking about assumptions",
            "encouragement": "Reinforced progress and built confidence",
            "general": "Contributed to the coaching conversation",
        }
        return impacts.get(moment_type, "")

    def _generate_summary(
        self,
        moments: List[CoachingMoment],
        pursuit_title: str,
        duration_days: int,
        outcome: str,
    ) -> tuple:
        """
        Generate coaching themes and overall reflection.

        Returns:
            (themes list, reflection string) tuple
        """
        if not moments:
            return ["Exploration", "Learning", "Growth"], "No specific coaching moments captured."

        # Format moments for prompt
        moments_text = "\n\n".join([
            f"[{m.moment_type}] Coach: \"{m.coach_quote[:200]}...\"\n"
            f"Response: \"{m.innovator_response[:100]}...\""
            for m in moments[:5]
        ])

        prompt = CURATION_PROMPT.format(
            moments_text=moments_text,
            pursuit_title=pursuit_title,
            duration_days=duration_days,
            outcome=outcome,
        )

        try:
            response = self._http_client.post(
                f"{self._gateway_url}/llm/chat",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "system_prompt": CURATION_SYSTEM_PROMPT,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "preferred_provider": "auto"
                },
                timeout=45.0
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("content", "")

            # Parse JSON response
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    summary_data = json.loads(content[json_start:json_end])
                    return (
                        summary_data.get("themes", ["Exploration", "Learning", "Growth"]),
                        summary_data.get("overall_reflection", ""),
                    )
            except json.JSONDecodeError:
                logger.warning("[CoachCurator] Failed to parse LLM JSON response")

        except Exception as e:
            logger.error(f"[CoachCurator] LLM call failed: {e}")

        # Default themes if LLM fails
        return ["Exploration", "Learning", "Growth"], ""

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _empty_layer(self) -> CoachsPerspectiveLayer:
        """Return an empty layer."""
        return CoachsPerspectiveLayer(
            moments=[],
            coaching_themes=["Coaching"],
            overall_reflection="No coaching perspective available.",
            generated_at=datetime.now(timezone.utc),
        )

    def close(self):
        """Close HTTP client."""
        self._http_client.close()
