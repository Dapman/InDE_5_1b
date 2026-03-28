"""
InDE v4.8 - Projection Module

Implements three ITD intelligence components:
  - ForwardProjectionEngine: Layer 6 - IML-powered trajectory analysis
  - PatternConnectionsCompiler: Layer 5 - Cross-pursuit influence map
  - MethodologyTransparencyLayer: Expert-mode coaching provenance reveal

All three components are assembled into the ITD by the ITDCompositionEngine
via ITDLayerResolver (new in v4.8).

2026 Yul Williams | InDEVerse, Incorporated
"""

from .forward_projection_engine import ForwardProjectionEngine
from .pattern_connections_compiler import PatternConnectionsCompiler
from .methodology_transparency_layer import MethodologyTransparencyLayer
from .itd_layer_resolver import ITDLayerResolver

__all__ = [
    "ForwardProjectionEngine",
    "PatternConnectionsCompiler",
    "MethodologyTransparencyLayer",
    "ITDLayerResolver",
]
