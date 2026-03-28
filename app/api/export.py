"""
InDE MVP v5.1b.0 - Export Engine API

REST endpoints for audience-specific export generation.

Endpoints:
- GET /api/v1/pursuits/{pursuit_id}/export/availability - Get export availability
- POST /api/v1/pursuits/{pursuit_id}/export/generate - Generate export
- GET /api/v1/export/{export_id} - Get export record by ID
- GET /api/v1/export/{export_id}/download - Download export file
- GET /api/v1/pursuits/{pursuit_id}/exports - List exports for pursuit

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger("inde.api.export")

router = APIRouter(prefix="/api/v1", tags=["Export"])


# =============================================================================
# ENUMS
# =============================================================================

class ExportFormat(str, Enum):
    """Supported export formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"


class ExportNarrativeStyle(str, Enum):
    """Supported narrative styles."""
    INVESTOR = "investor"
    ACADEMIC = "academic"
    COMMERCIAL = "commercial"
    GRANT = "grant"
    INTERNAL = "internal"
    STANDARD = "standard"


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ExportGenerateRequest(BaseModel):
    """Request to generate an export."""
    template_key: str = Field(..., description="Template family key (e.g., 'business_model_canvas')")
    narrative_style: ExportNarrativeStyle = Field(
        default=ExportNarrativeStyle.STANDARD,
        description="Narrative style for ITD voice"
    )
    format: ExportFormat = Field(
        default=ExportFormat.PDF,
        description="Output format"
    )
    custom_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional custom rendering options"
    )


class TemplateAvailabilityResponse(BaseModel):
    """Template availability details."""
    template_key: str
    display_name: str
    description: str
    category: str
    is_available: bool
    readiness_score: float
    fields_ready: int
    fields_total: int
    missing_fields: List[str]


class ExportAvailabilityResponse(BaseModel):
    """Export availability for a pursuit."""
    pursuit_id: str
    pursuit_title: str
    itd_exists: bool
    itd_status: Optional[str]
    overall_readiness: float
    templates: List[TemplateAvailabilityResponse]
    recommended_template: Optional[str]
    recommended_style: Optional[str]


class ExportRecordResponse(BaseModel):
    """Export record response."""
    export_id: str
    pursuit_id: str
    template_key: str
    narrative_style: str
    format: str
    status: str
    readiness_at_generation: float
    partial_fields: List[str]
    file_size_bytes: Optional[int]
    created_at: str
    download_url: Optional[str]


class ExportListResponse(BaseModel):
    """List of exports for a pursuit."""
    pursuit_id: str
    exports: List[ExportRecordResponse]
    total: int


class ExportGenerateResponse(BaseModel):
    """Response from export generation."""
    export_id: str
    pursuit_id: str
    template_key: str
    narrative_style: str
    format: str
    status: str
    readiness_score: float
    partial_fields: List[str]
    download_url: Optional[str]
    warnings: List[str]


# =============================================================================
# DEPENDENCIES
# =============================================================================

def get_export_engine(request: Request):
    """Get export orchestration engine from app state."""
    engine = getattr(request.app.state, "export_engine", None)
    if not engine:
        raise HTTPException(status_code=503, detail="Export engine not available")
    return engine


def get_template_registry(request: Request):
    """Get export template registry from app state."""
    registry = getattr(request.app.state, "export_template_registry", None)
    if not registry:
        # Create on demand if not initialized
        from modules.export_engine import ExportTemplateRegistry
        registry = ExportTemplateRegistry()
        request.app.state.export_template_registry = registry
    return registry


def get_db(request: Request):
    """Get database from app state."""
    db = getattr(request.app.state, "db", None)
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")
    return db


