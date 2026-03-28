"""
InDE MVP v5.1b.0 - ITD Composition Engine

The main orchestrator for Innovation Thesis Document generation.

Coordinates all six layer generators and the assembler to produce
complete ITD documents for pursuits entering terminal state.

v4.9 Changes:
- Layers 5 and 6 now fully implemented via ITDLayerResolver
- Pattern Connections (Layer 5) - IML/IKF influence map
- Forward Projection (Layer 6) - 90/180/365-day trajectory analysis
- Methodology Transparency section (expert-gated)

Responsibilities:
- Orchestrate layer generation in optimal order
- Handle failures gracefully (partial documents)
- Emit telemetry events
- Coordinate with event bus for async triggers

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Callable

from modules.itd.itd_schemas import (
    InnovationThesisDocument,
    ITDGenerationStatus,
    ITDLayerType,
)
from modules.itd.thesis_statement_generator import ThesisStatementGenerator
from modules.itd.evidence_architecture_compiler import EvidenceArchitectureCompiler
from modules.itd.narrative_arc_generator import NarrativeArcGenerator
from modules.itd.coachs_perspective_curator import CoachsPerspectiveCurator
from modules.itd.itd_assembler import ITDAssembler

# v4.9: Import ITDLayerResolver for Layers 5, 6, and Methodology Transparency
from modules.projection import ITDLayerResolver

logger = logging.getLogger("inde.itd.engine")


# =============================================================================
# ITD COMPOSITION ENGINE
# =============================================================================

class ITDCompositionEngine:
    """
    Orchestrates the generation of Innovation Thesis Documents.

    Coordinates all layer generators and the assembler to produce
    complete ITD documents.
    """

    def __init__(
        self,
        db,
        gateway_url: str = None,
        event_bus=None,
        telemetry_fn: Callable = None,
        llm_gateway=None,
    ):
        """
        Initialize ITDCompositionEngine.

        Args:
            db: Database instance
            gateway_url: LLM Gateway URL (optional)
            event_bus: Event bus for publishing events (optional)
            telemetry_fn: Function to track telemetry events (optional)
            llm_gateway: LLM Gateway instance for projection module (optional)
        """
        self.db = db
        self.event_bus = event_bus
        self.telemetry_fn = telemetry_fn or (lambda *args, **kwargs: None)

        # Initialize generators (Layers 1-4)
        self.thesis_generator = ThesisStatementGenerator(db, gateway_url)
        self.evidence_compiler = EvidenceArchitectureCompiler(db)
        self.narrative_generator = NarrativeArcGenerator(db, gateway_url)
        self.coach_curator = CoachsPerspectiveCurator(db, gateway_url)

        # v4.9: Initialize layer resolver for Layers 5, 6, and Methodology Transparency
        self.layer_resolver = ITDLayerResolver(db=db, llm_gateway=llm_gateway)

        self.assembler = ITDAssembler(db)

    def generate(
        self,
        pursuit_id: str,
        retrospective_data: Dict = None,
        innovator_experience_level: str = "NOVICE",
        is_admin: bool = False,
    ) -> InnovationThesisDocument:
        """
        Generate a complete ITD for a pursuit.

        Args:
            pursuit_id: The pursuit to generate ITD for
            retrospective_data: Optional retrospective artifact data
            innovator_experience_level: NOVICE, INTERMEDIATE, ADVANCED, or EXPERT
                                        (determines Methodology Transparency eligibility)
            is_admin: Whether user has admin privileges (bypasses experience gate)

        Returns:
            InnovationThesisDocument (may be partial if some layers fail)
        """
        logger.info(f"[ITDEngine] Starting ITD generation for pursuit: {pursuit_id}")

        # Get pursuit metadata
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.error(f"[ITDEngine] Pursuit not found: {pursuit_id}")
            return self._error_document(pursuit_id, "Pursuit not found")

        user_id = pursuit.get("user_id", "")
        pursuit_title = pursuit.get("title", "Innovation Pursuit")
        archetype = pursuit.get("methodology", {}).get("archetype", "lean_startup")
        if isinstance(archetype, dict):
            archetype = archetype.get("id", "lean_startup")
        terminal_state = pursuit.get("state", "ACTIVE")

        # Emit start event
        self._emit_event("itd.generation_started", {
            "pursuit_id": pursuit_id,
            "archetype": archetype,
        })
        self.telemetry_fn("itd.generation_started", pursuit_id, {
            "archetype": archetype,
            "terminal_state": terminal_state,
        })

        # Generate layers in order
        layers_results = {}

        # Layer 1: Thesis Statement
        try:
            logger.info(f"[ITDEngine] Generating Layer 1: Thesis Statement")
            thesis_layer = self.thesis_generator.generate(pursuit_id)
            layers_results["thesis_statement"] = thesis_layer
            self._emit_layer_event("thesis_statement", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Thesis generation failed: {e}")
            layers_results["thesis_statement"] = None
            self._emit_layer_event("thesis_statement", pursuit_id, False, str(e))

        # Layer 2: Evidence Architecture
        try:
            logger.info(f"[ITDEngine] Generating Layer 2: Evidence Architecture")
            evidence_layer = self.evidence_compiler.compile(pursuit_id)
            layers_results["evidence_architecture"] = evidence_layer
            self._emit_layer_event("evidence_architecture", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Evidence compilation failed: {e}")
            layers_results["evidence_architecture"] = None
            self._emit_layer_event("evidence_architecture", pursuit_id, False, str(e))

        # Layer 3: Narrative Arc
        try:
            logger.info(f"[ITDEngine] Generating Layer 3: Narrative Arc")
            narrative_layer = self.narrative_generator.generate(
                pursuit_id,
                evidence_layer=layers_results.get("evidence_architecture"),
                retrospective_data=retrospective_data,
            )
            layers_results["narrative_arc"] = narrative_layer
            self._emit_layer_event("narrative_arc", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Narrative generation failed: {e}")
            layers_results["narrative_arc"] = None
            self._emit_layer_event("narrative_arc", pursuit_id, False, str(e))

        # Layer 4: Coach's Perspective
        try:
            logger.info(f"[ITDEngine] Generating Layer 4: Coach's Perspective")
            coach_layer = self.coach_curator.curate(pursuit_id)
            layers_results["coachs_perspective"] = coach_layer
            self._emit_layer_event("coachs_perspective", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Coach curation failed: {e}")
            layers_results["coachs_perspective"] = None
            self._emit_layer_event("coachs_perspective", pursuit_id, False, str(e))

        # Layer 5: Pattern Connections (NEW in v4.9)
        try:
            logger.info(f"[ITDEngine] Generating Layer 5: Pattern Connections")
            pattern_connections_layer = self.layer_resolver.resolve_layer_5(pursuit_id)
            layers_results["pattern_connections"] = pattern_connections_layer
            self._emit_layer_event("pattern_connections", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Pattern Connections generation failed: {e}")
            layers_results["pattern_connections"] = None
            self._emit_layer_event("pattern_connections", pursuit_id, False, str(e))

        # Layer 6: Forward Projection (NEW in v4.9)
        try:
            logger.info(f"[ITDEngine] Generating Layer 6: Forward Projection")
            forward_projection_layer = self.layer_resolver.resolve_layer_6(pursuit_id)
            layers_results["forward_projection"] = forward_projection_layer
            self._emit_layer_event("forward_projection", pursuit_id, True)
        except Exception as e:
            logger.error(f"[ITDEngine] Forward Projection generation failed: {e}")
            layers_results["forward_projection"] = None
            self._emit_layer_event("forward_projection", pursuit_id, False, str(e))

        # Methodology Transparency (NEW in v4.9 - optional, experience-gated)
        methodology_transparency = None
        try:
            logger.info(
                f"[ITDEngine] Resolving Methodology Transparency "
                f"(experience={innovator_experience_level})"
            )
            methodology_transparency = self.layer_resolver.resolve_methodology_transparency(
                pursuit_id=pursuit_id,
                innovator_experience_level=innovator_experience_level,
                is_admin=is_admin,
            )
            if methodology_transparency:
                self._emit_event("itd.methodology_transparency_generated", {
                    "pursuit_id": pursuit_id,
                    "experience_level": innovator_experience_level,
                })
        except Exception as e:
            logger.warning(f"[ITDEngine] Methodology Transparency failed (non-blocking): {e}")
            methodology_transparency = None

        # Assemble the document
        itd = self.assembler.assemble(
            pursuit_id=pursuit_id,
            user_id=user_id,
            pursuit_title=pursuit_title,
            archetype=archetype,
            terminal_state=terminal_state,
            thesis_layer=layers_results.get("thesis_statement"),
            evidence_layer=layers_results.get("evidence_architecture"),
            narrative_layer=layers_results.get("narrative_arc"),
            coach_layer=layers_results.get("coachs_perspective"),
            pattern_connections_layer=layers_results.get("pattern_connections"),
            forward_projection_layer=layers_results.get("forward_projection"),
            methodology_transparency=methodology_transparency,
        )

        # Save the document
        saved = self.assembler.save(itd)

        # Calculate quality
        quality_score = self.assembler.calculate_quality_score(itd)

        # Emit completion event
        self._emit_event("itd.generation_completed", {
            "pursuit_id": pursuit_id,
            "itd_id": itd.itd_id,
            "status": itd.status.value,
            "layers_completed": len(itd.layers_completed),
            "quality_score": quality_score,
        })
        self.telemetry_fn("itd.generation_completed", pursuit_id, {
            "itd_id": itd.itd_id,
            "status": itd.status.value,
            "quality_score": quality_score,
        })

        logger.info(
            f"[ITDEngine] ITD generation complete: {itd.itd_id}, "
            f"status={itd.status.value}, quality={quality_score:.2f}"
        )

        return itd

    def regenerate_layer(
        self,
        itd_id: str,
        layer_type: ITDLayerType,
    ) -> InnovationThesisDocument:
        """
        Regenerate a specific layer of an existing ITD.

        Args:
            itd_id: The ITD to update
            layer_type: Which layer to regenerate

        Returns:
            Updated InnovationThesisDocument
        """
        # Load existing ITD
        itd = self.assembler.load(itd_id)
        if not itd:
            logger.error(f"[ITDEngine] ITD not found: {itd_id}")
            return None

        pursuit_id = itd.pursuit_id

        # Regenerate the specific layer
        if layer_type == ITDLayerType.THESIS_STATEMENT:
            itd.thesis_statement = self.thesis_generator.generate(pursuit_id)
        elif layer_type == ITDLayerType.EVIDENCE_ARCHITECTURE:
            itd.evidence_architecture = self.evidence_compiler.compile(pursuit_id)
        elif layer_type == ITDLayerType.NARRATIVE_ARC:
            itd.narrative_arc = self.narrative_generator.generate(
                pursuit_id, evidence_layer=itd.evidence_architecture
            )
        elif layer_type == ITDLayerType.COACHS_PERSPECTIVE:
            itd.coachs_perspective = self.coach_curator.curate(pursuit_id)
        else:
            logger.warning(f"[ITDEngine] Layer {layer_type} is a placeholder, cannot regenerate")
            return itd

        # Update metadata
        itd.updated_at = datetime.now(timezone.utc)
        itd.version += 1

        # Save
        self.assembler.save(itd)

        logger.info(f"[ITDEngine] Regenerated layer {layer_type.value} for ITD {itd_id}")
        return itd

    def get_itd(self, pursuit_id: str) -> Optional[InnovationThesisDocument]:
        """
        Get the ITD for a pursuit.

        Args:
            pursuit_id: The pursuit ID

        Returns:
            InnovationThesisDocument or None
        """
        return self.assembler.get_for_pursuit(pursuit_id)

    def _emit_event(self, event_type: str, payload: Dict):
        """Emit an event via the event bus."""
        if not self.event_bus:
            return

        try:
            from events.schemas import DomainEvent

            event = DomainEvent(
                event_type=event_type,
                payload=payload,
                timestamp=datetime.now(timezone.utc),
            )
            self.event_bus.emit(event)
        except Exception as e:
            logger.warning(f"[ITDEngine] Failed to emit event: {e}")

    def _emit_layer_event(
        self,
        layer_name: str,
        pursuit_id: str,
        success: bool,
        error: str = None
    ):
        """Emit a layer completion event."""
        self._emit_event("itd.layer_completed", {
            "pursuit_id": pursuit_id,
            "layer": layer_name,
            "success": success,
            "error": error,
        })
        self.telemetry_fn("itd.layer_completed", pursuit_id, {
            "layer": layer_name,
            "success": success,
        })

    def _error_document(self, pursuit_id: str, error: str) -> InnovationThesisDocument:
        """Create an error document."""
        return InnovationThesisDocument(
            pursuit_id=pursuit_id,
            status=ITDGenerationStatus.FAILED,
            layers_failed=["all"],
            created_at=datetime.now(timezone.utc),
        )

    def close(self):
        """Close all resources."""
        self.thesis_generator.close()
        self.narrative_generator.close()
        self.coach_curator.close()
