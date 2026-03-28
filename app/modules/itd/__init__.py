"""
InDE MVP v4.7.0 - ITD Composition Engine

The ITD (Innovation Thesis Document) Composition Engine transforms pursuit
artifacts into structured narrative documents that tell the story of an
innovation journey.

Key Components:
- ITD Schemas: Data structures for the 6-layer document architecture
- Thesis Statement Generator: Synthesizes vision, concerns, and archetype
- Evidence Architecture Compiler: Builds confidence trajectory and pivot record
- Narrative Arc Generator: Creates archetype-structured story in 5 acts
- Coach's Perspective Curator: Selects and curates coaching moments
- ITD Assembler: Composes layers into final document
- ITD Composition Engine: Orchestrates the generation process

2026 Yul Williams | InDEVerse, Incorporated
"""

# Data structures
from modules.itd.itd_schemas import (
    # Enums
    ITDLayerType,
    ITDGenerationStatus,
    NarrativeActType,

    # Layer data classes
    ThesisStatementLayer,
    ConfidenceDataPoint,
    PivotRecord,
    EvidenceArchitectureLayer,
    NarrativeAct,
    NarrativeArcLayer,
    CoachingMoment,
    CoachsPerspectiveLayer,
    MetricsDashboardLayer,
    FuturePathwaysLayer,

    # Complete document
    InnovationThesisDocument,
)

# Layer generators
from modules.itd.thesis_statement_generator import ThesisStatementGenerator
from modules.itd.evidence_architecture_compiler import EvidenceArchitectureCompiler
from modules.itd.narrative_arc_generator import NarrativeArcGenerator
from modules.itd.coachs_perspective_curator import CoachsPerspectiveCurator

# Assembler and engine
from modules.itd.itd_assembler import ITDAssembler
from modules.itd.itd_composition_engine import ITDCompositionEngine

__all__ = [
    # Enums
    "ITDLayerType",
    "ITDGenerationStatus",
    "NarrativeActType",

    # Layer data classes
    "ThesisStatementLayer",
    "ConfidenceDataPoint",
    "PivotRecord",
    "EvidenceArchitectureLayer",
    "NarrativeAct",
    "NarrativeArcLayer",
    "CoachingMoment",
    "CoachsPerspectiveLayer",
    "MetricsDashboardLayer",
    "FuturePathwaysLayer",

    # Complete document
    "InnovationThesisDocument",

    # Generators
    "ThesisStatementGenerator",
    "EvidenceArchitectureCompiler",
    "NarrativeArcGenerator",
    "CoachsPerspectiveCurator",
    "ITDAssembler",
    "ITDCompositionEngine",
]
