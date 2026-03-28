"""
InDE v4.8 - Pattern Connections Compiler

Produces ITD Layer 5 (Pattern Connections).

Uses the ConnectionMapBuilder to assemble raw connection data, then
generates a narrative that makes the compounding effect of InDE's
intelligence infrastructure visible to the innovator.

The narrative is not a list of patterns. It is an explanation of how
the intelligence accumulated across pursuits, domains, and organizations
contributed to what this specific innovation became.

Language Sovereignty enforced. Methodology names not used.

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from .connection_map_builder import ConnectionMapBuilder
from .projection_llm_client import ProjectionLLMClient

logger = logging.getLogger("inde.projection.pattern_connections")

PATTERN_CONNECTIONS_SYSTEM_PROMPT = """
You are an analyst describing how an innovation guidance system's accumulated
intelligence contributed to a specific innovation pursuit.

You have been given a structured description of which intelligence patterns
influenced this pursuit, where those patterns came from, and how strongly they
correlated with the outcomes produced.

Your task is to write a Pattern Connections narrative - a section in the
Innovation Thesis Document that makes the compounding effect of this
intelligence infrastructure visible, in plain terms, to the innovator.

CRITICAL REQUIREMENTS:
- Write as if explaining to someone who built something remarkable and is
  now understanding the full scope of the intellectual infrastructure that
  supported them.
- DO NOT use methodology names (Lean Startup, Design Thinking, TRIZ,
  Blue Ocean Strategy, Stage-Gate, etc.) under any circumstances.
- DO NOT use the words: fear, afraid, failure, fail, risk, threat, danger,
  worry, problem, mistake, struggle, warn, dead end.
- DO use: pattern, connection, intelligence, insight, contribution, signal,
  learning, compound, converge, influence, shape.
- Express the compounding effect - not "the system used X" but "the
  accumulated intelligence from Y context shaped Z dimension of this pursuit."
- Be specific where the data supports it. Be appropriately general where it
  does not.
- The narrative should leave the innovator with a clear sense of:
  (1) what intelligence contributed to their journey
  (2) where it came from
  (3) why the output of their pursuit is more than what any individual
      session could have produced

Output JSON:
{
  "opening": "...",
  "within_pursuit_narrative": "...",
  "cross_pursuit_narrative": "...",
  "federation_narrative": "...",
  "synthesis": "..."
}

- opening: 2-3 sentences introducing the Pattern Connections section
- within_pursuit_narrative: 80-120 words on IML patterns within this pursuit
- cross_pursuit_narrative: 60-90 words on cross-pursuit connections
  (if no cross-pursuit data: acknowledge in 1 sentence, move on)
- federation_narrative: 60-80 words on IKF federation contributions
  (if federation not available: omit this key or set to null)
- synthesis: 2-3 sentences closing the section - the compounding effect
  made concrete for this specific pursuit
