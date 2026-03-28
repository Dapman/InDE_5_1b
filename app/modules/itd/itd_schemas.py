"""
InDE MVP v5.1b.0 - ITD Composition Engine Schemas

Data classes for the Innovation Thesis Document (ITD) structure.
The ITD is a 6-layer document that tells the story of an innovation journey.

Layer Architecture:
1. Thesis Statement - Core innovation narrative synthesis
2. Evidence Architecture - Confidence trajectory and pivot record
3. Narrative Arc - Archetype-structured story in 5 acts
4. Coach's Perspective - Curated coaching moments and quotes
5. Pattern Connections - IML/IKF influence map (NEW in v4.9)
6. Forward Projection - 90/180/365-day trajectory analysis (NEW in v4.9)

Optional Section:
- Methodology Transparency - Expert-gated coaching provenance (NEW in v4.9)

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class ITDLayerType(str, Enum):
    """The six layers of an Innovation Thesis Document."""
    THESIS_STATEMENT = "thesis_statement"
    EVIDENCE_ARCHITECTURE = "evidence_architecture"
    NARRATIVE_ARC = "narrative_arc"
    COACHS_PERSPECTIVE = "coachs_perspective"
    PATTERN_CONNECTIONS = "pattern_connections"  # NEW in v4.9
    FORWARD_PROJECTION = "forward_projection"  # NEW in v4.9
    # Deprecated layer names (for backward compatibility)
    METRICS_DASHBOARD = "metrics_dashboard"  # Legacy - maps to PATTERN_CONNECTIONS
    FUTURE_PATHWAYS = "future_pathways"  # Legacy - maps to FORWARD_PROJECTION


class ITDGenerationStatus(str, Enum):
    """Status of ITD generation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some layers completed


class NarrativeActType(str, Enum):
    """The five acts of the narrative arc."""
    INCEPTION = "inception"
    EXPLORATION = "exploration"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"
    RESOLUTION = "resolution"


# =============================================================================
# LAYER 1: THESIS STATEMENT
# =============================================================================

@dataclass
class ThesisStatementLayer:
    """
    Layer 1: The core thesis statement synthesizing vision, concerns, and archetype.

    Output: A single, compelling paragraph that captures the essence of the innovation.
    """
    # The synthesized thesis (2-3 sentences)
    thesis_text: str = ""

    # Component sources
    vision_summary: str = ""
    concerns_summary: str = ""
    archetype_context: str = ""

    # Generation metadata
    generated_at: Optional[datetime] = None
    token_budget_used: int = 0
    confidence_score: float = 0.0


# =============================================================================
# LAYER 2: EVIDENCE ARCHITECTURE
# =============================================================================

@dataclass
class ConfidenceDataPoint:
    """A single point in the confidence trajectory."""
    timestamp: datetime = None
    element_key: str = ""
    confidence: float = 0.0
    event_type: str = ""  # e.g., "vision_artifact_finalized", "hypothesis_validated"


@dataclass
class PivotRecord:
    """A recorded pivot or significant direction change."""
    timestamp: datetime = None
    pivot_type: str = ""  # "major", "minor", "course_correction"
    description: str = ""
    trigger: str = ""  # What caused the pivot
    outcome: str = ""  # What changed as a result


@dataclass
class EvidenceArchitectureLayer:
    """
    Layer 2: Confidence trajectory and pivot record.

    Captures how confidence evolved and where pivots occurred.
    """
    # Confidence trajectory (time-series data)
    confidence_trajectory: List[ConfidenceDataPoint] = field(default_factory=list)

    # Pivot record
    pivots: List[PivotRecord] = field(default_factory=list)

    # Summary statistics
    initial_confidence: float = 0.0
    final_confidence: float = 0.0
    confidence_delta: float = 0.0
    total_pivots: int = 0

    # Generation metadata
    generated_at: Optional[datetime] = None

    # v4.10: Resource landscape from IRC (optional, non-breaking if absent)
    resource_landscape: Optional[Dict[str, Any]] = None


# =============================================================================
# LAYER 3: NARRATIVE ARC
# =============================================================================

@dataclass
class NarrativeAct:
    """A single act in the 5-act narrative structure."""
    act_type: NarrativeActType = NarrativeActType.INCEPTION
    title: str = ""
    content: str = ""  # The narrative text for this act
    key_moments: List[str] = field(default_factory=list)
    duration_days: int = 0


@dataclass
class NarrativeArcLayer:
    """
    Layer 3: Archetype-structured story in 5 acts.

    Tells the innovation story using methodology-appropriate narrative structure.
    """
    # The five acts
    acts: List[NarrativeAct] = field(default_factory=list)

    # Archetype influence
    archetype: str = ""  # e.g., "lean_startup", "design_thinking"
    narrative_style: str = ""  # The narrative voice/approach

    # Summary
    opening_hook: str = ""  # The compelling opening
    closing_reflection: str = ""  # The final takeaway

    # Generation metadata
    generated_at: Optional[datetime] = None
    token_budget_used: int = 0


# =============================================================================
# LAYER 4: COACH'S PERSPECTIVE
# =============================================================================

@dataclass
class CoachingMoment:
    """A significant coaching moment to highlight."""
    timestamp: datetime = None
    moment_type: str = ""  # "breakthrough", "reframe", "challenge", "encouragement"
    coach_quote: str = ""  # The coach's actual words
    innovator_response: str = ""  # How the innovator responded
    impact: str = ""  # What changed as a result
    session_context: str = ""  # Brief context


