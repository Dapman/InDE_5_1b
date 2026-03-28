"""
Artifact Export API

InDE MVP v4.5.0 — The Engagement Engine

REST endpoints for artifact export:
- POST /api/v1/pursuits/{pursuit_id}/artifacts/{artifact_type}/export
- GET /api/v1/share/{share_token} — public, no auth
- GET /api/v1/pursuits/{pursuit_id}/share-analytics

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import os

from auth.middleware import get_current_user
from modules.artifact_export import ArtifactExportEngine, ShareLinkService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class ExportRequest(BaseModel):
    """Request body for artifact export."""
    format: str = Field(..., pattern="^(pdf|link|markdown)$",
                        description="Export format: pdf, link, or markdown")
    expiry_days: Optional[int] = Field(default=7, ge=1, le=90,
                                       description="Days until share link expires (1-90)")


class ExportResponse(BaseModel):
    """Response for artifact export."""
    format: str
    url: Optional[str] = None
    token: Optional[str] = None
    markdown: Optional[str] = None
    expires_at: Optional[str] = None


class ShareAnalyticsResponse(BaseModel):
    """Analytics for a single share link."""
    token: str
    artifact_type: str
    pursuit_title: Optional[str] = None
    view_count: int
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    last_viewed_at: Optional[str] = None


class ShareAnalyticsListResponse(BaseModel):
    """List of share link analytics."""
    links: List[ShareAnalyticsResponse]
    total_views: int


@router.post("/pursuits/{pursuit_id}/artifacts/{artifact_type}/export",
             response_model=ExportResponse)
async def export_artifact(
    pursuit_id: str,
    artifact_type: str,
    request: Request,
    data: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Export a finalized artifact in the requested format.

    - **pdf**: Returns PDF as binary download
    - **link**: Creates a time-limited shareable URL
    - **markdown**: Returns plain text for clipboard

    Only finalized artifacts can be exported.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({"pursuit_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("user_id") != current_user["user_id"]:
        is_team_member = db.db.team_members.find_one({
            "pursuit_id": pursuit_id,
            "user_id": current_user["user_id"]
        })
        if not is_team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get user name for export
    user = db.db.users.find_one({"user_id": current_user["user_id"]})
    innovator_name = user.get("display_name", user.get("email", "")) if user else ""

    # Get base URL from environment or request
    base_url = os.getenv("PUBLIC_BASE_URL", str(request.base_url).rstrip("/"))

    # Initialize engine and export
    engine = ArtifactExportEngine(db, base_url=base_url)

    try:
        result = engine.export(
            pursuit_id=pursuit_id,
            artifact_type=artifact_type,
            format=data.format,
            innovator_name=innovator_name,
            expiry_days=data.expiry_days
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle PDF response specially (binary download)
    if data.format == "pdf":
        return Response(
            content=result.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={artifact_type}_export.pdf"
            }
        )

    return ExportResponse(
        format=result.format,
        url=result.url,
        token=result.token,
        markdown=result.markdown,
        expires_at=result.expires_at
    )


@router.get("/share/{share_token}", response_class=HTMLResponse)
async def view_shared_artifact(
    share_token: str,
    request: Request
):
    """
    Public endpoint to view a shared artifact.

    No authentication required. Returns a branded HTML page with the artifact content.
    Returns 404 if token is expired or invalid.
    """
    db = request.app.state.db

    share_service = ShareLinkService(db)
    shared = share_service.get_by_token(share_token)

    if not shared:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    # Render a clean, branded HTML page
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{shared.get('pursuit_title', 'Shared Innovation')} | InDE</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .brand {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .brand-name {{
            font-size: 32px;
            font-weight: bold;
            color: #2dd4bf;
            letter-spacing: 2px;
        }}
        .brand-tagline {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .card {{
            background: rgba(30, 30, 45, 0.8);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 40px;
            backdrop-filter: blur(10px);
        }}
        .pursuit-title {{
            font-size: 28px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 8px;
        }}
        .artifact-label {{
            font-size: 14px;
            color: #2dd4bf;
            margin-bottom: 24px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .author {{
            font-size: 14px;
            color: #888;
            font-style: italic;
            margin-bottom: 24px;
        }}
        .divider {{
            height: 1px;
            background: rgba(255,255,255,0.1);
            margin: 24px 0;
        }}
        .content {{
            font-size: 16px;
            line-height: 1.8;
            color: #ccc;
            white-space: pre-wrap;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        .footer-text {{
            font-size: 12px;
            color: #666;
        }}
        .footer-link {{
            color: #2dd4bf;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">
            <div class="brand-name">InDE</div>
            <div class="brand-tagline">Innovation Development Environment</div>
        </div>

        <div class="card">
            <div class="pursuit-title">{shared.get('pursuit_title', 'Innovation')}</div>
            <div class="artifact-label">{shared.get('artifact_label', 'Artifact')}</div>
            {'<div class="author">By ' + shared.get('innovator_name') + '</div>' if shared.get('innovator_name') else ''}

            <div class="divider"></div>

            <div class="content">{shared.get('artifact_content', '')}</div>
        </div>

        <div class="footer">
            <p class="footer-text">
                Shared via <a href="https://indeverse.com" class="footer-link">InDE</a> —
                the Innovation Development Environment
            </p>
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content)


@router.get("/pursuits/{pursuit_id}/share-analytics",
            response_model=ShareAnalyticsListResponse)
async def get_share_analytics(
    pursuit_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get analytics for all share links associated with a pursuit.

    Requires authentication and pursuit ownership.
    """
    db = request.app.state.db

    # Verify pursuit exists and user has access
    pursuit = db.db.pursuits.find_one({"pursuit_id": pursuit_id})
    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    if pursuit.get("user_id") != current_user["user_id"]:
        is_team_member = db.db.team_members.find_one({
            "pursuit_id": pursuit_id,
            "user_id": current_user["user_id"]
        })
        if not is_team_member:
            raise HTTPException(status_code=403, detail="Access denied")

    share_service = ShareLinkService(db)
    links = share_service.get_links_for_pursuit(pursuit_id)

    total_views = sum(link.get("view_count", 0) for link in links)

    return ShareAnalyticsListResponse(
        links=[ShareAnalyticsResponse(
            token=link.get("token", ""),
            artifact_type=link.get("artifact_type", ""),
            pursuit_title=pursuit.get("title"),
            view_count=link.get("view_count", 0),
            created_at=link.get("created_at").isoformat() if link.get("created_at") else None,
            expires_at=link.get("expires_at").isoformat() if link.get("expires_at") else None,
            last_viewed_at=link.get("last_viewed_at").isoformat() if link.get("last_viewed_at") else None,
        ) for link in links],
        total_views=total_views
    )
