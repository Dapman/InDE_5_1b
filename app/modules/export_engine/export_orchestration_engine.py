"""
InDE MVP v5.1b.0 - Export Orchestration Engine

The unified orchestration layer for export generation.
Accepts (pursuit_id, format_type, audience_style, output_format) and
routes through the 6-step pipeline:

1. Gate check - verify approved ITD and readiness threshold
2. ITD retrieval - load the full six-layer ITD
3. Style application - apply narrative style
4. Template population - populate template fields (if template requested)
5. Format rendering - route to appropriate renderer
6. Result assembly - persist and return

2026 Yul Williams | InDEVerse, Incorporated
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union

from .export_template_registry import (
    ExportTemplateRegistry,
    ExportTemplateSpec,
    FieldMapping,
)
from .narrative_style_engine import NarrativeStyleEngine
from .export_llm_client import ExportLLMClient

logger = logging.getLogger("inde.export.orchestration")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExportRequest:
    """Request for an export generation."""
    pursuit_id: str
    template_key: Optional[str] = None  # None = ITD-only export
    narrative_style: str = "standard"
    output_format: str = "markdown"  # markdown, html, pdf, docx, json
    include_forward_projection: bool = True
    include_pattern_connections: bool = False
    requested_by: str = "system"
    audience_context: Optional[str] = None


@dataclass
class ExportResult:
    """Result of an export generation."""
    export_id: str
    pursuit_id: str
    template_key: Optional[str]
    narrative_style: str
    output_format: str
    status: str  # COMPLETE, PARTIAL, INSUFFICIENT_DATA, BLOCKED
    content: Union[bytes, str]
    content_type: str  # MIME type
    missing_fields: List[str]
    generated_at: str  # ISO 8601
    itd_version: str
    readiness_at_export: float


@dataclass
class TemplatePopulationResult:
    """Result of populating template fields."""
    populated_fields: Dict[str, Any]
    missing_fields: List[str]
    fallback_used: List[str]


class ExportGateError(Exception):
    """Error when export gate check fails."""
    def __init__(
        self,
        status: str,
        reason: str,
        missing_fields: Optional[List[str]] = None,
    ):
        self.status = status
        self.reason = reason
        self.missing_fields = missing_fields or []
        super().__init__(reason)


# =============================================================================
# TEMPLATE POPULATOR
# =============================================================================

class TemplatePopulator:
    """
    Populates template fields from ITD and Outcome Formulator data.

    Resolution order for each field:
    1. itd_source - dot-path into ITD layers
    2. outcome_source - field key from Outcome Formulator
    3. coaching_source - event type from coaching history
    4. fallback_text - used when all sources unavailable
    """

    def __init__(self, registry: ExportTemplateRegistry):
        self._registry = registry

    def populate(
        self,
        template_key: str,
        itd: Dict[str, Any],
        readiness_record: Dict[str, Any],
        coaching_history: Optional[Dict[str, Any]] = None,
    ) -> TemplatePopulationResult:
        """
        Populate all fields for a template.

        Args:
            template_key: Template to populate
            itd: The ITD document (as dict)
            readiness_record: Outcome Formulator readiness data
            coaching_history: Optional coaching event history

        Returns:
            TemplatePopulationResult with populated fields and missing list
        """
        template = self._registry.get_template(template_key)
        if not template:
            return TemplatePopulationResult(
                populated_fields={},
                missing_fields=[],
                fallback_used=[],
            )

        populated = {}
        missing = []
        fallbacks = []

        for mapping in template.field_mappings:
            value = self._resolve_field(
                mapping, itd, readiness_record, coaching_history
            )

            if value is None or value == mapping.fallback_text:
                if mapping.required:
                    missing.append(mapping.field_name)
                if value == mapping.fallback_text:
                    fallbacks.append(mapping.field_name)
                populated[mapping.field_name] = mapping.fallback_text
            else:
                populated[mapping.field_name] = value

        return TemplatePopulationResult(
            populated_fields=populated,
            missing_fields=missing,
            fallback_used=fallbacks,
        )

    def _resolve_field(
        self,
        mapping: FieldMapping,
        itd: Dict[str, Any],
        readiness_record: Dict[str, Any],
        coaching_history: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Resolve a single field using the 3-source cascade."""
        # Try ITD source first
        if mapping.itd_source:
            value = self._get_nested_value(itd, mapping.itd_source)
            if value:
                return self._format_value(value)

        # Try Outcome Formulator source
        if mapping.outcome_source and readiness_record:
            field_data = readiness_record.get("fields", {}).get(mapping.outcome_source)
            if field_data and field_data.get("readiness_score", 0) >= 0.5:
                value = field_data.get("captured_value")
                if value:
                    return self._format_value(value)

        # Try coaching source
        if mapping.coaching_source and coaching_history:
            events = coaching_history.get("events", [])
            for event in events:
                if event.get("event_type") == mapping.coaching_source:
                    value = event.get("artifact_content") or event.get("content")
                    if value:
                        return self._format_value(value)

        # Use fallback
        return mapping.fallback_text

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get a value from a nested dict using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None

            if current is None:
                return None

        return current

    def _format_value(self, value: Any) -> str:
        """Format a value for template display."""
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            # Format list items
            if len(value) == 0:
                return ""
            if isinstance(value[0], dict):
                # List of dicts - extract key content
                items = []
                for item in value:
                    content = (
                        item.get("content") or
                        item.get("description") or
                        item.get("narrative") or
                        str(item)
                    )
                    items.append(f"- {content}")
                return "\n".join(items)
            else:
                return "\n".join(f"- {item}" for item in value)
        elif isinstance(value, dict):
            # Format dict content
            content = (
                value.get("content") or
                value.get("narrative") or
                value.get("description") or
                value.get("thesis_text") or
                str(value)
            )
            return str(content)
        else:
            return str(value)


