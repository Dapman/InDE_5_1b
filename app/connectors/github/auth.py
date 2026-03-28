"""
InDE MVP v5.1b.0 - GitHub App OAuth Flow

Handles GitHub App installation OAuth flow:
1. Generate secure state, store in ephemeral collection
2. Redirect user to GitHub App installation URL
3. Handle callback, exchange code for installation token
4. Store encrypted token in connector_installations collection
"""

import os
import logging
import secrets
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger("inde.connectors.github.auth")


def get_github_app_config() -> dict:
    """
    Get GitHub App configuration from environment.

    Returns:
        Dict with app_id, client_id, client_secret, webhook_secret, pem_path
    """
    return {
        "app_id": os.getenv("GITHUB_APP_ID"),
        "client_id": os.getenv("GITHUB_APP_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_APP_CLIENT_SECRET"),
        "webhook_secret": os.getenv("GITHUB_APP_WEBHOOK_SECRET"),
        "pem_path": os.getenv("GITHUB_APP_PRIVATE_KEY_PATH"),
    }


def get_private_key() -> str:
    """
    Read the GitHub App private key from file.

    Returns:
        PEM-encoded private key string

    Raises:
        ValueError: If key file not found or unreadable
    """
    config = get_github_app_config()
    pem_path = config.get("pem_path")

    if not pem_path:
        raise ValueError("GITHUB_APP_PRIVATE_KEY_PATH not configured")

    path = Path(pem_path)
    if not path.exists():
        raise ValueError(f"Private key file not found: {pem_path}")

    try:
        return path.read_text()
    except Exception as e:
        raise ValueError(f"Failed to read private key: {e}")


def generate_app_jwt() -> str:
    """
    Generate a JWT for GitHub App authentication.

    The JWT is used to authenticate as the GitHub App itself
    (not as an installation) for operations like getting installation tokens.

    Returns:
        JWT string (valid for 10 minutes)
    """
    config = get_github_app_config()
    app_id = config.get("app_id")

    if not app_id:
        raise ValueError("GITHUB_APP_ID not configured")

    private_key = get_private_key()

    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds ago (clock skew tolerance)
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": app_id,
    }

    return jwt.encode(payload, private_key, algorithm="RS256")


def generate_oauth_state() -> str:
    """
    Generate a cryptographically secure state parameter.

    Returns:
        32-byte hex-encoded random string
    """
    return secrets.token_hex(32)


async def store_oauth_state(
    db,
    state: str,
    org_id: str,
    admin_user_id: str,
    expires_minutes: int = 10
) -> None:
    """
    Store OAuth state in ephemeral collection.

    Args:
        db: MongoDB database
        state: The state parameter
        org_id: InDE organization ID
        admin_user_id: User initiating the installation
        expires_minutes: How long the state is valid
    """
    expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)

    db.connector_oauth_states.insert_one({
        "state": state,
        "org_id": org_id,
        "admin_user_id": admin_user_id,
        "expires_at": expires_at,
        "created_at": datetime.utcnow(),
        "used": False,
    })

    logger.debug(f"OAuth state stored for org {org_id}, expires at {expires_at}")


async def validate_oauth_state(
    db,
    state: str
) -> Optional[Tuple[str, str]]:
    """
    Validate and consume OAuth state (one-time use).

    Args:
        db: MongoDB database
        state: The state parameter to validate

    Returns:
        Tuple of (org_id, admin_user_id) if valid, None otherwise
    """
    now = datetime.utcnow()

    # Find and delete in one operation (atomic one-time use)
    doc = db.connector_oauth_states.find_one_and_delete({
        "state": state,
        "expires_at": {"$gt": now},
        "used": False,
    })

    if not doc:
        logger.warning(f"OAuth state validation failed: not found or expired")
        return None

    logger.debug(f"OAuth state validated for org {doc['org_id']}")
    return (doc["org_id"], doc["admin_user_id"])


def get_github_app_installation_url(state: str) -> str:
    """
    Get the GitHub App installation URL with state parameter.

    Args:
        state: OAuth state parameter

    Returns:
        Full installation URL
    """
    # The app slug is derived from the app name (lowercase, hyphens)
    # For InDE, we use 'inde-enterprise' as the app slug
    # This should be configured or derived from GITHUB_APP_SLUG env var
    app_slug = os.getenv("GITHUB_APP_SLUG", "inde-enterprise")

    return f"https://github.com/apps/{app_slug}/installations/new?state={state}"


async def cleanup_expired_states(db) -> int:
    """
    Remove expired OAuth states from the collection.

    Args:
        db: MongoDB database

    Returns:
        Number of states removed
    """
    result = db.connector_oauth_states.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    return result.deleted_count
