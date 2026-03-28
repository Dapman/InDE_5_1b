"""
Innovation Health Card Engine

InDE MVP v4.5.0 — The Engagement Engine

Computes an Innovation Health Card for each active pursuit. The Health Card
is an organic, depth-framed representation of how developed an idea is across
five growth dimensions:

  1. Clarity    — Derived from vision scaffolding readiness and artifact existence
  2. Resilience — Derived from risk/protection artifact state
  3. Evidence   — Derived from hypothesis and validation artifact state
  4. Direction  — Derived from coaching convergence state and pursuit phase
  5. Momentum   — Derived from the MME's most recent session momentum score

Each dimension is scored 0.0–1.0 from existing system state. The composite
growth stage is computed from the dimension vector, not from a simple average.

The Health Card is computed on demand — never stored — to ensure it always
reflects real-time pursuit state.

This module READS from existing systems. It does not modify scaffolding state,
momentum snapshots, or artifact records.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


# Growth stage thresholds — based on highest dimensions achieved
GROWTH_STAGES = [
    # (stage_key, min_dimensions_above_threshold, threshold, label)
    ("canopy",   4, 0.6, "Full canopy — your idea has real depth"),
    ("branches", 3, 0.5, "Branching out — you're testing what matters"),
    ("stem",     2, 0.4, "Growing stronger — you're seeing what could go wrong"),
    ("roots",    1, 0.3, "Roots forming — your story is getting clear"),
    ("seed",     0, 0.0, "Just planted — your idea is taking shape"),
]


@dataclass
class HealthCardDimension:
    """Single dimension of the Innovation Health Card."""
    key: str           # clarity | resilience | evidence | direction | momentum
    label: str         # Innovator-facing label from Display Label Registry
    score: float       # 0.0–1.0
    description: str   # Brief explanation of what this score means


@dataclass
class InnovationHealthCard:
    """Complete Health Card for a single pursuit."""
    pursuit_id: str
    dimensions: List[HealthCardDimension]
    growth_stage: str          # seed | roots | stem | branches | canopy
    growth_stage_label: str    # Innovator-facing label
    summary_sentence: str      # Natural-language summary
    next_growth_hint: str      # What to do next to grow
    computed_at: str           # ISO 8601 timestamp


class HealthCardEngine:
    """
    Computes Innovation Health Cards from existing pursuit state.

    Dependencies (injected via db parameter):
      - db: Database connection with access to:
        - scaffolding_states collection
        - artifacts collection
        - momentum_snapshots collection (or similar)
        - pursuits collection
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database connection with db.db.<collection> access pattern
        """
        self.db = db

    def compute(self, pursuit_id: str) -> InnovationHealthCard:
        """
        Compute the Innovation Health Card for a pursuit.
        All data is read from existing collections — nothing is stored.
        """
        clarity = self._compute_clarity(pursuit_id)
        resilience = self._compute_resilience(pursuit_id)
        evidence = self._compute_evidence(pursuit_id)
        direction = self._compute_direction(pursuit_id)
        momentum = self._compute_momentum(pursuit_id)

        dimensions = [clarity, resilience, evidence, direction, momentum]
        growth_stage, growth_label = self._determine_growth_stage(dimensions)
        summary = self._generate_summary(dimensions, growth_stage)
        hint = self._generate_next_hint(dimensions, growth_stage)

        return InnovationHealthCard(
            pursuit_id=pursuit_id,
            dimensions=dimensions,
            growth_stage=growth_stage,
            growth_stage_label=growth_label,
            summary_sentence=summary,
            next_growth_hint=hint,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compute_clarity(self, pursuit_id: str) -> HealthCardDimension:
        """
        Clarity = vision scaffolding completeness + artifact existence.
        If vision artifact exists: base score = 0.7+.
        If only scaffolding progress: lower scores.
        """
        try:
            # Check for vision artifact
            vision_artifact = self.db.db.artifacts.find_one({
                "pursuit_id": pursuit_id,
                "artifact_type": "vision"
            })

            # Check scaffolding completeness
            scaffolding = self.db.db.scaffolding_states.find_one({
                "pursuit_id": pursuit_id
            })

            if vision_artifact:
                # Vision artifact exists — high clarity
                score = 0.85
            elif scaffolding:
                # Calculate from scaffolding elements
                vision_elements = scaffolding.get("vision_elements", {})
                filled = sum(1 for v in vision_elements.values() if v and v.get("text"))
                total = max(len(vision_elements), 1)
                base_score = filled / total
                score = base_score * 0.6  # Cap at 0.6 without artifact
            else:
                score = 0.0

        except Exception as e:
            logger.warning(f"Clarity computation failed for {pursuit_id}: {e}")
            score = 0.0

        return HealthCardDimension(
            key="clarity",
            label="How clear is your story?",
            score=round(min(1.0, score), 2),
            description=self._clarity_description(score),
        )

    def _compute_resilience(self, pursuit_id: str) -> HealthCardDimension:
        """
        Resilience = fear/risk artifact existence + scaffolding progress.
        Uses same tiered approach as Clarity.
        """
        try:
            # Check for fears artifact
            fears_artifact = self.db.db.artifacts.find_one({
                "pursuit_id": pursuit_id,
                "artifact_type": "fears"
            })

            # Check scaffolding for fear elements
            scaffolding = self.db.db.scaffolding_states.find_one({
                "pursuit_id": pursuit_id
            })

            if fears_artifact:
                score = 0.80
            elif scaffolding:
                fear_elements = scaffolding.get("fear_elements", {})
                filled = sum(1 for v in fear_elements.values() if v and v.get("text"))
                total = max(len(fear_elements), 1)
                base_score = filled / total
                score = base_score * 0.5
            else:
                score = 0.0

        except Exception as e:
            logger.warning(f"Resilience computation failed for {pursuit_id}: {e}")
            score = 0.0

        return HealthCardDimension(
            key="resilience",
            label="How protected is your idea?",
            score=round(min(1.0, score), 2),
            description=self._resilience_description(score),
        )

    def _compute_evidence(self, pursuit_id: str) -> HealthCardDimension:
        """
        Evidence = hypothesis + validation artifact state.
        Hypothesis exists = 0.3–0.5. Validation recorded = 0.5–1.0.
        """
        try:
            hypothesis = self.db.db.artifacts.find_one({
                "pursuit_id": pursuit_id,
                "artifact_type": "hypothesis"
            })

            # Check for validation evidence
            evidence = self.db.db.evidence_packages.find_one({
                "pursuit_id": pursuit_id
            })

            if evidence:
                score = 0.80
            elif hypothesis:
                score = 0.50
            else:
                # Check scaffolding for hypothesis elements
                scaffolding = self.db.db.scaffolding_states.find_one({
                    "pursuit_id": pursuit_id
                })
                if scaffolding and scaffolding.get("hypothesis_elements"):
                    hyp_elements = scaffolding.get("hypothesis_elements", {})
                    filled = sum(1 for v in hyp_elements.values() if v and v.get("text"))
                    total = max(len(hyp_elements), 1)
                    score = (filled / total) * 0.3
                else:
                    score = 0.0

        except Exception as e:
            logger.warning(f"Evidence computation failed for {pursuit_id}: {e}")
            score = 0.0

        return HealthCardDimension(
            key="evidence",
            label="What have you tested?",
            score=round(min(1.0, score), 2),
            description=self._evidence_description(score),
        )

    def _compute_direction(self, pursuit_id: str) -> HealthCardDimension:
        """
        Direction = pursuit phase depth + coaching session engagement.
        Earlier phases = lower score. More sessions = higher engagement.
        """
        try:
            pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})

            if not pursuit:
                score = 0.1
            else:
                # Map pursuit state to score
                state = pursuit.get("state", "ACTIVE")
                phase = pursuit.get("current_phase", "VISION")

                # Phase scoring
                phase_scores = {
                    "VISION": 0.2,
                    "PITCH": 0.3,
                    "DE_RISK": 0.5,
                    "BUILD": 0.7,
                    "DEPLOY": 0.9,
                }
                base_score = phase_scores.get(phase, 0.2)

                # Boost for multiple coaching sessions
                session_count = self.db.db.coaching_sessions.count_documents({
                    "pursuit_id": pursuit_id
                })
                session_boost = min(0.2, session_count * 0.02)

                score = min(1.0, base_score + session_boost)

        except Exception as e:
            logger.warning(f"Direction computation failed for {pursuit_id}: {e}")
            score = 0.1

        return HealthCardDimension(
            key="direction",
            label="Where are you heading next?",
            score=round(min(1.0, score), 2),
            description=self._direction_description(score),
        )

    def _compute_momentum(self, pursuit_id: str) -> HealthCardDimension:
        """
        Momentum = most recent MME session momentum score.
        If no session data exists, returns 0.5 (neutral — not penalizing new users).
        """
        try:
            # Find most recent momentum snapshot for this pursuit
            snapshot = self.db.db.momentum_snapshots.find_one(
                {"pursuit_id": pursuit_id},
                sort=[("recorded_at", -1)]
            )

            if snapshot:
                score = snapshot.get("composite_score", 0.5)
            else:
                score = 0.5  # Neutral starting point

        except Exception as e:
            logger.warning(f"Momentum computation failed for {pursuit_id}: {e}")
            score = 0.5

        return HealthCardDimension(
            key="momentum",
            label="How much energy are you bringing?",
            score=round(min(1.0, score), 2),
            description=self._momentum_description(score),
        )

    def _determine_growth_stage(self, dimensions: List[HealthCardDimension]) -> tuple:
        """Determine growth stage from dimension scores."""
        for stage_key, min_dims, threshold, label in GROWTH_STAGES:
            dims_above = sum(1 for d in dimensions if d.score >= threshold)
            if dims_above >= min_dims:
                return stage_key, label
        return "seed", GROWTH_STAGES[-1][3]

    def _generate_summary(self, dimensions: List[HealthCardDimension], stage: str) -> str:
        """Generate a natural-language summary sentence."""
        if stage == "seed":
            return "Your idea is just getting started — every conversation makes it stronger."
        elif stage == "roots":
            return "Your idea has roots now — your story is taking shape."
        elif stage == "stem":
            strongest = max(dimensions[:3], key=lambda d: d.score)
            return (f"Your idea is growing stronger — especially in "
                    f"{strongest.label.lower().rstrip('?')}. "
                    f"Keep exploring to build more branches.")
        elif stage == "branches":
            weak = min(dimensions[:4], key=lambda d: d.score)
            return (f"Your idea has real breadth. Strengthening "
                    f"{weak.label.lower().rstrip('?')} would make it even more resilient.")
        else:  # canopy
            return ("Your idea has serious depth — clear story, tested assumptions, "
                    "and a strong sense of direction. You've built something substantial.")

    def _generate_next_hint(self, dimensions: List[HealthCardDimension], stage: str) -> str:
        """Generate a hint about what to do next to grow."""
        # Find the lowest non-momentum dimension
        growth_dims = [d for d in dimensions if d.key != "momentum"]
        weakest = min(growth_dims, key=lambda d: d.score)

        hints = {
            "clarity":    "Tell your story — the coach can help you make it compelling.",
            "resilience": "Explore what could threaten your idea — and how to protect it.",
            "evidence":   "Define what you believe and design a way to test it.",
            "direction":  "Keep the conversation going — clarity builds with every turn.",
        }
        return hints.get(weakest.key, "Keep exploring — your idea grows with every session.")

    # --- Description generators (brief, innovator-facing) ---

    def _clarity_description(self, score: float) -> str:
        if score >= 0.7:
            return "Your story is clear and compelling."
        if score >= 0.4:
            return "Your story is forming — a few more details will sharpen it."
        if score > 0:
            return "You've started describing your idea — keep going."
        return "Not started yet."

    def _resilience_description(self, score: float) -> str:
        if score >= 0.7:
            return "You've identified key risks and thought about protections."
        if score >= 0.4:
            return "You're starting to see what could go wrong."
        if score > 0:
            return "A few risks are emerging in the conversation."
        return "Not explored yet."

    def _evidence_description(self, score: float) -> str:
        if score >= 0.7:
            return "You have real evidence shaping your idea."
        if score >= 0.4:
            return "You've defined what to test."
        if score > 0:
            return "Early assumptions are forming."
        return "Not started yet."

    def _direction_description(self, score: float) -> str:
        if score >= 0.7:
            return "You have a clear sense of where to go next."
        if score >= 0.4:
            return "Your next steps are becoming clearer."
        return "Still exploring — that's exactly where you should be."

    def _momentum_description(self, score: float) -> str:
        if score >= 0.7:
            return "You're bringing strong energy to this idea."
        if score >= 0.4:
            return "Steady momentum — keep the conversation going."
        return "Let's rekindle some energy around this idea."
