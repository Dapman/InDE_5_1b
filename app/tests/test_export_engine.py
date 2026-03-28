"""
InDE MVP v5.1b.0 - Export Engine Tests

Unit tests for the Export Engine components:
- ExportTemplateRegistry: Template loading and readiness checks
- NarrativeStyleEngine: Style application and layer ordering
- ExportCoachBridge: Discovery suggestions and coach framing
- Renderers: Markdown, HTML, PDF, DOCX output generation

2026 Yul Williams | InDEVerse, Incorporated
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# =============================================================================
# Test: ExportTemplateRegistry
# =============================================================================

class TestExportTemplateRegistry:
    """Tests for the Export Template Registry."""

    def test_registry_initialization(self):
        """Registry initializes with 6 template families."""
        from modules.export_engine import ExportTemplateRegistry

        registry = ExportTemplateRegistry()
        templates = registry.get_all_templates()
        assert len(templates) == 6

    def test_template_keys_exist(self):
        """All expected template keys are present."""
        from modules.export_engine import ExportTemplateRegistry

        registry = ExportTemplateRegistry()
        expected_keys = [
            "business_model_canvas",
            "empathy_journey_map",
            "gate_review_package",
            "strategy_canvas",
            "contradiction_resolution",
            "investment_readiness",
        ]
        for key in expected_keys:
            assert key in registry.get_all_templates()

    def test_template_spec_structure(self):
        """Template specs have required fields."""
        from modules.export_engine import ExportTemplateRegistry

        registry = ExportTemplateRegistry()
        template = registry.get_template("business_model_canvas")

        assert template is not None
        assert template.template_key == "business_model_canvas"
        assert template.display_name is not None
        assert template.description is not None
        assert template.category is not None
        assert len(template.fields) > 0
        assert template.readiness_threshold > 0

    def test_template_readiness_check_no_data(self):
        """Readiness check returns 0 score with no data."""
        from modules.export_engine import ExportTemplateRegistry

        registry = ExportTemplateRegistry()
        result = registry.check_template_readiness(
            template_key="business_model_canvas",
            pursuit_id="test-pursuit",
            readiness_data={},
        )

        assert result.is_ready is False
        assert result.readiness_score >= 0.0
        assert result.readiness_score <= 1.0

    def test_template_categories(self):
        """Templates have valid categories."""
        from modules.export_engine import ExportTemplateRegistry

        registry = ExportTemplateRegistry()
        valid_categories = [
            "strategy",
            "design_thinking",
            "governance",
            "investor_communications",
        ]

        for key, template in registry.get_all_templates().items():
            assert template.category in valid_categories


# =============================================================================
# Test: NarrativeStyleEngine
# =============================================================================

class TestNarrativeStyleEngine:
    """Tests for the Narrative Style Engine."""

    def test_engine_initialization(self):
        """Engine initializes with 6 narrative styles."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        styles = engine.get_all_styles()
        assert len(styles) == 6

    def test_style_keys_exist(self):
        """All expected style keys are present."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        expected_keys = [
            "investor",
            "academic",
            "commercial",
            "grant",
            "internal",
            "standard",
        ]
        for key in expected_keys:
            assert engine.get_style(key) is not None

    def test_style_layer_ordering(self):
        """Styles define valid layer ordering."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        valid_layers = [
            "thesis_statement",
            "evidence_architecture",
            "narrative_arc",
            "coachs_perspective",
            "pattern_connections",
            "forward_projection",
        ]

        for style_key in ["investor", "academic", "standard"]:
            style = engine.get_style(style_key)
            for layer in style.layer_ordering:
                assert layer in valid_layers

    def test_apply_style_returns_styled_itd(self):
        """apply_style returns ITD with style metadata."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        mock_itd = {
            "pursuit_id": "test",
            "thesis_statement": {"thesis_text": "Test thesis"},
            "narrative_arc": {"opening_hook": "Test hook"},
        }

        styled = engine.apply_style("investor", mock_itd)

        assert "style_key" in styled
        assert styled["style_key"] == "investor"
        assert "layer_ordering" in styled
        assert "style_metadata" in styled

    def test_investor_style_emphasizes_projection(self):
        """Investor style has forward_projection first."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        style = engine.get_style("investor")

        assert style.layer_ordering[0] == "forward_projection"

    def test_academic_style_emphasizes_evidence(self):
        """Academic style has evidence_architecture first."""
        from modules.export_engine import NarrativeStyleEngine

        engine = NarrativeStyleEngine()
        style = engine.get_style("academic")

        assert style.layer_ordering[0] == "evidence_architecture"


# =============================================================================
# Test: Renderers
# =============================================================================

