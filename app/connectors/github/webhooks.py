"""
InDE MVP v5.1b.0 - GitHub Webhook Handling

Webhook signature verification and event routing.
"""

import os
import hmac
import hashlib
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger("inde.connectors.github.webhooks")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256.

    GitHub sends the signature in the X-Hub-Signature-256 header as:
    sha256=<hex-digest>

    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid, False otherwise
    """
    webhook_secret = os.getenv("GITHUB_APP_WEBHOOK_SECRET")

    if not webhook_secret:
        logger.error("GITHUB_APP_WEBHOOK_SECRET not configured")
        return False

    if not signature:
        logger.warning("No signature provided")
        return False

    if not signature.startswith("sha256="):
        logger.warning(f"Invalid signature format: {signature[:20]}...")
        return False

    expected_signature = signature[7:]  # Remove 'sha256=' prefix

    # Compute HMAC-SHA256
    mac = hmac.new(
        webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256
    )
    computed_signature = mac.hexdigest()

    # Timing-safe comparison
    is_valid = hmac.compare_digest(computed_signature, expected_signature)

    if not is_valid:
        logger.warning("Webhook signature verification failed")

    return is_valid


def compute_payload_hash(payload: bytes) -> str:
    """
    Compute SHA-256 hash of payload for audit storage.

    We store the hash instead of the payload itself for security.

    Args:
        payload: Raw webhook payload

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(payload).hexdigest()


async def store_webhook_event(
    db,
    org_id: str,
    connector_slug: str,
    delivery_id: str,
    event_type: str,
    payload_hash: str
) -> bool:
    """
    Store webhook event metadata (not payload) in MongoDB.

    Returns True if this is a new event, False if duplicate (idempotent).

    Args:
        db: MongoDB database
        org_id: InDE organization ID
        connector_slug: Connector identifier (e.g., "github")
        delivery_id: X-GitHub-Delivery header (idempotency key)
        event_type: X-GitHub-Event header
        payload_hash: SHA-256 hash of payload

    Returns:
        True if new event stored, False if duplicate
    """
    now = datetime.utcnow()

    try:
        db.webhook_events.insert_one({
            "org_id": org_id,
            "connector_slug": connector_slug,
            "delivery_id": delivery_id,
            "event_type": event_type,
            "received_at": now,
            "processed": False,
            "processing_result": None,
            "error_detail": None,
            "payload_hash": payload_hash,
        })
        return True
    except Exception as e:
        # Duplicate key error (delivery_id is unique)
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            logger.debug(f"Duplicate webhook delivery: {delivery_id}")
            return False
        raise


async def mark_webhook_processed(
    db,
    delivery_id: str,
    result: str,
    error_detail: Optional[str] = None
) -> None:
    """
    Mark a webhook event as processed.

    Args:
        db: MongoDB database
        delivery_id: Webhook delivery ID
        result: Processing result (SUCCESS, SKIPPED, ERROR)
        error_detail: Error message if result is ERROR
    """
    db.webhook_events.update_one(
        {"delivery_id": delivery_id},
        {
            "$set": {
                "processed": True,
                "processing_result": result,
                "error_detail": error_detail,
                "processed_at": datetime.utcnow(),
            }
        }
    )


def get_org_id_from_installation(db, installation_id: int) -> Optional[str]:
    """
    Look up InDE org_id from GitHub installation ID.

    Args:
        db: MongoDB database
        installation_id: GitHub App installation ID

    Returns:
        org_id if found, None otherwise
    """
    doc = db.connector_installations.find_one({
        "github_installation_id": installation_id,
        "connector_slug": "github",
        "status": {"$ne": "UNINSTALLED"}
    })

    return doc["org_id"] if doc else None
