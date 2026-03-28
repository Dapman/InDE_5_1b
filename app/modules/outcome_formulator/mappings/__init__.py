"""
Outcome Scaffolding Mappings

InDE MVP v4.6.0 - The Outcome Engine

Contains field mapping definitions for each archetype:
  - lean_startup_mappings.py
  - design_thinking_mappings.py
  - stage_gate_mappings.py
  - triz_mappings.py
  - blue_ocean_mappings.py
  - incubation_mappings.py

Each mapping file exports a FIELD_MAPPINGS list of OutcomeFieldMapping instances.
"""

from .mapping_registry import (
    get_mappings_for_archetype,
    get_artifact_type_for_field,
)

__all__ = [
    "get_mappings_for_archetype",
    "get_artifact_type_for_field",
]
