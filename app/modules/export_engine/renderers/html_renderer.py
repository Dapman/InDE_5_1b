"""
InDE MVP v5.1b.0 - HTML Renderer

Renders styled ITD to self-contained HTML with inline CSS.
Consistent with InDE's v4.3 organic visual identity.
Print-ready layout with page-break hints.

2026 Yul Williams | InDEVerse, Incorporated
"""

from typing import Dict, Optional, Any
import html
from .base_renderer import BaseRenderer


# HTML Template with inline CSS - v4.3 organic visual identity
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{pursuit_name} — Innovation Thesis</title>
  <style>
    /* InDE v4.3 organic visual identity */
    :root {{
      --color-primary: #2d4a3e;
      --color-accent: #7fb069;
      --color-accent-light: #c9ddb8;
      --color-text: #1a1a2e;
      --color-text-secondary: #4a4a5c;
      --color-text-muted: #707080;
      --color-bg: #fafaf7;
      --color-surface: #ffffff;
      --color-border: #e0e0d8;
      --color-partial: #8a6c3d;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Georgia', 'Times New Roman', serif;
      max-width: 860px;
      margin: 0 auto;
      padding: 40px;
      color: var(--color-text);
      background: var(--color-bg);
      line-height: 1.7;
    }}

    h1 {{
      color: var(--color-primary);
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
      border-bottom: 3px solid var(--color-accent);
      padding-bottom: 12px;
    }}

    h2 {{
      color: var(--color-primary);
      font-size: 20px;
      font-weight: 600;
      margin: 32px 0 16px 0;
    }}

    h3 {{
      color: var(--color-text-secondary);
      font-size: 16px;
      font-weight: 600;
      margin: 20px 0 12px 0;
    }}

    p {{
      margin-bottom: 16px;
    }}

    .meta {{
      color: var(--color-text-muted);
      font-size: 14px;
      font-style: italic;
      margin-bottom: 24px;
    }}

    .style-opening {{
      font-size: 17px;
      line-height: 1.8;
      color: var(--color-text);
      padding: 20px 0;
      border-bottom: 1px solid var(--color-border);
      margin-bottom: 32px;
    }}

    .layer-section {{
      margin: 32px 0;
      padding: 24px;
      background: var(--color-surface);
      border-radius: 8px;
      border-left: 4px solid var(--color-accent);
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}

    .layer-section h2 {{
      margin-top: 0;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--color-border);
    }}

    .template-section {{
      background: #f0f4ec;
      border-left: 4px solid var(--color-accent-light);
    }}

    .thesis-text {{
      font-size: 18px;
      font-style: italic;
      line-height: 1.8;
      color: var(--color-text);
    }}

    .confidence-badge {{
      display: inline-block;
      margin-top: 12px;
      padding: 4px 12px;
      background: var(--color-accent-light);
      border-radius: 4px;
      font-size: 13px;
      font-family: system-ui, sans-serif;
    }}

    blockquote {{
      margin: 16px 0;
      padding: 12px 20px;
      border-left: 3px solid var(--color-accent);
      font-style: italic;
      color: var(--color-text-secondary);
      background: rgba(127, 176, 105, 0.05);
    }}

    .moment {{
      padding: 16px;
      background: rgba(0,0,0,0.02);
      border-radius: 8px;
      margin-bottom: 16px;
    }}

    .moment-type {{
      display: inline-block;
      padding: 2px 10px;
      background: var(--color-accent);
      color: white;
      font-size: 12px;
      font-weight: 600;
      border-radius: 4px;
      text-transform: uppercase;
      margin-bottom: 8px;
      font-family: system-ui, sans-serif;
    }}

    .moment-impact {{
      font-size: 14px;
      color: var(--color-text-muted);
      margin-top: 8px;
    }}

    .horizon {{
      padding: 16px;
      background: rgba(0,0,0,0.02);
      border-radius: 8px;
      border-left: 4px solid var(--color-accent);
      margin-bottom: 16px;
    }}

    .horizon h3 {{
      margin-top: 0;
      color: var(--color-primary);
    }}

    .horizon-confidence {{
      font-size: 13px;
      color: var(--color-text-muted);
      font-family: system-ui, sans-serif;
    }}

    .actions-list {{
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--color-border);
    }}

    .actions-list h4 {{
      font-size: 13px;
      color: var(--color-text-muted);
      margin-bottom: 8px;
    }}

    ul {{
      margin: 8px 0;
      padding-left: 24px;
    }}

    li {{
      margin-bottom: 4px;
    }}

    .partial-field {{
      color: var(--color-partial);
      font-style: italic;
      padding: 12px;
      background: rgba(138, 108, 61, 0.08);
      border-radius: 4px;
    }}

    .partial-field::before {{
      content: "⚠ ";
    }}

    .footer {{
      margin-top: 60px;
      padding-top: 20px;
      border-top: 1px solid var(--color-border);
      font-size: 13px;
      color: var(--color-text-muted);
      text-align: center;
    }}

    @media print {{
      body {{
        padding: 20px;
      }}
      .layer-section {{
        break-inside: avoid;
        box-shadow: none;
        border: 1px solid var(--color-border);
      }}
    }}

    @page {{
      margin: 2cm;
      @bottom-center {{
        content: "Generated by InDE — Innovation Thesis Intelligence | Page " counter(page);
      }}
    }}
  </style>
