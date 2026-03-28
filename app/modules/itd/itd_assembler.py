"""
InDE MVP v5.1b.0 - ITD Assembler

Composes the six ITD layers into a complete Innovation Thesis Document.

v4.9 Changes:
- Layers 5 and 6 now fully implemented (no longer placeholders)
- Pattern Connections (Layer 5) - IML/IKF influence map
- Forward Projection (Layer 6) - 90/180/365-day trajectory analysis
- Methodology Transparency section (expert-gated, optional)

Responsibilities:
- Validate layer completeness
- Assemble layers into final document structure
- Calculate overall document quality score
- Handle partial documents gracefully

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from modules.itd.itd_schemas import (
    InnovationThesisDocument,
    ITDGenerationStatus,
    ThesisStatementLayer,
    EvidenceArchitectureLayer,
    NarrativeArcLayer,
    CoachsPerspectiveLayer,
    PatternConnectionsLayer,
    ForwardProjectionLayer,
    MethodologyTransparencySection,
)

logger = logging.getLogger("inde.itd.assembler")


# =============================================================================
# ITD ASSEMBLER
# =============================================================================

class ITDAssembler:
    """
    Assembles ITD layers into a complete document.

    Takes generated layers and composes them into a coherent
    Innovation Thesis Document with quality scoring.
    """

    def __init__(self, db=None):
        """
        Initialize ITDAssembler.

        Args:
            db: Optional database instance for persistence
        """
        self.db = db

    def assemble(
        self,
        pursuit_id: str,
        user_id: str,
        pursuit_title: str,
        archetype: str,
        terminal_state: str,
        thesis_layer: ThesisStatementLayer = None,
        evidence_layer: EvidenceArchitectureLayer = None,
        narrative_layer: NarrativeArcLayer = None,
        coach_layer: CoachsPerspectiveLayer = None,
        pattern_connections_layer: dict = None,
        forward_projection_layer: dict = None,
        methodology_transparency: dict = None,
    ) -> InnovationThesisDocument:
        """
        Assemble layers into a complete ITD.

        Args:
            pursuit_id: The pursuit this ITD belongs to
            user_id: The user who owns the pursuit
            pursuit_title: Title of the pursuit
            archetype: Innovation methodology archetype
            terminal_state: Pursuit's terminal state
            thesis_layer: Layer 1 - Thesis Statement
            evidence_layer: Layer 2 - Evidence Architecture
            narrative_layer: Layer 3 - Narrative Arc
            coach_layer: Layer 4 - Coach's Perspective
            pattern_connections_layer: Layer 5 - Pattern Connections (NEW in v4.9)
            forward_projection_layer: Layer 6 - Forward Projection (NEW in v4.9)
            methodology_transparency: Optional expert-gated section (NEW in v4.9)

        Returns:
            Assembled InnovationThesisDocument
        """
        logger.info(f"[ITDAssembler] Assembling ITD for pursuit: {pursuit_id}")

        # Track which layers completed
        layers_completed = []
        layers_failed = []

        # Validate and track each layer
        if thesis_layer and thesis_layer.thesis_text:
            layers_completed.append("thesis_statement")
        else:
            layers_failed.append("thesis_statement")

        if evidence_layer and evidence_layer.confidence_trajectory:
            layers_completed.append("evidence_architecture")
        else:
            layers_failed.append("evidence_architecture")

        if narrative_layer and narrative_layer.acts:
            layers_completed.append("narrative_arc")
        else:
            layers_failed.append("narrative_arc")

        if coach_layer and (coach_layer.moments or coach_layer.overall_reflection):
            layers_completed.append("coachs_perspective")
        else:
            layers_failed.append("coachs_perspective")

        # Layer 5: Pattern Connections (v4.9 - live resolution)
        pattern_layer = None
        if pattern_connections_layer and pattern_connections_layer.get("status") in [
            "POPULATED_V4_8", "POPULATED_V4_8_FALLBACK"
        ]:
            pattern_layer = PatternConnectionsLayer(
                opening=pattern_connections_layer.get("content", {}).get("opening", ""),
                within_pursuit=pattern_connections_layer.get("content", {}).get("within_pursuit", {}),
                cross_pursuit=pattern_connections_layer.get("content", {}).get("cross_pursuit", {}),
                cross_domain=pattern_connections_layer.get("content", {}).get("cross_domain", {}),
                federation=pattern_connections_layer.get("content", {}).get("federation"),
                synthesis=pattern_connections_layer.get("content", {}).get("synthesis", ""),
                connection_metadata=pattern_connections_layer.get("content", {}).get("connection_metadata", {}),
                status=pattern_connections_layer.get("status", "NOT_GENERATED"),
                composition_version=pattern_connections_layer.get("composition_version", "5.1b.0"),
                generated_at=datetime.now(timezone.utc),
            )
            layers_completed.append("pattern_connections")
        else:
            layers_failed.append("pattern_connections")

        # Layer 6: Forward Projection (v4.9 - live resolution)
        projection_layer = None
        if forward_projection_layer and forward_projection_layer.get("status") in [
            "POPULATED_V4_8", "POPULATED_V4_8_FALLBACK"
        ]:
            projection_layer = ForwardProjectionLayer(
                synthesis_statement=forward_projection_layer.get("content", {}).get("synthesis_statement", ""),
                horizons=forward_projection_layer.get("content", {}).get("horizons", {}),
                projection_metadata=forward_projection_layer.get("content", {}).get("projection_metadata", {}),
                status=forward_projection_layer.get("status", "NOT_GENERATED"),
                composition_version=forward_projection_layer.get("composition_version", "5.1b.0"),
                generated_at=datetime.now(timezone.utc),
            )
            layers_completed.append("forward_projection")
        else:
            layers_failed.append("forward_projection")

        # Optional: Methodology Transparency (v4.9 - expert-gated)
        transparency_section = None
        if methodology_transparency and methodology_transparency.get("status") == "POPULATED_V4_8":
            transparency_section = MethodologyTransparencySection(
                orchestration_summary=methodology_transparency.get("content", {}).get("orchestration_summary", ""),
                methodology_influences=methodology_transparency.get("content", {}).get("methodology_influences", []),
                blending_notes=methodology_transparency.get("content", {}).get("blending_notes", ""),
                adaptation_narrative=methodology_transparency.get("content", {}).get("adaptation_narrative", ""),
                transparency_metadata=methodology_transparency.get("content", {}).get("transparency_metadata", {}),
                visibility=methodology_transparency.get("visibility", "EXPERT_ONLY"),
                default_collapsed=methodology_transparency.get("default_collapsed", True),
                status=methodology_transparency.get("status", "NOT_GENERATED"),
                composition_version=methodology_transparency.get("composition_version", "5.1b.0"),
                generated_at=datetime.now(timezone.utc),
            )

        # Determine overall status
        if len(layers_failed) == 0:
            status = ITDGenerationStatus.COMPLETED
        elif len(layers_completed) >= 3:
            status = ITDGenerationStatus.PARTIAL
        else:
            status = ITDGenerationStatus.FAILED

        # Create the document
        itd = InnovationThesisDocument(
            itd_id=str(uuid.uuid4()),
            pursuit_id=pursuit_id,
            user_id=user_id,
            thesis_statement=thesis_layer,
            evidence_architecture=evidence_layer,
            narrative_arc=narrative_layer,
            coachs_perspective=coach_layer,
            pattern_connections=pattern_layer,
            forward_projection=projection_layer,
            methodology_transparency=transparency_section,
            status=status,
            layers_completed=layers_completed,
            layers_failed=layers_failed,
            pursuit_title=pursuit_title,
            archetype=archetype,
            terminal_state=terminal_state,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if status == ITDGenerationStatus.COMPLETED else None,
            version=1,
            composition_version="5.1b.0",
        )

        logger.info(
            f"[ITDAssembler] Assembled ITD: {itd.itd_id}, "
            f"status={status.value}, "
            f"completed={len(layers_completed)}/{len(layers_completed) + len(layers_failed)} layers"
        )

        return itd

    def save(self, itd: InnovationThesisDocument) -> bool:
        """
        Save ITD to database.

        Args:
            itd: The assembled ITD

        Returns:
            True if saved successfully
        """
        if not self.db:
            logger.warning("[ITDAssembler] No database configured, cannot save")
            return False

        try:
            # Convert to dict for MongoDB
            doc = itd.to_dict()

            # Upsert based on itd_id
            result = self.db.db.innovation_thesis_documents.replace_one(
                {"itd_id": itd.itd_id},
                doc,
                upsert=True
            )

            logger.info(f"[ITDAssembler] Saved ITD: {itd.itd_id}")
            return True

        except Exception as e:
            logger.error(f"[ITDAssembler] Failed to save ITD: {e}")
            return False

    def load(self, itd_id: str) -> Optional[InnovationThesisDocument]:
        """
        Load ITD from database.

        Args:
            itd_id: The ITD ID to load

        Returns:
            InnovationThesisDocument or None
        """
        if not self.db:
            logger.warning("[ITDAssembler] No database configured, cannot load")
            return None

        try:
            doc = self.db.db.innovation_thesis_documents.find_one({"itd_id": itd_id})
            if doc:
                # Remove MongoDB _id
                doc.pop("_id", None)
                return InnovationThesisDocument.from_dict(doc)
            return None

        except Exception as e:
            logger.error(f"[ITDAssembler] Failed to load ITD: {e}")
            return None

    def get_for_pursuit(self, pursuit_id: str) -> Optional[InnovationThesisDocument]:
        """
        Get the ITD for a pursuit.

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Most recent InnovationThesisDocument for the pursuit or None
        """
        if not self.db:
            return None

        try:
            doc = self.db.db.innovation_thesis_documents.find_one(
                {"pursuit_id": pursuit_id},
                sort=[("created_at", -1)]
            )
            if doc:
                doc.pop("_id", None)
                return InnovationThesisDocument.from_dict(doc)
            return None

        except Exception as e:
            logger.error(f"[ITDAssembler] Failed to get ITD for pursuit: {e}")
            return None

    def calculate_quality_score(self, itd: InnovationThesisDocument) -> float:
        """
        Calculate overall quality score for an ITD.

        Quality is based on:
        - Layer completeness (40%)
        - Confidence scores where available (30%)
        - Content richness (30%)

        Returns:
            Quality score 0.0 - 1.0
        """
        score = 0.0

        # Layer completeness (40%) - all 6 layers now count
        total_layers = 6
        completed = len(itd.layers_completed)
        completeness = completed / total_layers
        score += completeness * 0.4

        # Confidence scores (30%)
        confidence_scores = []
        if itd.thesis_statement and itd.thesis_statement.confidence_score:
            confidence_scores.append(itd.thesis_statement.confidence_score)
        if itd.evidence_architecture and itd.evidence_architecture.final_confidence:
            confidence_scores.append(itd.evidence_architecture.final_confidence)
        # v4.9: Include projection confidence
        if itd.forward_projection and itd.forward_projection.projection_metadata:
            overall_conf = itd.forward_projection.projection_metadata.get("overall_confidence", 0)
            if overall_conf > 0:
                confidence_scores.append(overall_conf)

        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            score += avg_confidence * 0.3
        else:
            score += 0.15  # Neutral if no confidence data

        # Content richness (30%)
        richness = 0.0
        if itd.thesis_statement and len(itd.thesis_statement.thesis_text) > 100:
            richness += 0.16
        if itd.narrative_arc and len(itd.narrative_arc.acts) >= 5:
            richness += 0.16
        if itd.coachs_perspective and len(itd.coachs_perspective.moments) >= 3:
            richness += 0.16
        if itd.evidence_architecture and len(itd.evidence_architecture.pivots) > 0:
            richness += 0.16
        # v4.9: Check pattern connections richness
        if itd.pattern_connections and itd.pattern_connections.connection_metadata:
            if itd.pattern_connections.connection_metadata.get("total_connections", 0) > 0:
                richness += 0.18
        # v4.9: Check forward projection richness
        if itd.forward_projection and itd.forward_projection.horizons:
            if len(itd.forward_projection.horizons) >= 3:
                richness += 0.18

        score += min(richness, 1.0) * 0.3

        return min(score, 1.0)
