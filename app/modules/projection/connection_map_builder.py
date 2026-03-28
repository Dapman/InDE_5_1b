"""
InDE v4.8 - Connection Map Builder

Builds a connection map for a completing pursuit by identifying:
  - IML patterns that were applied during coaching decisions
  - IKF federation contributions (cross-org patterns, if IKF connected)
  - Cross-pursuit connections (other pursuits that share the same patterns)
  - Cross-domain connections (patterns that crossed archetype boundaries)

Connection types:
  WITHIN_PURSUIT    - IML pattern applied within this pursuit
  CROSS_PURSUIT     - pattern shared with other pursuits in this org
  CROSS_DOMAIN      - pattern from a different archetype family
  FEDERATION        - pattern contributed via IKF federation (if available)

Data sources (read-only, no modifications):
  - iml_decisions collection (or equivalent in IML module)
  - momentum_patterns collection (from v4.4 IML momentum engine)
  - IKF contribution records (if IKF connected)
  - outcome_formulator readiness snapshots (from v4.6)

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger("inde.projection.connection_map")


@dataclass
class Connection:
    """A single pattern connection in the connection map."""
    connection_type: str  # WITHIN_PURSUIT, CROSS_PURSUIT, CROSS_DOMAIN, FEDERATION
    pattern_id: str
    pattern_description: str
    applied_at_phase: str
    influence_score: float  # 0.0-1.0
    outcome_attribution: Optional[str]  # which artifact dimension was influenced
    source_pursuit_id: Optional[str]  # for CROSS_PURSUIT and FEDERATION


@dataclass
class ConnectionMap:
    """Complete connection map for a pursuit."""
    pursuit_id: str
    connections: List[Connection] = field(default_factory=list)
    iml_pattern_count: int = 0
    ikf_contribution_count: int = 0
    cross_pursuit_count: int = 0
    cross_domain_count: int = 0
    strongest_connection: Optional[Connection] = None
    federation_available: bool = False


class ConnectionMapBuilder:
    """
    Constructs the Connection Map from IML decision records,
    IKF contributions, and cross-pursuit pattern overlap.
    """

    def __init__(self, db):
        """
        Initialize ConnectionMapBuilder.

        Args:
            db: Database instance for querying patterns
        """
        self.db = db

    def build(self, pursuit_id: str) -> ConnectionMap:
        """
        Main entry point. Returns a ConnectionMap for the given pursuit.

        Args:
            pursuit_id: The pursuit to build connections for

        Returns:
            ConnectionMap with all identified connections
        """
        logger.info(f"[ConnectionMap] Building for pursuit: {pursuit_id}")
        connection_map = ConnectionMap(pursuit_id=pursuit_id)

        # Source 1: IML decision records for this pursuit
        iml_connections = self._extract_iml_connections(pursuit_id)
        connection_map.connections.extend(iml_connections)
        connection_map.iml_pattern_count = len(iml_connections)

        # Source 2: Cross-pursuit pattern overlap
        cross_pursuit = self._find_cross_pursuit_connections(
            pursuit_id, iml_connections
        )
        connection_map.connections.extend(cross_pursuit)
        connection_map.cross_pursuit_count = len(cross_pursuit)

        # Source 3: Cross-domain connections
        cross_domain = self._find_cross_domain_connections(iml_connections)
        connection_map.connections.extend(cross_domain)
        connection_map.cross_domain_count = len(cross_domain)

        # Source 4: IKF federation contributions (graceful if unavailable)
        ikf_connections, federation_available = self._extract_ikf_contributions(
            pursuit_id
        )
        connection_map.connections.extend(ikf_connections)
        connection_map.ikf_contribution_count = len(ikf_connections)
        connection_map.federation_available = federation_available

        # Find strongest connection
        if connection_map.connections:
            connection_map.strongest_connection = max(
                connection_map.connections,
                key=lambda c: c.influence_score
            )

        logger.info(
            f"[ConnectionMap] Built for {pursuit_id}: "
            f"{len(connection_map.connections)} total connections"
        )
        return connection_map

    def _extract_iml_connections(self, pursuit_id: str) -> List[Connection]:
        """Extract IML patterns that influenced coaching for this pursuit."""
        connections = []

        if not self.db:
            return connections

        try:
            # Query IML decision records - collection name may vary
            decisions = list(self.db.iml_decisions.find(
                {"pursuit_id": pursuit_id}
            ).sort("timestamp", 1))

            for decision in decisions:
                pattern_id = decision.get("pattern_id", "")
                if not pattern_id:
                    continue

                # Get pattern metadata
                pattern_meta = self.db.momentum_patterns.find_one(
                    {"pattern_id": pattern_id},
                    {"description": 1, "archetype": 1, "domain": 1}
                ) or {}

                connections.append(Connection(
                    connection_type="WITHIN_PURSUIT",
                    pattern_id=pattern_id,
                    pattern_description=pattern_meta.get(
                        "description", f"Pattern: {pattern_id[:8]}"
                    ),
                    applied_at_phase=decision.get("pursuit_phase", "unknown"),
                    influence_score=float(decision.get("lift_applied", 0.5)),
                    outcome_attribution=decision.get("dimension_influenced"),
                    source_pursuit_id=None,
                ))

        except Exception as e:
            logger.debug(f"[ConnectionMap] Error extracting IML connections: {e}")

        return connections

    def _find_cross_pursuit_connections(
        self, pursuit_id: str, iml_connections: List[Connection]
    ) -> List[Connection]:
        """Find other pursuits (in same org) that share patterns with this one."""
        if not iml_connections or not self.db:
            return []

        pattern_ids = [c.pattern_id for c in iml_connections if c.pattern_id]
        if not pattern_ids:
            return []

        connections = []

        try:
            sharing_pursuits = list(self.db.iml_decisions.aggregate([
                {"$match": {
                    "pattern_id": {"$in": pattern_ids},
                    "pursuit_id": {"$ne": pursuit_id},
                }},
                {"$group": {
                    "_id": "$pursuit_id",
                    "shared_patterns": {"$addToSet": "$pattern_id"},
                    "avg_lift": {"$avg": "$lift_applied"},
                }},
                {"$limit": 10},
            ]))

            for sp in sharing_pursuits:
                shared_count = len(sp.get("shared_patterns", []))
                influence = min(1.0, shared_count / max(len(pattern_ids), 1))
                connections.append(Connection(
                    connection_type="CROSS_PURSUIT",
                    pattern_id="|".join(sp.get("shared_patterns", [])[:3]),
                    pattern_description=(
                        f"{shared_count} shared pattern(s) with a parallel pursuit"
                    ),
                    applied_at_phase="cross_pursuit",
                    influence_score=round(influence, 3),
                    outcome_attribution=None,
                    source_pursuit_id=str(sp["_id"]),
                ))

        except Exception as e:
            logger.debug(f"[ConnectionMap] Error finding cross-pursuit: {e}")

        return connections

    def _find_cross_domain_connections(
        self, iml_connections: List[Connection]
    ) -> List[Connection]:
        """
        Identify patterns that originated from a different archetype family
        (cross-domain intelligence contribution).
        """
        if not self.db:
            return []

        connections = []

        for c in iml_connections:
            if not c.pattern_id:
                continue

            try:
                pattern = self.db.momentum_patterns.find_one(
                    {"pattern_id": c.pattern_id, "cross_domain": True},
                    {"source_archetype": 1, "description": 1}
                )
                if pattern:
                    connections.append(Connection(
                        connection_type="CROSS_DOMAIN",
                        pattern_id=c.pattern_id,
                        pattern_description=(
                            f"Pattern from {pattern.get('source_archetype', 'adjacent')} "
                            "domain applied to this pursuit"
                        ),
                        applied_at_phase=c.applied_at_phase,
                        influence_score=min(1.0, c.influence_score * 1.1),  # small boost
                        outcome_attribution=c.outcome_attribution,
                        source_pursuit_id=None,
                    ))
            except Exception:
                pass

        return connections

    def _extract_ikf_contributions(
        self, pursuit_id: str
    ) -> Tuple[List[Connection], bool]:
        """
        Extract IKF federation contributions for this pursuit.
        Gracefully returns empty list if IKF is not connected.
        """
        if not self.db:
            return [], False

        try:
            ikf_records = list(self.db.ikf_contributions.find(
                {"pursuit_id": pursuit_id, "confidence": {"$gte": 0.6}}
            ))
            connections = []

            for record in ikf_records:
                connections.append(Connection(
                    connection_type="FEDERATION",
                    pattern_id=record.get("pattern_id", ""),
                    pattern_description=(
                        "Cross-organization intelligence contribution "
                        f"(confidence: {record.get('confidence', 0.0):.2f})"
                    ),
                    applied_at_phase=record.get("applied_phase", "unknown"),
                    influence_score=float(record.get("confidence", 0.6)),
                    outcome_attribution=record.get("dimension_influenced"),
                    source_pursuit_id=None,
                ))

            return connections, True

        except Exception as e:
            logger.info(
                f"[ConnectionMap] IKF not available - {e}. "
                "Proceeding without federation contributions."
            )
            return [], False
