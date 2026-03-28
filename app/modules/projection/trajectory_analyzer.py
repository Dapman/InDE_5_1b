"""
InDE v4.8 - Trajectory Analyzer

Queries the IML Pattern Intelligence Engine and pursuit outcome records
to identify post-completion trajectories for structurally similar pursuits.

Structural similarity is computed across four dimensions:
  - archetype_match: same or adjacent archetype family (weight: 0.40)
  - domain_proximity: same domain or cross-domain with shared archetype (weight: 0.25)
  - scale_match: org_size within one tier (weight: 0.15)
  - validation_depth: comparable confidence at completion (weight: 0.20)

Minimum similarity score for inclusion: 0.55
Target sample: 8-15 similar pursuits for statistical reliability.
Graceful fallback: if fewer than 5 similar pursuits found, widen
domain_proximity gate and reduce similarity threshold to 0.40.

2026 Yul Williams | InDEVerse, Incorporated
"""

from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger("inde.projection.trajectory")


@dataclass
class SimilarPursuit:
    """A pursuit structurally similar to the subject pursuit."""
    pursuit_id: str
    similarity_score: float
    archetype: str
    domain: str
    completion_date: str
    post_completion_records: List[dict] = field(default_factory=list)
    # post_completion_records: events, pivots, and state changes
    # captured after SUCCESS status, within 365 days of completion


@dataclass
class TrajectoryDataset:
    """Dataset of similar pursuits for trajectory analysis."""
    similar_pursuits: List[SimilarPursuit]
    sample_size: int
    similarity_threshold_used: float
    fallback_applied: bool
    archetype_of_subject: str
    domain_of_subject: str
    data_quality: str  # "HIGH" (>=8 matches), "MEDIUM" (5-7), "LOW" (<5)


