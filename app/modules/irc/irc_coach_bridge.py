"""
InDE MVP v5.1b.0 - IRC Coach Bridge

Primary Deliverable D: Language Sovereignty-compliant coaching interface for
all IRC interactions. Injects resource-aware context into ODICM coaching
responses and orchestrates the three-step consolidation conversation.

Walk-through State Machine:
OFFER_PENDING -> WALK_THROUGH_PITCH -> WALK_THROUGH_DERISK ->
WALK_THROUGH_DEPLOY -> SYNTHESIS -> COMPLETE

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List
from enum import Enum

from .signal_detection_engine import ResourceSignal, ResourceSignalFamily
from .resource_entry_manager import ResourceEntryManager, AvailabilityStatus, PhaseAlignment
from .consolidation_engine import IRCConsolidationEngine
from .irc_display_labels import get_display_label

logger = logging.getLogger("inde.irc.coach_bridge")


# =============================================================================
# WALK-THROUGH STATE
# =============================================================================

class WalkthroughState(str, Enum):
    """Consolidation walk-through states."""
    OFFER_PENDING = "OFFER_PENDING"
    WALK_THROUGH_PITCH = "WALK_THROUGH_PITCH"
    WALK_THROUGH_DERISK = "WALK_THROUGH_DERISK"
    WALK_THROUGH_DEPLOY = "WALK_THROUGH_DEPLOY"
    SYNTHESIS = "SYNTHESIS"
    COMPLETE = "COMPLETE"
    DECLINED = "DECLINED"


# =============================================================================
# COACHING SCRIPTS (Language Sovereignty Compliant)
# =============================================================================

CONSOLIDATION_OFFER = """
You've touched on several things that will be essential to making this real \
— some people you'll need, some tools, a few things that are still open. \
It might be worth stepping back to get a clear picture of the full resource \
landscape. Want to work through that together?
"""

CONSOLIDATION_DECLINE_ACK = """
That's fine — we can come back to it. I'll keep track of what we've discussed \
so far and we can pull it together when the timing feels better.
"""

WALKTHROUGH_PHASE_INTROS = {
    PhaseAlignment.PITCH: """
Let's start with what you'll need for the early stage — getting the idea \
off the ground. Based on what you've described, the main things I'm hearing are: \
{resource_summary}. Does that feel right, or is there something important I'm missing?
""",
    PhaseAlignment.DE_RISK: """
Now for the testing and validation stage — what you'll need to learn whether \
this is going to work. I'm hearing: {resource_summary}. Anything else that \
comes to mind?
""",
    PhaseAlignment.DEPLOY: """
