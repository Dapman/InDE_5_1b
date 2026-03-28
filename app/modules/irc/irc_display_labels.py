"""
InDE MVP v5.1b.0 - IRC Display Labels

Display Label Registry entries for the Innovation Resource Canvas module.
All innovator-facing labels use plain language — no methodology terminology,
no internal field names.

2026 Yul Williams | InDEVerse, Incorporated
"""

# =============================================================================
# IRC DISPLAY LABELS — INNOVATOR-FACING
# =============================================================================

IRC_DISPLAY_LABELS = {
    # Resource Category — innovator-facing
    "category_display": {
        "HUMAN_CAPITAL": "People & Expertise",
        "CAPITAL_EQUIPMENT": "Tools & Equipment",
        "DATA_AND_IP": "Data & Knowledge",
        "SERVICES": "External Services",
        "FINANCIAL": "Funding & Capital",
    },

    # Availability Status — innovator-facing
    "availability_display": {
        "SECURED": "In Place",
        "IN_DISCUSSION": "Being Arranged",
        "UNRESOLVED": "Still Open",
        "UNKNOWN": "Not Yet Explored",
    },

    # Cost Confidence — innovator-facing
    "confidence_display": {
        "KNOWN": "Confirmed Figure",
        "ESTIMATED": "Working Estimate",
        "ROUGH_ORDER": "Rough Order of Magnitude",
        "UNKNOWN": "Not Yet Estimated",
    },

    # Duration Type — innovator-facing
    "duration_display": {
        "ONE_TIME": "One-Time",
        "RECURRING": "Ongoing",
        "SUSTAINED": "Throughout",
        "UNKNOWN": "To Be Determined",
    },

    # Criticality — innovator-facing
    "criticality_display": {
        "ESSENTIAL": "Essential",
        "IMPORTANT": "Important",
        "HELPFUL": "Helpful",
        "UNKNOWN": "To Be Assessed",
    },

    # Phase Alignment — innovator-facing
    "phase_display": {
        "PITCH": "Getting Started",
        "DE_RISK": "Testing & Validation",
        "DEPLOY": "Building & Launching",
        "ACROSS_ALL": "Throughout",
    },

    # IRC Status — innovator-facing (for status indicator)
    "irc_status_display": {
        "NO_CANVAS": "No resource picture yet",
        "BUILDING": "Building your resource picture",
        "CANVAS_READY": "Resource picture ready",
    },

    # Cost Type — innovator-facing
    "cost_type_display": {
        "FIXED": "Fixed Cost",
        "VARIABLE": "Variable Cost",
        "ONE_TIME": "One-Time Cost",
        "RECURRING": "Recurring Cost",
        "UNKNOWN": "Cost Type Unknown",
    },
}


def get_display_label(category: str, internal_value: str) -> str:
    """
    Get the innovator-facing display label for an internal value.

    Args:
        category: The label category (e.g., "category_display", "availability_display")
        internal_value: The internal enum value (e.g., "HUMAN_CAPITAL", "SECURED")

    Returns:
        The display label string, or the internal value if not found
    """
    category_labels = IRC_DISPLAY_LABELS.get(category, {})
    return category_labels.get(internal_value, internal_value)


def get_all_display_labels() -> dict:
    """Return all IRC display labels for API exposure."""
    return IRC_DISPLAY_LABELS.copy()
