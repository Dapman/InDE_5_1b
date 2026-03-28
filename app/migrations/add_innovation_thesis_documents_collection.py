"""
InDE MVP v4.7.0 - Innovation Thesis Documents Collection Migration

Creates the `innovation_thesis_documents` collection with appropriate indexes.

Collection Schema:
{
    "itd_id": str,           # Unique document ID
    "pursuit_id": str,       # Foreign key to pursuits
    "user_id": str,          # Foreign key to users
    "status": str,           # ITDGenerationStatus value
    "layers_completed": [],  # List of completed layer names
    "layers_failed": [],     # List of failed layer names
    "thesis_statement": {},  # ThesisStatementLayer
    "evidence_architecture": {},  # EvidenceArchitectureLayer
    "narrative_arc": {},     # NarrativeArcLayer
    "coachs_perspective": {},  # CoachsPerspectiveLayer
    "metrics_dashboard": {}, # MetricsDashboardLayer (placeholder)
    "future_pathways": {},   # FuturePathwaysLayer (placeholder)
    "pursuit_title": str,
    "archetype": str,
    "terminal_state": str,
    "created_at": datetime,
    "updated_at": datetime,
    "completed_at": datetime,
    "version": int
}

Usage:
    python -m migrations.add_innovation_thesis_documents_collection

2026 Yul Williams | InDEVerse, Incorporated
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def create_innovation_thesis_documents_collection():
    """Create the innovation_thesis_documents collection with indexes."""

    # Get MongoDB URL from environment
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017/inde")

    print(f"Connecting to MongoDB: {mongo_url}")
    client = AsyncIOMotorClient(mongo_url)

    # Parse database name from URL
    db_name = mongo_url.rsplit("/", 1)[-1].split("?")[0] if "/" in mongo_url else "inde"
    db = client[db_name]

    collection_name = "innovation_thesis_documents"

    print(f"Creating collection: {collection_name}")

    # Check if collection exists
    existing_collections = await db.list_collection_names()
    if collection_name in existing_collections:
        print(f"Collection {collection_name} already exists")
    else:
        # Create collection explicitly
        await db.create_collection(collection_name)
        print(f"Created collection: {collection_name}")

    collection = db[collection_name]

    # Create indexes
    print("Creating indexes...")

    # Primary lookup index
    await collection.create_index("itd_id", unique=True, name="idx_itd_id")
    print("  Created index: idx_itd_id (unique)")

    # Pursuit lookup index
    await collection.create_index("pursuit_id", name="idx_pursuit_id")
    print("  Created index: idx_pursuit_id")

    # User lookup index for listing user's ITDs
    await collection.create_index("user_id", name="idx_user_id")
    print("  Created index: idx_user_id")

    # Status index for finding incomplete ITDs
    await collection.create_index("status", name="idx_status")
    print("  Created index: idx_status")

    # Compound index for user + status queries
    await collection.create_index(
        [("user_id", 1), ("status", 1)],
        name="idx_user_status"
    )
    print("  Created compound index: idx_user_status")

    # Timestamp index for recent ITDs
    await collection.create_index(
        [("created_at", -1)],
        name="idx_created_at"
    )
    print("  Created index: idx_created_at")

    print(f"\nMigration complete: {collection_name} collection ready")

    client.close()


def main():
    """Run the migration."""
    asyncio.run(create_innovation_thesis_documents_collection())


if __name__ == "__main__":
    main()
