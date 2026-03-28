"""
InDE Behavioral Telemetry Service
Lightweight local event tracking — stored in MongoDB, visible in admin panel.
No external services. No PII. All events are keyed by GII, not email or display_name.

v3.16: Initial implementation
v4.5.0: Added IML momentum learning telemetry events
v4.6.0: Added Outcome Formulator telemetry events
v4.7.0: Added ITD Composition Engine telemetry events
v5.1b.0: Added Export Engine telemetry events
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("inde.telemetry")

# Event taxonomy — extend as needed
EVENTS = {
    # Session lifecycle
    "session.started": "User opened InDE (authenticated)",
    "session.ended": "Session ended (logout or timeout)",

    # Onboarding funnel
    "onboarding.screen_viewed": "Onboarding screen rendered",
    "onboarding.screen_completed": "Onboarding screen criterion met",
    "onboarding.completed": "All 4 onboarding criteria satisfied",
    "onboarding.abandoned": "User left onboarding mid-flow",

    # Pursuit lifecycle
    "pursuit.created": "New pursuit created",
    "pursuit.first_coaching": "First coaching message sent in pursuit",
    "pursuit.artifact_generated": "First artifact created in pursuit",
    "pursuit.archived": "Pursuit archived",
    "pursuit.completed": "Pursuit reached terminal state",

    # Coaching engagement
    "coaching.message_sent": "User sent coaching message",
    "coaching.rate_limited": "User hit coaching rate limit",
    "coaching.timeout": "Coaching response timed out",
    "coaching.cancelled": "User cancelled pending coaching request",

    # GII
    "gii.issued": "New PROVISIONAL GII issued",
    "gii.profile_viewed": "User viewed their GII profile",

    # =========================================================================
    # v4.0: MOMENTUM MANAGEMENT EVENTS
    # Properties schema: { momentum_level: str, days_since_last: int, depth_stage: str }
    # =========================================================================

    # Session momentum
    "momentum.session_opened": "Session opened with momentum context",
    "momentum.session_closed": "Session closed with momentum bridge shown",

    # Re-engagement
    "momentum.re_engaged": "User returned after gap (with momentum greeting)",
    "momentum.long_gap_return": "User returned after extended absence (7+ days)",

    # Depth progression
    "momentum.depth_advanced": "User idea depth advanced to new stage",
    "momentum.depth_acknowledged": "Depth acknowledgment shown to user",

    # Coaching continuity
    "momentum.bridge_shown": "Momentum bridge message displayed",
    "momentum.context_restored": "Previous session context restored for user",

    # =========================================================================
    # v4.4: IML MOMENTUM LEARNING EVENTS
    # Properties schema: { pattern_type: str, confidence: float, sample_size: int }
    # =========================================================================

    # Pattern aggregation
    "iml.pattern_created": "New momentum pattern created from aggregation",
    "iml.pattern_updated": "Existing momentum pattern updated with new sample",
    "iml.aggregation_cycle": "IML aggregation cycle completed",

    # Feedback loop
    "iml.bridge_recommended": "IML recommended a bridge (vs static library)",
    "iml.bridge_fallback": "IML fell back to static library (no strong recommendation)",
    "iml.circuit_breaker_opened": "IML feedback receiver circuit breaker opened",
    "iml.circuit_breaker_closed": "IML feedback receiver circuit breaker closed",

    # Knowledge surfacing
    "iml.insight_lift_scored": "Insight scored with momentum-lift factor",
    "iml.insight_boosted": "Insight ranking boosted by momentum-lift score",

    # IKF contribution
    "ikf.momentum_pattern_eligible": "Momentum pattern reached IKF contribution threshold",
    "ikf.momentum_pattern_contributed": "Momentum pattern contributed to IKF",

    # =========================================================================
    # v4.5: ENGAGEMENT ENGINE EVENTS
    # Properties schema varies by event type (see individual events)
    # =========================================================================

    # Health Card
    "engagement.health_card_viewed": "Innovation Health Card viewed in panel",

    # Artifact Export
    "engagement.share_link_created": "Shareable artifact link created",
    "engagement.share_link_viewed": "Shared artifact viewed (public endpoint)",
    "engagement.pdf_exported": "Artifact exported as PDF",

    # Cohort Signals
    "engagement.cohort_pulse_viewed": "Cohort presence signal viewed",

    # Pathway Teaser
    "engagement.pathway_teaser_shown": "Pathway teaser displayed after milestone",
    "engagement.pathway_teaser_clicked": "User clicked pathway teaser CTA",
    "engagement.pathway_teaser_dismissed": "User dismissed pathway teaser",

    # Milestone
    "engagement.milestone_delivered": "Milestone achievement narrative delivered",

    # =========================================================================
    # v4.6: OUTCOME FORMULATOR EVENTS
    # Properties schema: { archetype: str, artifact_type: str, from_state: str, to_state: str }
    # =========================================================================

    # Field capture
    "outcome.field_captured": "Outcome field captured from event",
    "outcome.field_updated": "Outcome field updated with new data",

    # State transitions
    "outcome.state_transition": "Outcome readiness state transitioned",

    # Tracking lifecycle
    "outcome.artifact_tracking_started": "New outcome artifact tracking started",
    "outcome.artifact_ready": "Outcome artifact reached READY state",

    # =========================================================================
    # v4.7: ITD COMPOSITION ENGINE EVENTS
    # Properties schema: { layer_type: str, pursuit_id: str, archetype: str }
    # =========================================================================

    # ITD generation
    "itd.generation_started": "ITD generation started for pursuit",
    "itd.layer_completed": "ITD layer generation completed",
    "itd.layer_failed": "ITD layer generation failed",
    "itd.generation_completed": "Full ITD generation completed",
    "itd.generation_failed": "ITD generation failed",

    # ITD viewing
    "itd.viewed": "ITD document viewed",
    "itd.layer_regenerated": "ITD layer regenerated on request",

    # Exit flow
    "itd.exit_started": "Four-phase exit flow started",
    "itd.phase_completed": "Exit flow phase completed",
    "itd.exit_completed": "Four-phase exit flow completed",

    # Retrospective mapping
    "itd.retrospective_mapped": "Retrospective data mapped to ITD layers",

    # =========================================================================
    # v4.9: EXPORT ENGINE EVENTS
    # Properties schema: { template_key: str, narrative_style: str, format: str, readiness_score: float }
    # =========================================================================

    # Export generation
    "export.generation_started": "Export generation started",
    "export.generation_completed": "Export generation completed",
    "export.generation_partial": "Export generated with partial fields",
    "export.generation_failed": "Export generation failed",

    # Export downloads
    "export.downloaded": "Export file downloaded",

    # Export discovery
    "export.discovery_shown": "Export discovery suggestions shown (Phase 3)",
    "export.suggestion_selected": "User selected export suggestion",
}

# Module-level db reference (set during app startup)
_db = None


def init_telemetry(db):
    """Initialize telemetry with database reference."""
    global _db
    _db = db
    logger.info("Telemetry service initialized")


def track(event_name: str, gii_id: Optional[str], properties: Optional[Dict[str, Any]] = None):
    """
    Record a behavioral event. Fire-and-forget — never blocks user operations.
    Events are keyed by GII, never by email or display_name.

    Args:
        event_name: Event type from EVENTS taxonomy
        gii_id: User's Global Innovator Identifier (no PII)
        properties: Additional event context
    """
    if event_name not in EVENTS:
        logger.warning(f"Unknown telemetry event: {event_name}")

    record = {
        "event": event_name,
        "gii_id": gii_id,  # Attribution via GII only — no PII
        "properties": properties or {},
        "recorded_at": datetime.utcnow()
    }

    try:
        if _db is not None:
            _db.db.telemetry_events.insert_one(record)
        else:
            logger.warning(f"Telemetry not initialized, event dropped: {event_name}")
    except Exception as e:
        logger.error(f"Telemetry write failed: {event_name}: {e}")
        # Never raise — telemetry failure must never impact user experience


# =============================================================================
# v4.0: Momentum Telemetry Helpers
# =============================================================================

def track_momentum(
    event_type: str,
    gii_id: Optional[str],
    momentum_level: str = "moderate",
    days_since_last: int = 0,
    depth_stage: str = "idea_forming",
    pursuit_id: Optional[str] = None
):
    """
    Track momentum-related events with standard properties.

    Args:
        event_type: Momentum event suffix (e.g., "session_opened", "re_engaged")
        gii_id: User's Global Innovator Identifier
        momentum_level: One of 'high', 'moderate', 'low'
        days_since_last: Days since last session
        depth_stage: Current idea depth stage
        pursuit_id: Optional pursuit context
    """
    event_name = f"momentum.{event_type}"
    properties = {
        "momentum_level": momentum_level,
        "days_since_last": days_since_last,
        "depth_stage": depth_stage,
    }
    if pursuit_id:
        properties["pursuit_id"] = pursuit_id

    track(event_name, gii_id, properties)


# =============================================================================
# v4.4: IML Momentum Telemetry Helpers
# =============================================================================

def track_iml(
    event_type: str,
    pattern_type: str = "unknown",
    confidence: float = 0.0,
    sample_size: int = 0,
    context_hash: str = None,
    selection_source: str = None
):
    """
    Track IML momentum learning events.

    Args:
        event_type: IML event suffix (e.g., "pattern_created", "bridge_recommended")
        pattern_type: Type of momentum pattern
        confidence: Pattern confidence score (0-1)
        sample_size: Number of samples in pattern
        context_hash: Optional context fingerprint
        selection_source: Source of selection ("iml" or "static")
    """
    event_name = f"iml.{event_type}"
    properties = {
        "pattern_type": pattern_type,
        "confidence": round(confidence, 3),
        "sample_size": sample_size,
    }
    if context_hash:
        properties["context_hash"] = context_hash
    if selection_source:
        properties["selection_source"] = selection_source

    track(event_name, None, properties)  # IML events are not user-specific


def get_iml_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get IML momentum learning telemetry summary.

    Args:
        days: Number of days to include in summary

    Returns:
        Summary dict with IML pattern and feedback loop metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    # Aggregate IML events
    iml_events = [
        "iml.pattern_created",
        "iml.pattern_updated",
        "iml.aggregation_cycle",
        "iml.bridge_recommended",
        "iml.bridge_fallback",
        "iml.circuit_breaker_opened",
        "iml.insight_lift_scored",
        "ikf.momentum_pattern_contributed"
    ]

    event_counts = {}
    for event in iml_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Calculate IML effectiveness
    bridge_recommended = event_counts.get("iml.bridge_recommended", 0)
    bridge_fallback = event_counts.get("iml.bridge_fallback", 0)
    total_bridge_selections = bridge_recommended + bridge_fallback

    iml_selection_rate = (
        bridge_recommended / total_bridge_selections
        if total_bridge_selections > 0 else 0
    )

    return {
        "period_days": days,
        "event_counts": event_counts,
        "patterns_created": event_counts.get("iml.pattern_created", 0),
        "patterns_updated": event_counts.get("iml.pattern_updated", 0),
        "iml_selection_rate": round(iml_selection_rate, 3),
        "circuit_breaker_trips": event_counts.get("iml.circuit_breaker_opened", 0),
        "ikf_contributions": event_counts.get("ikf.momentum_pattern_contributed", 0)
    }


# =============================================================================
# v4.5: Engagement Telemetry Helpers
# =============================================================================

def track_engagement(
    event_type: str,
    gii_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    growth_stage: Optional[str] = None,
    teaser_type: Optional[str] = None,
    source: Optional[str] = None,
    **extra_props
):
    """
    Track engagement-related events from v4.5 Engagement Engine.

    Args:
        event_type: Engagement event suffix (e.g., "health_card_viewed")
        gii_id: User's Global Innovator Identifier (optional for some events)
        artifact_type: Type of artifact involved (optional)
        growth_stage: Health card growth stage (optional)
        teaser_type: Pathway teaser type (optional)
        source: Event source ("iml" or "fallback") (optional)
        **extra_props: Additional properties
    """
    event_name = f"engagement.{event_type}"
    properties = {}

    if artifact_type:
        properties["artifact_type"] = artifact_type
    if growth_stage:
        properties["growth_stage"] = growth_stage
    if teaser_type:
        properties["teaser_type"] = teaser_type
    if source:
        properties["source"] = source

    properties.update(extra_props)
    track(event_name, gii_id, properties)


def get_engagement_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get engagement telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary (default 7)

    Returns:
        Summary dict with engagement health and conversion metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)
    since_24h = datetime.utcnow() - timedelta(hours=24)

    # Count engagement events
    engagement_events = [
        "engagement.health_card_viewed",
        "engagement.share_link_created",
        "engagement.share_link_viewed",
        "engagement.pdf_exported",
        "engagement.cohort_pulse_viewed",
        "engagement.pathway_teaser_shown",
        "engagement.pathway_teaser_clicked",
        "engagement.pathway_teaser_dismissed",
        "engagement.milestone_delivered"
    ]

    event_counts = {}
    for event in engagement_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Health Card views in 24h
    health_cards_24h = _db.db.telemetry_events.count_documents({
        "event": "engagement.health_card_viewed",
        "recorded_at": {"$gte": since_24h}
    })

    # Calculate teaser click rate
    teasers_shown = event_counts.get("engagement.pathway_teaser_shown", 0)
    teasers_clicked = event_counts.get("engagement.pathway_teaser_clicked", 0)
    teaser_click_rate = (
        teasers_clicked / teasers_shown if teasers_shown > 0 else 0
    )

    # Share link analytics
    share_links_created = event_counts.get("engagement.share_link_created", 0)
    share_link_views = event_counts.get("engagement.share_link_viewed", 0)
    avg_views_per_link = (
        share_link_views / share_links_created if share_links_created > 0 else 0
    )

    # Most shared artifact type
    most_shared = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "engagement.share_link_created",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.artifact_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ])
    most_shared_list = list(most_shared)
    most_shared_type = most_shared_list[0]["_id"] if most_shared_list else None

    return {
        "engagement_health": {
            "health_cards_viewed_24h": health_cards_24h,
            "share_links_created_7d": share_links_created,
            "share_link_total_views_7d": share_link_views,
            "pdf_exports_7d": event_counts.get("engagement.pdf_exported", 0),
            "avg_views_per_share_link": round(avg_views_per_link, 2),
            "most_shared_artifact_type": most_shared_type,
        },
        "engagement_conversion": {
            "pathway_teasers_shown_7d": teasers_shown,
            "pathway_teasers_clicked_7d": teasers_clicked,
            "pathway_teaser_click_rate": round(teaser_click_rate, 3),
            "milestones_delivered_7d": event_counts.get("engagement.milestone_delivered", 0),
            # Primary v4.5 success metric:
            # What % of innovators who received a milestone + teaser continued?
            "post_milestone_session_continuation_rate": None,  # Computed separately
        },
        "period_days": days,
        "event_counts": event_counts,
    }


# =============================================================================
# v4.6: Outcome Telemetry Helpers
# =============================================================================

def track_outcome(
    event_type: str,
    archetype: Optional[str] = None,
    artifact_type: Optional[str] = None,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    pursuit_id: Optional[str] = None,
    field_key: Optional[str] = None,
    confidence: Optional[float] = None,
    **extra_props
):
    """
    Track outcome formulator events.

    Args:
        event_type: Outcome event suffix (e.g., "field_captured", "state_transition")
        archetype: Methodology archetype (e.g., "lean_startup")
        artifact_type: Outcome artifact type (e.g., "business_model_canvas")
        from_state: Previous readiness state (for transitions)
        to_state: New readiness state (for transitions)
        pursuit_id: Pursuit ID (not GII - outcome events are pursuit-scoped)
        field_key: Field key that was captured/updated
        confidence: Field capture confidence score
        **extra_props: Additional properties
    """
    event_name = f"outcome.{event_type}"
    properties = {}

    if archetype:
        properties["archetype"] = archetype
    if artifact_type:
        properties["artifact_type"] = artifact_type
    if from_state:
        properties["from_state"] = from_state
    if to_state:
        properties["to_state"] = to_state
    if pursuit_id:
        properties["pursuit_id"] = pursuit_id
    if field_key:
        properties["field_key"] = field_key
    if confidence is not None:
        properties["confidence"] = round(confidence, 3)

    properties.update(extra_props)
    track(event_name, None, properties)  # Outcome events are pursuit-scoped, not user-scoped


def get_outcome_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get outcome readiness telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary (default 7)

    Returns:
        Summary dict with outcome readiness metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    # Count outcome events
    outcome_events = [
        "outcome.field_captured",
        "outcome.field_updated",
        "outcome.state_transition",
        "outcome.artifact_tracking_started",
        "outcome.artifact_ready",
    ]

    event_counts = {}
    for event in outcome_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Count state transitions by archetype
    transitions_by_archetype = {}
    transition_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "outcome.state_transition",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.archetype", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in transition_cursor:
        if doc["_id"]:
            transitions_by_archetype[doc["_id"]] = doc["count"]

    # Count artifacts reaching READY state
    ready_by_archetype = {}
    ready_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "outcome.artifact_ready",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.archetype", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in ready_cursor:
        if doc["_id"]:
            ready_by_archetype[doc["_id"]] = doc["count"]

    return {
        "period_days": days,
        "event_counts": event_counts,
        "fields_captured": event_counts.get("outcome.field_captured", 0),
        "fields_updated": event_counts.get("outcome.field_updated", 0),
        "state_transitions": event_counts.get("outcome.state_transition", 0),
        "artifacts_started": event_counts.get("outcome.artifact_tracking_started", 0),
        "artifacts_ready": event_counts.get("outcome.artifact_ready", 0),
        "transitions_by_archetype": transitions_by_archetype,
        "ready_by_archetype": ready_by_archetype,
    }


# =============================================================================
# v4.7: ITD Telemetry Helpers
# =============================================================================

def track_itd(
    event_type: str,
    pursuit_id: Optional[str] = None,
    layer_type: Optional[str] = None,
    archetype: Optional[str] = None,
    itd_id: Optional[str] = None,
    session_id: Optional[str] = None,
    phase: Optional[str] = None,
    layers_completed: Optional[int] = None,
    **extra_props
):
    """
    Track ITD composition engine events.

    Args:
        event_type: ITD event suffix (e.g., "generation_started", "layer_completed")
        pursuit_id: Pursuit ID being processed
        layer_type: ITD layer type (thesis_statement, evidence_architecture, etc.)
        archetype: Methodology archetype
        itd_id: Generated ITD document ID
        session_id: Exit session ID (for exit flow events)
        phase: Exit flow phase (for phase events)
        layers_completed: Number of layers completed
        **extra_props: Additional properties
    """
    event_name = f"itd.{event_type}"
    properties = {}

    if pursuit_id:
        properties["pursuit_id"] = pursuit_id
    if layer_type:
        properties["layer_type"] = layer_type
    if archetype:
        properties["archetype"] = archetype
    if itd_id:
        properties["itd_id"] = itd_id
    if session_id:
        properties["session_id"] = session_id
    if phase:
        properties["phase"] = phase
    if layers_completed is not None:
        properties["layers_completed"] = layers_completed

    properties.update(extra_props)
    track(event_name, None, properties)  # ITD events are pursuit-scoped, not user-scoped


def get_itd_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get ITD composition engine telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary (default 7)

    Returns:
        Summary dict with ITD generation and exit flow metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    # Count ITD events
    itd_events = [
        "itd.generation_started",
        "itd.layer_completed",
        "itd.layer_failed",
        "itd.generation_completed",
        "itd.generation_failed",
        "itd.viewed",
        "itd.layer_regenerated",
        "itd.exit_started",
        "itd.phase_completed",
        "itd.exit_completed",
        "itd.retrospective_mapped",
    ]

    event_counts = {}
    for event in itd_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Count layers completed by type
    layers_by_type = {}
    layer_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "itd.layer_completed",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.layer_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in layer_cursor:
        if doc["_id"]:
            layers_by_type[doc["_id"]] = doc["count"]

    # Count generations by archetype
    generations_by_archetype = {}
    archetype_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "itd.generation_completed",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.archetype", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in archetype_cursor:
        if doc["_id"]:
            generations_by_archetype[doc["_id"]] = doc["count"]

    # Calculate success rate
    generations_started = event_counts.get("itd.generation_started", 0)
    generations_completed = event_counts.get("itd.generation_completed", 0)
    generation_success_rate = (
        generations_completed / generations_started
        if generations_started > 0 else 0
    )

    # Exit flow completion rate
    exits_started = event_counts.get("itd.exit_started", 0)
    exits_completed = event_counts.get("itd.exit_completed", 0)
    exit_completion_rate = (
        exits_completed / exits_started
        if exits_started > 0 else 0
    )

    return {
        "period_days": days,
        "event_counts": event_counts,
        "generations_started": generations_started,
        "generations_completed": generations_completed,
        "generation_success_rate": round(generation_success_rate, 3),
        "layers_by_type": layers_by_type,
        "generations_by_archetype": generations_by_archetype,
        "exits_started": exits_started,
        "exits_completed": exits_completed,
        "exit_completion_rate": round(exit_completion_rate, 3),
        "itds_viewed": event_counts.get("itd.viewed", 0),
        "layers_regenerated": event_counts.get("itd.layer_regenerated", 0),
    }


# =============================================================================
# v4.9: Export Engine Telemetry Helpers
# =============================================================================

def track_export(
    event_type: str,
    pursuit_id: Optional[str] = None,
    template_key: Optional[str] = None,
    narrative_style: Optional[str] = None,
    output_format: Optional[str] = None,
    export_id: Optional[str] = None,
    readiness_score: Optional[float] = None,
    partial_fields: Optional[int] = None,
    **extra_props
):
    """
    Track export engine events.

    Args:
        event_type: Export event suffix (e.g., "generation_started", "downloaded")
        pursuit_id: Pursuit ID being exported
        template_key: Export template key (e.g., "business_model_canvas")
        narrative_style: Narrative style used (e.g., "investor", "academic")
        output_format: Output format (e.g., "pdf", "docx")
        export_id: Generated export record ID
        readiness_score: Template readiness score at generation time
        partial_fields: Number of partial/fallback fields in export
        **extra_props: Additional properties
    """
    event_name = f"export.{event_type}"
    properties = {}

    if pursuit_id:
        properties["pursuit_id"] = pursuit_id
    if template_key:
        properties["template_key"] = template_key
    if narrative_style:
        properties["narrative_style"] = narrative_style
    if output_format:
        properties["format"] = output_format
    if export_id:
        properties["export_id"] = export_id
    if readiness_score is not None:
        properties["readiness_score"] = round(readiness_score, 3)
    if partial_fields is not None:
        properties["partial_fields"] = partial_fields

    properties.update(extra_props)
    track(event_name, None, properties)  # Export events are pursuit-scoped


def get_export_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get export engine telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary (default 7)

    Returns:
        Summary dict with export generation and download metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    # Count export events
    export_events = [
        "export.generation_started",
        "export.generation_completed",
        "export.generation_partial",
        "export.generation_failed",
        "export.downloaded",
        "export.discovery_shown",
        "export.suggestion_selected",
    ]

    event_counts = {}
    for event in export_events:
        count = _db.db.telemetry_events.count_documents({
            "event": event,
            "recorded_at": {"$gte": since}
        })
        event_counts[event] = count

    # Count exports by template
    exports_by_template = {}
    template_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "export.generation_completed",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.template_key", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in template_cursor:
        if doc["_id"]:
            exports_by_template[doc["_id"]] = doc["count"]

    # Count exports by format
    exports_by_format = {}
    format_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "export.generation_completed",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.format", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in format_cursor:
        if doc["_id"]:
            exports_by_format[doc["_id"]] = doc["count"]

    # Count exports by narrative style
    exports_by_style = {}
    style_cursor = _db.db.telemetry_events.aggregate([
        {"$match": {
            "event": "export.generation_completed",
            "recorded_at": {"$gte": since}
        }},
        {"$group": {"_id": "$properties.narrative_style", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    for doc in style_cursor:
        if doc["_id"]:
            exports_by_style[doc["_id"]] = doc["count"]

    # Calculate success rate
    exports_started = event_counts.get("export.generation_started", 0)
    exports_completed = event_counts.get("export.generation_completed", 0)
    exports_partial = event_counts.get("export.generation_partial", 0)
    total_successful = exports_completed + exports_partial
    success_rate = (
        total_successful / exports_started
        if exports_started > 0 else 0
    )

    # Discovery to selection conversion
    discovery_shown = event_counts.get("export.discovery_shown", 0)
    suggestion_selected = event_counts.get("export.suggestion_selected", 0)
    suggestion_selection_rate = (
        suggestion_selected / discovery_shown
        if discovery_shown > 0 else 0
    )

    return {
        "period_days": days,
        "event_counts": event_counts,
        "exports_started": exports_started,
        "exports_completed": exports_completed,
        "exports_partial": exports_partial,
        "exports_failed": event_counts.get("export.generation_failed", 0),
        "success_rate": round(success_rate, 3),
        "downloads": event_counts.get("export.downloaded", 0),
        "exports_by_template": exports_by_template,
        "exports_by_format": exports_by_format,
        "exports_by_style": exports_by_style,
        "discovery_shown": discovery_shown,
        "suggestion_selected": suggestion_selected,
        "suggestion_selection_rate": round(suggestion_selection_rate, 3),
    }


def get_summary(days: int = 30) -> Dict[str, Any]:
    """
    Get aggregated telemetry summary for admin dashboard.

    Args:
        days: Number of days to include in summary

    Returns:
        Summary dict with event totals and funnel metrics
    """
    from datetime import timedelta

    if _db is None:
        return {"error": "Telemetry not initialized"}

    since = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {"recorded_at": {"$gte": since}}},
        {"$group": {"_id": "$event", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    results = list(_db.db.telemetry_events.aggregate(pipeline))

    # Onboarding funnel specific
    funnel_stages = [
        "onboarding.screen_viewed",
        "onboarding.screen_completed",
        "onboarding.completed"
    ]
    funnel = {}
    for stage in funnel_stages:
        funnel[stage] = _db.db.telemetry_events.count_documents(
            {"event": stage, "recorded_at": {"$gte": since}}
        )

    return {
        "period_days": days,
        "event_totals": {r["_id"]: r["count"] for r in results},
        "onboarding_funnel": funnel,
        "total_events": sum(r["count"] for r in results)
    }
