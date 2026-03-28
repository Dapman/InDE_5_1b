"""
InDE v4.8 - Layer Readiness Assessor

Assesses the current readiness of each ITD layer for an active pursuit.

Readiness is expressed as:
  - score: 0.0-1.0 (what fraction of each layer's data is currently available)
  - status: NOT_STARTED | FORMING | READY | COMPLETE
  - display_label: human-readable label via Display Label Registry

Layer readiness sources:
  Layer 1 - Thesis Statement:      vision artifact confidence + convergence signal
  Layer 2 - Evidence Architecture: IML decision count + artifact validation depth
  Layer 3 - Narrative Arc:         inflection point count + retrospective records
  Layer 4 - Coach's Perspective:   coaching session count + intervention quality signals
  Layer 5 - Pattern Connections:   IML pattern count + IKF availability signal
  Layer 6 - Forward Projection:    pursuit completion status + trajectory data availability

Readiness thresholds:
  NOT_STARTED: < 0.10
  FORMING:     0.10 - 0.49
  READY:       0.50 - 0.89
  COMPLETE:    >= 0.90

Layer 6 (Forward Projection) cannot reach COMPLETE until the pursuit
reaches SUCCESS state - it requires post-completion trajectory queries.

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger("inde.itd_preview.readiness")


@dataclass
class LayerReadiness:
    """Readiness assessment for a single ITD layer."""
    layer_number: int
    layer_key: str
    score: float
    status: str
    display_label: str
    data_signals: List[str]  # what's driving the readiness score


class LayerReadinessAssessor:
    """
    Assesses readiness of all six ITD layers for a given pursuit.
    """

    THRESHOLDS = {
        "NOT_STARTED": (0.0, 0.10),
        "FORMING":     (0.10, 0.50),
        "READY":       (0.50, 0.90),
        "COMPLETE":    (0.90, 1.01),
    }

    def assess_all_layers(self, pursuit_id: str, db) -> List[LayerReadiness]:
        """
        Assess all six ITD layers for the given pursuit.
        Returns a list of LayerReadiness objects in layer order.

        Args:
            pursuit_id: The pursuit to assess
            db: Database instance

        Returns:
            List of LayerReadiness for all 6 layers
        """
        return [
            self._assess_layer_1(pursuit_id, db),
            self._assess_layer_2(pursuit_id, db),
            self._assess_layer_3(pursuit_id, db),
            self._assess_layer_4(pursuit_id, db),
            self._assess_layer_5(pursuit_id, db),
            self._assess_layer_6(pursuit_id, db),
        ]

    def _score_to_status(self, score: float) -> str:
        """Convert a numeric score to a status label."""
        for status, (low, high) in self.THRESHOLDS.items():
            if low <= score < high:
                return status
        return "NOT_STARTED"

    def _assess_layer_1(self, pursuit_id: str, db) -> LayerReadiness:
        """Layer 1 - Thesis Statement: vision confidence + convergence signal"""
        try:
            vision = db.vision_artifacts.find_one(
                {"pursuit_id": pursuit_id}, {"confidence": 1, "approved": 1}
            ) or {}
        except Exception:
            vision = {}

        vision_conf = float(vision.get("confidence", 0.0))
        approved_boost = 0.25 if vision.get("approved") else 0.0

        try:
            convergence = db.convergence_records.find_one(
                {"pursuit_id": pursuit_id}, {"convergence_score": 1}
            ) or {}
        except Exception:
            convergence = {}

        conv_score = float(convergence.get("convergence_score", 0.0)) * 0.25
        score = min(1.0, vision_conf * 0.5 + approved_boost + conv_score)

        signals = []
        if vision_conf > 0.3:
            signals.append("vision statement established")
        if vision.get("approved"):
            signals.append("vision approved")
        if conv_score > 0.1:
            signals.append("convergence signal detected")

        return LayerReadiness(
            layer_number=1,
            layer_key="thesis_statement",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("thesis_statement", score),
            data_signals=signals or ["vision forming"],
        )

    def _assess_layer_2(self, pursuit_id: str, db) -> LayerReadiness:
        """Layer 2 - Evidence Architecture: IML decisions + validation depth"""
        try:
            iml_count = db.iml_decisions.count_documents(
                {"pursuit_id": pursuit_id}
            )
        except Exception:
            iml_count = 0

        try:
            validation_records = list(db.validation_records.find(
                {"pursuit_id": pursuit_id}, {"confidence": 1}
            ))
        except Exception:
            validation_records = []

        avg_validation = (
            sum(float(v.get("confidence", 0)) for v in validation_records)
            / max(len(validation_records), 1)
        )
        score = min(1.0, (iml_count / 15.0) * 0.5 + avg_validation * 0.5)

        signals = []
        if iml_count > 0:
            signals.append(f"{iml_count} coaching decision(s) recorded")
        if validation_records:
            signals.append(
                f"{len(validation_records)} validation record(s) present"
            )

        return LayerReadiness(
            layer_number=2,
            layer_key="evidence_architecture",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("evidence_architecture", score),
            data_signals=signals or ["evidence accumulating"],
        )

    def _assess_layer_3(self, pursuit_id: str, db) -> LayerReadiness:
        """Layer 3 - Narrative Arc: inflection points + retrospective records"""
        try:
            inflections = db.inflection_points.count_documents(
                {"pursuit_id": pursuit_id}
            )
        except Exception:
            inflections = 0

        try:
            retro = db.retrospective_records.find_one(
                {"pursuit_id": pursuit_id}, {"tier": 1}
            )
        except Exception:
            retro = None

        retro_boost = 0.30 if retro else 0.0
        score = min(1.0, (inflections / 8.0) * 0.70 + retro_boost)

        signals = []
        if inflections > 0:
            signals.append(f"{inflections} inflection point(s) captured")
        if retro:
            signals.append("retrospective conversation complete")

        return LayerReadiness(
            layer_number=3,
            layer_key="narrative_arc",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("narrative_arc", score),
            data_signals=signals or ["story emerging"],
        )

    def _assess_layer_4(self, pursuit_id: str, db) -> LayerReadiness:
        """Layer 4 - Coach's Perspective: session count + intervention quality"""
        try:
            session_count = db.session_records.count_documents(
                {"pursuit_id": pursuit_id}
            )
        except Exception:
            session_count = 0

        try:
            high_impact = db.session_records.count_documents(
                {"pursuit_id": pursuit_id, "intervention_quality": {"$gte": 0.7}}
            )
        except Exception:
            high_impact = 0

        score = min(
            1.0,
            (session_count / 10.0) * 0.60 + (high_impact / 5.0) * 0.40
        )

        signals = []
        if session_count > 0:
            signals.append(f"{session_count} coaching session(s)")
        if high_impact > 0:
            signals.append(f"{high_impact} high-impact moment(s) identified")

        return LayerReadiness(
            layer_number=4,
            layer_key="coachs_perspective",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("coachs_perspective", score),
            data_signals=signals or ["coaching intelligence forming"],
        )

    def _assess_layer_5(self, pursuit_id: str, db) -> LayerReadiness:
        """Layer 5 - Pattern Connections: IML patterns + IKF availability"""
        try:
            iml_patterns = db.iml_decisions.count_documents(
                {"pursuit_id": pursuit_id}
            )
        except Exception:
            iml_patterns = 0

        try:
            ikf_available = db.ikf_contributions.count_documents(
                {"pursuit_id": pursuit_id}
            ) > 0
        except Exception:
            ikf_available = False

        ikf_boost = 0.20 if ikf_available else 0.0
        score = min(1.0, (iml_patterns / 10.0) * 0.80 + ikf_boost)

        signals = []
        if iml_patterns > 0:
            signals.append(f"{iml_patterns} pattern(s) accumulated")
        if ikf_available:
            signals.append("cross-organization intelligence available")

        return LayerReadiness(
            layer_number=5,
            layer_key="pattern_connections",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("pattern_connections", score),
            data_signals=signals or ["patterns forming"],
        )

    def _assess_layer_6(self, pursuit_id: str, db) -> LayerReadiness:
        """
        Layer 6 - Forward Projection: cannot reach COMPLETE until SUCCESS.
        During active pursuit: readiness reflects trajectory data availability.
        """
        try:
            pursuit = db.pursuits.find_one(
                {"_id": pursuit_id}, {"status": 1, "archetype": 1}
            ) or {}
        except Exception:
            pursuit = {}

        is_complete = pursuit.get("status") == "SUCCESS"

        if is_complete:
            score = 1.0
            signals = ["pursuit complete - trajectory analysis ready"]
        else:
            # Score based on trajectory data availability from IML
            try:
                similar_count = db.pursuits.count_documents({
                    "status": "SUCCESS",
                    "archetype": pursuit.get("archetype"),
                })
            except Exception:
                similar_count = 0

            score = min(0.85, similar_count / 10.0)  # Max 0.85 until complete
            signals = []
            if similar_count > 0:
                signals.append(
                    f"{similar_count} comparable pursuit(s) in dataset"
                )
            else:
                signals.append("trajectory data accumulating")

        return LayerReadiness(
            layer_number=6,
            layer_key="forward_projection",
            score=round(score, 3),
            status=self._score_to_status(score),
            display_label=self._get_display_label("forward_projection", score),
            data_signals=signals,
        )

    def _get_display_label(self, layer_key: str, score: float) -> str:
        """Return Display Label Registry value for layer readiness status."""
        status = self._score_to_status(score)

        # Default labels for each status
        default_labels = {
            "NOT_STARTED": "Not yet begun",
            "FORMING": "Taking shape",
            "READY": "Ready",
            "COMPLETE": "Complete",
        }

        try:
            from shared.display_labels import DISPLAY_LABELS
            labels = DISPLAY_LABELS.get("preview_layer_status", {})
            key = f"{layer_key}.{status}"
            return labels.get(key, default_labels.get(status, status))
        except ImportError:
            return default_labels.get(status, status)
