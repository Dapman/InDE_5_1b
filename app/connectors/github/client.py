"""
InDE MVP v5.1b.0 - GitHub REST API Client

Authenticated client for GitHub API calls using installation tokens.
Handles rate limiting, token refresh, and error handling.
"""

import os
import logging
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from .auth import generate_app_jwt, get_github_app_config

logger = logging.getLogger("inde.connectors.github.client")

# GitHub API base URL
GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIClient:
    """
    Authenticated GitHub API client using installation tokens.
    """

    def __init__(
        self,
        installation_id: int,
        access_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None
    ):
        self.installation_id = installation_id
        self._access_token = access_token
        self._token_expires_at = token_expires_at
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
                timeout=30.0,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _ensure_token(self) -> str:
        """
        Ensure we have a valid access token, refreshing if needed.

        Returns:
            Valid access token
        """
        # Check if current token is still valid (with 5 min buffer)
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < (self._token_expires_at - timedelta(minutes=5)):
                return self._access_token

        # Need to refresh token
        new_token, expires_at = await self._refresh_installation_token()
        self._access_token = new_token
        self._token_expires_at = expires_at

        return self._access_token

    async def _refresh_installation_token(self) -> tuple[str, datetime]:
        """
        Get a new installation access token from GitHub.

        Returns:
            Tuple of (access_token, expires_at)
        """
        app_jwt = generate_app_jwt()

        client = await self._get_http_client()
        response = await client.post(
            f"/app/installations/{self.installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {app_jwt}"}
        )

        if response.status_code != 201:
            logger.error(f"Failed to get installation token: {response.status_code} {response.text}")
            raise ValueError(f"Failed to get GitHub installation token: {response.status_code}")

        data = response.json()
        token = data["token"]
        expires_at_str = data["expires_at"]

        # Parse ISO 8601 timestamp
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        # Convert to UTC naive datetime for MongoDB compatibility
        expires_at = expires_at.replace(tzinfo=None)

        logger.debug(f"Refreshed installation token, expires at {expires_at}")
        return token, expires_at

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make authenticated GET request to GitHub API.

        Args:
            path: API path (e.g., "/orgs/my-org/members")
            params: Optional query parameters

        Returns:
            Response JSON
        """
        token = await self._ensure_token()
        client = await self._get_http_client()

        response = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 401:
            # Token might have been invalidated, try refresh
            self._access_token = None
            token = await self._ensure_token()
            response = await client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {token}"}
            )

        response.raise_for_status()
        return response.json()

    async def get_installation(self) -> Dict[str, Any]:
        """
        Get information about the current installation.

        Returns:
            Installation details
        """
        app_jwt = generate_app_jwt()
        client = await self._get_http_client()

        response = await client.get(
            f"/app/installations/{self.installation_id}",
            headers={"Authorization": f"Bearer {app_jwt}"}
        )

        if response.status_code != 200:
            logger.warning(f"Failed to get installation: {response.status_code}")
            raise ValueError(f"Installation not found or access denied")

        return response.json()

    async def get_org_members(self, org_login: str) -> list[Dict[str, Any]]:
        """
        Get organization members.

        Args:
            org_login: GitHub organization login name

        Returns:
            List of member objects
        """
        return await self.get(f"/orgs/{org_login}/members")

    async def get_org_teams(self, org_login: str) -> list[Dict[str, Any]]:
        """
        Get organization teams.

        Args:
            org_login: GitHub organization login name

        Returns:
            List of team objects
        """
        return await self.get(f"/orgs/{org_login}/teams")


async def exchange_code_for_installation(
    code: str
) -> Dict[str, Any]:
    """
    Exchange OAuth authorization code for installation details.

    This is called after the user completes the GitHub App installation flow.

    Args:
        code: Authorization code from callback

    Returns:
        Dict with installation_id, org_login, access_token, expires_at
    """
    config = get_github_app_config()

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
            },
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            logger.error(f"OAuth token exchange failed: {response.status_code}")
            raise ValueError("Failed to exchange authorization code")

        data = response.json()

        if "error" in data:
            logger.error(f"OAuth error: {data.get('error_description', data['error'])}")
            raise ValueError(f"OAuth error: {data.get('error_description', data['error'])}")

        # For GitHub App installations, the response includes installation info
        # We need to get the installation ID from the access token permissions
        access_token = data.get("access_token")

        # Get the user's installations to find the one they just authorized
        installs_response = await client.get(
            f"{GITHUB_API_BASE}/user/installations",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            }
        )

        if installs_response.status_code != 200:
            logger.error(f"Failed to get installations: {installs_response.status_code}")
            raise ValueError("Failed to get user installations")

        installs_data = installs_response.json()
        installations = installs_data.get("installations", [])

        if not installations:
            raise ValueError("No installations found for user")

        # Get the most recent installation (should be the one just created)
        installation = installations[0]
        installation_id = installation["id"]
        account = installation.get("account", {})
        org_login = account.get("login")

        logger.info(f"Found installation {installation_id} for org {org_login}")

        # Now get an installation access token
        app_jwt = generate_app_jwt()
        token_response = await client.post(
            f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            }
        )

        if token_response.status_code != 201:
            logger.error(f"Failed to get installation token: {token_response.status_code}")
            raise ValueError("Failed to get installation access token")

        token_data = token_response.json()
        install_token = token_data["token"]
        expires_at_str = token_data["expires_at"]

        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        expires_at = expires_at.replace(tzinfo=None)

        return {
            "installation_id": installation_id,
            "org_login": org_login,
            "access_token": install_token,
            "expires_at": expires_at,
        }