@dataclass
class CoachsPerspectiveLayer:
    """
    Layer 4: Curated coaching moments with thematic quotes.

    Surfaces the most impactful coaching interactions.
    """
    # Selected coaching moments (3-5 highlights)
    moments: List[CoachingMoment] = field(default_factory=list)

    # Thematic summary
    coaching_themes: List[str] = field(default_factory=list)
    overall_reflection: str = ""  # Coach's summary perspective

    # Statistics
    total_sessions: int = 0
    total_messages: int = 0
    moments_considered: int = 0

    # Generation metadata
    generated_at: Optional[datetime] = None


# =============================================================================
# LAYER 5: PATTERN CONNECTIONS (NEW in v4.9)
# =============================================================================

@dataclass
class PatternConnectionsLayer:
    """
    Layer 5: Pattern Connections - IML/IKF influence map.

    Shows how accumulated intelligence from IML (Intelligence Memory Layer)
    and IKF (Intelligence Knowledge Federation) contributed to this pursuit.
    """
    # Content sections
    opening: str = ""
    within_pursuit: Dict[str, Any] = field(default_factory=dict)
    cross_pursuit: Dict[str, Any] = field(default_factory=dict)
    cross_domain: Dict[str, Any] = field(default_factory=dict)
    federation: Optional[Dict[str, Any]] = None
    synthesis: str = ""

    # Metadata
    connection_metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "NOT_GENERATED"  # NOT_GENERATED, POPULATED_V4_8, POPULATED_V4_8_FALLBACK
    composition_version: str = "5.1b.0"
    generated_at: Optional[datetime] = None


# Backward compatibility alias
MetricsDashboardLayer = PatternConnectionsLayer


# =============================================================================
# LAYER 6: FORWARD PROJECTION (NEW in v4.9)
# =============================================================================

@dataclass
class ForwardProjectionLayer:
    """
    Layer 6: Forward Projection - 90/180/365-day trajectory analysis.

    Projects forward based on patterns from similar completed pursuits
    to provide intelligence on what commonly happens in the months ahead.
    """
    # Content sections
    synthesis_statement: str = ""
    horizons: Dict[str, Any] = field(default_factory=dict)  # day_90, day_180, day_365

    # Metadata
    projection_metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "NOT_GENERATED"  # NOT_GENERATED, POPULATED_V4_8, POPULATED_V4_8_FALLBACK
    composition_version: str = "5.1b.0"
    generated_at: Optional[datetime] = None


# Backward compatibility alias
FuturePathwaysLayer = ForwardProjectionLayer


# =============================================================================
# METHODOLOGY TRANSPARENCY (NEW in v4.9 - Optional Section)
# =============================================================================

@dataclass
class MethodologyTransparencySection:
    """
    Optional section: Methodology Transparency - Expert-gated coaching provenance.

    Only included for EXPERT or ADVANCED experience level users.
    Reveals how coaching orchestration logic adapted to this pursuit.
    """
    # Content sections
    orchestration_summary: str = ""
    methodology_influences: List[Dict[str, str]] = field(default_factory=list)
    blending_notes: str = ""
    adaptation_narrative: str = ""

    # Metadata
    transparency_metadata: Dict[str, Any] = field(default_factory=dict)
    visibility: str = "EXPERT_ONLY"
    default_collapsed: bool = True
    status: str = "NOT_GENERATED"
    composition_version: str = "5.1b.0"
    generated_at: Optional[datetime] = None


# =============================================================================
# COMPLETE ITD DOCUMENT
# =============================================================================

@dataclass
class InnovationThesisDocument:
    """
    The complete Innovation Thesis Document.

    A 6-layer document that tells the story of an innovation journey.
    Plus optional Methodology Transparency section (expert-gated).
    """
    # Identification
    itd_id: str = ""
    pursuit_id: str = ""
    user_id: str = ""

    # The six layers
    thesis_statement: Optional[ThesisStatementLayer] = None
    evidence_architecture: Optional[EvidenceArchitectureLayer] = None
    narrative_arc: Optional[NarrativeArcLayer] = None
    coachs_perspective: Optional[CoachsPerspectiveLayer] = None
    pattern_connections: Optional[PatternConnectionsLayer] = None  # NEW in v4.9
    forward_projection: Optional[ForwardProjectionLayer] = None  # NEW in v4.9

    # Backward compatibility aliases (deprecated - use new names)
    metrics_dashboard: Optional[PatternConnectionsLayer] = None
    future_pathways: Optional[ForwardProjectionLayer] = None

    # Optional expert-gated section (NEW in v4.9)
    methodology_transparency: Optional[MethodologyTransparencySection] = None

    # Generation status
    status: ITDGenerationStatus = ITDGenerationStatus.NOT_STARTED
    layers_completed: List[str] = field(default_factory=list)
    layers_failed: List[str] = field(default_factory=list)

    # Metadata
    pursuit_title: str = ""
    archetype: str = ""
    terminal_state: str = ""  # e.g., "COMPLETED.SUCCESSFUL"

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Version tracking
    version: int = 1
    composition_version: str = "5.1b.0"  # NEW in v4.9

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        from dataclasses import asdict

        def convert_value(val):
            if isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, Enum):
                return val.value
            elif isinstance(val, list):
                return [convert_value(v) for v in val]
            elif hasattr(val, '__dataclass_fields__'):
                return {k: convert_value(v) for k, v in asdict(val).items()}
            return val

        return {k: convert_value(v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InnovationThesisDocument":
        """Create from MongoDB document."""
        # Handle datetime parsing
        for dt_field in ["created_at", "updated_at", "completed_at"]:
            if data.get(dt_field) and isinstance(data[dt_field], str):
                data[dt_field] = datetime.fromisoformat(data[dt_field])

        # Handle enum parsing
        if data.get("status"):
            data["status"] = ITDGenerationStatus(data["status"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
