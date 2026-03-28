"""
InDE v4.8 - ITD Preview Engine

Assembles the ITD Living Preview from layer readiness data.

Provides the back-end data for the ITDLivingPreview.jsx component.
Mirrors the Health Card pattern: a real-time window into what InDE
has already assembled, surfaced to the innovator during an active pursuit.

If the pursuit has a completed ITD (approved), the preview returns the
full ITD status with completion indicators. If the pursuit is active,
the preview returns layer-by-layer readiness scores.

Update triggers:
  - On-demand (GET /api/v1/pursuits/{id}/itd/preview)
  - On pursuit state change events (coaching session complete, validation recorded)
  - On retrospective completion

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from .layer_readiness_assessor import LayerReadinessAssessor

logger = logging.getLogger("inde.itd_preview.engine")


class ITDPreviewEngine:
    """
    Produces the ITD Living Preview payload for the frontend.
    """

    def __init__(self, db):
        """
        Initialize ITDPreviewEngine.

        Args:
            db: Database instance
        """
        self.db = db
        self.assessor = LayerReadinessAssessor()

    def generate_preview(self, pursuit_id: str) -> dict:
        """
        Main entry point. Returns a complete preview payload.

        Args:
            pursuit_id: The pursuit to generate preview for

        Returns:
            Preview payload dict for frontend consumption
        """
        logger.info(f"[ITDPreview] Generating preview for pursuit: {pursuit_id}")

        # Check if ITD already exists (post-completion)
        try:
            existing_itd = self.db.db.innovation_thesis_documents.find_one(
                {"pursuit_id": pursuit_id}
            )
        except Exception:
            existing_itd = None

        if existing_itd:
            return self._completed_itd_preview(existing_itd)

        # Active pursuit - assess layer readiness in real time
        layer_readiness = self.assessor.assess_all_layers(pursuit_id, self.db)

        overall_score = sum(l.score for l in layer_readiness) / len(
            layer_readiness
        )
        layers_ready = sum(
            1 for l in layer_readiness if l.status in ("READY", "COMPLETE")
        )
        layers_forming = sum(
            1 for l in layer_readiness if l.status == "FORMING"
        )

        result = {
            "pursuit_id": pursuit_id,
            "preview_type": "ACTIVE",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_readiness": round(overall_score, 3),
            "layers_complete": 0,
            "layers_ready": layers_ready,
            "layers_forming": layers_forming,
            "layers": [
                {
                    "layer_number": l.layer_number,
                    "layer_key": l.layer_key,
                    "score": l.score,
                    "status": l.status,
                    "display_label": l.display_label,
                    "data_signals": l.data_signals,
                }
                for l in layer_readiness
            ],
            "coach_message": self._generate_coach_message(
                overall_score, layers_ready, layers_forming
            ),
        }

        logger.info(
            f"[ITDPreview] Generated ACTIVE preview for {pursuit_id}: "
            f"readiness={overall_score:.2f}"
        )
        return result

    def _completed_itd_preview(self, itd: dict) -> dict:
        """
        Return a preview for a pursuit with a completed ITD.

        Args:
            itd: The completed ITD document from database

        Returns:
            Preview payload for completed ITD
        """
        approved = itd.get("approved_at") is not None

        # Build layer statuses from the completed ITD
        layer_mapping = [
            ("thesis_statement", 1),
            ("evidence_architecture", 2),
            ("narrative_arc", 3),
            ("coachs_perspective", 4),
            ("pattern_connections", 5),
            ("forward_projection", 6),
        ]

        layer_statuses = []
        for key, num in layer_mapping:
            layer_data = itd.get(key, {})
            if layer_data is None:
                layer_data = {}

            # Check if layer has content
            has_content = False
            if isinstance(layer_data, dict):
                status = layer_data.get("status", "")
                has_content = "POPULATED" in status or bool(layer_data.get("content"))
            else:
                # It's a dataclass/object
                has_content = bool(layer_data)

            layer_statuses.append({
                "layer_number": num,
                "layer_key": key,
                "score": 1.0 if has_content else 0.5,
                "status": "COMPLETE" if has_content else "READY",
                "display_label": "Complete" if has_content else "Ready",
                "data_signals": ["assembled in Innovation Thesis"],
            })

        layers_completed = itd.get("layers_completed", [])

        result = {
            "pursuit_id": itd.get("pursuit_id"),
            "preview_type": "COMPLETED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_readiness": 1.0,
            "layers_complete": len([s for s in layer_statuses if s["status"] == "COMPLETE"]),
            "layers_ready": 0,
            "layers_forming": 0,
            "approved": approved,
            "itd_id": itd.get("itd_id"),
            "layers": layer_statuses,
            "coach_message": (
                "Your Innovation Thesis is complete and captures the full "
                "story of your pursuit."
                if approved
                else "Your Innovation Thesis has been assembled and is ready "
                "for your review."
            ),
        }

        logger.info(
            f"[ITDPreview] Generated COMPLETED preview for {itd.get('pursuit_id')}"
        )
        return result

    def _generate_coach_message(
        self, overall_score: float, layers_ready: int, layers_forming: int
    ) -> str:
        """
        Generate a coach-voiced message about current ITD readiness.
        Language Sovereignty enforced - no fear, no warning, no anxiety.

        Args:
            overall_score: Overall readiness score (0.0-1.0)
            layers_ready: Count of layers in READY or COMPLETE status
            layers_forming: Count of layers in FORMING status

        Returns:
            Coach message string
        """
        if overall_score >= 0.75:
            return (
                "Your Innovation Thesis is taking shape. The depth of what "
                "you've explored is already visible in the intelligence I've "
                "been assembling on your behalf."
            )
        elif overall_score >= 0.40:
            return (
                "Each session adds another layer to your Innovation Thesis. "
                "The story of your pursuit is forming - and it's a rich one."
            )
        else:
            return (
                "Your Innovation Thesis begins here. As we work together, "
                "I'm assembling the intelligence that will tell the full story "
                "of your innovation."
            )
