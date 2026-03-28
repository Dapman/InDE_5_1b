"""
InDE v3.1 - Reports API Routes
Report generation and distribution.

v4.5: Fixed to actually call LivingSnapshotGenerator instead of placeholder.
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth.middleware import get_current_user
from reporting.living_snapshot_generator import LivingSnapshotGenerator
from reporting.template_manager import ReportTemplateManager

logger = logging.getLogger("inde.api.reports")

router = APIRouter()


def _format_snapshot_content(content: dict) -> str:
    """
    Format snapshot content dict into readable markdown text.
    """
    if not content:
        return "No content available."

    md_parts = []

    for section_id, section_data in content.items():
        status = section_data.get("status", "UNKNOWN")
        title = section_id.replace("_", " ").title()

        md_parts.append(f"## {title}")
        md_parts.append(f"*Status: {status}*\n")

        if status == "COMPLETE":
            data = section_data.get("data", {})
            if "content" in data:
                md_parts.append(data["content"])
            else:
                for key, value in data.items():
                    if isinstance(value, dict):
                        md_parts.append(f"**{key.replace('_', ' ').title()}:**")
                        for k, v in value.items():
                            md_parts.append(f"- {k}: {v}")
                    elif isinstance(value, list):
                        md_parts.append(f"**{key.replace('_', ' ').title()}:**")
                        for item in value:
                            md_parts.append(f"- {item}")
                    else:
                        md_parts.append(f"**{key.replace('_', ' ').title()}:** {value}")

        elif status == "IN_PROGRESS":
            note = section_data.get("note", "In progress")
            md_parts.append(f"*{note}*")
            if "data" in section_data:
                for key, value in section_data["data"].items():
                    if key != "note":
                        md_parts.append(f"- {key.replace('_', ' ').title()}: {value}")

        elif status == "PLANNED":
            projection = section_data.get("projection", {})
            note = projection.get("note", section_data.get("note", "Planned for later"))
            md_parts.append(f"*{note}*")

        md_parts.append("")  # Blank line between sections

    return "\n".join(md_parts)


class CreateReportRequest(BaseModel):
    pursuit_id: str
    report_type: str  # "living_snapshot", "terminal", "portfolio"
    template: Optional[str] = "silr-standard"


class ReportResponse(BaseModel):
    report_id: str
    pursuit_id: Optional[str]
    report_type: str
    template: str
    status: str
    content: Optional[str]
    created_at: datetime


@router.post("", response_model=ReportResponse)
async def create_report(
    request: Request,
    data: CreateReportRequest,
    user: dict = Depends(get_current_user)
):
    """
    Generate a new report for a pursuit.

    v4.5: Now actually generates the report content using the appropriate generator.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": data.pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    # Generate report based on type
    if data.report_type == "living_snapshot":
        try:
            # Initialize generator and template manager
            template_manager = ReportTemplateManager(db)
            generator = LivingSnapshotGenerator(db, template_manager)

            # Generate the snapshot
            result = generator.generate_snapshot(
                pursuit_id=data.pursuit_id,
                template_id=data.template or "silr-light",
                formats=["markdown"],
                include_projections=True
            )

            # Build response from generated content
            report = {
                "report_id": result["report_id"],
                "pursuit_id": data.pursuit_id,
                "report_type": data.report_type,
                "template": data.template or "silr-light",
                "status": "complete",
                "content": _format_snapshot_content(result.get("content", {})),
                "created_at": datetime.now(timezone.utc)
            }

            logger.info(f"Generated living snapshot {result['report_id']} for pursuit {data.pursuit_id}")

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Snapshot generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    else:
        # For terminal and portfolio reports, create placeholder (not yet implemented)
        report_id = str(uuid.uuid4())
        report = {
            "report_id": report_id,
            "pursuit_id": data.pursuit_id,
            "user_id": user["user_id"],
            "report_type": data.report_type,
            "template": data.template,
            "status": "draft",
            "content": f"# Report for {pursuit['title']}\n\nReport generation in progress.",
            "created_at": datetime.now(timezone.utc)
        }

        # Store in appropriate collection
        if data.report_type == "terminal":
            db.db.terminal_reports.insert_one(report)
        else:
            db.db.portfolio_analytics_reports.insert_one(report)

    return ReportResponse(**{k: v for k, v in report.items() if k != "_id" and k != "user_id"})


@router.get("/{report_id}")
async def get_report(
    request: Request,
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get a report by ID.
    """
    db = request.app.state.db

    # Check all report collections
    for collection in ["living_snapshot_reports", "terminal_reports", "portfolio_analytics_reports"]:
        report = db.db[collection].find_one({
            "report_id": report_id,
            "user_id": user["user_id"]
        })
        if report:
            if "_id" in report:
                del report["_id"]
            return report

    raise HTTPException(status_code=404, detail="Report not found")


@router.get("/pursuit/{pursuit_id}")
async def list_pursuit_reports(
    request: Request,
    pursuit_id: str,
    user: dict = Depends(get_current_user)
):
    """
    List all reports for a pursuit.
    """
    db = request.app.state.db

    # Verify pursuit ownership
    pursuit = db.db.pursuits.find_one({
        "pursuit_id": pursuit_id,
        "user_id": user["user_id"]
    })

    if not pursuit:
        raise HTTPException(status_code=404, detail="Pursuit not found")

    reports = []

    for collection in ["living_snapshot_reports", "terminal_reports"]:
        docs = list(db.db[collection].find(
            {"pursuit_id": pursuit_id},
            {"_id": 0}
        ).sort("created_at", -1))
        reports.extend(docs)

    return {"pursuit_id": pursuit_id, "reports": reports}