class TestMarkdownRenderer:
    """Tests for the Markdown Renderer."""

    def test_renderer_content_type(self):
        """Markdown renderer returns correct content type."""
        from modules.export_engine.renderers import MarkdownRenderer

        renderer = MarkdownRenderer()
        assert renderer.content_type == "text/markdown"

    def test_render_returns_string(self):
        """render() returns a string."""
        from modules.export_engine.renderers import MarkdownRenderer

        renderer = MarkdownRenderer()
        mock_itd = {
            "pursuit_title": "Test Pursuit",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": ["thesis_statement"],
            "thesis_statement": {"thesis_text": "This is a test thesis."},
        }

        result = renderer.render(mock_itd)
        assert isinstance(result, str)
        assert "Test Pursuit" in result
        assert "Innovation Thesis" in result

    def test_render_includes_all_layers(self):
        """render() includes all provided layers."""
        from modules.export_engine.renderers import MarkdownRenderer

        renderer = MarkdownRenderer()
        mock_itd = {
            "pursuit_title": "Test",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": ["thesis_statement", "narrative_arc"],
            "thesis_statement": {"thesis_text": "Thesis text here"},
            "narrative_arc": {"opening_hook": "Once upon a time..."},
        }

        result = renderer.render(mock_itd)
        assert "Thesis text here" in result
        assert "Once upon a time" in result


class TestHTMLRenderer:
    """Tests for the HTML Renderer."""

    def test_renderer_content_type(self):
        """HTML renderer returns correct content type."""
        from modules.export_engine.renderers import HTMLRenderer

        renderer = HTMLRenderer()
        assert renderer.content_type == "text/html"

    def test_render_returns_valid_html(self):
        """render() returns HTML document structure."""
        from modules.export_engine.renderers import HTMLRenderer

        renderer = HTMLRenderer()
        mock_itd = {
            "pursuit_title": "Test Pursuit",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": ["thesis_statement"],
            "thesis_statement": {"thesis_text": "Test thesis"},
        }

        result = renderer.render(mock_itd)
        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "</html>" in result
        assert "Test Pursuit" in result

    def test_render_includes_inline_css(self):
        """render() includes inline CSS styles."""
        from modules.export_engine.renderers import HTMLRenderer

        renderer = HTMLRenderer()
        mock_itd = {
            "pursuit_title": "Test",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": [],
        }

        result = renderer.render(mock_itd)
        assert "<style>" in result
        assert "--color-primary" in result

    def test_html_escapes_content(self):
        """render() properly escapes HTML in content."""
        from modules.export_engine.renderers import HTMLRenderer

        renderer = HTMLRenderer()
        mock_itd = {
            "pursuit_title": "Test <script>alert('xss')</script>",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": [],
        }

        result = renderer.render(mock_itd)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestPDFRenderer:
    """Tests for the PDF Renderer."""

    def test_renderer_content_type(self):
        """PDF renderer returns correct content type."""
        from modules.export_engine.renderers import PDFRenderer

        renderer = PDFRenderer()
        assert renderer.content_type == "application/pdf"

    def test_render_returns_bytes(self):
        """render() returns bytes."""
        from modules.export_engine.renderers import PDFRenderer

        renderer = PDFRenderer()
        mock_itd = {
            "pursuit_title": "Test Pursuit",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": ["thesis_statement"],
            "thesis_statement": {"thesis_text": "Test thesis"},
        }

        result = renderer.render(mock_itd)
        assert isinstance(result, bytes)

    def test_render_fallback_when_no_weasyprint(self):
        """render() uses fallback when weasyprint unavailable."""
        from modules.export_engine.renderers import PDFRenderer

        renderer = PDFRenderer()
        renderer._weasyprint_available = False

        mock_itd = {
            "pursuit_title": "Test",
            "style_key": "standard",
            "style_metadata": {"display_name": "Standard"},
            "layer_ordering": [],
        }

        result = renderer.render(mock_itd)
        assert isinstance(result, bytes)
        assert b"%PDF" in result


class TestDOCXRenderer:
    """Tests for the DOCX Renderer."""

    def test_renderer_content_type(self):
        """DOCX renderer returns correct content type."""
        from modules.export_engine.renderers import DOCXRenderer

        renderer = DOCXRenderer()
        assert "wordprocessingml" in renderer.content_type


# =============================================================================
# Test: ExportCoachBridge
# =============================================================================

