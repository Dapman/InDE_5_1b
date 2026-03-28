"""
InDE MVP v5.1b.0 - GitHub Signal Ingester

Ingests GitHub activity signals for IDTFS Pillar 1/2 discovery.
Append-only, idempotent signal storage.

Signal types:
- push_commit: Commit activity from push events
- pr_opened: Pull request opened
- pr_merged: Pull request merged
- pr_reviewed: Pull request reviewed
- team_added: User added to team
- team_removed: User removed from team

Design invariants:
- Append-only: Signals are never overwritten or deleted
- Idempotent: delivery_id + signal_type is unique
- No RBAC mutation: Signals are informational, do not affect roles
- Sovereignty: No import path to coaching/maturity/fear/pursuit_content
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger("inde.connectors.github.signal_ingester")


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class IngestResult:
    """Result of signal ingestion."""
    signal_type: str
    github_login: str
    github_repo_full_name: str
    delivery_id: str
    action: str  # "ingested" | "duplicate" | "skipped" | "error"
    pursuit_id: Optional[str] = None
    is_primary_repo: Optional[bool] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class SummaryRecomputeResult:
    """Result of activity summary recomputation."""
    user_id: str
    signal_count_90d: int
    pillar_1_signal_strength: str  # "strong" | "moderate" | "weak" | "none"
    updated: bool


# =============================================================================
# GITHUB SIGNAL INGESTER
# =============================================================================

class GitHubSignalIngester:
    """
    Ingests GitHub activity signals for IDTFS Pillar 1/2 discovery.

    Design invariants:
    - Append-only: Signals are never overwritten or deleted
    - Idempotent: delivery_id + signal_type is unique
    - No RBAC mutation: Signals are informational, do not affect roles
    """

    def __init__(self, db, event_publisher=None):
        """
        Initialize the signal ingester.

        Args:
            db: MongoDB database instance
            event_publisher: Event publisher for audit events
        """
        self.db = db
        self.event_publisher = event_publisher

    async def ingest_push(
        self,
        org_id: str,
        payload: dict,
        delivery_id: str
    ) -> List[IngestResult]:
        """
        Ingest push event signals.

        Creates one signal per commit author in the push.

        Args:
            org_id: InDE organization ID
            payload: Webhook payload
            delivery_id: Delivery ID

        Returns:
            List of IngestResult for each signal created
        """
        results = []
        repo = payload.get("repository", {})
        github_repo_id = repo.get("id")
        github_repo_full_name = repo.get("full_name", "")
        commits = payload.get("commits", [])
        pusher = payload.get("pusher", {})
        pusher_login = pusher.get("name") or pusher.get("email", "").split("@")[0]

        # Get pursuit links for this repo
        pursuit_links = self._get_pursuit_links(org_id, github_repo_id)

        # Process each commit
        for idx, commit in enumerate(commits):
            author = commit.get("author", {})
            github_login = author.get("username") or author.get("name") or pusher_login

            if not github_login:
                continue

            # Create a unique delivery_id for each commit in the push
            commit_delivery_id = f"{delivery_id}-commit-{idx}"

            result = await self._ingest_signal(
                org_id=org_id,
                github_login=github_login,
                signal_type="push_commit",
                repo_full_name=github_repo_full_name,
                github_repo_id=github_repo_id,
                delivery_id=commit_delivery_id,
                occurred_at=datetime.now(timezone.utc),
                pursuit_links=pursuit_links,
                event_metadata={
                    "commit_sha": commit.get("id", "")[:12],
                    "commit_message": commit.get("message", "")[:100],
                    "ref": payload.get("ref", ""),
                }
            )
            results.append(result)

        return results

    async def ingest_pull_request(
        self,
        org_id: str,
        payload: dict,
        delivery_id: str
    ) -> IngestResult:
        """
        Ingest pull request event signals.

        Signal types based on action:
        - "opened" → pr_opened
        - "closed" + merged=True → pr_merged
        - "submitted" (review) → pr_reviewed

        Args:
            org_id: InDE organization ID
            payload: Webhook payload
            delivery_id: Delivery ID

        Returns:
            IngestResult
        """
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        github_repo_id = repo.get("id")
        github_repo_full_name = repo.get("full_name", "")

        # Determine signal type based on action
        if action == "opened":
            signal_type = "pr_opened"
            github_login = pr.get("user", {}).get("login", "")
        elif action == "closed" and pr.get("merged"):
            signal_type = "pr_merged"
            # For merge, attribute to the PR author
            github_login = pr.get("user", {}).get("login", "")
        elif action == "submitted":
            # This is from pull_request_review event
            signal_type = "pr_reviewed"
            review = payload.get("review", {})
            github_login = review.get("user", {}).get("login", "")
        else:
            # Skip other actions
            return IngestResult(
                signal_type="unknown",
                github_login="",
                github_repo_full_name=github_repo_full_name,
                delivery_id=delivery_id,
                action="skipped",
                error_message=f"Unhandled action: {action}"
            )

        if not github_login:
            return IngestResult(
                signal_type=signal_type,
                github_login="",
                github_repo_full_name=github_repo_full_name,
                delivery_id=delivery_id,
                action="skipped",
                error_message="No github_login found"
            )

        # Get pursuit links for this repo
        pursuit_links = self._get_pursuit_links(org_id, github_repo_id)

        return await self._ingest_signal(
            org_id=org_id,
            github_login=github_login,
            signal_type=signal_type,
            repo_full_name=github_repo_full_name,
            github_repo_id=github_repo_id,
            delivery_id=delivery_id,
            occurred_at=datetime.now(timezone.utc),
            pursuit_links=pursuit_links,
            event_metadata={
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title", "")[:100],
                "pr_state": pr.get("state"),
                "merged": pr.get("merged", False),
            }
        )

    async def ingest_team_activity(
        self,
        org_id: str,
        payload: dict,
        delivery_id: str,
        signal_type: str
    ) -> IngestResult:
        """
        Ingest team membership signals.

        Signal types:
        - "team_added": User added to team
        - "team_removed": User removed from team

        Args:
            org_id: InDE organization ID
            payload: Webhook payload
            delivery_id: Delivery ID
            signal_type: "team_added" or "team_removed"

        Returns:
            IngestResult
        """
        member = payload.get("member", {})
        team = payload.get("team", {})
        org = payload.get("organization", {})

        github_login = member.get("login", "")
        team_name = team.get("name", "")
        team_slug = team.get("slug", "")

        if not github_login:
            return IngestResult(
                signal_type=signal_type,
                github_login="",
                github_repo_full_name="",
                delivery_id=delivery_id,
                action="skipped",
                error_message="No github_login found"
            )

        # Team signals don't have a specific repo, so no pursuit_links
        return await self._ingest_signal(
            org_id=org_id,
            github_login=github_login,
            signal_type=signal_type,
            repo_full_name="",  # No repo for team events
            github_repo_id=0,
            delivery_id=delivery_id,
            occurred_at=datetime.now(timezone.utc),
            pursuit_links=[],
            event_metadata={
                "team_name": team_name,
                "team_slug": team_slug,
                "team_id": team.get("id"),
                "org_login": org.get("login"),
            }
        )

    async def recompute_activity_summary(
        self,
        org_id: str,
        user_id: str
    ) -> SummaryRecomputeResult:
        """
        Recompute activity summary for an innovator_profile.

        Calculates 90-day signal count and updates pillar_1_signal_strength.

        Args:
            org_id: InDE organization ID
            user_id: InDE user ID

        Returns:
            SummaryRecomputeResult with computed values
        """
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)

        # Count signals in the last 90 days
        signal_count = self.db.github_activity_signals.count_documents({
            "org_id": org_id,
            "user_id": user_id,
            "occurred_at": {"$gte": ninety_days_ago}
        })

        # Compute signal strength
        if signal_count >= 10:
            strength = "strong"
        elif signal_count >= 4:
            strength = "moderate"
        elif signal_count >= 1:
            strength = "weak"
        else:
            strength = "none"

        # Update innovator_profile
        result = self.db.innovator_profiles.update_one(
            {"org_id": org_id, "user_id": user_id},
            {
                "$set": {
                    "github_activity_summary": {
                        "signal_count_90d": signal_count,
                        "pillar_1_signal_strength": strength,
                        "last_computed_at": datetime.now(timezone.utc)
                    }
                }
            },
            upsert=True
        )

        return SummaryRecomputeResult(
            user_id=user_id,
            signal_count_90d=signal_count,
            pillar_1_signal_strength=strength,
            updated=result.modified_count > 0 or result.upserted_id is not None
        )

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _get_pursuit_links(
        self,
        org_id: str,
        github_repo_id: int
    ) -> List[dict]:
        """Get pursuit links for a GitHub repo."""
        if not github_repo_id:
            return []

        return list(self.db.pursuit_repo_links.find({
            "org_id": org_id,
            "github_repo_id": github_repo_id,
            "is_active": True,
        }))

    async def _ingest_signal(
        self,
        org_id: str,
        github_login: str,
        signal_type: str,
        repo_full_name: str,
        github_repo_id: int,
        delivery_id: str,
        occurred_at: datetime,
        pursuit_links: List[dict],
        event_metadata: Dict[str, Any]
    ) -> IngestResult:
        """
        Ingest a single signal into github_activity_signals.

        Idempotent: If delivery_id + signal_type already exists, returns duplicate.
        """
        # Check for duplicate
        existing = self.db.github_activity_signals.find_one({
            "github_delivery_id": delivery_id,
            "signal_type": signal_type
        })
        if existing:
            return IngestResult(
                signal_type=signal_type,
                github_login=github_login,
                github_repo_full_name=repo_full_name,
                delivery_id=delivery_id,
                action="duplicate"
            )

        # Look up user_id by github_login
        user_id = None
        user = self.db.users.find_one({"github_login": github_login})
        if user:
            user_id = str(user["_id"])
        else:
            # Try membership lookup
            membership = self.db.memberships.find_one({
                "org_id": org_id,
                "github_login": github_login,
                "status": "active"
            })
            if membership:
                user_id = membership.get("user_id")

        # Determine primary pursuit (if any)
        pursuit_id = None
        is_primary_repo = None
        if pursuit_links:
            primary_link = next((l for l in pursuit_links if l.get("is_primary")), None)
            if primary_link:
                pursuit_id = primary_link.get("pursuit_id")
                is_primary_repo = True
            else:
                # Use first link if no primary
                pursuit_id = pursuit_links[0].get("pursuit_id")
                is_primary_repo = False

        # Insert signal
        signal_doc = {
            "org_id": org_id,
            "user_id": user_id,
            "github_login": github_login,
            "signal_type": signal_type,
            "repo_full_name": repo_full_name,
            "github_repo_id": github_repo_id,
            "pursuit_id": pursuit_id,
            "is_primary_repo": is_primary_repo,
            "github_delivery_id": delivery_id,
            "event_metadata": event_metadata,
            "occurred_at": occurred_at,
            "ingested_at": datetime.now(timezone.utc),
        }

        try:
            self.db.github_activity_signals.insert_one(signal_doc)

            # Emit audit event
            if self.event_publisher:
                await self.event_publisher.publish("github.signal_ingested", {
                    "org_id": org_id,
                    "user_id": user_id,
                    "github_login": github_login,
                    "signal_type": signal_type,
                    "repo_full_name": repo_full_name,
                    "pursuit_id": pursuit_id,
                    "delivery_id": delivery_id,
                    "timestamp": occurred_at.isoformat()
                })

            logger.info(
                f"Ingested signal: {signal_type} from {github_login} "
                f"in {repo_full_name}"
            )

            return IngestResult(
                signal_type=signal_type,
                github_login=github_login,
                github_repo_full_name=repo_full_name,
                delivery_id=delivery_id,
                action="ingested",
                pursuit_id=pursuit_id,
                is_primary_repo=is_primary_repo,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Failed to ingest signal: {e}")
            return IngestResult(
                signal_type=signal_type,
                github_login=github_login,
                github_repo_full_name=repo_full_name,
                delivery_id=delivery_id,
                action="error",
                error_message=str(e)
            )
