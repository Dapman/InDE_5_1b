"""
InDE v4.8 - ITD Layer Resolver

The v4.8 integration point between the ITD Composition Engine
and the new projection module.

Provides a clean interface for ITDCompositionEngine to call when
resolving Layers 5 and 6 (previously placeholder stubs).

Also provides the Methodology Transparency Layer (optional, experience-gated).

Called by ITDCompositionEngine.compose() during ITD assembly.
Does not modify the ITD Composition Engine - it is injected as a
dependency so the ITD module remains unmodified except at the
call site where placeholders are resolved.

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Optional
from .forward_projection_engine import ForwardProjectionEngine
from .pattern_connections_compiler import PatternConnectionsCompiler
from .methodology_transparency_layer import MethodologyTransparencyLayer

logger = logging.getLogger("inde.projection.layer_resolver")


class ITDLayerResolver:
    """
    Resolves ITD Layers 5, 6, and the optional Methodology Transparency
    section for a completing pursuit.
    """

    def __init__(self, db, llm_gateway=None):
        """
        Initialize ITDLayerResolver with database and optional LLM gateway.

        Args:
            db: Database instance
            llm_gateway: Optional LLM Gateway for generation
        """
        self.db = db
        self.llm_gateway = llm_gateway
        self.forward_projection = ForwardProjectionEngine(
            db=db, llm_gateway=llm_gateway
        )
        self.pattern_connections = PatternConnectionsCompiler(
            db=db, llm_gateway=llm_gateway
        )
        self.methodology_transparency = MethodologyTransparencyLayer(
            db=db, llm_gateway=llm_gateway
        )

    def resolve_layer_5(self, pursuit_id: str) -> dict:
        """
        Resolve Pattern Connections (Layer 5).
        Always returns a structurally valid dict - never raises.

        Args:
            pursuit_id: The pursuit to resolve Layer 5 for

        Returns:
            Layer 5 dict with content, status, and metadata
        """
        logger.info(
            f"[ITDLayerResolver] Resolving Layer 5 (Pattern Connections) "
            f"for pursuit {pursuit_id}"
        )
        return self.pattern_connections.compile(pursuit_id)

    def resolve_layer_6(self, pursuit_id: str) -> dict:
        """
        Resolve Forward Projection (Layer 6).
        Always returns a structurally valid dict - never raises.

        Args:
            pursuit_id: The pursuit to resolve Layer 6 for

        Returns:
            Layer 6 dict with content, status, and metadata
        """
        logger.info(
            f"[ITDLayerResolver] Resolving Layer 6 (Forward Projection) "
            f"for pursuit {pursuit_id}"
        )
        return self.forward_projection.generate(pursuit_id)

    def resolve_methodology_transparency(
        self,
        pursuit_id: str,
        innovator_experience_level: str,
        is_admin: bool = False,
    ) -> Optional[dict]:
        """
        Resolve Methodology Transparency section (optional, experience-gated).
        Returns None for ineligible experience levels - caller must check.

        Args:
            pursuit_id: The pursuit to resolve transparency for
            innovator_experience_level: NOVICE, INTERMEDIATE, ADVANCED, or EXPERT
            is_admin: Whether the user has admin privileges

        Returns:
            Methodology Transparency section dict or None if ineligible
        """
        logger.info(
            f"[ITDLayerResolver] Resolving Methodology Transparency for "
            f"pursuit {pursuit_id} "
            f"(experience={innovator_experience_level}, admin={is_admin})"
        )
        return self.methodology_transparency.generate(
            pursuit_id=pursuit_id,
            innovator_experience_level=innovator_experience_level,
            is_admin=is_admin,
        )

    def resolve_all(
        self,
        pursuit_id: str,
        innovator_experience_level: str = "NOVICE",
        is_admin: bool = False,
    ) -> dict:
        """
        Resolve all layers and optional transparency section.

        Args:
            pursuit_id: The pursuit to resolve for
            innovator_experience_level: NOVICE, INTERMEDIATE, ADVANCED, or EXPERT
            is_admin: Whether the user has admin privileges

        Returns:
            Dict containing layer_5, layer_6, and methodology_transparency
        """
        logger.info(
            f"[ITDLayerResolver] Resolving all layers for pursuit {pursuit_id}"
        )

        return {
            "layer_5": self.resolve_layer_5(pursuit_id),
            "layer_6": self.resolve_layer_6(pursuit_id),
            "methodology_transparency": self.resolve_methodology_transparency(
                pursuit_id=pursuit_id,
                innovator_experience_level=innovator_experience_level,
                is_admin=is_admin,
            ),
        }
