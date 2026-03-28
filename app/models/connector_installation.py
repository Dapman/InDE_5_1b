"""
InDE MVP v5.1b.0 - Connector Installation Model

MongoDB schema for connector_installations collection.
CINDE-only, org_id scoped.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class ConnectorInstallationSchema(BaseModel):
    """Schema for connector installation documents."""

    org_id: str = Field(..., description="FK to organisations._id")
    connector_slug: str = Field(..., description="e.g., 'github', 'slack'")
    status: str = Field(default="ACTIVE", description="ACTIVE | SUSPENDED | UNINSTALLED")

    installed_at: datetime = Field(default_factory=datetime.utcnow)
    installed_by: str = Field(..., description="FK to users._id (must be org Admin)")
    last_active: Optional[datetime] = None

    # GitHub-specific fields (stored encrypted)
    github_installation_id: Optional[int] = None
    github_org_login: Optional[str] = None
    github_access_token_enc: Optional[str] = None  # AES-256 encrypted
    github_token_expires_at: Optional[datetime] = None

    # Audit
    uninstalled_at: Optional[datetime] = None
    uninstalled_by: Optional[str] = None

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


def create_connector_installations_indexes(db):
    """
    Create indexes for connector_installations collection.

    Called at startup - idempotent.
    """
    collection = db.connector_installations

    # Unique index on org_id + connector_slug where not uninstalled
    # Note: MongoDB partial indexes need to be created with raw command
    collection.create_index(
        [("org_id", 1), ("connector_slug", 1)],
        unique=True,
        partialFilterExpression={"status": {"$ne": "UNINSTALLED"}},
        background=True,
        name="idx_org_connector_unique_active"
    )

    # Index for listing by org
    collection.create_index(
        [("org_id", 1), ("status", 1)],
        background=True,
        name="idx_org_status"
    )

    # Index for finding by GitHub installation ID
    collection.create_index(
        [("github_installation_id", 1)],
        background=True,
        sparse=True,
        name="idx_github_installation_id"
    )
