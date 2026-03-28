"""
InDE MVP v4.7.0 - Evidence Architecture Compiler

Layer 2 of the ITD Composition Engine.
Compiles confidence trajectory and pivot record from pursuit history.

Input Sources:
- Scaffolding element history (confidence over time)
- Conversation history (for pivot detection)
- Outcome readiness snapshots
- Phase transitions

Output:
- Confidence trajectory (time-series data points)
- Pivot record (significant direction changes)
- Summary statistics

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from modules.itd.itd_schemas import (
    EvidenceArchitectureLayer,
    ConfidenceDataPoint,
    PivotRecord,
)

logger = logging.getLogger("inde.itd.evidence_architecture")


# =============================================================================
# PIVOT DETECTION PATTERNS
# =============================================================================

PIVOT_INDICATORS = [
    # Major direction changes
    "changed direction", "pivoted", "shifted focus", "reconsidered",
    "abandoned", "dropped", "replaced with", "instead of",
    # Significant reframes
    "realized that", "discovered that", "learned that",
    "actually need", "should focus on", "better approach",
    # Validation outcomes
    "invalidated", "disproved", "didn't work", "failed to",
    "validated", "confirmed", "proved that",
]


# =============================================================================
# EVIDENCE ARCHITECTURE COMPILER
# =============================================================================

class EvidenceArchitectureCompiler:
    """
    Compiles Layer 2: Evidence Architecture.

    Extracts confidence trajectory from scaffolding history and
    identifies pivots from conversation and phase transitions.
    """

    def __init__(self, db):
        """
        Initialize EvidenceArchitectureCompiler.

        Args:
            db: Database instance for history retrieval
        """
        self.db = db

    def compile(self, pursuit_id: str) -> EvidenceArchitectureLayer:
        """
        Compile the evidence architecture layer for a pursuit.

        Args:
            pursuit_id: The pursuit to compile evidence for

        Returns:
            EvidenceArchitectureLayer with trajectory and pivots
        """
        logger.info(f"[EvidenceCompiler] Compiling evidence for pursuit: {pursuit_id}")

        # Get pursuit
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.error(f"[EvidenceCompiler] Pursuit not found: {pursuit_id}")
            return self._empty_layer()

        # Build confidence trajectory
        trajectory = self._build_confidence_trajectory(pursuit_id)

        # Detect pivots
        pivots = self._detect_pivots(pursuit_id)

        # Calculate statistics
        initial_confidence = trajectory[0].confidence if trajectory else 0.0
        final_confidence = trajectory[-1].confidence if trajectory else 0.0
        confidence_delta = final_confidence - initial_confidence

        layer = EvidenceArchitectureLayer(
            confidence_trajectory=trajectory,
            pivots=pivots,
            initial_confidence=initial_confidence,
            final_confidence=final_confidence,
            confidence_delta=confidence_delta,
            total_pivots=len(pivots),
            generated_at=datetime.now(timezone.utc),
        )

        # v4.10 IRC Integration (additive — non-breaking if IRC absent)
        resource_landscape = None
        try:
            from modules.irc.itd_integration import IRCITDIntegration
            irc_itd = IRCITDIntegration(self.db)
            irc_data = irc_itd.get_itd_layer2_resource_data(pursuit_id)
            if irc_data:
                resource_landscape = irc_data
                logger.info(
                    f"[EvidenceCompiler] IRC resource data added: "
                    f"completeness={irc_data.get('canvas_completeness', 0):.2f}"
                )
        except ImportError:
            pass  # IRC module not available — ITD generation proceeds normally
        except Exception as e:
            logger.warning(f"[EvidenceCompiler] IRC integration error (non-blocking): {e}")

        # Attach resource landscape to layer if available
        if resource_landscape:
            layer.resource_landscape = resource_landscape

        logger.info(
            f"[EvidenceCompiler] Compiled: {len(trajectory)} trajectory points, "
            f"{len(pivots)} pivots, delta={confidence_delta:.2f}"
        )
        return layer

    def _build_confidence_trajectory(self, pursuit_id: str) -> List[ConfidenceDataPoint]:
        """
        Build confidence trajectory from scaffolding snapshots and element history.

        Returns time-ordered list of confidence data points.
        """
        trajectory = []

        # Try scaffolding snapshots first
        snapshots = self._get_scaffolding_snapshots(pursuit_id)

        if snapshots:
            for snapshot in snapshots:
                timestamp = snapshot.get("created_at")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                # Calculate average confidence across elements
                elements = snapshot.get("elements", {})
                confidences = []

                for category in ["vision_elements", "fear_elements", "hypothesis_elements"]:
                    category_elements = elements.get(category, {})
                    for elem_key, elem_data in category_elements.items():
                        if isinstance(elem_data, dict) and "confidence" in elem_data:
                            confidences.append(elem_data["confidence"])

                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    trajectory.append(ConfidenceDataPoint(
                        timestamp=timestamp,
                        element_key="aggregate",
                        confidence=avg_confidence,
                        event_type="scaffolding_snapshot",
                    ))

        # If no snapshots, try outcome readiness data
        if not trajectory:
            trajectory = self._get_outcome_readiness_trajectory(pursuit_id)

        # If still empty, create a single point from current state
        if not trajectory:
            current_confidence = self._get_current_confidence(pursuit_id)
            trajectory.append(ConfidenceDataPoint(
                timestamp=datetime.now(timezone.utc),
                element_key="current",
                confidence=current_confidence,
                event_type="current_state",
            ))

        # Sort by timestamp
        trajectory.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min)

        return trajectory

    def _get_scaffolding_snapshots(self, pursuit_id: str) -> List[Dict]:
        """Get scaffolding snapshots from database."""
        try:
            # Query scaffolding_snapshots collection
            cursor = self.db.db.scaffolding_snapshots.find(
                {"pursuit_id": pursuit_id}
            ).sort("created_at", 1).limit(50)
            return list(cursor)
        except Exception as e:
            logger.warning(f"[EvidenceCompiler] Error getting snapshots: {e}")
            return []

    def _get_outcome_readiness_trajectory(self, pursuit_id: str) -> List[ConfidenceDataPoint]:
        """Get confidence trajectory from outcome readiness data."""
        trajectory = []
        try:
            # Query outcome_readiness collection
            cursor = self.db.db.outcome_readiness.find(
                {"pursuit_id": pursuit_id}
            ).sort("updated_at", 1)

            for doc in cursor:
                timestamp = doc.get("updated_at")
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                readiness_score = doc.get("readiness_score", 0.0)
                trajectory.append(ConfidenceDataPoint(
                    timestamp=timestamp,
                    element_key="outcome_readiness",
                    confidence=readiness_score,
                    event_type="outcome_readiness_update",
                ))
        except Exception as e:
            logger.warning(f"[EvidenceCompiler] Error getting outcome readiness: {e}")

        return trajectory

    def _get_current_confidence(self, pursuit_id: str) -> float:
        """Calculate current confidence from scaffolding state."""
        try:
            state = self.db.get_scaffolding_state(pursuit_id)
            if not state:
                return 0.0

            confidences = []
            for category in ["vision_elements", "fear_elements", "hypothesis_elements"]:
                elements = state.get(category, {})
                for elem_key, elem_data in elements.items():
                    if isinstance(elem_data, dict) and "confidence" in elem_data:
                        confidences.append(elem_data["confidence"])

            return sum(confidences) / len(confidences) if confidences else 0.0
        except Exception as e:
            logger.warning(f"[EvidenceCompiler] Error getting current confidence: {e}")
            return 0.0

    def _detect_pivots(self, pursuit_id: str) -> List[PivotRecord]:
        """
        Detect pivots from conversation history and phase transitions.

        Looks for:
        1. Explicit pivot language in conversations
        2. Phase transitions that indicate direction changes
        3. Major artifact revisions
        """
        pivots = []

        # Check conversation history for pivot indicators
        conversation_pivots = self._detect_conversation_pivots(pursuit_id)
        pivots.extend(conversation_pivots)

        # Check phase transitions
        phase_pivots = self._detect_phase_pivots(pursuit_id)
        pivots.extend(phase_pivots)

        # Sort by timestamp
        pivots.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min)

        return pivots

    def _detect_conversation_pivots(self, pursuit_id: str) -> List[PivotRecord]:
        """Detect pivots from conversation history."""
        pivots = []

        try:
            # Get conversation history
            cursor = self.db.db.conversation_history.find(
                {"pursuit_id": pursuit_id}
            ).sort("timestamp", 1)

            for msg in cursor:
                content = msg.get("content", "").lower()
                role = msg.get("role", "")

                # Only analyze user messages
                if role != "user":
                    continue

                # Check for pivot indicators
                for indicator in PIVOT_INDICATORS:
                    if indicator in content:
                        timestamp = msg.get("timestamp")
                        if isinstance(timestamp, str):
                            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                        # Classify pivot type
                        pivot_type = self._classify_pivot(content, indicator)

                        pivots.append(PivotRecord(
                            timestamp=timestamp,
                            pivot_type=pivot_type,
                            description=f"User indicated: '{indicator}'",
                            trigger=self._truncate(content, 200),
                            outcome="Direction change noted in conversation",
                        ))
                        break  # One pivot per message max

        except Exception as e:
            logger.warning(f"[EvidenceCompiler] Error detecting conversation pivots: {e}")

        return pivots

    def _detect_phase_pivots(self, pursuit_id: str) -> List[PivotRecord]:
        """Detect pivots from phase transitions."""
        pivots = []

        try:
            # Get temporal events for phase changes
            cursor = self.db.db.temporal_events.find({
                "pursuit_id": pursuit_id,
                "event_type": {"$regex": "phase", "$options": "i"}
            }).sort("timestamp", 1)

            previous_phase = None
            for event in cursor:
                current_phase = event.get("new_phase") or event.get("phase")
                timestamp = event.get("timestamp")

                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                # Detect regressive phase transitions (going back)
                if previous_phase and current_phase:
                    if self._is_regressive_transition(previous_phase, current_phase):
                        pivots.append(PivotRecord(
                            timestamp=timestamp,
                            pivot_type="course_correction",
                            description=f"Phase regression: {previous_phase} -> {current_phase}",
                            trigger="Phase transition detected",
                            outcome="Returned to earlier phase for refinement",
                        ))

                previous_phase = current_phase

        except Exception as e:
            logger.warning(f"[EvidenceCompiler] Error detecting phase pivots: {e}")

        return pivots

    def _classify_pivot(self, content: str, indicator: str) -> str:
        """Classify pivot type based on content and indicator."""
        content_lower = content.lower()

        # Major pivots
        if any(word in content_lower for word in ["pivoted", "abandoned", "completely", "major"]):
            return "major"

        # Course corrections
        if any(word in content_lower for word in ["adjusted", "refined", "tweaked", "modified"]):
            return "course_correction"

        # Default to minor
        return "minor"

    def _is_regressive_transition(self, previous: str, current: str) -> bool:
        """Check if phase transition is regressive (going backward)."""
        phase_order = ["VISION", "FEAR", "DERISK", "VALIDATE", "BUILD", "LAUNCH"]

        try:
            prev_idx = phase_order.index(previous.upper())
            curr_idx = phase_order.index(current.upper())
            return curr_idx < prev_idx
        except (ValueError, AttributeError):
            return False

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    def _empty_layer(self) -> EvidenceArchitectureLayer:
        """Return an empty layer."""
        return EvidenceArchitectureLayer(
            generated_at=datetime.now(timezone.utc),
        )