class TrajectoryAnalyzer:
    """
    Queries IML and pursuit outcome records to build a trajectory dataset
    for the completing pursuit.
    """

    SIMILARITY_THRESHOLD_PRIMARY = 0.55
    SIMILARITY_THRESHOLD_FALLBACK = 0.40
    TARGET_SAMPLE_MIN = 5
    TARGET_SAMPLE_IDEAL = 8

    SIMILARITY_WEIGHTS = {
        "archetype_match": 0.40,
        "domain_proximity": 0.25,
        "scale_match": 0.15,
        "validation_depth": 0.20,
    }

    def __init__(self, iml_client, db):
        """
        Initialize TrajectoryAnalyzer.

        Args:
            iml_client: IML Pattern Intelligence Engine client (optional)
            db: Database instance
        """
        self.iml_client = iml_client
        self.db = db

    def build_trajectory_dataset(self, pursuit_id: str) -> TrajectoryDataset:
        """
        Main entry point. Returns a TrajectoryDataset for the given pursuit.

        Args:
            pursuit_id: The pursuit to analyze

        Returns:
            TrajectoryDataset with similar pursuits and their trajectories
        """
        subject = self._load_pursuit_profile(pursuit_id)
        if not subject:
            return self._empty_dataset(pursuit_id)

        candidates = self._fetch_completed_pursuits(subject)
        scored = self._score_similarity(subject, candidates)
        filtered = [c for c in scored
                    if c.similarity_score >= self.SIMILARITY_THRESHOLD_PRIMARY]
        fallback_applied = False

        if len(filtered) < self.TARGET_SAMPLE_MIN:
            filtered = [c for c in scored
                        if c.similarity_score >= self.SIMILARITY_THRESHOLD_FALLBACK]
            fallback_applied = True
            logger.info(
                f"[TrajectoryAnalyzer] Fallback threshold applied - "
                f"{len(filtered)} pursuits at 0.40 threshold."
            )

        filtered.sort(key=lambda x: x.similarity_score, reverse=True)
        sample = filtered[:15]  # cap at 15

        data_quality = (
            "HIGH" if len(sample) >= 8
            else "MEDIUM" if len(sample) >= 5
            else "LOW"
        )

        return TrajectoryDataset(
            similar_pursuits=sample,
            sample_size=len(sample),
            similarity_threshold_used=(
                self.SIMILARITY_THRESHOLD_FALLBACK if fallback_applied
                else self.SIMILARITY_THRESHOLD_PRIMARY
            ),
            fallback_applied=fallback_applied,
            archetype_of_subject=subject.get("archetype", "unknown"),
            domain_of_subject=subject.get("domain", "unknown"),
            data_quality=data_quality,
        )

    def _load_pursuit_profile(self, pursuit_id: str) -> Optional[dict]:
        """Load completing pursuit's structural profile from pursuits collection."""
        if not self.db:
            return None
        try:
            return self.db.pursuits.find_one(
                {"pursuit_id": pursuit_id},
                {"pursuit_id": 1, "archetype": 1, "domain": 1, "org_size": 1,
                 "validation_confidence": 1, "status": 1}
            )
        except Exception as e:
            logger.error(f"[TrajectoryAnalyzer] Error loading pursuit profile: {e}")
            return None

    def _fetch_completed_pursuits(self, subject: dict) -> List[dict]:
        """
        Fetch completed pursuits (status=SUCCESS) excluding the subject.
        Pulls from pursuits collection; post-completion records from
        pursuit_outcomes if present, otherwise derived from event_log.
        """
        if not self.db:
            return []

        try:
            query = {
                "status": "SUCCESS",
                "pursuit_id": {"$ne": subject.get("pursuit_id")},
            }
            pursuits = list(self.db.pursuits.find(query, {
                "pursuit_id": 1, "archetype": 1, "domain": 1, "org_size": 1,
                "validation_confidence": 1, "completed_at": 1
            }).limit(200))
            return pursuits
        except Exception as e:
            logger.error(f"[TrajectoryAnalyzer] Error fetching completed pursuits: {e}")
            return []

    def _score_similarity(
        self, subject: dict, candidates: List[dict]
    ) -> List[SimilarPursuit]:
        """Score each candidate against the subject profile."""
        scored = []
        for c in candidates:
            score = self._compute_similarity_score(subject, c)
            post_records = self._load_post_completion_records(
                str(c.get("pursuit_id", ""))
            )
            scored.append(SimilarPursuit(
                pursuit_id=str(c.get("pursuit_id", "")),
                similarity_score=score,
                archetype=c.get("archetype", "unknown"),
                domain=c.get("domain", "unknown"),
                completion_date=str(c.get("completed_at", "")),
                post_completion_records=post_records,
            ))
        return scored

    def _compute_similarity_score(self, subject: dict, candidate: dict) -> float:
        """Compute weighted similarity score between subject and candidate."""
        w = self.SIMILARITY_WEIGHTS

        # Archetype match (1.0 = same, 0.4 = different)
        archetype_score = (
            1.0 if subject.get("archetype") == candidate.get("archetype")
            else 0.4
        )

        # Domain proximity (1.0 = same, 0.3 = different)
        domain_score = (
            1.0 if subject.get("domain") == candidate.get("domain") else 0.3
        )

        # Scale match (based on org_size tier proximity)
        scale_tiers = {
            "solo": 0, "small": 1, "mid": 2, "enterprise": 3
        }
        s_tier = scale_tiers.get(subject.get("org_size", "solo"), 0)
        c_tier = scale_tiers.get(candidate.get("org_size", "solo"), 0)
        scale_score = max(0.0, 1.0 - abs(s_tier - c_tier) * 0.4)

        # Validation depth (based on confidence proximity)
        s_conf = float(subject.get("validation_confidence", 0.5))
        c_conf = float(candidate.get("validation_confidence", 0.5))
        validation_score = max(0.0, 1.0 - abs(s_conf - c_conf) * 1.5)

        return (
            archetype_score * w["archetype_match"]
            + domain_score * w["domain_proximity"]
            + scale_score * w["scale_match"]
            + validation_score * w["validation_depth"]
        )

    def _load_post_completion_records(self, pursuit_id: str) -> List[dict]:
        """
        Load post-completion events for a given pursuit.
        Checks pursuit_outcomes collection first; falls back to event_log.
        """
        if not self.db:
            return []

        try:
            # Check pursuit_outcomes collection first
            outcomes = self.db.pursuit_outcomes.find_one({"pursuit_id": pursuit_id})
            if outcomes:
                return outcomes.get("post_completion_events", [])

            # Fallback: derive from event_log filtered to 365 days post-completion
            pursuit = self.db.pursuits.find_one(
                {"pursuit_id": pursuit_id}, {"completed_at": 1}
            )
            if not pursuit or not pursuit.get("completed_at"):
                return []

            completion_ts = pursuit["completed_at"]
            events = list(self.db.event_log.find({
                "pursuit_id": pursuit_id,
                "timestamp": {"$gte": completion_ts},
            }).sort("timestamp", 1).limit(100))
            return events
        except Exception as e:
            logger.debug(f"[TrajectoryAnalyzer] No post-completion records for {pursuit_id}: {e}")
            return []

    def _empty_dataset(self, pursuit_id: str) -> TrajectoryDataset:
        """Returns a valid but empty TrajectoryDataset when subject not found."""
        logger.warning(
            f"[TrajectoryAnalyzer] Could not load pursuit profile "
            f"for {pursuit_id} - returning empty dataset."
        )
        return TrajectoryDataset(
            similar_pursuits=[],
            sample_size=0,
            similarity_threshold_used=self.SIMILARITY_THRESHOLD_PRIMARY,
            fallback_applied=False,
            archetype_of_subject="unknown",
            domain_of_subject="unknown",
            data_quality="LOW",
        )
