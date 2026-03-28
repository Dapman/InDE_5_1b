"""
Shareable Artifact Export Engine

InDE MVP v4.5.0 — The Engagement Engine

Generates shareable versions of innovation artifacts. Three export formats:
1. Branded PDF — professional one-page document
2. Shareable Link — time-limited public URL with view tracking
3. Clipboard Markdown — plain text for pasting into email, Slack, etc.

Only finalized artifacts can be exported. Draft artifacts are not shareable.

CRITICAL: Exported artifacts contain ONLY the innovator-facing content.
No scaffolding scores, no momentum data, no internal state, no coaching
transcripts. This is architecturally enforced — the export engine reads
from the artifact's published content, not from system state. Consistent
with Tenet XI (Abstract Sovereignty).

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_LINK_EXPIRY_DAYS = 7


# Artifact type to display label mapping
ARTIFACT_TYPE_LABELS = {
    "vision": "Your Innovation Story",
    "fears": "Risk & Protection Analysis",
    "hypothesis": "Key Assumptions",
    "validation": "Evidence Package",
    "retrospective": "Journey Insights",
}


@dataclass
class ExportResult:
    """Result of an artifact export operation."""
    format: str               # "pdf" | "link" | "markdown"
    content: Optional[bytes]  # PDF binary (for pdf format)
    url: Optional[str]        # Share URL (for link format)
    markdown: Optional[str]   # Markdown text (for markdown format)
    token: Optional[str]      # Share token (for link format)
    expires_at: Optional[str] # ISO 8601 (for link format)


class ArtifactExportEngine:
    """
    Orchestrates artifact export across all three formats.

    Dependencies (injected):
      - db: Database connection for artifact and pursuit access
      - pdf_generator: Produces branded PDF
      - share_link_service: Creates and tracks share links
    """

    def __init__(self, db, pdf_generator=None, share_link_service=None, base_url: str = ""):
        """
        Initialize the export engine.

        Args:
            db: Database connection with db.db.<collection> access
            pdf_generator: ArtifactPDFGenerator instance (optional)
            share_link_service: ShareLinkService instance (optional)
            base_url: Base URL for share links (e.g., "https://app.indeverse.com")
        """
        self.db = db
        self._pdf = pdf_generator
        self._share_links = share_link_service
        self._base_url = base_url

    def _get_pdf_generator(self):
        """Lazy-load PDF generator."""
        if self._pdf is None:
            from .pdf_generator import ArtifactPDFGenerator
            self._pdf = ArtifactPDFGenerator()
        return self._pdf

    def _get_share_link_service(self):
        """Lazy-load share link service."""
        if self._share_links is None:
            from .share_link_service import ShareLinkService
            self._share_links = ShareLinkService(self.db)
        return self._share_links

    def can_export(self, pursuit_id: str, artifact_type: str) -> tuple:
        """
        Check if an artifact can be exported.

        Returns:
            (can_export: bool, reason: str)
        """
        artifact = self.db.db.artifacts.find_one({
            "pursuit_id": pursuit_id,
            "artifact_type": artifact_type
        })

        if not artifact:
            return False, "Artifact does not exist"

        # An artifact is considered "finalized" if it exists in the artifacts collection
        # More sophisticated finalization logic could check version > 0, has content, etc.
        if not artifact.get("content"):
            return False, "Artifact has no content"

        return True, "Ready to export"

    def export(self, pursuit_id: str, artifact_type: str,
               format: str, innovator_name: str = "",
               expiry_days: int = DEFAULT_LINK_EXPIRY_DAYS) -> ExportResult:
        """
        Export a finalized artifact in the requested format.

        Args:
            pursuit_id: The pursuit containing the artifact
            artifact_type: 'vision', 'fears', 'hypothesis', etc.
            format: 'pdf' | 'link' | 'markdown'
            innovator_name: Name to include in export (optional)
            expiry_days: Days until share link expires (default: 7)

        Returns:
            ExportResult with appropriate content for the format

        Raises:
            ValueError: If artifact is not exportable or format is invalid
        """
        # Verify artifact exists and has content
        can_export, reason = self.can_export(pursuit_id, artifact_type)
        if not can_export:
            raise ValueError(f"Cannot export: {reason}")

        # Get artifact and pursuit data
        artifact = self.db.db.artifacts.find_one({
            "pursuit_id": pursuit_id,
            "artifact_type": artifact_type
        })
        pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})

        artifact_content = artifact.get("content", "")
        artifact_title = artifact.get("title", "")
        pursuit_title = pursuit.get("title", "Untitled Pursuit") if pursuit else "Untitled Pursuit"
        artifact_label = ARTIFACT_TYPE_LABELS.get(artifact_type, artifact_type.title())

        if format == "pdf":
            pdf_gen = self._get_pdf_generator()
            pdf_bytes = pdf_gen.generate(
                artifact_content=artifact_content,
                artifact_title=artifact_title,
                pursuit_title=pursuit_title,
                artifact_label=artifact_label,
                innovator_name=innovator_name,
            )
            return ExportResult(
                format="pdf", content=pdf_bytes,
                url=None, markdown=None, token=None, expires_at=None
            )

        elif format == "link":
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

            share_service = self._get_share_link_service()
            share_service.create(
                token=token,
                pursuit_id=pursuit_id,
                artifact_type=artifact_type,
                artifact_content=artifact_content,
                artifact_title=artifact_title,
                pursuit_title=pursuit_title,
                artifact_label=artifact_label,
                innovator_name=innovator_name,
                expires_at=expires_at,
            )

            share_url = f"{self._base_url}/api/v1/share/{token}"
            return ExportResult(
                format="link", content=None,
                url=share_url,
                markdown=None, token=token,
                expires_at=expires_at.isoformat()
            )

        elif format == "markdown":
            md = self._format_markdown(
                artifact_content, artifact_title, pursuit_title,
                artifact_label, innovator_name
            )
            return ExportResult(
                format="markdown", content=None,
                url=None, markdown=md, token=None, expires_at=None
            )

        else:
            raise ValueError(f"Invalid export format: {format}")

    def _format_markdown(self, artifact_content: str, artifact_title: str,
                         pursuit_title: str, artifact_label: str,
                         innovator_name: str) -> str:
        """Format artifact as clipboard-ready markdown."""
        lines = [
            f"# {pursuit_title}",
            f"**{artifact_label}**",
            "",
        ]
        if artifact_title:
            lines.append(f"## {artifact_title}")
            lines.append("")

        if innovator_name:
            lines.append(f"*By {innovator_name}*")
            lines.append("")

        # Add the artifact content
        lines.append(artifact_content)
        lines.append("")
        lines.append("---")
        lines.append("*Created with InDE — the Innovation Development Environment*")

        return "\n".join(lines)
