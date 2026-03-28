"""
Outcome Scaffolding Mapping Registry

InDE MVP v4.6.0 - The Outcome Engine

Loads and serves outcome field mappings for each archetype.
The OutcomeScaffoldingMapper calls get_mappings_for_archetype() on each event.

No business logic here - only loading and caching of mapping definitions.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# Lazy-loaded archetype mapping cache
_MAPPING_CACHE: dict = {}


def get_mappings_for_archetype(archetype: str) -> List:
    """Return all OutcomeFieldMapping instances for the given archetype."""
    if archetype not in _MAPPING_CACHE:
        _MAPPING_CACHE[archetype] = _load_mappings(archetype)
    return _MAPPING_CACHE[archetype]


def get_artifact_type_for_field(archetype: str, field_key: str) -> str:
    """
    Return the artifact_type that owns a given field_key for an archetype.
    """
    mappings = get_mappings_for_archetype(archetype)
    for m in mappings:
        if m.field_key == field_key:
            return m.artifact_type
    # Return a default if not found
    logger.warning(f"No mapping found for {archetype}.{field_key}")
    return "unknown"


def _load_mappings(archetype: str) -> List:
    """Import and return the FIELD_MAPPINGS list for the given archetype."""
    archetype_modules = {
        "lean_startup": "lean_startup_mappings",
        "design_thinking": "design_thinking_mappings",
        "stage_gate": "stage_gate_mappings",
        "triz": "triz_mappings",
        "blue_ocean": "blue_ocean_mappings",
        "incubation": "incubation_mappings",
    }
    module_name = archetype_modules.get(archetype)
    if not module_name:
        logger.warning(f"No mappings defined for archetype: {archetype}")
        return []
    try:
        import importlib
        module = importlib.import_module(
            f"modules.outcome_formulator.mappings.{module_name}"
        )
        return module.FIELD_MAPPINGS
    except ImportError as e:
        logger.error(f"Failed to load mappings for {archetype}: {e}")
        return []
