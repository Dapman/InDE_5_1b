"""
User Data Migration Script

Migrates a single user's data from one InDE MongoDB database to another.
Copies: user account, pursuits, artifacts, conversation history, scaffolding,
temporal events, time allocations, milestones, and telemetry.

Usage:
    python migrate_user_data.py --email director@indeverse.com \
        --source mongodb://localhost:27017/inde_4_5 \
        --target mongodb://localhost:27017/inde_4_6

Or using environment variables:
    SOURCE_MONGODB_URL=mongodb://localhost:27017/inde_4_5 \
    TARGET_MONGODB_URL=mongodb://localhost:27017/inde_4_6 \
    python migrate_user_data.py --email director@indeverse.com
"""

import argparse
import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# Collections that contain user-specific data (keyed by user_id)
USER_COLLECTIONS = [
    "users",                    # User account
    "pursuits",                 # User's pursuits
    "artifacts",                # Pursuit artifacts (linked via pursuit_id)
    "conversation_history",     # Coaching conversations
    "scaffolding",              # Vision/fear/hypothesis scaffolding
    "scaffolding_snapshots",    # Scaffolding version history
    "temporal_events",          # Time-based events
    "time_allocations",         # Time tracking
    "pursuit_milestones",       # Milestone tracking
    "telemetry_events",         # Behavioral telemetry (keyed by gii_id)
    "momentum_snapshots",       # IML momentum data
    "coaching_sessions",        # Coaching session data
    "experiment_results",       # Experiment/validation results
    "retrospectives",           # Pursuit retrospectives
    "elevator_pitches",         # Generated pitches
    "pitch_decks",              # Generated pitch decks
    "share_links",              # Artifact share links
    "notifications",            # User notifications
]

# Collections that link via pursuit_id (need pursuit IDs first)
PURSUIT_LINKED_COLLECTIONS = [
    "artifacts",
    "conversation_history",
    "scaffolding",
    "scaffolding_snapshots",
    "temporal_events",
    "time_allocations",
    "pursuit_milestones",
    "momentum_snapshots",
    "coaching_sessions",
    "experiment_results",
    "retrospectives",
    "elevator_pitches",
    "pitch_decks",
    "share_links",
]


def parse_mongo_url(url: str) -> tuple:
    """Parse MongoDB URL into (connection_string, database_name)."""
    # URL format: mongodb://host:port/database
    if "/" in url.split("://")[1]:
        parts = url.rsplit("/", 1)
        return parts[0], parts[1]
    else:
        return url, "inde"


