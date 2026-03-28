# InDE v5.1b - IDTFS GitHub Signals

## Overview

v5.1b introduces **IDTFS GitHub Activation** - the ability to capture activity signals from GitHub repositories and attribute them to InDE pursuits. This enables Pillar 1 (Activity) and Pillar 2 (Collaboration) metrics to be populated from real GitHub activity.

## Architecture

### Signal Flow

```
GitHub Webhook → InDE Webhook Receiver → Signal Ingester → innovator_profiles
                                              ↓
                                    pursuit_repo_links (lookup)
                                              ↓
                                    github_activity_signals (storage)
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `PursuitRepoLinker` | `app/connectors/github/pursuit_linker.py` | Manages 1:N pursuit-repo linkage |
| `GitHubSignalIngester` | `app/connectors/github/signal_ingester.py` | Ingests webhook events as signals |
| Webhook Handlers | `app/connectors/github/webhook_handlers.py` | Process `push`, `pull_request`, `pull_request_review` |

## Signal Types

| Signal Type | GitHub Event | Pillar | Description |
|-------------|--------------|--------|-------------|
| `push_commit` | `push` | 1 | Each commit in a push event |
| `pr_opened` | `pull_request.opened` | 1/2 | Pull request created |
| `pr_merged` | `pull_request.closed` (merged=true) | 1/2 | Pull request merged |
| `pr_reviewed` | `pull_request_review.submitted` | 2 | Review submitted |
| `team_added` | `team.added_to_repository` | 2 | Team added to repo |
| `team_removed` | `team.removed_from_repository` | 2 | Team removed from repo |

## Pursuit-Repo Linkage

### Model

Each pursuit can be linked to multiple GitHub repositories with exactly **one primary**:

```python
PursuitRepoLink:
    org_id: str              # InDE organization
    pursuit_id: str          # InDE pursuit ID
    github_repo_id: int      # GitHub repository ID
    github_repo_full_name: str  # e.g., "org/repo"
    is_primary: bool         # Only one primary per pursuit
    linked_at: datetime
    linked_by: str           # User who created link
    status: str              # "active" | "deleted"
```

### Primary Repo Significance

- **Layer 2 RBAC**: Only the primary repo governs pursuit-level roles
- **Signal Attribution**: All linked repos contribute signals to the pursuit
- **Auto-Promotion**: When primary is unlinked, oldest remaining link is promoted

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/pursuit-repo-links/` | POST | Link a repo to a pursuit |
| `/api/v1/pursuit-repo-links/{pursuit_id}` | GET | List repos linked to pursuit |
| `/api/v1/pursuit-repo-links/{pursuit_id}/{repo_id}` | DELETE | Unlink repo |
| `/api/v1/pursuit-repo-links/{pursuit_id}/{repo_id}/primary` | PATCH | Set primary |

## Layer 2 RBAC

### Role Mapping (Repo → Pursuit)

| GitHub Repo Permission | InDE Pursuit Role |
|------------------------|-------------------|
| `admin` | `pursuit_editor` (NOT owner) |
| `maintain` | `pursuit_editor` |
| `push` / `write` | `pursuit_editor` |
| `triage` | `pursuit_viewer` |
| `pull` / `read` | `pursuit_viewer` |

### Human Floor Enforcement

- Pursuit roles respect the human floor: `effective_role = max(github_derived, human_set)`
- Human overrides can only elevate, never demote
- GitHub sync can only demote if human floor allows

### Two-Layer Independence

Layer 1 (org role) and Layer 2 (pursuit role) are **completely independent**:
- Syncing org membership doesn't affect pursuit roles
- Syncing pursuit roles doesn't affect org membership
- Each layer has its own human floor

## Signal Ingestion

### Idempotency

Signals use composite key `(delivery_id, signal_type)` for idempotency. Duplicate deliveries return `"duplicate"` action without storing.

### Activity Summary

Per-user, per-pursuit activity summaries are computed over 90-day rolling window:

```python
{
    "user_id": str,
    "pursuit_id": str,
    "signal_count_90d": int,
    "signal_strength": "strong" | "moderate" | "weak" | "none",
    "last_computed_at": datetime
}
```

**Signal Strength Thresholds**:
- `strong`: 10+ signals in 90 days
- `moderate`: 4-9 signals
- `weak`: 1-3 signals
- `none`: 0 signals

## Admin Confirmation UI

### Unlinked Members

When a user is removed from GitHub but has an active InDE membership, they are marked as `github_unlinked=True` instead of being auto-removed. This allows admin review.

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/connectors/github/members/unlinked` | GET | List unlinked members |
| `/api/v1/connectors/github/members/{user_id}/confirm-unlink` | POST | Confirm action |

### Actions

- `remove`: Revokes membership (`status` → `REVOKED`)
- `retain`: Clears GitHub link, converts to human-managed membership

## Sovereignty Boundary

### Rule

**No outbound data flow from pursuit content to GitHub.**

Connectors must NOT import from:
- `coaching`
- `maturity`
- `fear`
- `pursuit_content`

### Enforcement

Sovereignty is enforced by AST-based tests that scan all connector files for forbidden imports:

```python
class TestSovereigntyEnforcement:
    def test_no_coaching_imports_in_connectors(self):
        # Scans app/connectors/**/*.py for "coaching" imports
```

## Collections

### pursuit_repo_links

```javascript
{
    "_id": ObjectId,
    "org_id": "string",
    "pursuit_id": "string",
    "github_repo_id": 12345,
    "github_repo_full_name": "org/repo",
    "is_primary": true,
    "linked_at": ISODate,
    "linked_by": "user_id",
    "status": "active"
}
// Index: { org_id: 1, pursuit_id: 1, github_repo_id: 1, status: 1 } unique
// Index: { org_id: 1, github_repo_id: 1, status: 1 }
```

### github_activity_signals

```javascript
{
    "_id": ObjectId,
    "org_id": "string",
    "pursuit_id": "string",
    "user_id": "string",
    "github_login": "string",
    "delivery_id": "guid",
    "signal_type": "push_commit",
    "occurred_at": ISODate,
    "ingested_at": ISODate,
    "metadata": { ... }
}
// Index: { delivery_id: 1, signal_type: 1 } unique (idempotency)
// Index: { org_id: 1, pursuit_id: 1, user_id: 1, occurred_at: -1 }
```

## Test Coverage

| Test File | Count | Coverage |
|-----------|-------|----------|
| `test_pursuit_repo_links.py` | 12 | Linkage CRUD, primary promotion |
| `test_layer2_live.py` | 8 | Repo→Pursuit role sync |
| `test_signal_ingestion.py` | 13 | Signal types, idempotency, attribution |
| `test_admin_ui_sovereignty.py` | 8 | Admin UI, sovereignty enforcement |
| **Total v5.1b** | **41** | |

## Version

- **Version**: v5.1b.0
- **Theme**: IDTFS GitHub Activation
- **Parent**: v5.1a.0 (The GitHub RBAC Bridge)