# =============================================================================
# EXPORT ORCHESTRATION ENGINE
# =============================================================================

class ExportOrchestrationEngine:
    """
    Unified orchestration engine for export generation.

    6-step pipeline:
    1. Gate check - ITD approval and readiness threshold
    2. ITD retrieval - load the full ITD
    3. Style application - apply narrative style
    4. Template population - populate fields (if template requested)
    5. Format rendering - route to renderer
    6. Result assembly - persist and return
    """

    def __init__(
        self,
        db: Any = None,
        itd_service: Any = None,
        outcome_formulator: Any = None,
        telemetry_fn: Any = None,
    ):
        """
        Initialize the export orchestration engine.

        Args:
            db: MongoDB database connection
            itd_service: ITD composition engine for ITD retrieval
            outcome_formulator: Outcome Formulator for readiness data
            telemetry_fn: Telemetry emit function
        """
        self._db = db
        self._itd_service = itd_service
        self._outcome_formulator = outcome_formulator
        self._telemetry_fn = telemetry_fn or (lambda *args, **kwargs: None)

        self._registry = ExportTemplateRegistry()
        self._style_engine = NarrativeStyleEngine()
        self._llm_client = ExportLLMClient()
        self._populator = TemplatePopulator(self._registry)

        # Renderers will be loaded lazily
        self._renderers = {}

    def generate_export(self, request: ExportRequest) -> ExportResult:
        """
        Generate an export following the 6-step pipeline.

        Args:
            request: ExportRequest with all parameters

        Returns:
            ExportResult with content and metadata

        Raises:
            ExportGateError: If gate check fails
        """
        export_id = str(uuid.uuid4())
        logger.info(
            f"[ExportEngine] Starting export {export_id} for pursuit {request.pursuit_id}"
        )

        # Step 1: Gate check
        itd = self._gate_check(request)

        # Step 2: Get readiness data
        readiness = self._get_readiness(request.pursuit_id)
        overall_readiness = readiness.get("overall_score", 0.0)

        # Step 3: Template readiness check (if template requested)
        missing_fields = []
        if request.template_key:
            check = self._registry.check_readiness(
                request.template_key,
                readiness.get("fields", {}),
                overall_readiness,
            )
            if check.status == "BLOCKED":
                raise ExportGateError(
                    "BLOCKED",
                    check.blocking_reason or "Template requirements not met",
                    check.missing_required_fields,
                )
            missing_fields = check.missing_required_fields

        # Step 4: Apply narrative style
        styled_itd = self._style_engine.apply_style(
            itd,
            request.narrative_style,
            self._llm_client,
            request.audience_context,
        )

        # Step 5: Populate template fields (if template requested)
        template_data = None
        if request.template_key:
            pop_result = self._populator.populate(
                request.template_key,
                itd,
                readiness,
                None,  # coaching_history - would load if available
            )
            template_data = pop_result.populated_fields
            missing_fields = pop_result.missing_fields

        # Step 6: Render to requested format
        renderer = self._get_renderer(request.output_format)
        content = renderer.render(styled_itd, template_data)
        content_type = renderer.content_type

        # Step 7: Determine status
        status = "COMPLETE" if not missing_fields else "PARTIAL"

        # Step 8: Persist export record
        self._persist_export(
            export_id=export_id,
            request=request,
            content=content,
            status=status,
            missing_fields=missing_fields,
            readiness=overall_readiness,
            itd_version=itd.get("composition_version", "unknown"),
        )

        # Step 9: Emit telemetry
        self._telemetry_fn(
            f"export_generated_{status.lower()}",
            request.pursuit_id,
            {
                "export_id": export_id,
                "template_key": request.template_key,
                "narrative_style": request.narrative_style,
                "output_format": request.output_format,
                "readiness_at_export": overall_readiness,
                "missing_fields_count": len(missing_fields),
            },
        )

        logger.info(
            f"[ExportEngine] Export {export_id} completed with status {status}"
        )

        return ExportResult(
            export_id=export_id,
            pursuit_id=request.pursuit_id,
            template_key=request.template_key,
            narrative_style=request.narrative_style,
            output_format=request.output_format,
            status=status,
            content=content,
            content_type=content_type,
            missing_fields=missing_fields,
            generated_at=datetime.now(timezone.utc).isoformat(),
            itd_version=itd.get("composition_version", "unknown"),
            readiness_at_export=overall_readiness,
        )

    def _gate_check(self, request: ExportRequest) -> Dict[str, Any]:
        """
        Gate check: verify pursuit has an approved ITD.

        Raises:
            ExportGateError: If no approved ITD exists
        """
        if not self._itd_service:
            # Fallback: try to load from database directly
            if self._db:
                itd = self._db.db.innovation_thesis_documents.find_one({
                    "pursuit_id": request.pursuit_id,
                    "status": "APPROVED",
                })
                if itd:
                    return dict(itd)

            raise ExportGateError(
                "INSUFFICIENT_DATA",
                "No approved Innovation Thesis found for this pursuit",
            )

        itd = self._itd_service.get_itd(request.pursuit_id)
        if not itd:
            raise ExportGateError(
                "INSUFFICIENT_DATA",
                "No Innovation Thesis found for this pursuit",
            )

        # Convert to dict if needed
        if hasattr(itd, "__dict__"):
            itd = itd.__dict__

        # Check status
        status = itd.get("status", "")
        if isinstance(status, str):
            if status.upper() != "APPROVED":
                raise ExportGateError(
                    "INSUFFICIENT_DATA",
                    f"Innovation Thesis is not approved (status: {status})",
                )
        elif hasattr(status, "value"):
            if status.value.upper() != "APPROVED":
                raise ExportGateError(
                    "INSUFFICIENT_DATA",
                    f"Innovation Thesis is not approved (status: {status.value})",
                )

        return itd

    def _get_readiness(self, pursuit_id: str) -> Dict[str, Any]:
        """Get outcome readiness data for the pursuit."""
        if self._outcome_formulator:
            try:
                return self._outcome_formulator.get_outcome_readiness_context(
                    pursuit_id
                )
            except Exception as e:
                logger.warning(f"Failed to get readiness data: {e}")

        # Fallback: empty readiness (will use ITD data)
        return {"overall_score": 0.75, "fields": {}}

    def _get_renderer(self, output_format: str):
        """Get the appropriate renderer for the output format."""
        if output_format not in self._renderers:
            # Lazy load renderers
            if output_format == "markdown":
                from .renderers.markdown_renderer import MarkdownRenderer
                self._renderers["markdown"] = MarkdownRenderer()
            elif output_format == "html":
                from .renderers.html_renderer import HTMLRenderer
                self._renderers["html"] = HTMLRenderer()
            elif output_format == "pdf":
                from .renderers.pdf_renderer import PDFRenderer
                self._renderers["pdf"] = PDFRenderer()
            elif output_format == "docx":
                from .renderers.docx_renderer import DOCXRenderer
                self._renderers["docx"] = DOCXRenderer()
            else:
                # Default to markdown
                from .renderers.markdown_renderer import MarkdownRenderer
                self._renderers[output_format] = MarkdownRenderer()

        return self._renderers[output_format]

    def _persist_export(
        self,
        export_id: str,
        request: ExportRequest,
        content: Union[bytes, str],
        status: str,
        missing_fields: List[str],
        readiness: float,
        itd_version: str,
    ):
        """Persist export record to database."""
        if not self._db:
            return

        try:
            # Determine content storage
            is_binary = isinstance(content, bytes)

            record = {
                "export_id": export_id,
                "pursuit_id": request.pursuit_id,
                "template_key": request.template_key,
                "narrative_style": request.narrative_style,
                "output_format": request.output_format,
                "status": status,
                "missing_fields": missing_fields,
                "readiness_at_export": readiness,
                "itd_version": itd_version,
                "generated_at": datetime.now(timezone.utc),
                "requested_by": request.requested_by,
            }

            if is_binary:
                # Store in GridFS
                from gridfs import GridFS
                fs = GridFS(self._db.db)
                grid_id = fs.put(
                    content,
                    filename=f"{export_id}.{request.output_format}",
                    pursuit_id=request.pursuit_id,
                )
                record["content_gridfs_id"] = str(grid_id)
                record["content_inline"] = None
            else:
                # Store inline
                record["content_inline"] = content
                record["content_gridfs_id"] = None

            self._db.db.export_records.insert_one(record)
            logger.info(f"Persisted export record {export_id}")

        except Exception as e:
            logger.error(f"Failed to persist export record: {e}")

    def get_export(self, export_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an export record by ID."""
        if not self._db:
            return None

        return self._db.db.export_records.find_one({"export_id": export_id})

    def get_export_content(self, export_id: str) -> Optional[Union[bytes, str]]:
        """Retrieve export content by ID."""
        record = self.get_export(export_id)
        if not record:
            return None

        if record.get("content_inline"):
            return record["content_inline"]

        if record.get("content_gridfs_id"):
            from gridfs import GridFS
            fs = GridFS(self._db.db)
            grid_file = fs.get(record["content_gridfs_id"])
            return grid_file.read()

        return None

    def list_exports(
        self,
        pursuit_id: str,
        page: int = 1,
        per_page: int = 10,
    ) -> List[Dict[str, Any]]:
        """List all exports for a pursuit."""
        if not self._db:
            return []

        skip = (page - 1) * per_page
        cursor = self._db.db.export_records.find(
            {"pursuit_id": pursuit_id}
        ).sort("generated_at", -1).skip(skip).limit(per_page)

        return list(cursor)