def get_current_user(request: Request):
    """Get current user from request state."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# =============================================================================
# EXPORT AVAILABILITY ENDPOINT
# =============================================================================

@router.get("/pursuits/{pursuit_id}/export/availability", response_model=ExportAvailabilityResponse)
async def get_export_availability(
    pursuit_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Get export availability for a pursuit.

    Returns which templates are available based on the pursuit's ITD
    and outcome readiness state.
    """
    logger.info(f"[Export API] Get availability for pursuit: {pursuit_id}")

    db = get_db(request)
    template_registry = get_template_registry(request)

    # Get pursuit
    pursuit = db.db.pursuits.find_one({"_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    pursuit_title = pursuit.get("title", "Untitled Pursuit")

    # Get ITD status
    itd = db.db.innovation_thesis_documents.find_one(
        {"pursuit_id": pursuit_id},
        sort=[("created_at", -1)]
    )
    itd_exists = itd is not None
    itd_status = itd.get("status") if itd else None

    # Get outcome readiness
    outcome_state = db.db.outcome_readiness_states.find_one({"pursuit_id": pursuit_id})

    # Build readiness data for template registry
    readiness_data = {
        "itd": itd.get("layers", {}) if itd else {},
        "outcome_state": outcome_state or {},
        "pursuit": pursuit,
    }

    # Get availability for all templates
    all_templates = template_registry.get_all_templates()
    template_availabilities = []
    highest_readiness = 0.0
    recommended_template = None

    for template_key, template_spec in all_templates.items():
        readiness_result = template_registry.check_template_readiness(
            template_key=template_key,
            pursuit_id=pursuit_id,
            readiness_data=readiness_data,
        )

        is_available = readiness_result.is_ready or readiness_result.readiness_score >= 0.5
        fields_ready = len([f for f in readiness_result.field_statuses if f.get("is_ready")])
        fields_total = len(template_spec.fields)
        missing_fields = [
            f.get("field_name") for f in readiness_result.field_statuses
            if not f.get("is_ready")
        ]

        template_availabilities.append(TemplateAvailabilityResponse(
            template_key=template_key,
            display_name=template_spec.display_name,
            description=template_spec.description,
            category=template_spec.category,
            is_available=is_available,
            readiness_score=readiness_result.readiness_score,
            fields_ready=fields_ready,
            fields_total=fields_total,
            missing_fields=missing_fields[:5],  # Limit to first 5
        ))

        if readiness_result.readiness_score > highest_readiness:
            highest_readiness = readiness_result.readiness_score
            recommended_template = template_key

    # Calculate overall readiness
    if template_availabilities:
        overall_readiness = sum(t.readiness_score for t in template_availabilities) / len(template_availabilities)
    else:
        overall_readiness = 0.0

    # Determine recommended style based on template
    style_recommendations = {
        "investment_readiness": "investor",
        "grant": "grant",
        "gate_review_package": "internal",
        "business_model_canvas": "commercial",
        "empathy_journey_map": "standard",
        "strategy_canvas": "commercial",
    }
    recommended_style = style_recommendations.get(recommended_template, "standard")

    return ExportAvailabilityResponse(
        pursuit_id=pursuit_id,
        pursuit_title=pursuit_title,
        itd_exists=itd_exists,
        itd_status=itd_status,
        overall_readiness=overall_readiness,
        templates=template_availabilities,
        recommended_template=recommended_template,
        recommended_style=recommended_style,
    )


# =============================================================================
# EXPORT GENERATION ENDPOINT
# =============================================================================

@router.post("/pursuits/{pursuit_id}/export/generate", response_model=ExportGenerateResponse)
async def generate_export(
    pursuit_id: str,
    body: ExportGenerateRequest,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Generate an export for a pursuit.

    Creates a styled export document using the specified template,
    narrative style, and output format.
    """
    logger.info(f"[Export API] Generate export for pursuit: {pursuit_id}, template: {body.template_key}")

    db = get_db(request)

    # Verify pursuit exists
    pursuit = db.db.pursuits.find_one({"_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Get or create export engine
    export_engine = getattr(request.app.state, "export_engine", None)
    if not export_engine:
        # Initialize on demand
        from modules.export_engine import ExportOrchestrationEngine
        export_engine = ExportOrchestrationEngine(db=db)
        request.app.state.export_engine = export_engine

    # Build export request
    from modules.export_engine import ExportRequest

    export_request = ExportRequest(
        pursuit_id=pursuit_id,
        template_key=body.template_key,
        narrative_style=body.narrative_style.value,
        output_format=body.format.value,
        user_id=user.get("user_id"),
        custom_options=body.custom_options or {},
    )

    try:
        # Generate export
        result = export_engine.generate_export(export_request)

        # Build download URL if successful
        download_url = None
        if result.export_id and result.status in ["complete", "partial"]:
            download_url = f"/api/v1/export/{result.export_id}/download"

        return ExportGenerateResponse(
            export_id=result.export_id or "",
            pursuit_id=pursuit_id,
            template_key=body.template_key,
            narrative_style=body.narrative_style.value,
            format=body.format.value,
            status=result.status,
            readiness_score=result.readiness_score,
            partial_fields=result.partial_fields,
            download_url=download_url,
            warnings=result.warnings,
        )

    except Exception as e:
        logger.error(f"[Export API] Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EXPORT RETRIEVAL ENDPOINTS
# =============================================================================

@router.get("/export/{export_id}", response_model=ExportRecordResponse)
async def get_export_record(
    export_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Get an export record by ID.

    Returns metadata about the export, not the content itself.
    """
    db = get_db(request)

    # Find export record
    export_record = db.db.export_records.find_one({"_id": export_id})
    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")

    # Build download URL
    download_url = None
    if export_record.get("status") in ["complete", "partial"]:
        download_url = f"/api/v1/export/{export_id}/download"

    return ExportRecordResponse(
        export_id=export_id,
        pursuit_id=export_record.get("pursuit_id", ""),
        template_key=export_record.get("template_key", ""),
        narrative_style=export_record.get("narrative_style", "standard"),
        format=export_record.get("format", ""),
        status=export_record.get("status", ""),
        readiness_at_generation=export_record.get("readiness_at_generation", 0.0),
        partial_fields=export_record.get("partial_fields", []),
        file_size_bytes=export_record.get("file_size_bytes"),
        created_at=export_record.get("created_at", datetime.utcnow()).isoformat(),
        download_url=download_url,
    )


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """
    Download an export file.

    Returns the generated export in its native format.
    """
    db = get_db(request)

    # Find export record
    export_record = db.db.export_records.find_one({"_id": export_id})
    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")

    export_format = export_record.get("format", "")
    status = export_record.get("status", "")

    if status not in ["complete", "partial"]:
        raise HTTPException(status_code=400, detail=f"Export not ready. Status: {status}")

    # Get content
    content = None
    content_type = "application/octet-stream"
    filename = f"export_{export_id}"

    # Check for inline content (text formats)
    if "content_inline" in export_record:
        content = export_record["content_inline"]
        if isinstance(content, str):
            content = content.encode("utf-8")
    elif "gridfs_id" in export_record:
        # Retrieve from GridFS
        from gridfs import GridFS
        fs = GridFS(db.db)
        try:
            grid_file = fs.get(export_record["gridfs_id"])
            content = grid_file.read()
        except Exception as e:
            logger.error(f"[Export API] GridFS retrieval failed: {e}")
            raise HTTPException(status_code=500, detail="Export file not found in storage")
    else:
        raise HTTPException(status_code=500, detail="Export content not available")

    # Set content type and filename based on format
    format_details = {
        "markdown": ("text/markdown", f"{filename}.md"),
        "html": ("text/html", f"{filename}.html"),
        "pdf": ("application/pdf", f"{filename}.pdf"),
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"{filename}.docx"
        ),
    }

    content_type, filename = format_details.get(export_format, ("application/octet-stream", filename))

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/pursuits/{pursuit_id}/exports", response_model=ExportListResponse)
async def list_exports_for_pursuit(
    pursuit_id: str,
    request: Request,
    limit: int = 20,
    user=Depends(get_current_user),
):
    """
    List exports for a pursuit.

    Returns recent export records ordered by creation date.
    """
    db = get_db(request)

    # Find exports
    exports_cursor = db.db.export_records.find(
        {"pursuit_id": pursuit_id}
    ).sort("created_at", -1).limit(limit)

    exports = []
    for record in exports_cursor:
        download_url = None
        if record.get("status") in ["complete", "partial"]:
            download_url = f"/api/v1/export/{record['_id']}/download"

        exports.append(ExportRecordResponse(
            export_id=str(record["_id"]),
            pursuit_id=record.get("pursuit_id", ""),
            template_key=record.get("template_key", ""),
            narrative_style=record.get("narrative_style", "standard"),
            format=record.get("format", ""),
            status=record.get("status", ""),
            readiness_at_generation=record.get("readiness_at_generation", 0.0),
            partial_fields=record.get("partial_fields", []),
            file_size_bytes=record.get("file_size_bytes"),
            created_at=record.get("created_at", datetime.utcnow()).isoformat(),
            download_url=download_url,
        ))

    # Get total count
    total = db.db.export_records.count_documents({"pursuit_id": pursuit_id})

    return ExportListResponse(
        pursuit_id=pursuit_id,
        exports=exports,
        total=total,
    )
