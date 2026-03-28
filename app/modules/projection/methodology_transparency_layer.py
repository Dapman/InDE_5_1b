"""
InDE v4.8 - Methodology Transparency Layer

Experience-gated optional ITD section that reveals coaching pattern provenance.

Visibility rules:
  EXPERT or ADVANCED experience level -> included (default collapsed, expandable)
  NOVICE or INTERMEDIATE              -> not included in ITD output
  Admin users                         -> always included (for system analysis)

This module:
  1. Checks the innovator's experience level
  2. If eligible, queries the ADL for archetype methodology profile
  3. Queries coaching history for orchestration decision records
  4. Generates analytical narrative via LLM
  5. Returns a structured section dict or None (if ineligible)

Language Sovereignty and methodology naming rules are enforced.
No methodology names. No anxiety vocabulary.

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Optional
from .transparency_prompt_library import (
    TRANSPARENCY_SYSTEM_PROMPT,
    translate_methodology_family,
)
from .projection_llm_client import ProjectionLLMClient

logger = logging.getLogger("inde.projection.methodology_transparency")

EXPERIENCE_LEVELS_ELIGIBLE = {"EXPERT", "ADVANCED"}


class MethodologyTransparencyLayer:
    """
    Produces the optional Methodology Transparency section for the ITD.
    Returns None for ineligible experience levels.
    """

    def __init__(self, db, llm_gateway=None):
        """
        Initialize MethodologyTransparencyLayer.

        Args:
            db: Database instance
            llm_gateway: Optional LLM Gateway for generation
        """
        self.db = db
        self.llm_client = ProjectionLLMClient(llm_gateway=llm_gateway)

    def generate(
        self,
        pursuit_id: str,
        innovator_experience_level: str,
        is_admin: bool = False
    ) -> Optional[dict]:
        """
        Main entry point.
        Returns structured transparency section or None if ineligible.

        Args:
            pursuit_id: The pursuit to generate transparency for
            innovator_experience_level: NOVICE, INTERMEDIATE, ADVANCED, or EXPERT
            is_admin: Whether the user has admin privileges (bypasses level gate)

        Returns:
            Transparency section dict or None if ineligible
        """
        eligible = (
            innovator_experience_level.upper() in EXPERIENCE_LEVELS_ELIGIBLE
            or is_admin
        )
        if not eligible:
            logger.debug(
                f"[MethodologyTransparency] Skipping for "
                f"experience_level={innovator_experience_level}"
            )
            return None

        try:
            logger.info(
                f"[MethodologyTransparency] Generating for pursuit: {pursuit_id}"
            )
            orchestration_data = self._collect_orchestration_data(pursuit_id)
            narrative = self._generate_narrative(orchestration_data)

            result = {
                "content": {
                    "orchestration_summary": narrative.get(
                        "orchestration_summary", ""
                    ),
                    "methodology_influences": narrative.get(
                        "methodology_influences", []
                    ),
                    "blending_notes": narrative.get("blending_notes", ""),
                    "adaptation_narrative": narrative.get(
                        "adaptation_narrative", ""
                    ),
                    "transparency_metadata": {
                        "experience_level": innovator_experience_level,
                        "is_admin": is_admin,
                        "archetype": orchestration_data.get("archetype"),
                        "orchestration_decisions_analyzed": orchestration_data.get(
                            "decision_count", 0
                        ),
                    }
                },
                "visibility": "EXPERT_ONLY",
                "default_collapsed": True,
                "status": "POPULATED_V4_8",
                "composition_version": "5.1b.0",
                "layer_name": "methodology_transparency",
            }

            logger.info(
                f"[MethodologyTransparency] Generated successfully for {pursuit_id}"
            )
            return result

        except Exception as e:
            logger.error(
                f"[MethodologyTransparency] Generation failed for "
                f"pursuit {pursuit_id}: {e}"
            )
            return None  # Never block ITD for transparency failure

    def _collect_orchestration_data(self, pursuit_id: str) -> dict:
        """
        Collect orchestration decision records for this pursuit.

        Args:
            pursuit_id: The pursuit to collect data for

        Returns:
            Dict containing orchestration analysis data
        """
        if not self.db:
            return self._empty_orchestration_data()

        try:
            pursuit = self.db.pursuits.find_one(
                {"_id": pursuit_id},
                {"archetype": 1, "archetype_blend": 1, "phase_history": 1}
            ) or {}

            # Query orchestration / scaffolding decision log
            decisions = list(self.db.coaching_decisions.find(
                {"pursuit_id": pursuit_id}
            ).sort("timestamp", 1).limit(50))

            # Summarize methodology family activations
            methodology_activations: dict = {}
            for d in decisions:
                family = d.get("methodology_family", "")
                if family:
                    methodology_activations[family] = (
                        methodology_activations.get(family, 0) + 1
                    )

            # Translate to analytical descriptions
            translated_activations = {
                translate_methodology_family(family): count
                for family, count in methodology_activations.items()
            }

            blends_detected = len(methodology_activations) > 1

            return {
                "archetype": pursuit.get("archetype", "unknown"),
                "archetype_blend": pursuit.get("archetype_blend", []),
                "methodology_activations": translated_activations,
                "raw_methodology_activations": methodology_activations,
                "blends_detected": blends_detected,
                "decision_count": len(decisions),
                "phase_history": pursuit.get("phase_history", []),
            }

        except Exception as e:
            logger.debug(
                f"[MethodologyTransparency] Error collecting orchestration data: {e}"
            )
            return self._empty_orchestration_data()

    def _empty_orchestration_data(self) -> dict:
        """Return empty orchestration data structure."""
        return {
            "archetype": "unknown",
            "archetype_blend": [],
            "methodology_activations": {},
            "raw_methodology_activations": {},
            "blends_detected": False,
            "decision_count": 0,
            "phase_history": [],
        }

    def _generate_narrative(self, orchestration_data: dict) -> dict:
        """
        Generate LLM narrative from orchestration data.

        Args:
            orchestration_data: Collected orchestration analysis data

        Returns:
            Dict with narrative sections
        """
        user_prompt = f"""
Generate the Methodology Transparency section for an expert innovator's
Innovation Thesis Document.

Pursuit Archetype: {orchestration_data.get('archetype', 'unknown')}
Archetype Blend (if any): {orchestration_data.get('archetype_blend', [])}
Orchestration Decisions Analyzed: {orchestration_data.get('decision_count', 0)}
Methodology Families Activated (analytical descriptions): {orchestration_data.get('methodology_activations', {})}
Blending Detected: {orchestration_data.get('blends_detected', False)}
Phase History: {orchestration_data.get('phase_history', [])}

Important: Do not fabricate methodology influences if the activation data is sparse.
If fewer than 3 methodology family activations are recorded, write the
orchestration_summary and adaptation_narrative honestly, and provide only
the supported methodology_influences entries (can be 1 if warranted).
Do NOT use branded methodology names under any circumstances.
"""
        return self.llm_client.generate(
            system_prompt=TRANSPARENCY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=500,
            parse_json=True,
            sovereignty_validate=True,
        )

    def is_eligible(
        self, experience_level: str, is_admin: bool = False
    ) -> bool:
        """
        Check if an innovator is eligible for methodology transparency.

        Args:
            experience_level: The innovator's experience level
            is_admin: Whether the user has admin privileges

        Returns:
            True if eligible for transparency section
        """
        return (
            experience_level.upper() in EXPERIENCE_LEVELS_ELIGIBLE
            or is_admin
        )