</head>
<body>
  <h1>{pursuit_name}</h1>
  <p class="meta">{style_display_name} | {generated_date}</p>

  {style_opening_html}

  {layers_html}

  {template_html}

  <div class="footer">
    Generated by InDE — Innovation Thesis Intelligence
  </div>
</body>
</html>"""


class HTMLRenderer(BaseRenderer):
    """
    Renders styled ITD to self-contained HTML.

    Features:
    - All CSS inline, zero external dependencies
    - v4.3 organic visual identity
    - Print-ready layout with page-break hints
    - Template sections as collapsible blocks
    """

    @property
    def content_type(self) -> str:
        return "text/html"

    def render(
        self,
        styled_itd: Dict[str, Any],
        template_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render the styled ITD as HTML."""
        pursuit_name = self._escape(self._get_pursuit_title(styled_itd))
        style_display_name = self._escape(self._get_style_display_name(styled_itd))
        generated_date = self._get_generated_date()

        # Style opening
        style_opening = styled_itd.get("style_opening", "")
        style_opening_html = ""
        if style_opening:
            style_opening_html = f'<div class="style-opening">{self._escape(style_opening)}</div>'

        # Render layers
        layers_html = self._render_layers(styled_itd)

        # Render template section
        template_html = ""
        if template_data:
            template_html = self._render_template(template_data)

        return HTML_TEMPLATE.format(
            pursuit_name=pursuit_name,
            style_display_name=style_display_name,
            generated_date=generated_date,
            style_opening_html=style_opening_html,
            layers_html=layers_html,
            template_html=template_html,
        )

    def _escape(self, text: str) -> str:
        """HTML-escape text."""
        return html.escape(str(text)) if text else ""

    def _render_layers(self, styled_itd: Dict[str, Any]) -> str:
        """Render all ITD layers in style order."""
        layer_ordering = styled_itd.get(
            "layer_ordering",
            ["thesis_statement", "narrative_arc", "evidence_architecture",
             "coachs_perspective", "pattern_connections", "forward_projection"]
        )

        layer_titles = {
            "thesis_statement": "Your Innovation Thesis",
            "evidence_architecture": "Evidence Architecture",
            "narrative_arc": "Narrative Arc",
            "coachs_perspective": "Coach's Perspective",
            "pattern_connections": "Pattern Connections",
            "forward_projection": "Forward Projection",
        }

        parts = []
        for layer_key in layer_ordering:
            layer = styled_itd.get(layer_key)
            if layer:
                title = layer_titles.get(layer_key, layer_key.replace("_", " ").title())
                content_html = self._render_layer(layer_key, layer)
                parts.append(f'''
                <section class="layer-section">
                    <h2>{self._escape(title)}</h2>
                    {content_html}
                </section>
                ''')

        return "\n".join(parts)

    def _render_layer(self, layer_key: str, layer: Dict[str, Any]) -> str:
        """Render a specific layer to HTML."""
        if layer_key == "thesis_statement":
            return self._render_thesis_html(layer)
        elif layer_key == "evidence_architecture":
            return self._render_evidence_html(layer)
        elif layer_key == "narrative_arc":
            return self._render_narrative_html(layer)
        elif layer_key == "coachs_perspective":
            return self._render_coach_html(layer)
        elif layer_key == "pattern_connections":
            return self._render_patterns_html(layer)
        elif layer_key == "forward_projection":
            return self._render_projection_html(layer)
        else:
            return f"<p>{self._escape(self._get_layer_content(layer))}</p>"

    def _render_thesis_html(self, layer: Dict[str, Any]) -> str:
        """Render thesis statement as HTML."""
        thesis_text = self._escape(layer.get("thesis_text", ""))
        html_parts = [f'<p class="thesis-text">{thesis_text}</p>']

        confidence = layer.get("confidence_score", 0)
        if confidence > 0:
            html_parts.append(f'<span class="confidence-badge">Confidence: {confidence:.0%}</span>')

        return "\n".join(html_parts)

    def _render_evidence_html(self, layer: Dict[str, Any]) -> str:
        """Render evidence architecture as HTML."""
        parts = []

        # Confidence journey
        initial = layer.get("initial_confidence", 0)
        final = layer.get("final_confidence", 0)
        delta = layer.get("confidence_delta", 0)

        if initial > 0 or final > 0:
            parts.append("<h3>Confidence Journey</h3>")
            parts.append(f"""
            <p>
                <strong>Started:</strong> {initial:.0%} |
                <strong>Ended:</strong> {final:.0%} |
                <strong>Change:</strong> {'+' if delta > 0 else ''}{delta:.0%}
            </p>
            """)

        # Pivots
        pivots = layer.get("pivots", [])
        if pivots:
            parts.append("<h3>Direction Changes</h3>")
            for pivot in pivots:
                pivot_type = self._escape(pivot.get("pivot_type", "Pivot"))
                description = self._escape(pivot.get("description", ""))
                parts.append(f'<p><strong>{pivot_type}:</strong> {description}</p>')

        return "\n".join(parts)

    def _render_narrative_html(self, layer: Dict[str, Any]) -> str:
        """Render narrative arc as HTML."""
        parts = []

        opening = layer.get("opening_hook", "")
        if opening:
            parts.append(f'<p><em>{self._escape(opening)}</em></p>')

        acts = layer.get("acts", [])
        for act in acts:
            title = self._escape(act.get("title", act.get("act_type", "Act")))
            content = self._escape(act.get("content", ""))
            parts.append(f"<h3>{title}</h3>")
            parts.append(f"<p>{content}</p>")

        closing = layer.get("closing_reflection", "")
        if closing:
            parts.append(f'<p><em>{self._escape(closing)}</em></p>')

        return "\n".join(parts)

    def _render_coach_html(self, layer: Dict[str, Any]) -> str:
        """Render coach's perspective as HTML."""
        parts = []

        reflection = layer.get("overall_reflection", "")
        if reflection:
            parts.append(f"<p>{self._escape(reflection)}</p>")

        moments = layer.get("moments", [])
        for moment in moments:
            moment_type = self._escape(moment.get("moment_type", "Moment"))
            quote = self._escape(moment.get("coach_quote", ""))
            impact = self._escape(moment.get("impact", ""))

            parts.append(f'''
            <div class="moment">
                <span class="moment-type">{moment_type}</span>
                <blockquote>{quote}</blockquote>
                {"<p class='moment-impact'>Impact: " + impact + "</p>" if impact else ""}
            </div>
            ''')

        return "\n".join(parts)

    def _render_patterns_html(self, layer: Dict[str, Any]) -> str:
        """Render pattern connections as HTML."""
        parts = []
        content = layer.get("content", layer)

        opening = content.get("opening", "")
        if opening:
            parts.append(f"<p>{self._escape(opening)}</p>")

        within = content.get("within_pursuit", {})
        if within and within.get("narrative"):
            parts.append("<h3>Within This Pursuit</h3>")
            parts.append(f"<p>{self._escape(within['narrative'])}</p>")

        cross = content.get("cross_pursuit", {})
        if cross and cross.get("narrative"):
            parts.append("<h3>Connections to Other Pursuits</h3>")
            parts.append(f"<p>{self._escape(cross['narrative'])}</p>")

        synthesis = content.get("synthesis", "")
        if synthesis:
            parts.append(f'<p><em>{self._escape(synthesis)}</em></p>')

        return "\n".join(parts)

    def _render_projection_html(self, layer: Dict[str, Any]) -> str:
        """Render forward projection as HTML."""
        parts = []
        content = layer.get("content", layer)

        synthesis = content.get("synthesis_statement", "")
        if synthesis:
            parts.append(f"<p>{self._escape(synthesis)}</p>")

        horizons = content.get("horizons", {})
        horizon_names = {
            "day_90": "90-Day Horizon",
            "day_180": "180-Day Horizon",
            "day_365": "One-Year Horizon",
        }

        for key in ["day_90", "day_180", "day_365"]:
            horizon = horizons.get(key)
            if horizon:
                name = horizon_names.get(key, key)
                narrative = self._escape(horizon.get("narrative", ""))
                confidence = horizon.get("confidence", 0)
                actions = horizon.get("success_correlated_actions", [])

                parts.append(f'''
                <div class="horizon">
                    <h3>{name}</h3>
                    <p>{narrative}</p>
                    {"<p class='horizon-confidence'>Confidence: " + f"{confidence:.0%}" + "</p>" if confidence > 0 else ""}
                    {"<div class='actions-list'><h4>Recommended Actions:</h4><ul>" + "".join(f"<li>{self._escape(a)}</li>" for a in actions) + "</ul></div>" if actions else ""}
                </div>
                ''')

        return "\n".join(parts)

    def _render_template(self, template_data: Dict[str, Any]) -> str:
        """Render template section as HTML."""
        parts = ['<section class="layer-section template-section">']
        parts.append('<h2>Supporting Documentation</h2>')

        for field_name, value in template_data.items():
            display_name = field_name.replace("_", " ").title()
            parts.append(f"<h3>{self._escape(display_name)}</h3>")

            if value and str(value).startswith("[") and str(value).endswith("]"):
                # Partial field
                parts.append(f'<p class="partial-field">{self._escape(value[1:-1])}</p>')
            else:
                parts.append(f"<p>{self._escape(str(value) if value else 'Not available')}</p>")

        parts.append("</section>")
        return "\n".join(parts)
