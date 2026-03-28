"""
Milestone Narrative Templates

InDE MVP v4.5.0 — The Engagement Engine

Natural-language templates for milestone achievements.
Three variants per artifact type, randomly selected.

Templates use pursuit-specific injection:
  {idea_domain} — domain extracted from pursuit title/description
  {idea_summary} — brief summary of the idea

IMPORTANT: Fear-centric language has been eliminated.
Uses: risk, protection, resilience vocabulary instead.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import random
from typing import Dict, List


class MilestoneTemplates:
    """
    Provides narrative templates for milestone achievements.

    Each artifact type has 3 template variants. Selection is randomized
    to keep the experience fresh.
    """

    TEMPLATES: Dict[str, List[Dict[str, str]]] = {
        "vision": [
            {
                "headline": "Your story is taking shape",
                "narrative": (
                    "You've captured what matters most about {idea_domain}. "
                    "This clarity will guide every decision from here."
                ),
                "next_hint": "Now let's explore what could challenge this vision.",
            },
            {
                "headline": "Vision documented",
                "narrative": (
                    "The core of your idea is now clear and documented. "
                    "You know what you're building and why it matters."
                ),
                "next_hint": "Strong visions face hard questions early.",
            },
            {
                "headline": "Foundation set",
                "narrative": (
                    "You've defined the what and the why for {idea_domain}. "
                    "This foundation will support everything you build."
                ),
                "next_hint": "What risks should you protect against?",
            },
        ],
        "fears": [
            {
                "headline": "Risks mapped, protections considered",
                "narrative": (
                    "You've identified what could threaten {idea_domain} and "
                    "thought about how to protect against it. That's resilience."
                ),
                "next_hint": "Now define what you believe and how to test it.",
            },
            {
                "headline": "Risk analysis complete",
                "narrative": (
                    "Understanding what could go wrong is half the battle. "
                    "You've strengthened your position by thinking ahead."
                ),
                "next_hint": "What assumptions are you making?",
            },
            {
                "headline": "Protection layer added",
                "narrative": (
                    "Your idea now has a protection layer — you know the "
                    "risks and how to navigate them."
                ),
                "next_hint": "Time to test your key assumptions.",
            },
        ],
        "hypothesis": [
            {
                "headline": "Assumptions surfaced",
                "narrative": (
                    "You've named the beliefs that {idea_domain} rests on. "
                    "Now you can test what matters most."
                ),
                "next_hint": "Design a simple test for your biggest assumption.",
            },
            {
                "headline": "Key beliefs identified",
                "narrative": (
                    "Every idea rests on assumptions. You've surfaced yours. "
                    "That's how evidence replaces hope."
                ),
                "next_hint": "How will you know if you're right?",
            },
            {
                "headline": "Testable hypotheses defined",
                "narrative": (
                    "You've transformed assumptions into testable statements. "
                    "That's the first step toward real validation."
                ),
                "next_hint": "Pick your riskiest assumption to test first.",
            },
        ],
        "validation": [
            {
                "headline": "Evidence collected",
                "narrative": (
                    "You've run a test and gathered real evidence for {idea_domain}. "
                    "That's worth more than any amount of speculation."
                ),
                "next_hint": "What did you learn? Capture it while it's fresh.",
            },
            {
                "headline": "Test complete",
                "narrative": (
                    "Whether the result was what you expected or a surprise, "
                    "you now have evidence to guide your next move."
                ),
                "next_hint": "Time to reflect on what this means.",
            },
            {
                "headline": "Real data, real progress",
                "narrative": (
                    "You've moved from belief to evidence. That's the heart "
                    "of smart innovation — learn fast, adapt faster."
                ),
                "next_hint": "What does this evidence tell you?",
            },
        ],
        "retrospective": [
            {
                "headline": "Journey documented",
                "narrative": (
                    "You've captured what this pursuit taught you. "
                    "That wisdom will compound in everything you do next."
                ),
                "next_hint": "Ready for your next innovation?",
            },
            {
                "headline": "Learnings preserved",
                "narrative": (
                    "The lessons from {idea_domain} are now documented. "
                    "They'll inform your next pursuit."
                ),
                "next_hint": "Every ending is a beginning.",
            },
            {
                "headline": "Reflection complete",
                "narrative": (
                    "You've done what few innovators take time to do — "
                    "reflect honestly on the journey. That's growth."
                ),
                "next_hint": "What will you pursue next?",
            },
        ],
    }

    @classmethod
    def get_template(cls, artifact_type: str) -> Dict[str, str]:
        """
        Get a random template for the artifact type.

        Args:
            artifact_type: The type of artifact finalized

        Returns:
            Dict with headline, narrative, and next_hint
        """
        templates = cls.TEMPLATES.get(artifact_type, cls.TEMPLATES["vision"])
        return random.choice(templates)

    @classmethod
    def render(cls, artifact_type: str, idea_domain: str = "",
               idea_summary: str = "") -> Dict[str, str]:
        """
        Get and render a milestone template with pursuit-specific context.

        Args:
            artifact_type: The type of artifact finalized
            idea_domain: Domain extracted from pursuit (e.g., "sustainable packaging")
            idea_summary: Brief summary of the idea

        Returns:
            Dict with rendered headline, narrative, and next_hint
        """
        template = cls.get_template(artifact_type)

        # Fallback for empty domain
        domain = idea_domain or "your idea"

        return {
            "headline": template["headline"],
            "narrative": template["narrative"].format(
                idea_domain=domain,
                idea_summary=idea_summary or domain,
            ),
            "next_hint": template["next_hint"],
        }
