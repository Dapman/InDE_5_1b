"""
InDE v4.8 - Transparency Prompt Library

System and user prompts for the Methodology Transparency Layer narrative.
This is the one place in InDE where methodology structure is described -
but even here, it is described analytically with no branded framework names.

Permitted analytical descriptions:
  - "a discovery-and-validation approach"        (not "Lean Startup")
  - "a human-centered design pattern"            (not "Design Thinking")
  - "a contradiction-resolution approach"        (not "TRIZ")
  - "a stage-and-review structure"               (not "Stage-Gate" / "PIM")
  - "a value-innovation approach"                (not "Blue Ocean Strategy")
  - "a hypothesis-driven incubation pattern"     (not "Incubation methodology")

Language Sovereignty applies to all generated content.

2026 Yul Williams | InDEVerse, Incorporated
"""

TRANSPARENCY_SYSTEM_PROMPT = """
You are an analytical writer preparing the optional Methodology Transparency
section of an Innovation Thesis Document. This section is only shown to
innovators with expert or advanced experience designation.

Your task is to explain, in analytical terms, how the coaching orchestration
logic adapted to this specific pursuit - which methodology families it drew on,
where it blended approaches, and how it calibrated to pursuit conditions.

CRITICAL REQUIREMENTS:
- NEVER use branded methodology names: Lean Startup, Design Thinking, TRIZ,
  Blue Ocean Strategy, Stage-Gate, PIM, IDEO, etc.
- ALWAYS use analytical descriptions:
    "a discovery-and-validation approach" (not "Lean Startup")
    "a human-centered design pattern" (not "Design Thinking")
    "a contradiction-resolution approach" (not "TRIZ")
    "a stage-and-review structure" (not "Stage-Gate")
    "a value-innovation approach" (not "Blue Ocean")
    "a hypothesis-driven incubation pattern" (not "Incubation")
- Write from a position of intellectual analysis, not evaluation or judgment
- Write in past tense - describe what occurred, not what should have occurred
- DO NOT use the words: fear, afraid, failure, fail, risk, threat, danger,
  worry, struggle, problem, mistake, warn.
- The reader is a sophisticated innovator who wants to understand the
  orchestration logic, not be coached further. Write accordingly.
- 200-300 words total. Structured but not formulaic.

Output JSON:
{
  "orchestration_summary": "...",
  "methodology_influences": [
    {
      "approach_description": "...",
      "where_applied": "...",
      "why_selected": "..."
    }
  ],
  "blending_notes": "...",
  "adaptation_narrative": "..."
}

orchestration_summary: 2 sentences - the overall orchestration approach for this pursuit
methodology_influences: 1-4 entries describing each methodology family applied
  - approach_description: the analytical name (not brand name)
  - where_applied: which pursuit phase or dimension
  - why_selected: what pursuit condition triggered this approach
blending_notes: 1-2 sentences on where approaches were blended (if applicable)
adaptation_narrative: 1-2 sentences on how the orchestration logic adapted
  over the course of the pursuit
"""

# Analytical methodology mappings for data translation
# These map internal methodology family codes to permitted analytical descriptions
METHODOLOGY_ANALYTICAL_MAPPINGS = {
    "lean": "a discovery-and-validation approach",
    "lean_startup": "a discovery-and-validation approach",
    "design_thinking": "a human-centered design pattern",
    "human_centered": "a human-centered design pattern",
    "triz": "a contradiction-resolution approach",
    "contradiction": "a contradiction-resolution approach",
    "stage_gate": "a stage-and-review structure",
    "pim": "a stage-and-review structure",
    "blue_ocean": "a value-innovation approach",
    "value_innovation": "a value-innovation approach",
    "incubation": "a hypothesis-driven incubation pattern",
    "hypothesis_driven": "a hypothesis-driven incubation pattern",
    "agile": "an iterative development approach",
    "iterative": "an iterative development approach",
    "systems_thinking": "a systems-level analysis pattern",
    "systems": "a systems-level analysis pattern",
}


def translate_methodology_family(family_code: str) -> str:
    """
    Translate internal methodology family code to analytical description.

    Args:
        family_code: Internal methodology family identifier

    Returns:
        Analytical description safe for Language Sovereignty
    """
    normalized = family_code.lower().replace("-", "_").replace(" ", "_")
    return METHODOLOGY_ANALYTICAL_MAPPINGS.get(
        normalized,
        f"a structured coaching approach ({family_code})"
    )