And for the building and launching stage — what you'll need once you're ready \
to make it real. So far: {resource_summary}. What am I missing?
""",
}

CANVAS_SYNTHESIS_TEMPLATE = """
Here's where things stand. {secured_summary}. {open_summary}. \
{cost_summary}. {completeness_note} Does that give you a useful picture to work from?
"""

PHASE_APPROACH_NUDGE = """
You're moving toward the {phase_display} stage, and one thing worth \
making sure is settled is {resource_name} — do you have a better sense \
of where that stands now?
"""


# =============================================================================
# IRC COACH BRIDGE
# =============================================================================

class IRCCoachBridge:
    """
    Coaching interface for IRC module interactions.
    All output passes Language Sovereignty validation.
    """

    def __init__(self, db, llm_client=None):
        """
        Initialize IRC Coach Bridge.

        Args:
            db: Database instance
            llm_client: Optional IRCLLMClient for LLM-generated coaching
        """
        self.db = db
        self.llm_client = llm_client
        self.resource_manager = ResourceEntryManager(db)
        self.consolidation_engine = IRCConsolidationEngine(db, llm_client)

    async def handle_resource_signal(
        self,
        signal: ResourceSignal,
        resource_entry: Dict,
        pursuit_context: Dict[str, Any],
        coaching_context: Dict[str, Any],
    ) -> str:
        """
        Generate a coaching probe for a detected resource signal.

        The probe extends the resource signal naturally in one of the
        most salient dimensions given pursuit phase and signal family.

        Probe selection priority:
        1. If UNCERTAINTY signal: probe availability path
        2. If AVAILABILITY signal + unresolved: probe resolution path
        3. If COST signal + unknown confidence: probe estimate range
        4. If TIMING signal: confirm phase alignment
        5. If IDENTIFICATION signal: probe for category/phase/duration

        Args:
            signal: The detected ResourceSignal
            resource_entry: The created/updated resource entry
            pursuit_context: Current pursuit context
            coaching_context: Current coaching context

        Returns:
            Coaching probe text to inject into ODICM response
        """
        # Determine probe type based on signal family and resource state
        probe = await self._select_probe(
            signal=signal,
            resource=resource_entry,
            pursuit_phase=pursuit_context.get("current_phase", ""),
            coaching_context=coaching_context,
        )

        logger.info(f"[IRCCoach] Generated probe for {signal.family.value} signal")
        return probe

    async def _select_probe(
        self,
        signal: ResourceSignal,
        resource: Dict,
        pursuit_phase: str,
        coaching_context: Dict[str, Any],
    ) -> str:
        """Select and generate the appropriate coaching probe."""
        from .irc_prompt_library import PROBE_TEMPLATES

        family = signal.family
        resource_name = resource.get("resource_name", "what you mentioned")
        availability = resource.get("availability_status", "UNKNOWN")

        # Select probe based on priority rules
        if family == ResourceSignalFamily.UNCERTAINTY:
            # Probe availability path
            probe_category = "AVAILABILITY"
        elif family == ResourceSignalFamily.AVAILABILITY and availability in ["UNRESOLVED", "UNKNOWN"]:
            # Probe resolution path
            probe_category = "AVAILABILITY"
        elif family == ResourceSignalFamily.COST and resource.get("cost_confidence") == "UNKNOWN":
            # Probe estimate range
            probe_category = "COST"
        elif family == ResourceSignalFamily.TIMING:
            # Confirm phase alignment
            probe_category = "TIMING"
        else:
            # IDENTIFICATION or default: probe for more details
            probe_category = "IDENTIFICATION"

        # Get template probes
        templates = PROBE_TEMPLATES.get(probe_category, PROBE_TEMPLATES["IDENTIFICATION"])

        # Select appropriate template (cycle through for variety)
        # In production, this would consider conversation history
        template = templates[0]

        # If LLM client available, generate custom probe
        if self.llm_client:
            try:
                return await self.llm_client.generate_coaching_probe(
                    signal_family=family.value,
                    resource_name=resource_name,
                    pursuit_phase=pursuit_phase,
                    coaching_context=coaching_context,
                )
            except Exception as e:
                logger.warning(f"[IRCCoach] LLM probe generation error: {e}")

        # Fallback to template
        return template

    async def handle_consolidation_offer(
        self,
        canvas_snapshot: Dict[str, Any],
        pursuit_context: Dict[str, Any],
    ) -> str:
        """
        Generate the consolidation offer coaching text.

        Args:
            canvas_snapshot: Current resource snapshot
            pursuit_context: Pursuit context

        Returns:
            Consolidation offer text (Language Sovereignty validated)
        """
        # Try LLM-generated offer first
        if self.llm_client:
            try:
                resource_summary = self._format_resource_summary(
                    canvas_snapshot.get("resources", [])
                )
                return await self.llm_client.generate_consolidation_offer(
                    resource_summary=resource_summary,
                    pursuit_context=pursuit_context,
                )
            except Exception as e:
                logger.warning(f"[IRCCoach] LLM consolidation offer error: {e}")

        # Fallback to template
        return CONSOLIDATION_OFFER.strip()

    def handle_consolidation_decline(self, pursuit_id: str) -> str:
        """
        Handle user declining consolidation offer.

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Acknowledgment text
        """
        # Record decline event
        self.consolidation_engine.record_consolidation_event(
            pursuit_id=pursuit_id,
            event_type="CONSOLIDATION_DECLINED",
        )

        return CONSOLIDATION_DECLINE_ACK.strip()

    async def handle_consolidation_walkthrough(
        self,
        walkthrough_state: Dict[str, Any],
        innovator_response: str,
        pursuit_context: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Manage the phase-by-phase guided walk-through conversation.

        Args:
            walkthrough_state: Current walk-through state
            innovator_response: User's response to previous turn
            pursuit_context: Pursuit context

        Returns:
            Tuple of (coaching_turn_text, updated_walkthrough_state)
        """
        current_state = WalkthroughState(
            walkthrough_state.get("state", WalkthroughState.OFFER_PENDING.value)
        )
        pursuit_id = pursuit_context.get("pursuit_id", "")

        # State machine transitions
        if current_state == WalkthroughState.OFFER_PENDING:
            # Check if user accepted
            if self._is_affirmative(innovator_response):
                return await self._start_walkthrough(pursuit_id, pursuit_context)
            else:
                return self.handle_consolidation_decline(pursuit_id), {
                    "state": WalkthroughState.DECLINED.value,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }

        elif current_state == WalkthroughState.WALK_THROUGH_PITCH:
            # Move to De-Risk phase
            return await self._walkthrough_phase(
                pursuit_id,
                PhaseAlignment.DE_RISK,
                innovator_response,
                pursuit_context,
            )

        elif current_state == WalkthroughState.WALK_THROUGH_DERISK:
            # Move to Deploy phase
            return await self._walkthrough_phase(
                pursuit_id,
                PhaseAlignment.DEPLOY,
                innovator_response,
                pursuit_context,
            )

        elif current_state == WalkthroughState.WALK_THROUGH_DEPLOY:
            # Move to synthesis
            return await self._complete_walkthrough(pursuit_id)

        elif current_state == WalkthroughState.SYNTHESIS:
            # Already complete
            return "", {"state": WalkthroughState.COMPLETE.value}

        # Default: complete
        return "", {"state": WalkthroughState.COMPLETE.value}

    async def _start_walkthrough(
        self,
        pursuit_id: str,
        pursuit_context: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Start the walk-through with Pitch phase."""
        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)
        pitch_resources = [
            r for r in resources
            if PhaseAlignment.PITCH.value in r.get("phase_alignment", [])
            or PhaseAlignment.ACROSS_ALL.value in r.get("phase_alignment", [])
        ]

        summary = self._format_resource_list(pitch_resources)
        text = WALKTHROUGH_PHASE_INTROS[PhaseAlignment.PITCH].format(
            resource_summary=summary or "a few things you'll need"
        ).strip()

        return text, {
            "state": WalkthroughState.WALK_THROUGH_PITCH.value,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _walkthrough_phase(
        self,
        pursuit_id: str,
        phase: PhaseAlignment,
        innovator_response: str,
        pursuit_context: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Handle a walk-through phase transition."""
        # Process any updates from the response (in production, would use NLU)
        # For now, just move to next phase

        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)
        phase_resources = [
            r for r in resources
            if phase.value in r.get("phase_alignment", [])
            or PhaseAlignment.ACROSS_ALL.value in r.get("phase_alignment", [])
        ]

        summary = self._format_resource_list(phase_resources)

        if phase in WALKTHROUGH_PHASE_INTROS:
            text = WALKTHROUGH_PHASE_INTROS[phase].format(
                resource_summary=summary or "what you'll need"
            ).strip()
        else:
            text = f"And for the next stage: {summary}"

        # Determine next state
        if phase == PhaseAlignment.DE_RISK:
            next_state = WalkthroughState.WALK_THROUGH_DERISK.value
        elif phase == PhaseAlignment.DEPLOY:
            next_state = WalkthroughState.WALK_THROUGH_DEPLOY.value
        else:
            next_state = WalkthroughState.SYNTHESIS.value

        return text, {"state": next_state}

    async def _complete_walkthrough(
        self,
        pursuit_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete the walk-through and generate canvas."""
        # Create/update the canvas
        canvas = await self.consolidation_engine.create_or_update_canvas(pursuit_id)

        # Generate synthesis presentation
        text = await self.handle_canvas_synthesis_presentation(
            irc_canvas=canvas,
            resource_entries=self.resource_manager.get_resources_for_pursuit(pursuit_id),
        )

        return text, {
            "state": WalkthroughState.COMPLETE.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "canvas_id": canvas.get("artifact_id"),
        }

    async def handle_canvas_synthesis_presentation(
        self,
        irc_canvas: Dict,
        resource_entries: List[Dict],
    ) -> str:
        """
        Present the synthesized canvas as a coaching reflection.

        Uses Display Label Registry values — never internal enum names.
        Frames as working hypothesis, not a plan.

        Args:
            irc_canvas: The computed canvas
            resource_entries: List of resource entries

        Returns:
            Synthesis presentation text (Language Sovereignty validated)
        """
        # Build summary components
        secured_count = irc_canvas.get("secured_count", 0)
        unresolved_count = irc_canvas.get("unresolved_count", 0)
        total_low = irc_canvas.get("total_cost_low", 0)
        total_high = irc_canvas.get("total_cost_high", 0)
        completeness = irc_canvas.get("canvas_completeness", 0)

        # Use LLM-generated synthesis notes if available
        synthesis_notes = irc_canvas.get("coach_synthesis_notes", "")
        if synthesis_notes:
            return synthesis_notes

        # Fallback: generate from template
        secured_summary = self._format_secured_summary(secured_count, resource_entries)
        open_summary = self._format_open_summary(unresolved_count, resource_entries)
        cost_summary = self._format_cost_summary(total_low, total_high)
        completeness_note = self._format_completeness_note(completeness)

        return CANVAS_SYNTHESIS_TEMPLATE.format(
            secured_summary=secured_summary,
            open_summary=open_summary,
            cost_summary=cost_summary,
            completeness_note=completeness_note,
        ).strip()

    def generate_phase_approach_nudge(
        self,
        pursuit_id: str,
        upcoming_phase: str,
        resource_name: str,
    ) -> str:
        """
        Generate a nudge about an unresolved resource as user approaches a phase.

        Args:
            pursuit_id: The pursuit ID
            upcoming_phase: The upcoming phase
            resource_name: Name of the unresolved resource

        Returns:
            Nudge text (Language Sovereignty validated)
        """
        phase_display = get_display_label("phase_display", upcoming_phase)

        return PHASE_APPROACH_NUDGE.format(
            phase_display=phase_display,
            resource_name=resource_name,
        ).strip()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _is_affirmative(self, response: str) -> bool:
        """Check if response is affirmative."""
        response_lower = response.lower().strip()
        affirmatives = [
            "yes", "yeah", "yep", "sure", "ok", "okay", "sounds good",
            "let's do it", "go for it", "absolutely", "definitely",
            "let's", "please", "go ahead",
        ]
        return any(aff in response_lower for aff in affirmatives)

    def _format_resource_list(self, resources: List[Dict]) -> str:
        """Format a list of resources for coaching text."""
        if not resources:
            return ""

        names = [r.get("resource_name", "resource") for r in resources[:5]]

        if len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]} and {names[1]}"
        else:
            return ", ".join(names[:-1]) + f", and {names[-1]}"

    def _format_resource_summary(self, resources: List[Dict]) -> str:
        """Format resource summary for LLM prompt."""
        if not resources:
            return "a few things you've mentioned"

        items = []
        for r in resources[:10]:
            name = r.get("resource_name", "resource")
            status = get_display_label(
                "availability_display",
                r.get("availability_status", "UNKNOWN")
            )
            items.append(f"{name} ({status})")

        return ", ".join(items)

    def _format_secured_summary(
        self,
        secured_count: int,
        resources: List[Dict],
    ) -> str:
        """Format summary of secured resources."""
        if secured_count == 0:
            return "Nothing is fully in place yet"
        elif secured_count == 1:
            secured = [
                r for r in resources
                if r.get("availability_status") == AvailabilityStatus.SECURED.value
            ]
            name = secured[0].get("resource_name", "One thing") if secured else "One thing"
            return f"{name} is in place"
        else:
            return f"{secured_count} things are in place"

    def _format_open_summary(
        self,
        open_count: int,
        resources: List[Dict],
    ) -> str:
        """Format summary of open resources."""
        if open_count == 0:
            return "nothing major is still open"
        elif open_count == 1:
            unresolved = [
                r for r in resources
                if r.get("availability_status") in [
                    AvailabilityStatus.UNRESOLVED.value,
                    AvailabilityStatus.UNKNOWN.value,
                ]
            ]
            name = unresolved[0].get("resource_name", "one thing") if unresolved else "one thing"
            return f"{name} is still open"
        else:
            return f"{open_count} things are still to sort out"

    def _format_cost_summary(self, low: float, high: float) -> str:
        """Format cost summary."""
        if low == 0 and high == 0:
            return "The cost picture is still forming"
        elif low == high:
            return f"You're looking at roughly ${low:,.0f}"
        else:
            return f"You're looking at roughly ${low:,.0f} to ${high:,.0f}"

    def _format_completeness_note(self, completeness: float) -> str:
        """Format completeness note."""
        if completeness >= 0.8:
            return "That's a fairly complete picture."
        elif completeness >= 0.6:
            return "There are still some details to fill in, but you have a working picture."
        else:
            return "This is a start — we'll fill in more as we go."
