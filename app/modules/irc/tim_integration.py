"""
InDE MVP v5.1b.0 - IRC TIM Integration

Primary Deliverable E: Bidirectional integration between the IRC module
and the Temporal Intelligence Module (TIM). This integration is read-and-notify
only — the IRC does not modify TIM data structures.

Functions:
- notify_resource_update: Notify TIM of resource changes
- get_upcoming_phase_resource_gaps: Query resources needing attention

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from typing import Dict, Any, List, Optional

from .resource_entry_manager import ResourceEntryManager, AvailabilityStatus, PhaseAlignment

logger = logging.getLogger("inde.irc.tim_integration")


class IRCTIMIntegration:
    """
    Integration layer between IRC and TIM modules.
    Read-and-notify only — does not modify TIM data.
    """

    def __init__(self, db):
        """
        Initialize TIM integration.

        Args:
            db: Database instance
        """
        self.db = db
        self.resource_manager = ResourceEntryManager(db)

    def notify_resource_update(
        self,
        resource_entry: Dict,
        event_type: str,
    ) -> None:
        """
        Notify TIM when a .resource entry is created or availability changes.

        TIM integration contract:
        - Resource with phase_alignment=DE_RISK and availability_status=UNRESOLVED
          → TIM registers as a De-Risk phase readiness consideration
        - Resource with availability_status=SECURED → TIM removes consideration
        - Notification is fire-and-forget; TIM handles its own response

        Args:
            resource_entry: The resource entry data
            event_type: "CREATED" | "AVAILABILITY_UPDATED" | "CONSOLIDATED"
        """
        try:
            pursuit_id = resource_entry.get("pursuit_id")
            resource_name = resource_entry.get("resource_name", "Unknown")
            availability = resource_entry.get("availability_status", "UNKNOWN")
            phases = resource_entry.get("phase_alignment", [])

            # Create TIM notification event
            event_data = {
                "source_module": "IRC",
                "event_type": f"IRC_RESOURCE_{event_type}",
                "pursuit_id": pursuit_id,
                "resource_id": resource_entry.get("artifact_id"),
                "resource_name": resource_name,
                "availability_status": availability,
                "phase_alignment": phases,
            }

            # Determine if this affects phase readiness
            if availability in [AvailabilityStatus.UNRESOLVED.value, AvailabilityStatus.UNKNOWN.value]:
                # Resource is unresolved — TIM should consider it
                event_data["tim_action"] = "REGISTER_CONSIDERATION"
                event_data["consideration_type"] = "RESOURCE_GAP"

                # Map to TIM phase
                for phase in phases:
                    if phase == PhaseAlignment.DE_RISK.value:
                        event_data["tim_phase"] = "DERISK"
                    elif phase == PhaseAlignment.DEPLOY.value:
                        event_data["tim_phase"] = "DEPLOY"
                    elif phase == PhaseAlignment.PITCH.value:
                        event_data["tim_phase"] = "PITCH"

            elif availability == AvailabilityStatus.SECURED.value:
                # Resource is secured — TIM can remove consideration
                event_data["tim_action"] = "REMOVE_CONSIDERATION"

            # Fire event to TIM (via event bus or direct call)
            self._fire_tim_event(event_data)

            logger.info(
                f"[IRCTIMIntegration] Notified TIM: {event_type} for "
                f"'{resource_name}' ({availability})"
            )

        except Exception as e:
            # Fire-and-forget — log but don't fail
            logger.warning(f"[IRCTIMIntegration] TIM notification error: {e}")

    def _fire_tim_event(self, event_data: Dict) -> None:
        """
        Fire event to TIM module.

        In production, this would use the Redis event bus.
        For now, writes to a tim_events collection.
        """
        try:
            # Store in events collection for TIM to process
            self.db.db.tim_irc_events.insert_one(event_data)
        except Exception as e:
            logger.warning(f"[IRCTIMIntegration] Event storage error: {e}")

    def get_upcoming_phase_resource_gaps(
        self,
        pursuit_id: str,
        upcoming_phase: str,
    ) -> List[Dict]:
        """
        Return resource entries for the upcoming phase where
        availability_status is UNRESOLVED or UNKNOWN.

        Used by TIM to request resource-awareness coaching nudges.

        Args:
            pursuit_id: The pursuit ID
            upcoming_phase: The upcoming phase (e.g., "DE_RISK", "DEPLOY")

        Returns:
            List of resource entries with gaps
        """
        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)

        gaps = []
        for resource in resources:
            # Check if resource is aligned to upcoming phase
            phases = resource.get("phase_alignment", [])
            is_aligned = (
                upcoming_phase in phases or
                PhaseAlignment.ACROSS_ALL.value in phases
            )

            if not is_aligned:
                continue

            # Check if availability is unresolved
            availability = resource.get("availability_status", "UNKNOWN")
            if availability in [AvailabilityStatus.UNRESOLVED.value, AvailabilityStatus.UNKNOWN.value]:
                gaps.append(resource)

        logger.debug(
            f"[IRCTIMIntegration] Found {len(gaps)} resource gaps "
            f"for {upcoming_phase} phase"
        )
        return gaps

    def get_phase_readiness_resource_data(
        self,
        pursuit_id: str,
        phase: str,
    ) -> Dict[str, Any]:
        """
        Get resource readiness summary for a specific phase.

        Used by TIM for phase readiness scoring.

        Args:
            pursuit_id: The pursuit ID
            phase: The phase to check

        Returns:
            Resource readiness data for the phase
        """
        resources = self.resource_manager.get_resources_for_pursuit(pursuit_id)

        phase_resources = [
            r for r in resources
            if phase in r.get("phase_alignment", []) or
            PhaseAlignment.ACROSS_ALL.value in r.get("phase_alignment", [])
        ]

        secured = sum(
            1 for r in phase_resources
            if r.get("availability_status") == AvailabilityStatus.SECURED.value
        )
        in_discussion = sum(
            1 for r in phase_resources
            if r.get("availability_status") == AvailabilityStatus.IN_DISCUSSION.value
        )
        unresolved = sum(
            1 for r in phase_resources
            if r.get("availability_status") in [
                AvailabilityStatus.UNRESOLVED.value,
                AvailabilityStatus.UNKNOWN.value,
            ]
        )

        total = len(phase_resources)
        readiness_score = secured / total if total > 0 else 0.0

        return {
            "phase": phase,
            "total_resources": total,
            "secured_count": secured,
            "in_discussion_count": in_discussion,
            "unresolved_count": unresolved,
            "resource_readiness_score": readiness_score,
            "has_gaps": unresolved > 0,
        }
