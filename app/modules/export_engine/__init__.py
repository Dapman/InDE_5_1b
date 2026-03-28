"""
InDE MVP v5.1b.0 - Export Engine Module

The Export Engine provides audience-specific export capabilities for
Innovation Thesis Documents and derived formats.

Primary Components:
- ExportTemplateRegistry: 6 template families with field mappings
- NarrativeStyleEngine: 6 audience styles for ITD voice modulation
- ExportOrchestrationEngine: Unified export pipeline
- ExportCoachBridge: Coach-assisted export discovery
- Renderers: Markdown, HTML, PDF, DOCX

2026 Yul Williams | InDEVerse, Incorporated
"""

from .export_template_registry import (
    ExportTemplateRegistry,
    ExportTemplateSpec,
    FieldMapping,
    ExportAvailability,
    TemplateReadinessResult,
)

from .narrative_style_engine import (
    NarrativeStyleEngine,
    NarrativeStyle,
    NARRATIVE_STYLES,
)

from .export_llm_client import ExportLLMClient

from .export_orchestration_engine import (
    ExportOrchestrationEngine,
    ExportRequest,
    ExportResult,
    TemplatePopulationResult,
    ExportGateError,
)

from .renderers import (
    BaseRenderer,
    MarkdownRenderer,
    HTMLRenderer,
    PDFRenderer,
    DOCXRenderer,
)

from .export_coach_bridge import (
    ExportCoachBridge,
    ExportSuggestion,
    ExportDiscoveryResult,
    get_export_discovery_for_phase3,
)

__all__ = [
    # Template Registry
    "ExportTemplateRegistry",
    "ExportTemplateSpec",
    "FieldMapping",
    "ExportAvailability",
    "TemplateReadinessResult",
    # Narrative Style Engine
    "NarrativeStyleEngine",
    "NarrativeStyle",
    "NARRATIVE_STYLES",
    # LLM Client
    "ExportLLMClient",
    # Orchestration Engine
    "ExportOrchestrationEngine",
    "ExportRequest",
    "ExportResult",
    "TemplatePopulationResult",
    "ExportGateError",
    # Renderers
    "BaseRenderer",
    "MarkdownRenderer",
    "HTMLRenderer",
    "PDFRenderer",
    "DOCXRenderer",
    # Coach Bridge
    "ExportCoachBridge",
    "ExportSuggestion",
    "ExportDiscoveryResult",
    "get_export_discovery_for_phase3",
]