def migrate_user_data(
    email: str,
    source_url: str,
    target_url: str,
    dry_run: bool = False
) -> dict:
    """
    Migrate all data for a user from source to target database.

    Args:
        email: User's email address
        source_url: Source MongoDB URL (e.g., mongodb://localhost:27017/inde_4_5)
        target_url: Target MongoDB URL (e.g., mongodb://localhost:27017/inde_4_6)
        dry_run: If True, only report what would be migrated

    Returns:
        dict with migration statistics
    """
    stats = {
        "email": email,
        "source": source_url,
        "target": target_url,
        "dry_run": dry_run,
        "collections": {},
        "errors": [],
        "started_at": datetime.utcnow().isoformat(),
    }

    # Parse URLs
    source_conn, source_db_name = parse_mongo_url(source_url)
    target_conn, target_db_name = parse_mongo_url(target_url)

    print(f"Source: {source_conn} / {source_db_name}")
    print(f"Target: {target_conn} / {target_db_name}")
    print(f"User email: {email}")
    print(f"Dry run: {dry_run}")
    print("-" * 60)

    # Connect to databases
    source_client = MongoClient(source_conn)
    target_client = MongoClient(target_conn)

    source_db = source_client[source_db_name]
    target_db = target_client[target_db_name]

    # Step 1: Find the user
    print("\n[1] Finding user...")
    user = source_db.users.find_one({"email": email})

    if not user:
        stats["errors"].append(f"User not found: {email}")
        print(f"ERROR: User not found with email: {email}")
        return stats

    user_id = user.get("user_id")
    gii_id = user.get("gii_id")

    print(f"    Found user: {user.get('display_name', 'Unknown')} (user_id: {user_id})")
    print(f"    GII: {gii_id}")

    # Step 2: Get all pursuit IDs for this user
    print("\n[2] Finding pursuits...")
    pursuits = list(source_db.pursuits.find({"user_id": user_id}))
    pursuit_ids = [p.get("pursuit_id") for p in pursuits]

    print(f"    Found {len(pursuits)} pursuits")
    for p in pursuits:
        print(f"      - {p.get('pursuit_id')}: {p.get('title', 'Untitled')}")

    # Step 3: Migrate user document
    print("\n[3] Migrating user document...")
    if not dry_run:
        # Check if user already exists in target
        existing = target_db.users.find_one({"user_id": user_id})
        if existing:
            print(f"    User already exists in target, updating...")
            target_db.users.replace_one({"user_id": user_id}, user)
        else:
            target_db.users.insert_one(user)
        stats["collections"]["users"] = {"migrated": 1, "action": "upsert"}
    else:
        stats["collections"]["users"] = {"would_migrate": 1}
    print(f"    {'Would migrate' if dry_run else 'Migrated'} user document")

    # Step 4: Migrate pursuits
    print("\n[4] Migrating pursuits...")
    if not dry_run:
        for pursuit in pursuits:
            existing = target_db.pursuits.find_one({"pursuit_id": pursuit["pursuit_id"]})
            if existing:
                target_db.pursuits.replace_one({"pursuit_id": pursuit["pursuit_id"]}, pursuit)
            else:
                target_db.pursuits.insert_one(pursuit)
        stats["collections"]["pursuits"] = {"migrated": len(pursuits), "action": "upsert"}
    else:
        stats["collections"]["pursuits"] = {"would_migrate": len(pursuits)}
    print(f"    {'Would migrate' if dry_run else 'Migrated'} {len(pursuits)} pursuits")

    # Step 5: Migrate pursuit-linked collections
    print("\n[5] Migrating pursuit-linked data...")
    for collection_name in PURSUIT_LINKED_COLLECTIONS:
        if collection_name in ["pursuits"]:  # Already handled
            continue

        try:
            collection = source_db[collection_name]

            # Find documents linked to user's pursuits
            docs = list(collection.find({"pursuit_id": {"$in": pursuit_ids}}))

            if docs:
                if not dry_run:
                    target_collection = target_db[collection_name]
                    for doc in docs:
                        # Use appropriate unique key based on collection
                        if "_id" in doc:
                            existing = target_collection.find_one({"_id": doc["_id"]})
                            if existing:
                                target_collection.replace_one({"_id": doc["_id"]}, doc)
                            else:
                                target_collection.insert_one(doc)
                    stats["collections"][collection_name] = {"migrated": len(docs), "action": "upsert"}
                else:
                    stats["collections"][collection_name] = {"would_migrate": len(docs)}

                print(f"    {collection_name}: {'Would migrate' if dry_run else 'Migrated'} {len(docs)} documents")
            else:
                stats["collections"][collection_name] = {"migrated": 0, "note": "no documents"}

        except Exception as e:
            stats["errors"].append(f"{collection_name}: {str(e)}")
            print(f"    {collection_name}: ERROR - {e}")

    # Step 6: Migrate telemetry (keyed by gii_id)
    print("\n[6] Migrating telemetry events...")
    if gii_id:
        try:
            telemetry_docs = list(source_db.telemetry_events.find({"gii_id": gii_id}))
            if telemetry_docs:
                if not dry_run:
                    for doc in telemetry_docs:
                        existing = target_db.telemetry_events.find_one({"_id": doc["_id"]})
                        if not existing:
                            target_db.telemetry_events.insert_one(doc)
                    stats["collections"]["telemetry_events"] = {"migrated": len(telemetry_docs)}
                else:
                    stats["collections"]["telemetry_events"] = {"would_migrate": len(telemetry_docs)}
                print(f"    telemetry_events: {'Would migrate' if dry_run else 'Migrated'} {len(telemetry_docs)} documents")
            else:
                print(f"    telemetry_events: No documents found for GII {gii_id}")
        except Exception as e:
            stats["errors"].append(f"telemetry_events: {str(e)}")
            print(f"    telemetry_events: ERROR - {e}")
    else:
        print(f"    telemetry_events: Skipped (no GII)")

    # Step 7: Migrate notifications (keyed by user_id)
    print("\n[7] Migrating notifications...")
    try:
        notifications = list(source_db.notifications.find({"user_id": user_id}))
        if notifications:
            if not dry_run:
                for doc in notifications:
                    existing = target_db.notifications.find_one({"_id": doc["_id"]})
                    if not existing:
                        target_db.notifications.insert_one(doc)
                stats["collections"]["notifications"] = {"migrated": len(notifications)}
            else:
                stats["collections"]["notifications"] = {"would_migrate": len(notifications)}
            print(f"    notifications: {'Would migrate' if dry_run else 'Migrated'} {len(notifications)} documents")
        else:
            print(f"    notifications: No documents found")
    except Exception as e:
        stats["errors"].append(f"notifications: {str(e)}")
        print(f"    notifications: ERROR - {e}")

    # Summary
    stats["completed_at"] = datetime.utcnow().isoformat()

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)

    total_migrated = sum(
        c.get("migrated", c.get("would_migrate", 0))
        for c in stats["collections"].values()
    )
    print(f"Total documents {'to migrate' if dry_run else 'migrated'}: {total_migrated}")

    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"]:
            print(f"  - {err}")
    else:
        print("\nNo errors encountered.")

    # Close connections
    source_client.close()
    target_client.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate user data between InDE MongoDB databases"
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address of the user to migrate"
    )
    parser.add_argument(
        "--source",
        default=os.environ.get("SOURCE_MONGODB_URL", "mongodb://localhost:27017/inde_4_5"),
        help="Source MongoDB URL (default: from SOURCE_MONGODB_URL env var)"
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("TARGET_MONGODB_URL", "mongodb://localhost:27017/inde_4_6"),
        help="Target MongoDB URL (default: from TARGET_MONGODB_URL env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("InDE User Data Migration")
    print("=" * 60)

    stats = migrate_user_data(
        email=args.email,
        source_url=args.source,
        target_url=args.target,
        dry_run=args.dry_run
    )

    if stats["errors"]:
        sys.exit(1)
    else:
        print("\nMigration completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