"""


class PatternConnectionsCompiler:
    """
    Produces ITD Layer 5: Pattern Connections.
    """

    def __init__(self, db, llm_gateway=None):
        """
        Initialize PatternConnectionsCompiler.

        Args:
            db: Database instance
            llm_gateway: Optional LLM Gateway for generation
        """
        self.db = db
        self.connection_map_builder = ConnectionMapBuilder(db=db)
        self.llm_client = ProjectionLLMClient(llm_gateway=llm_gateway)

    def compile(self, pursuit_id: str) -> dict:
        """
        Main entry point. Returns a complete Layer 5 dict for insertion
        into the .itd artifact.

        Args:
            pursuit_id: The pursuit to compile connections for

        Returns:
            Layer 5 dict with content, status, and metadata
        """
        try:
            logger.info(f"[PatternConnections] Compiling for pursuit: {pursuit_id}")

            connection_map = self.connection_map_builder.build(pursuit_id)
            narrative = self._generate_narrative(connection_map)

            layer_5 = {
                "content": {
                    "opening": narrative.get("opening", ""),
                    "within_pursuit": {
                        "narrative": narrative.get(
                            "within_pursuit_narrative", ""
                        ),
                        "pattern_count": connection_map.iml_pattern_count,
                        "strongest_pattern": (
                            connection_map.strongest_connection.pattern_description
                            if connection_map.strongest_connection
                            else None
                        ),
                    },
                    "cross_pursuit": {
                        "narrative": narrative.get(
                            "cross_pursuit_narrative", ""
                        ),
                        "connection_count": connection_map.cross_pursuit_count,
                    },
                    "cross_domain": {
                        "connection_count": connection_map.cross_domain_count,
                    },
                    "federation": (
                        {
                            "narrative": narrative.get(
                                "federation_narrative", ""
                            ),
                            "contribution_count": (
                                connection_map.ikf_contribution_count
                            ),
                        }
                        if connection_map.federation_available else None
                    ),
                    "synthesis": narrative.get("synthesis", ""),
                    "connection_metadata": {
                        "total_connections": len(connection_map.connections),
                        "iml_patterns": connection_map.iml_pattern_count,
                        "cross_pursuit": connection_map.cross_pursuit_count,
                        "cross_domain": connection_map.cross_domain_count,
                        "federation": connection_map.ikf_contribution_count,
                        "federation_available": connection_map.federation_available,
                    }
                },
                "status": "POPULATED_V4_8",
                "composition_version": "5.1b.0",
                "layer_name": "pattern_connections",
            }

            logger.info(f"[PatternConnections] Compiled successfully for {pursuit_id}")
            return layer_5

        except Exception as e:
            logger.error(
                f"[PatternConnections] Compilation failed for "
                f"pursuit {pursuit_id}: {e}"
            )
            return self._graceful_fallback()

    def _generate_narrative(self, connection_map) -> dict:
        """Generate LLM narrative from connection map data."""
        # Get top 5 connections by influence score
        top_connections = sorted(
            connection_map.connections,
            key=lambda x: x.influence_score,
            reverse=True
        )[:5]

        connection_details = [
            {
                'type': c.connection_type,
                'description': c.pattern_description,
                'phase': c.applied_at_phase,
                'influence': c.influence_score,
                'attribution': c.outcome_attribution,
            }
            for c in top_connections
        ]

        user_prompt = f"""
Generate the Pattern Connections narrative for an Innovation Thesis Document.

Connection Summary:
  Total IML patterns applied within this pursuit: {connection_map.iml_pattern_count}
  Cross-pursuit connections (shared patterns with other pursuits): {connection_map.cross_pursuit_count}
  Cross-domain connections (patterns from adjacent domains): {connection_map.cross_domain_count}
  IKF federation contributions: {connection_map.ikf_contribution_count}
  Federation available: {connection_map.federation_available}

Strongest connection: {
    connection_map.strongest_connection.pattern_description
    if connection_map.strongest_connection else 'none identified'
}

Connection details (top 5 by influence score):
{connection_details}

If IML pattern count is 0, write the within_pursuit_narrative acknowledging
that the coaching intelligence is still being accumulated for this pursuit,
and that patterns will compound as more pursuits complete. Do not fabricate
pattern descriptions.
"""
        return self.llm_client.generate(
            system_prompt=PATTERN_CONNECTIONS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=700,
            parse_json=True,
            sovereignty_validate=True,
        )

    def _graceful_fallback(self) -> dict:
        """Returns a structurally valid Layer 5 when compilation fails."""
        return {
            "content": {
                "opening": (
                    "The intelligence that shaped this pursuit ran deeper "
                    "than any single coaching conversation."
                ),
                "within_pursuit": {
                    "narrative": (
                        "The patterns from this pursuit's coaching history "
                        "are being assembled into the connection map."
                    ),
                    "pattern_count": 0,
                    "strongest_pattern": None,
                },
                "cross_pursuit": {"narrative": "", "connection_count": 0},
                "cross_domain": {"connection_count": 0},
                "federation": None,
                "synthesis": (
                    "This pursuit contributes its own patterns to the "
                    "growing intelligence of the system - adding to what "
                    "future innovations will draw on."
                ),
                "connection_metadata": {
                    "total_connections": 0,
                    "iml_patterns": 0,
                    "cross_pursuit": 0,
                    "cross_domain": 0,
                    "federation": 0,
                    "federation_available": False,
                }
            },
            "status": "POPULATED_V4_8_FALLBACK",
            "composition_version": "5.1b.0",
            "layer_name": "pattern_connections",
        }
