"""
InDE MVP v5.1b.0 - Webhook Event Model

MongoDB schema for webhook_events collection.
CINDE-only, org_id scoped.

CRITICAL: Raw webhook payload is NEVER stored - only its hash for audit purposes.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class WebhookEventSchema(BaseModel):
    """Schema for webhook event documents."""

    org_id: str = Field(..., description="FK to organisations._id")
    connector_slug: str = Field(..., description="e.g., 'github'")
    delivery_id: str = Field(..., description="X-GitHub-Delivery - idempotency key")
    event_type: str = Field(..., description="X-GitHub-Event header value")

    received_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False)
    processing_result: Optional[str] = None  # SUCCESS | SKIPPED | ERROR | null
    error_detail: Optional[str] = None

    # CRITICAL: Only store hash, never raw payload
    payload_hash: str = Field(..., description="SHA-256 of raw payload")

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


def create_webhook_events_indexes(db):
    """
    Create indexes for webhook_events collection.

    Called at startup - idempotent.
    """
    collection = db.webhook_events

    # Unique index on delivery_id for idempotency
    collection.create_index(
        [("delivery_id", 1)],
        unique=True,
        background=True,
        name="idx_delivery_id_unique"
    )

    # Index for querying by org and time
    collection.create_index(
        [("org_id", 1), ("received_at", -1)],
        background=True,
        name="idx_org_received"
    )

    # Index for finding unprocessed events
    collection.create_index(
        [("processed", 1), ("received_at", 1)],
        background=True,
        partialFilterExpression={"processed": False},
        name="idx_unprocessed"
    )

    # Index for connector-specific queries
    collection.create_index(
        [("connector_slug", 1), ("event_type", 1), ("received_at", -1)],
        background=True,
        name="idx_connector_event_type"
    )
