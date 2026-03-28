"""
Migration: Add outcome_readiness MongoDB collection

InDE MVP v4.6.0 - The Outcome Engine

Creates the outcome_readiness collection with the correct indexes.
Safe to run on an existing database - uses createIndexes with checkExistingIndexes.

Run with: python migrations/add_outcome_readiness_collection.py
"""

import asyncio
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


async def migrate_async(db) -> None:
    """Create outcome_readiness collection and required indexes (async version)."""
    collection = db["outcome_readiness"]

    # Unique compound index: one record per pursuit x archetype x artifact_type
    await collection.create_index(
        [("pursuit_id", 1), ("archetype", 1), ("artifact_type", 1)],
        unique=True,
        name="outcome_readiness_unique_pursuit_artifact",
    )

    # Admin dashboard aggregate queries
    await collection.create_index(
        [("state", 1), ("updated_at", -1)],
        name="outcome_readiness_state_updated",
    )

    # Per-pursuit lookup
    await collection.create_index(
        [("pursuit_id", 1)],
        name="outcome_readiness_by_pursuit",
    )

    # Archetype aggregation
    await collection.create_index(
        [("archetype", 1), ("state", 1)],
        name="outcome_readiness_archetype_state",
    )

    print("outcome_readiness collection indexes created.")


def migrate(db) -> None:
    """Create outcome_readiness collection and required indexes (sync version)."""
    collection = db["outcome_readiness"]

    # Unique compound index: one record per pursuit x archetype x artifact_type
    collection.create_index(
        [("pursuit_id", 1), ("archetype", 1), ("artifact_type", 1)],
        unique=True,
        name="outcome_readiness_unique_pursuit_artifact",
    )

    # Admin dashboard aggregate queries
    collection.create_index(
        [("state", 1), ("updated_at", -1)],
        name="outcome_readiness_state_updated",
    )

    # Per-pursuit lookup
    collection.create_index(
        [("pursuit_id", 1)],
        name="outcome_readiness_by_pursuit",
    )

    # Archetype aggregation
    collection.create_index(
        [("archetype", 1), ("state", 1)],
        name="outcome_readiness_archetype_state",
    )

    print("outcome_readiness collection indexes created.")


if __name__ == "__main__":
    from pymongo import MongoClient

    MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB = os.environ.get("MONGODB_DB", "inde")

    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]

    migrate(db)
    print("Migration complete.")
