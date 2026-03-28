"""
Artifact PDF Generator

InDE MVP v4.5.0 — The Engagement Engine

Generates branded, professional PDF documents for artifact export.
The PDF contains ONLY innovator-facing content — no internal system data,
no scaffolding scores, no coaching context.

Template structure:
- Header: InDE branding
- Body: Pursuit title, artifact label, content
- Footer: "Created with InDE" + generation date

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import PDF generation library (fpdf2 is lightweight and pure Python)
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logger.info("fpdf2 not installed - PDF generation will return HTML fallback")


class ArtifactPDFGenerator:
    """
    Generates branded single-page PDF documents for artifact export.

    The PDF template produces a clean, professional document:
    - InDE header with branding
    - Pursuit title and artifact type
    - Artifact content
    - Innovator name and generation date
    - Footer with InDE tagline
    """

    def __init__(self):
        """Initialize the PDF generator."""
        pass

    def generate(self, artifact_content: str, artifact_title: str = "",
                 pursuit_title: str = "", artifact_label: str = "",
                 innovator_name: str = "") -> bytes:
        """
        Generate a branded PDF for the artifact.

        Args:
            artifact_content: The main content of the artifact
            artifact_title: Title of the artifact (optional)
            pursuit_title: Title of the pursuit
            artifact_label: Innovator-facing label (e.g., "Your Innovation Story")
            innovator_name: Name of the creator (optional)

        Returns:
            PDF document as bytes
        """
        if PDF_AVAILABLE:
            return self._generate_with_fpdf(
                artifact_content, artifact_title, pursuit_title,
                artifact_label, innovator_name
            )
        else:
            return self._generate_html_fallback(
                artifact_content, artifact_title, pursuit_title,
                artifact_label, innovator_name
            )

    def _generate_with_fpdf(self, artifact_content: str, artifact_title: str,
                            pursuit_title: str, artifact_label: str,
                            innovator_name: str) -> bytes:
        """Generate PDF using fpdf2 library."""
        pdf = FPDF()
        pdf.add_page()

        # Set fonts (using built-in fonts)
        pdf.set_auto_page_break(auto=True, margin=25)

        # Header - InDE branding
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(45, 212, 191)  # InDE teal
        pdf.cell(0, 15, "InDE", align="L", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 5, "Innovation Development Environment", align="L", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(10)

        # Pursuit title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 10, pursuit_title)

        # Artifact label
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, artifact_label, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(5)

        # Artifact title (if different from pursuit title)
        if artifact_title and artifact_title != pursuit_title:
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 8, artifact_title)
            pdf.ln(5)

        # Innovator name
        if innovator_name:
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 8, f"By {innovator_name}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

        # Divider line
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

        # Main content
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(40, 40, 40)
        # Split content into paragraphs
        paragraphs = artifact_content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                pdf.multi_cell(0, 6, para.strip())
                pdf.ln(4)

        # Footer
        pdf.ln(10)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(128, 128, 128)
        generation_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
        pdf.cell(0, 5, f"Created with InDE — the Innovation Development Environment | {generation_date}",
                 align="C", new_x="LMARGIN", new_y="NEXT")

        # Return as bytes
        return bytes(pdf.output())

    def _generate_html_fallback(self, artifact_content: str, artifact_title: str,
                                pursuit_title: str, artifact_label: str,
                                innovator_name: str) -> bytes:
        """Generate HTML document as fallback when PDF library not available."""
        generation_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{pursuit_title} - {artifact_label}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }}
        .header {{ border-bottom: 2px solid #2dd4bf; padding-bottom: 15px; margin-bottom: 30px; }}
        .brand {{ color: #2dd4bf; font-size: 28px; font-weight: bold; }}
        .tagline {{ color: #888; font-size: 12px; }}
        h1 {{ color: #1a1a1a; font-size: 24px; margin-bottom: 5px; }}
        .artifact-label {{ color: #666; font-size: 14px; margin-bottom: 15px; }}
        .author {{ color: #555; font-style: italic; margin-bottom: 20px; }}
        .content {{ line-height: 1.6; white-space: pre-wrap; }}
        .footer {{ border-top: 1px solid #ddd; margin-top: 40px; padding-top: 15px; text-align: center; color: #888; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="brand">InDE</div>
        <div class="tagline">Innovation Development Environment</div>
    </div>

    <h1>{pursuit_title}</h1>
    <div class="artifact-label">{artifact_label}</div>
    {"<div class='author'>By " + innovator_name + "</div>" if innovator_name else ""}

    <div class="content">{artifact_content}</div>

    <div class="footer">
        Created with InDE — the Innovation Development Environment | {generation_date}
    </div>
</body>
</html>"""

        return html.encode('utf-8')
