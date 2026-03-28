"""
InDE MVP v5.1b.0 - IRC Resource Entry Manager

Primary Deliverable B: Creates and maintains .resource artifacts from
detected signals. The Resource Entry Manager is the persistence layer
between the signal detector and the canvas.

Core Operations:
- create_or_update: Creates/updates .resource entries from signals
- enrich_from_coaching_context: Updates fields from follow-up signals
- get_canvas_snapshot: Returns all entries organized by phase/category
- get_signal_density: Returns consolidation eligibility metrics

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from enum import Enum
from bson import ObjectId

logger = logging.getLogger("inde.irc.resource_manager")


# =============================================================================
# ENUMS
# =============================================================================

class ResourceCategory(str, Enum):
    HUMAN_CAPITAL = "HUMAN_CAPITAL"
    CAPITAL_EQUIPMENT = "CAPITAL_EQUIPMENT"
    DATA_AND_IP = "DATA_AND_IP"
    SERVICES = "SERVICES"
    FINANCIAL = "FINANCIAL"


class AvailabilityStatus(str, Enum):
    SECURED = "SECURED"           # display: "In Place"
    IN_DISCUSSION = "IN_DISCUSSION"  # display: "Being Arranged"
    UNRESOLVED = "UNRESOLVED"     # display: "Still Open"
    UNKNOWN = "UNKNOWN"           # display: "Not Yet Explored"


class CostConfidence(str, Enum):
    KNOWN = "KNOWN"               # display: "Confirmed Figure"
    ESTIMATED = "ESTIMATED"       # display: "Working Estimate"
    ROUGH_ORDER = "ROUGH_ORDER"   # display: "Rough Order of Magnitude"
    UNKNOWN = "UNKNOWN"           # display: "Not Yet Estimated"


class DurationType(str, Enum):
    ONE_TIME = "ONE_TIME"
    RECURRING = "RECURRING"
    SUSTAINED = "SUSTAINED"
    UNKNOWN = "UNKNOWN"


class CostType(str, Enum):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"
    ONE_TIME = "ONE_TIME"
    RECURRING = "RECURRING"
    UNKNOWN = "UNKNOWN"


class Criticality(str, Enum):
    ESSENTIAL = "ESSENTIAL"
    IMPORTANT = "IMPORTANT"
    HELPFUL = "HELPFUL"
    UNKNOWN = "UNKNOWN"


class PhaseAlignment(str, Enum):
    PITCH = "PITCH"
    DE_RISK = "DE_RISK"
    DEPLOY = "DEPLOY"
    ACROSS_ALL = "ACROSS_ALL"


# =============================================================================
# RESOURCE ENTRY MANAGER
# =============================================================================

class ResourceEntryManager:
    """
    Manages .resource artifact lifecycle.
    """

    SCHEMA_VERSION = "1.0"
    SIMILARITY_THRESHOLD = 0.80  # For fuzzy deduplication

    def __init__(self, db):
        """
        Initialize ResourceEntryManager.

        Args:
            db: Database instance
        """
        self.db = db

    def create_or_update(
        self,
        pursuit_id: str,
        signal: Any,
        llm_enrichment: Dict[str, Any],
    ) -> str:
        """
        Create a new .resource entry or update existing if signal references
        a resource already captured (fuzzy name match).

        Args:
            pursuit_id: The pursuit ID
            signal: ResourceSignal from detection
            llm_enrichment: LLM extraction data (resource_name, category, etc.)

        Returns:
            The resource artifact_id (str)
        """
        resource_name = llm_enrichment.get("resource_name") or "Unspecified Resource"
        category = llm_enrichment.get("category", "UNKNOWN")

        # Validate category
        if category not in [e.value for e in ResourceCategory]:
            category = "SERVICES"  # Default fallback

        # Check for existing resource with similar name
        existing = self._find_similar_resource(pursuit_id, resource_name)

        if existing:
            # Update existing resource
            return self._update_resource(
                existing["_id"],
                signal,
                llm_enrichment,
            )
        else:
            # Create new resource
            return self._create_resource(
                pursuit_id,
                signal,
                llm_enrichment,
                resource_name,
                category,
            )

    def _create_resource(
        self,
        pursuit_id: str,
        signal: Any,
        llm_enrichment: Dict[str, Any],
        resource_name: str,
        category: str,
    ) -> str:
        """Create a new resource entry."""
        now = datetime.now(timezone.utc)

        # Determine initial values
        uncertainty_flag = getattr(signal, 'uncertainty_flag', False)
        availability = AvailabilityStatus.UNKNOWN.value

        if llm_enrichment.get("uncertainty_flag", False) or uncertainty_flag:
            availability = AvailabilityStatus.UNRESOLVED.value

        # Build document
        doc = {
            "pursuit_id": pursuit_id,
            "schema_version": self.SCHEMA_VERSION,
            "created_at": now,
            "modified_at": now,
            "resource_name": resource_name,
            "category": category,
            "phase_alignment": [PhaseAlignment.ACROSS_ALL.value],
            "duration_type": DurationType.UNKNOWN.value,
            "duration_description": "",
            "cost_estimate_low": None,
            "cost_estimate_high": None,
            "cost_type": CostType.UNKNOWN.value,
            "cost_confidence": CostConfidence.UNKNOWN.value,
            "availability_status": availability,
            "availability_notes": "",
            "criticality": Criticality.UNKNOWN.value,
            "challenge_registered": uncertainty_flag,
            "source_turns": [getattr(signal, 'turn_id', 'unknown')],
            "irc_included": False,
            "raw_signal_text": getattr(signal, 'raw_text', '')[:500],
        }

        # Insert
        result = self.db.db.resource_entries.insert_one(doc)
        artifact_id = str(result.inserted_id)

        logger.info(
            f"[ResourceManager] Created resource '{resource_name}' "
            f"({category}) for pursuit {pursuit_id}: {artifact_id}"
        )

        return artifact_id

    def _update_resource(
        self,
        resource_id: ObjectId,
        signal: Any,
        llm_enrichment: Dict[str, Any],
    ) -> str:
        """Update an existing resource entry from follow-up signal."""
        now = datetime.now(timezone.utc)
        turn_id = getattr(signal, 'turn_id', 'unknown')

        update = {
            "$set": {
                "modified_at": now,
            },
            "$addToSet": {
                "source_turns": turn_id,
            },
        }

        # Update availability if signal suggests it
        if llm_enrichment.get("uncertainty_flag", False):
            update["$set"]["challenge_registered"] = True

        self.db.db.resource_entries.update_one(
            {"_id": resource_id},
            update,
        )

        artifact_id = str(resource_id)
        logger.info(f"[ResourceManager] Updated resource: {artifact_id}")

        return artifact_id

    def _find_similar_resource(
        self,
        pursuit_id: str,
        resource_name: str,
    ) -> Optional[Dict]:
        """
        Find existing resource with similar name.
        Uses simple token overlap for similarity (cosine similarity approximation).
        """
        existing = list(self.db.db.resource_entries.find({"pursuit_id": pursuit_id}))

        if not existing:
            return None

        # Normalize name for comparison
        name_tokens = set(resource_name.lower().split())

        for resource in existing:
            existing_name = resource.get("resource_name", "")
            existing_tokens = set(existing_name.lower().split())

            # Calculate Jaccard similarity (approximation of semantic similarity)
            if not name_tokens or not existing_tokens:
                continue

            intersection = len(name_tokens & existing_tokens)
            union = len(name_tokens | existing_tokens)

            similarity = intersection / union if union > 0 else 0

            if similarity >= self.SIMILARITY_THRESHOLD:
                logger.debug(
                    f"[ResourceManager] Found similar resource: "
                    f"'{resource_name}' ~ '{existing_name}' (sim={similarity:.2f})"
                )
                return resource

        return None

    def enrich_from_coaching_context(
        self,
        resource_id: str,
        turn_id: str,
        enrichment_type: str,
        extracted_data: Dict[str, Any],
    ) -> Dict:
        """
        Update specific fields on an existing resource entry.

        Args:
            resource_id: The resource artifact ID
            turn_id: Coaching session turn ID
            enrichment_type: "AVAILABILITY" | "COST" | "TIMING" | "CRITICALITY"
            extracted_data: Field values to update

        Returns:
            Updated resource record
        """
        now = datetime.now(timezone.utc)

        update_fields = {"modified_at": now}

        if enrichment_type == "AVAILABILITY":
            if "status" in extracted_data:
                update_fields["availability_status"] = extracted_data["status"]
            if "notes" in extracted_data:
                update_fields["availability_notes"] = extracted_data["notes"]

        elif enrichment_type == "COST":
            if "low" in extracted_data:
                update_fields["cost_estimate_low"] = extracted_data["low"]
            if "high" in extracted_data:
                update_fields["cost_estimate_high"] = extracted_data["high"]
            if "confidence" in extracted_data:
                update_fields["cost_confidence"] = extracted_data["confidence"]
            if "type" in extracted_data:
                update_fields["cost_type"] = extracted_data["type"]

        elif enrichment_type == "TIMING":
            if "phase" in extracted_data:
                update_fields["phase_alignment"] = extracted_data["phase"]
            if "duration_type" in extracted_data:
                update_fields["duration_type"] = extracted_data["duration_type"]
            if "description" in extracted_data:
                update_fields["duration_description"] = extracted_data["description"]

        elif enrichment_type == "CRITICALITY":
            if "level" in extracted_data:
                update_fields["criticality"] = extracted_data["level"]

        # Update in database
        self.db.db.resource_entries.update_one(
            {"_id": ObjectId(resource_id)},
            {
                "$set": update_fields,
                "$addToSet": {"source_turns": turn_id},
            },
        )

        # Return updated document
        return self.db.db.resource_entries.find_one({"_id": ObjectId(resource_id)})

    def get_canvas_snapshot(self, pursuit_id: str) -> Dict[str, Any]:
        """
        Return all .resource entries organized by phase and category.

        Args:
            pursuit_id: The pursuit ID

        Returns:
            Dict with resources organized for canvas display
        """
        resources = list(self.db.db.resource_entries.find({"pursuit_id": pursuit_id}))

        # Organize by phase
        by_phase = {phase.value: [] for phase in PhaseAlignment}
        for resource in resources:
            phases = resource.get("phase_alignment", [PhaseAlignment.ACROSS_ALL.value])
            for phase in phases:
                if phase in by_phase:
                    by_phase[phase].append(self._serialize_resource(resource))

        # Organize by category
        by_category = {cat.value: [] for cat in ResourceCategory}
        for resource in resources:
            category = resource.get("category", "SERVICES")
            if category in by_category:
                by_category[category].append(self._serialize_resource(resource))

        return {
            "pursuit_id": pursuit_id,
            "total_resources": len(resources),
            "resources_by_phase": by_phase,
            "resources_by_category": by_category,
            "resources": [self._serialize_resource(r) for r in resources],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_signal_density(self, pursuit_id: str) -> Dict[str, Any]:
        """
        Return signal density metrics for consolidation eligibility.

        Returns:
            {
                total_entries: int,
                unresolved_count: int,
                unknown_cost_count: int,
                phases_with_resources: list,
                consolidation_eligible: bool
            }

        Consolidation eligible when:
        - total_entries >= 4, OR
        - (unresolved_count >= 1 AND unknown_cost_count >= 2), OR
        - (total_entries >= 2 AND any entry has cost data)
        """
        resources = list(self.db.db.resource_entries.find({"pursuit_id": pursuit_id}))

        total = len(resources)
        unresolved = sum(
            1 for r in resources
            if r.get("availability_status") in [
                AvailabilityStatus.UNRESOLVED.value,
                AvailabilityStatus.UNKNOWN.value
            ]
        )
        unknown_cost = sum(
            1 for r in resources
            if r.get("cost_confidence") == CostConfidence.UNKNOWN.value
        )
        has_cost_data = any(
            r.get("cost_estimate_low") is not None or
            r.get("cost_estimate_high") is not None
            for r in resources
        )

        # Collect phases
        phases = set()
        for r in resources:
            for phase in r.get("phase_alignment", []):
                phases.add(phase)

        # Determine eligibility
        eligible = (
            total >= 4 or
            (unresolved >= 1 and unknown_cost >= 2) or
            (total >= 2 and has_cost_data)
        )

        return {
            "total_entries": total,
            "unresolved_count": unresolved,
            "unknown_cost_count": unknown_cost,
            "phases_with_resources": list(phases),
            "has_cost_data": has_cost_data,
            "consolidation_eligible": eligible,
        }

    def get_resource(self, resource_id: str) -> Optional[Dict]:
        """Get a single resource by ID."""
        try:
            resource = self.db.db.resource_entries.find_one(
                {"_id": ObjectId(resource_id)}
            )
            return self._serialize_resource(resource) if resource else None
        except Exception as e:
            logger.error(f"[ResourceManager] Error getting resource: {e}")
            return None

    def get_resources_for_pursuit(self, pursuit_id: str) -> List[Dict]:
        """Get all resources for a pursuit."""
        resources = list(self.db.db.resource_entries.find({"pursuit_id": pursuit_id}))
        return [self._serialize_resource(r) for r in resources]

    def mark_irc_included(self, resource_ids: List[str]) -> int:
        """Mark resources as included in an IRC canvas."""
        result = self.db.db.resource_entries.update_many(
            {"_id": {"$in": [ObjectId(rid) for rid in resource_ids]}},
            {"$set": {"irc_included": True, "modified_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    def _serialize_resource(self, resource: Dict) -> Dict:
        """Serialize a resource document for API response."""
        if not resource:
            return {}

        return {
            "artifact_id": str(resource.get("_id", "")),
            "pursuit_id": resource.get("pursuit_id", ""),
            "schema_version": resource.get("schema_version", "1.0"),
            "created_at": resource.get("created_at", "").isoformat()
                if hasattr(resource.get("created_at"), 'isoformat') else str(resource.get("created_at", "")),
            "modified_at": resource.get("modified_at", "").isoformat()
                if hasattr(resource.get("modified_at"), 'isoformat') else str(resource.get("modified_at", "")),
            "resource_name": resource.get("resource_name", ""),
            "category": resource.get("category", "SERVICES"),
            "phase_alignment": resource.get("phase_alignment", []),
            "duration_type": resource.get("duration_type", "UNKNOWN"),
            "duration_description": resource.get("duration_description", ""),
            "cost_estimate_low": resource.get("cost_estimate_low"),
            "cost_estimate_high": resource.get("cost_estimate_high"),
            "cost_type": resource.get("cost_type", "UNKNOWN"),
            "cost_confidence": resource.get("cost_confidence", "UNKNOWN"),
            "availability_status": resource.get("availability_status", "UNKNOWN"),
            "availability_notes": resource.get("availability_notes", ""),
            "criticality": resource.get("criticality", "UNKNOWN"),
            "challenge_registered": resource.get("challenge_registered", False),
            "source_turns": resource.get("source_turns", []),
            "irc_included": resource.get("irc_included", False),
        }
