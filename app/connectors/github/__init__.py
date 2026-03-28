"""
InDE MVP v5.1b.0 - GitHub App Connector

Enterprise GitHub App integration for organization-level authentication,
webhook ingestion, membership data access, and RBAC synchronization.
"""

from .app import GitHubAppConnector
from .auth import (
    generate_oauth_state,
    store_oauth_state,
    validate_oauth_state,
    get_github_app_installation_url,
    get_github_app_config,
)
from .client import GitHubAPIClient, exchange_code_for_installation
from .webhooks import (
    verify_webhook_signature,
    compute_payload_hash,
    store_webhook_event,
    mark_webhook_processed,
    get_org_id_from_installation,
)
from .events import process_github_webhook, EVENT_HANDLERS
from .role_mapper import GitHubRoleMapper, GITHUB_ORG_ROLE_TO_INDE, GITHUB_REPO_ROLE_TO_INDE_PURSUIT
from .rbac_bridge import (
    GitHubRBACBridge,
    InitialSyncResult,
    MembershipSyncResult,
    TeamSyncResult,
    OrgSyncResult,
    OverrideResult,
)
from .sync_service import GitHubSyncService, SyncStatus

__all__ = [
    # Core connector
    'GitHubAppConnector',
    'GitHubAPIClient',
    # OAuth
    'generate_oauth_state',
    'store_oauth_state',
    'validate_oauth_state',
    'get_github_app_installation_url',
    'get_github_app_config',
    'exchange_code_for_installation',
    # Webhooks
    'verify_webhook_signature',
    'compute_payload_hash',
    'store_webhook_event',
    'mark_webhook_processed',
    'get_org_id_from_installation',
    'process_github_webhook',
    'EVENT_HANDLERS',
    # Role mapping (v5.1a)
    'GitHubRoleMapper',
    'GITHUB_ORG_ROLE_TO_INDE',
    'GITHUB_REPO_ROLE_TO_INDE_PURSUIT',
    # RBAC Bridge (v5.1a)
    'GitHubRBACBridge',
    'InitialSyncResult',
    'MembershipSyncResult',
    'TeamSyncResult',
    'OrgSyncResult',
    'OverrideResult',
    # Sync Service (v5.1a)
    'GitHubSyncService',
    'SyncStatus',
]
