"""
InDE MVP v5.1b.0 - IRC Export Integration

Primary Deliverable H: Provides resource data for export templates that
have irc_integration=True. Adds resource appendix section to exports.

Functions:
- get_export_resource_data: Formatted resource data for export
- get_resource_appendix: Generate resource appendix section

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Dict, Any, Optional, List

from .resource_entry_manager import ResourceEntryManager, AvailabilityStatus, PhaseAlignment
from .consolidation_engine import IRCConsolidationEngine
from .irc_display_labels import get_display_label

logger = logging.getLogger("inde.irc.export_integration")


class IRCExportIntegration:
    """
    Integration layer between IRC and Export Engine modules.
    Provides formatted resource data for export templates.
    """

    def __init__(self, db):
        """
        Initialize Export integration.

        Args:
            db: Database instance
        """
        self.db = db
        self.resource_manager = ResourceEntryManager(db)
        self.consolidation_engine = IRCConsolidationEngine(db)

    def get_export_resource_data(self, pursuit_id: str) -> Optional[Dict[str, Any]]:
        """
        Get formatted resource data for an export.

        Used by templates with irc_integration=True:
        - investment_readiness
        - gate_review_package

        Returns None if no IRC canvas exists (templates render without resource section).

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Formatted resource data, or None if not available
        """
        # Get canvas
        canvas = self.consolidation_engine.get_canvas(pursuit_id)
        if not canvas:
            logger.debug(f"[IRCExport] No canvas for pursuit {pursuit_id}")
            return None

        # Get resources
        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)
        if not resources:
            return None

        # Format for export
        return {
            "summary": self._format_summary(canvas, resources),
            "resources_by_phase": self._format_by_phase(resources),
            "resources_by_category": self._format_by_category(resources),
            "cost_summary": self._format_cost_summary(canvas),
            "availability_summary": self._format_availability_summary(canvas, resources),
            "resource_count": len(resources),
            "canvas_completeness": canvas.get("canvas_completeness", 0),
            "appendix_rows": self._format_appendix_rows(resources),
        }

    def get_resource_appendix(
        self,
        pursuit_id: str,
        format_type: str = "markdown",
    ) -> str:
        """
        Generate a formatted resource appendix for export documents.

        Args:
            pursuit_id: The pursuit ID
            format_type: Output format ("markdown", "html", "text")

        Returns:
            Formatted appendix text
        """
        data = self.get_export_resource_data(pursuit_id)
        if not data:
            return ""

        if format_type == "markdown":
            return self._render_markdown_appendix(data)
        elif format_type == "html":
            return self._render_html_appendix(data)
        else:
            return self._render_text_appendix(data)

    def _format_summary(self, canvas: Dict, resources: List[Dict]) -> str:
        """Format summary prose for export."""
        total = len(resources)
        secured = canvas.get("secured_count", 0)
        open_count = canvas.get("unresolved_count", 0)

        if total == 0:
            return "Resource requirements have not yet been documented."

        parts = []

        # Count summary
        parts.append(f"The pursuit has identified {total} resource requirement{'s' if total != 1 else ''}")

        # Status summary
        status_parts = []
        if secured > 0:
            status_parts.append(f"{secured} secured")
        if open_count > 0:
            status_parts.append(f"{open_count} still being arranged")
        in_discussion = total - secured - open_count
        if in_discussion > 0:
            status_parts.append(f"{in_discussion} in discussion")

        if status_parts:
            parts.append(f"({', '.join(status_parts)})")

        # Cost summary
        low = canvas.get("total_cost_low", 0)
        high = canvas.get("total_cost_high", 0)
        if low > 0 or high > 0:
            if low == high:
                parts.append(f"with an estimated cost of ${low:,.0f}")
            else:
                parts.append(f"with estimated costs ranging from ${low:,.0f} to ${high:,.0f}")

        return " ".join(parts) + "."

    def _format_by_phase(self, resources: List[Dict]) -> Dict[str, List[Dict]]:
        """Format resources grouped by phase."""
        by_phase = {}

        for phase in PhaseAlignment:
            phase_label = get_display_label("phase_display", phase.value)
            phase_resources = [
                self._format_resource_item(r)
                for r in resources
                if phase.value in r.get("phase_alignment", [])
            ]
            if phase_resources:
                by_phase[phase_label] = phase_resources

        return by_phase

    def _format_by_category(self, resources: List[Dict]) -> Dict[str, List[Dict]]:
        """Format resources grouped by category."""
        by_category = {}

        for r in resources:
            cat = r.get("category", "SERVICES")
            cat_label = get_display_label("category_display", cat)
            if cat_label not in by_category:
                by_category[cat_label] = []
            by_category[cat_label].append(self._format_resource_item(r))

        return by_category

    def _format_resource_item(self, resource: Dict) -> Dict:
        """Format a single resource for export display."""
        availability = get_display_label(
            "availability_display",
            resource.get("availability_status", "UNKNOWN")
        )
        cost_conf = get_display_label(
            "confidence_display",
            resource.get("cost_confidence", "UNKNOWN")
        )

        cost_str = ""
        low = resource.get("cost_estimate_low")
        high = resource.get("cost_estimate_high")
        if low is not None and high is not None:
            if low == high:
                cost_str = f"${low:,.0f}"
            else:
                cost_str = f"${low:,.0f} - ${high:,.0f}"
        elif low is not None:
            cost_str = f"${low:,.0f}"
        elif high is not None:
            cost_str = f"up to ${high:,.0f}"

        return {
            "name": resource.get("resource_name", "Unknown"),
            "category": get_display_label("category_display", resource.get("category", "SERVICES")),
            "availability": availability,
            "cost": cost_str,
            "cost_confidence": cost_conf,
            "criticality": get_display_label("criticality_display", resource.get("criticality", "UNKNOWN")),
        }

    def _format_cost_summary(self, canvas: Dict) -> Dict[str, Any]:
        """Format cost summary for export."""
        return {
            "total_low": canvas.get("total_cost_low", 0),
            "total_high": canvas.get("total_cost_high", 0),
            "by_phase": canvas.get("cost_by_phase", {}),
        }

    def _format_availability_summary(self, canvas: Dict, resources: List[Dict]) -> Dict[str, int]:
        """Format availability summary."""
        return {
            "secured": canvas.get("secured_count", 0),
            "in_discussion": sum(
                1 for r in resources
                if r.get("availability_status") == AvailabilityStatus.IN_DISCUSSION.value
            ),
            "unresolved": canvas.get("unresolved_count", 0),
            "total": len(resources),
        }

    def _format_appendix_rows(self, resources: List[Dict]) -> List[Dict]:
        """Format resources as table rows for appendix."""
        return [self._format_resource_item(r) for r in resources]

    def _render_markdown_appendix(self, data: Dict) -> str:
        """Render appendix in Markdown format."""
        lines = [
            "## Resource Requirements",
            "",
            data["summary"],
            "",
            "### Resource Inventory",
            "",
            "| Resource | Category | Status | Cost |",
            "|----------|----------|--------|------|",
        ]

        for row in data["appendix_rows"]:
            lines.append(
                f"| {row['name']} | {row['category']} | {row['availability']} | {row['cost'] or 'TBD'} |"
            )

        lines.extend([
            "",
            f"**Total Estimated Cost Range:** ${data['cost_summary']['total_low']:,.0f} - ${data['cost_summary']['total_high']:,.0f}",
            "",
        ])

        return "\n".join(lines)

    def _render_html_appendix(self, data: Dict) -> str:
        """Render appendix in HTML format."""
        rows_html = ""
        for row in data["appendix_rows"]:
            rows_html += f"""
            <tr>
                <td>{row['name']}</td>
                <td>{row['category']}</td>
                <td>{row['availability']}</td>
                <td>{row['cost'] or 'TBD'}</td>
            </tr>"""

        return f"""
        <section class="resource-appendix">
            <h2>Resource Requirements</h2>
            <p>{data['summary']}</p>
            <h3>Resource Inventory</h3>
            <table class="resource-table">
                <thead>
                    <tr>
                        <th>Resource</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <p class="cost-summary">
                <strong>Total Estimated Cost Range:</strong>
                ${data['cost_summary']['total_low']:,.0f} - ${data['cost_summary']['total_high']:,.0f}
            </p>
        </section>
        """

    def _render_text_appendix(self, data: Dict) -> str:
        """Render appendix in plain text format."""
        lines = [
            "RESOURCE REQUIREMENTS",
            "=" * 40,
            "",
            data["summary"],
            "",
            "Resource Inventory:",
            "-" * 40,
        ]

        for row in data["appendix_rows"]:
            lines.append(f"  {row['name']}")
            lines.append(f"    Category: {row['category']}")
            lines.append(f"    Status: {row['availability']}")
            lines.append(f"    Cost: {row['cost'] or 'TBD'}")
            lines.append("")

        lines.extend([
            "-" * 40,
            f"Total Estimated Cost Range: ${data['cost_summary']['total_low']:,.0f} - ${data['cost_summary']['total_high']:,.0f}",
        ])

        return "\n".join(lines)
