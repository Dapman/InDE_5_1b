# InDE Enterprise Connectors

**Version:** 5.1b.0
**Status:** CINDE-only (not available in LINDE deployments)

## Overview

InDE Enterprise Connectors enable organization-level integration with external services. Connectors provide:

- OAuth-based authentication flows
- Webhook ingestion and processing
- Role synchronization with InDE RBAC
- Audit trail for all external interactions

## Available Connectors

| Connector | Status | Capabilities |
|-----------|--------|--------------|
| GitHub | Active | OAuth, webhooks, RBAC sync |
| Slack | Stub | Coming soon |
| Atlassian | Stub | Coming soon |

## GitHub Connector

The GitHub App connector enables:

1. **Organization-level authentication** via GitHub App installation
2. **Webhook ingestion** for real-time membership updates
3. **RBAC synchronization** (v5.1a) mapping GitHub roles to InDE roles

### Installation Flow

1. Org admin initiates install via `POST /api/v1/connectors/github/install`
2. User is redirected to GitHub App installation page
3. After approval, callback exchanges code for installation token
4. Token is encrypted and stored in `connector_installations`

### Webhook Events

| Event | Handler | RBAC Effect |
|-------|---------|-------------|
| `membership` | `handle_membership` | Creates/updates membership |
| `organization` | `handle_organization` | Handles rename, member changes |
| `team` | `handle_team` | Logged (v5.1b: IDTFS) |
| `team_add` | `handle_team_add` | Logged (v5.1b: IDTFS) |
| `repository` | `handle_repository` | Logged (v5.1b: pursuit link) |
| `installation` | `handle_installation` | Triggers initial sync |

## GitHub RBAC Bridge (v5.1a)

The RBAC Bridge synchronizes GitHub organization roles to InDE's two-layer RBAC model.

### Role Mapping Tables

#### Organization Roles

| GitHub Role | InDE Org Role |
|-------------|---------------|
| `owner` | `org_admin` |
| `admin` | `org_admin` |
| `member` | `org_member` |
| `outside_collaborator` | `org_viewer` |
| Unknown | `org_viewer` (safe default) |

#### Repository Roles (v5.1b IDTFS)

| GitHub Repo Role | InDE Pursuit Role |
|------------------|-------------------|
| `admin` | `editor` (NOT owner) |
| `maintain` | `editor` |
| `write` | `editor` |
| `triage` | `viewer` |
| `read` | `viewer` |

**Critical invariant:** GitHub repo `admin` does NOT become pursuit `owner`. Only InDE humans create pursuits; GitHub controls access level, not ownership.

### Human Floor Rule

The effective role is computed as:

```
effective_role = max(github_derived_role, human_set_role)
```

- GitHub sync can **elevate** a user's role
- GitHub sync **cannot demote** below a human-set floor
- When floor is applied, `human_floor_applied=True` in the sync log

### Removal Advisory Pattern

When a user is removed from the GitHub organization:

1. InDE sets `github_unlinked=True` on their membership
2. InDE sets `github_unlinked_at` timestamp
3. The membership document is **NOT** deleted
4. An admin must manually confirm removal in InDE

This prevents accidental data loss from GitHub org changes.

### Two-Layer Independence

InDE maintains strict independence between:

- **Org role**: Organization-wide access level (admin/member/viewer)
- **Pursuit role**: Per-pursuit access level (owner/editor/viewer)

A user can be `org_admin` but only have `viewer` access to a specific pursuit. The two layers never interfere.

### Initial Sync

When the GitHub App is installed:

1. InDE fetches all org members via GitHub API
2. For each member with a matching InDE user (by email/login):
   - Computes `github_derived_role` from GitHub org role
   - Applies human floor if set
   - Updates `effective_role`
3. Members without InDE accounts are flagged as `pending`
4. Sync results stored in `github_sync_status`

### v5.1a Limitations

- **Team events captured but not mapped** - Team membership signals are logged for v5.1b IDTFS backfill
- **Repository events logged only** - Pursuit linking is v5.1b scope
- **No automatic re-sync** - Use manual trigger via API

## API Routes

### Connector Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/connectors/` | List available connectors |
| GET | `/api/v1/connectors/{slug}/status` | Health status |
| POST | `/api/v1/connectors/{slug}/install` | Initiate OAuth |
| GET | `/api/v1/connectors/{slug}/callback` | OAuth callback |
| DELETE | `/api/v1/connectors/{slug}/uninstall` | Uninstall |
| GET | `/api/v1/connectors/{slug}/events` | Recent webhooks |

### GitHub RBAC Sync (v5.1a)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/connectors/github/sync/status` | Sync status |
| POST | `/api/v1/connectors/github/sync/trigger` | Manual sync (202) |
| GET | `/api/v1/connectors/github/sync/log` | Sync log (paginated) |
| GET | `/api/v1/connectors/github/members` | Members with sync info |
| GET | `/api/v1/connectors/github/members/{id}/role` | Member role details |
| POST | `/api/v1/connectors/github/members/{id}/role` | Set human override |

## Security

- All tokens encrypted with AES-256-GCM
- Webhook signatures verified via HMAC-SHA256
- OAuth state is single-use with 10-minute expiry
- All sync operations logged to `github_sync_log` (90-day TTL)

## Collections

### connector_installations

```javascript
{
  org_id: "org-123",
  connector_slug: "github",
  status: "ACTIVE",
  github_installation_id: 12345678,
  github_org_login: "myorg",
  github_access_token_enc: "base64...",
  installed_at: ISODate(),
  installed_by: "user-456"
}
```

### github_sync_log

```javascript
{
  org_id: "org-123",
  event_type: "webhook_membership",
  action: "elevated",
  github_delivery_id: "abc-123",
  affected_user_id: "user-789",
  github_login: "octocat",
  role_before: "org_member",
  role_after: "org_admin",
  human_floor_applied: false,
  created_at: ISODate()
}
```

### github_sync_status

```javascript
{
  org_id: "org-123",
  last_sync_at: ISODate(),
  last_sync_id: "sync-uuid",
  last_sync_status: "SUCCESS",
  synced_count: 42,
  pending_count: 3,
  floor_applied_count: 2,
  error_count: 0
}
```
