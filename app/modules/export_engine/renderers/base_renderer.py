"""
InDE MVP v5.1b.0 - Base Renderer

Abstract base class for all export format renderers.

2026 Yul Williams | InDEVerse, Incorporated
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Union, Any


class BaseRenderer(ABC):
    """
    Abstract base class for export format renderers.

    All renderers must implement:
    - render(): Convert styled ITD + template data to output format
    - content_type: MIME type of the output
    """

    @abstractmethod
    def render(
        self,
        styled_itd: Dict[str, Any],
        template_data: Optional[Dict[str, Any]] = None,
    ) -> Union[bytes, str]:
        """
        Render the styled ITD and optional template data.

        Args:
            styled_itd: The styled ITD document with layer ordering and style metadata
            template_data: Optional populated template fields

        Returns:
            Rendered content (str for text formats, bytes for binary)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def content_type(self) -> str:
        """
        Get the MIME content type for this renderer.

        Returns:
            MIME type string (e.g., "text/markdown", "application/pdf")
        """
        raise NotImplementedError

    def _get_pursuit_title(self, itd: Dict[str, Any]) -> str:
        """Extract pursuit title from ITD."""
        return itd.get("pursuit_title", "Innovation Thesis")

    def _get_style_display_name(self, itd: Dict[str, Any]) -> str:
        """Extract style display name from ITD metadata."""
        metadata = itd.get("style_metadata", {})
        return metadata.get("display_name", "Standard Narrative")

    def _get_generated_date(self) -> str:
        """Get current date formatted for display."""
        from datetime import datetime
        return datetime.now().strftime("%B %d, %Y")

    def _get_layer_content(self, layer: Dict[str, Any]) -> str:
        """Extract readable content from a layer."""
        if isinstance(layer, str):
            return layer

        # Try common content fields
        for key in ["content", "thesis_text", "narrative", "overall_reflection"]:
            if key in layer:
                value = layer[key]
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    return self._format_dict_content(value)

        # Handle specific layer structures
        if "acts" in layer:
            return self._format_acts(layer["acts"])
        if "moments" in layer:
            return self._format_moments(layer["moments"])
        if "horizons" in layer:
            return self._format_horizons(layer["horizons"])

        return str(layer)

    def _format_dict_content(self, d: Dict) -> str:
        """Format a dictionary as readable text."""
        parts = []
        for key, value in d.items():
            if isinstance(value, str):
                parts.append(f"**{key.replace('_', ' ').title()}:** {value}")
            elif isinstance(value, list):
                parts.append(f"**{key.replace('_', ' ').title()}:**")
                for item in value:
                    if isinstance(item, str):
                        parts.append(f"- {item}")
                    elif isinstance(item, dict):
                        parts.append(f"- {self._format_dict_content(item)}")
        return "\n".join(parts)

    def _format_acts(self, acts: list) -> str:
        """Format narrative arc acts."""
        parts = []
        for act in acts:
            title = act.get("title", act.get("act_type", "Act"))
            content = act.get("content", "")
            parts.append(f"### {title}\n\n{content}")
        return "\n\n".join(parts)

    def _format_moments(self, moments: list) -> str:
        """Format coaching moments."""
        parts = []
        for moment in moments:
            moment_type = moment.get("moment_type", "Moment")
            quote = moment.get("coach_quote", "")
            impact = moment.get("impact", "")
            parts.append(f"**{moment_type}**\n\n> {quote}")
            if impact:
                parts.append(f"\n*Impact: {impact}*")
        return "\n\n".join(parts)

    def _format_horizons(self, horizons: dict) -> str:
        """Format forward projection horizons."""
        parts = []
        horizon_names = {
            "day_90": "90-Day Horizon",
            "day_180": "180-Day Horizon",
            "day_365": "One-Year Horizon",
        }
        for key in ["day_90", "day_180", "day_365"]:
            horizon = horizons.get(key)
            if horizon:
                name = horizon_names.get(key, key)
                narrative = horizon.get("narrative", "")
                parts.append(f"### {name}\n\n{narrative}")

                actions = horizon.get("success_correlated_actions", [])
                if actions:
                    parts.append("\n**Recommended Actions:**")
                    for action in actions:
                        parts.append(f"- {action}")

        return "\n\n".join(parts)