class TestExportCoachBridge:
    """Tests for the Export Coach Bridge."""

    def test_bridge_initialization(self):
        """Bridge initializes without errors."""
        from modules.export_engine import ExportCoachBridge

        bridge = ExportCoachBridge()
        assert bridge is not None

    def test_discover_exports_returns_result(self):
        """discover_exports returns ExportDiscoveryResult."""
        from modules.export_engine import ExportCoachBridge, ExportDiscoveryResult

        bridge = ExportCoachBridge()
        result = bridge.discover_exports("test-pursuit")

        assert isinstance(result, ExportDiscoveryResult)
        assert result.pursuit_id == "test-pursuit"

    def test_discovery_includes_suggestions(self):
        """Discovery result includes export suggestions."""
        from modules.export_engine import ExportCoachBridge

        bridge = ExportCoachBridge()
        result = bridge.discover_exports("test-pursuit")

        assert len(result.suggestions) > 0
        for suggestion in result.suggestions:
            assert suggestion.template_key is not None
            assert suggestion.narrative_style is not None
            assert suggestion.coach_rationale is not None

    def test_discovery_includes_coach_framing(self):
        """Discovery result includes coach introduction and closing."""
        from modules.export_engine import ExportCoachBridge

        bridge = ExportCoachBridge()
        result = bridge.discover_exports("test-pursuit")

        assert result.coach_introduction is not None
        assert len(result.coach_introduction) > 0
        assert result.coach_closing is not None
        assert len(result.coach_closing) > 0

    def test_get_suggestion_for_audience(self):
        """get_suggestion_for_audience returns matching suggestion."""
        from modules.export_engine import ExportCoachBridge

        bridge = ExportCoachBridge()
        suggestion = bridge.get_suggestion_for_audience("test-pursuit", "investor")

        assert suggestion is not None
        assert suggestion.narrative_style == "investor"


# =============================================================================
# Test: Language Sovereignty
# =============================================================================

class TestLanguageSovereignty:
    """Tests for Language Sovereignty enforcement in exports."""

    def test_prohibited_vocabulary_list_exists(self):
        """PROHIBITED_VOCABULARY list is defined."""
        from modules.export_engine.export_llm_client import PROHIBITED_VOCABULARY

        assert len(PROHIBITED_VOCABULARY) > 0
        assert "fear" in PROHIBITED_VOCABULARY
        assert "pain point" in PROHIBITED_VOCABULARY

    def test_prohibited_methodology_list_exists(self):
        """PROHIBITED_METHODOLOGY_NAMES list is defined."""
        from modules.export_engine.export_llm_client import PROHIBITED_METHODOLOGY_NAMES

        assert len(PROHIBITED_METHODOLOGY_NAMES) > 0
        assert "sprint" in PROHIBITED_METHODOLOGY_NAMES or "lean startup" in [m.lower() for m in PROHIBITED_METHODOLOGY_NAMES]


# =============================================================================
# Test: Display Labels
# =============================================================================

class TestExportDisplayLabels:
    """Tests for Export Engine display labels."""

    def test_export_template_labels_exist(self):
        """export_template category has all templates."""
        from shared.display_labels import DisplayLabels

        templates = DisplayLabels.get_all("export_template")
        assert "business_model_canvas" in templates
        assert "investment_readiness" in templates

    def test_export_style_labels_exist(self):
        """export_narrative_style category has all styles."""
        from shared.display_labels import DisplayLabels

        styles = DisplayLabels.get_all("export_narrative_style")
        assert "investor" in styles
        assert "academic" in styles
        assert "standard" in styles

    def test_export_format_labels_exist(self):
        """export_format category has all formats."""
        from shared.display_labels import DisplayLabels

        formats = DisplayLabels.get_all("export_format")
        assert "markdown" in formats
        assert "html" in formats
        assert "pdf" in formats
        assert "docx" in formats

    def test_export_status_labels_exist(self):
        """export_status category has all statuses."""
        from shared.display_labels import DisplayLabels

        statuses = DisplayLabels.get_all("export_status")
        assert "complete" in statuses
        assert "partial" in statuses
        assert "failed" in statuses


# =============================================================================
# Test: Telemetry Events
# =============================================================================

class TestExportTelemetry:
    """Tests for Export Engine telemetry events."""

    def test_export_events_defined(self):
        """Export telemetry events are defined."""
        from services.telemetry import EVENTS

        export_events = [k for k in EVENTS.keys() if k.startswith("export.")]
        assert len(export_events) >= 7

        assert "export.generation_started" in EVENTS
        assert "export.generation_completed" in EVENTS
        assert "export.downloaded" in EVENTS
        assert "export.discovery_shown" in EVENTS

    def test_track_export_function_exists(self):
        """track_export helper function exists."""
        from services.telemetry import track_export

        assert callable(track_export)

    def test_get_export_summary_function_exists(self):
        """get_export_summary helper function exists."""
        from services.telemetry import get_export_summary

        assert callable(get_export_summary)
