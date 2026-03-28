"""
Innovation Health Card Renderer

InDE MVP v4.5.0 — The Engagement Engine

Transforms a computed InnovationHealthCard into a JSON payload for frontend
consumption. The renderer adds visual metadata (growth stage icon, dimension
color hints) that the React component uses for rendering.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""


class HealthCardRenderer:
    """Renders an InnovationHealthCard into a frontend-ready JSON payload."""

    # Growth stage visual metadata
    STAGE_VISUALS = {
        "seed":     {"icon": "seed",     "accent": "#8B7355"},
        "roots":    {"icon": "roots",    "accent": "#6B8E23"},
        "stem":     {"icon": "stem",     "accent": "#3CB371"},
        "branches": {"icon": "branches", "accent": "#2E8B57"},
        "canopy":   {"icon": "canopy",   "accent": "#228B22"},
    }

    # Dimension visual metadata
    DIMENSION_VISUALS = {
        "clarity":    {"icon": "eye",       "color": "#60A5FA"},
        "resilience": {"icon": "shield",    "color": "#F59E0B"},
        "evidence":   {"icon": "beaker",    "color": "#10B981"},
        "direction":  {"icon": "compass",   "color": "#8B5CF6"},
        "momentum":   {"icon": "lightning", "color": "#EC4899"},
    }

    def render(self, health_card) -> dict:
        """
        Convert an InnovationHealthCard to a JSON-serializable dict.

        Args:
            health_card: InnovationHealthCard dataclass instance

        Returns:
            dict ready for JSON serialization and frontend consumption
        """
        stage_visual = self.STAGE_VISUALS.get(
            health_card.growth_stage,
            self.STAGE_VISUALS["seed"]
        )

        return {
            "pursuit_id": health_card.pursuit_id,
            "growth_stage": health_card.growth_stage,
            "growth_stage_label": health_card.growth_stage_label,
            "growth_stage_icon": stage_visual["icon"],
            "growth_stage_accent": stage_visual["accent"],
            "summary": health_card.summary_sentence,
            "next_hint": health_card.next_growth_hint,
            "dimensions": [
                {
                    "key": d.key,
                    "label": d.label,
                    "score": d.score,
                    "description": d.description,
                    "icon": self.DIMENSION_VISUALS.get(d.key, {}).get("icon", "circle"),
                    "color": self.DIMENSION_VISUALS.get(d.key, {}).get("color", "#6B7280"),
                }
                for d in health_card.dimensions
            ],
            "computed_at": health_card.computed_at,
        }

    def render_minimal(self, health_card) -> dict:
        """
        Render a minimal version for novice users (no dimension scores).

        Args:
            health_card: InnovationHealthCard dataclass instance

        Returns:
            dict with only growth stage, summary, and hint (no dimension details)
        """
        stage_visual = self.STAGE_VISUALS.get(
            health_card.growth_stage,
            self.STAGE_VISUALS["seed"]
        )

        return {
            "pursuit_id": health_card.pursuit_id,
            "growth_stage": health_card.growth_stage,
            "growth_stage_label": health_card.growth_stage_label,
            "growth_stage_icon": stage_visual["icon"],
            "growth_stage_accent": stage_visual["accent"],
            "summary": health_card.summary_sentence,
            "next_hint": health_card.next_growth_hint,
            "computed_at": health_card.computed_at,
        }
