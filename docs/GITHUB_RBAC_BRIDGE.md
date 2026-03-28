# GitHub RBAC Bridge - Operations Guide

**Version:** 5.1b.0
**Audience:** Organization Administrators

## Overview

The GitHub RBAC Bridge synchronizes GitHub organization membership to InDE's role-based access control system. When users are added to or removed from your GitHub organization, their InDE access is automatically updated.

## Viewing Sync Status

### Via API

```bash
GET /api/v1/connectors/github/sync/status
```

Response:
```json
{
  "org_id": "org-123",
  "status": "IDLE",
  "last_sync_id": "abc-123",
  "last_sync_at": "2026-03-28T10:00:00Z",
  "synced_count": 42,
  "pending_count": 3,
  "floor_applied_count": 2,
  "error_count": 0,
  "message": null
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `IDLE` | No sync in progress, system ready |
| `IN_PROGRESS` | Sync currently running |
| `COMPLETED` | Last sync completed successfully |
| `PARTIAL` | Last sync completed with some errors |
| `FAILED` | Last sync failed |

## Triggering Manual Re-Sync

If you need to re-synchronize all GitHub members:

```bash
POST /api/v1/connectors/github/sync/trigger
```

Response (202 Accepted):
```json
{
  "sync_id": "abc-123-def",
  "status": "IN_PROGRESS",
  "message": "Sync initiated. Poll GET /sync/status for completion."
}
```

### Notes

- Only one sync can run per organization at a time
- Attempting to start a second sync returns `409 Conflict`
- Sync runs in the background; poll `/sync/status` to check progress
- Typical sync time: 1-2 seconds per 100 members

## Setting Human Role Overrides

The human floor prevents GitHub from demoting a user below an admin-set role.

### View Current Role

```bash
GET /api/v1/connectors/github/members/{user_id}/role
```

Response:
```json
{
  "user_id": "user-456",
  "github_login": "octocat",
  "github_org_role": "member",
  "github_derived_role": "org_member",
  "human_set_role": "org_admin",
  "effective_role": "org_admin",
  "human_set_at": "2026-03-15T14:30:00Z",
  "human_set_by": "admin-789"
}
```

### Set Override

```bash
POST /api/v1/connectors/github/members/{user_id}/role
Content-Type: application/json

{
  "role": "org_admin"
}
```

Valid roles: `org_admin`, `org_member`, `org_viewer`

Response:
```json
{
  "user_id": "user-456",
  "role_before": "org_member",
  "role_after": "org_admin",
  "human_floor_applied": true,
  "message": "Role override applied. Effective role is now org_admin."
}
```

### How the Floor Works

| GitHub Role | Human Floor | Effective Role | Floor Applied? |
|-------------|-------------|----------------|----------------|
| `org_admin` | None | `org_admin` | No |
| `org_member` | `org_admin` | `org_admin` | Yes |
| `org_member` | `org_member` | `org_member` | No |
| `org_admin` | `org_member` | `org_admin` | No |

The effective role is always the **higher** of the two.

## Reviewing the Sync Log

View recent sync operations:

```bash
GET /api/v1/connectors/github/sync/log?page=1&page_size=50
```

Response:
```json
{
  "entries": [
    {
      "event_type": "webhook_membership",
      "action": "elevated",
      "github_login": "octocat",
      "affected_user_id": "user-456",
      "role_before": "org_member",
      "role_after": "org_admin",
      "human_floor_applied": false,
      "created_at": "2026-03-28T10:15:00Z",
      "delivery_id": "gh-delivery-123"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

### Action Types

| Action | Meaning |
|--------|---------|
| `created` | New membership created |
| `elevated` | Role upgraded |
| `floor_applied` | Human floor prevented demotion |
| `unlinked_flagged` | User removed from GitHub (see below) |
| `no_change` | No role change needed |
| `pending` | User not in InDE yet |
| `error` | Sync failed for this user |

## Handling Unlinked Users

When a user is removed from your GitHub organization, InDE does **not** automatically remove them. Instead:

1. The `github_unlinked` flag is set to `true`
2. A sync log entry with action `unlinked_flagged` is created
3. The user retains their current InDE access

### Why This Design?

- Prevents accidental data loss from GitHub organization changes
- Allows time for the user to rejoin if removed by mistake
- Gives admins control over InDE access independent of GitHub

### What to Do

1. Review unlinked users in the members list:

```bash
GET /api/v1/connectors/github/members
```

Look for entries with `github_unlinked: true`.

2. Decide what to do:
   - If the user should retain access, leave them alone
   - If the user should be removed, use your existing InDE member management

## Troubleshooting

### Sync Shows "IN_PROGRESS" for a Long Time

Syncs should complete within minutes. If stuck:

1. Check `/sync/status` for `error_message`
2. Review container logs for errors
3. Verify GitHub App installation is still active
4. Trigger a new sync (previous in-progress sync will be cleared)

### User Not Getting Expected Role

Check in order:

1. **GitHub org role** - What role does GitHub show?
2. **User matching** - Is the InDE user linked by email or `github_login`?
3. **Human floor** - Is there a higher floor set?
4. **Sync timing** - Was there a sync after the GitHub change?

### Webhook Events Not Being Processed

1. Verify webhook secret matches between GitHub App and InDE
2. Check webhook deliveries in GitHub App settings
3. Review InDE container logs for signature verification errors
4. Ensure the GitHub App has the required event subscriptions

### "Connector Not Initialized" Error

The GitHub connector requires these environment variables:

- `GITHUB_APP_ID`
- `GITHUB_APP_PRIVATE_KEY_PATH`
- `GITHUB_APP_CLIENT_ID`
- `GITHUB_APP_CLIENT_SECRET`
- `GITHUB_APP_WEBHOOK_SECRET`
- `CONNECTOR_ENCRYPTION_KEY`

## Limitations (v5.1a)

1. **Team membership not yet mapped to pursuits** - Team events are captured but pursuit access via teams is v5.1b
2. **Repository events logged only** - Pursuit-to-repo linking is v5.1b
3. **No scheduled re-sync** - Use manual trigger or rely on webhooks
4. **Single GitHub org per InDE org** - Multi-org support is future scope

## Audit Trail

All sync operations are logged to the `github_sync_log` collection with 90-day retention. This provides:

- Complete history of role changes
- Attribution (which webhook triggered the change)
- Human floor application tracking
- Compliance-ready audit data
