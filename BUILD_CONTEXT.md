# InDE_5_1b Build Context

**Version:** 5.1b.0 — "IDTFS GitHub Activation"
**Series:** v5.x — Unified Platform (LInDE + CInDE)
**Base:** InDE_5_1a v5.1a.0 — "The GitHub RBAC Bridge" (36/36 tests passing)
**GitHub:** https://github.com/Dapman/InDE_5_1b
**Build Date:** March 2026
**Deployment:** LOCAL (CINDE mode for IDTFS development)

## What This Build Adds

IDTFS GitHub Activation: Pursuit-repo linkage, Layer 2 live activation, Pillar 1/2
signal ingestion, admin confirmation UI for unlinked users, and extended sovereignty
enforcement. Pursuits can be explicitly linked to GitHub repositories (1:N with
primary designation). Layer 2 RBAC becomes live: GitHub repo roles (admin/maintain/
write/triage/read) sync to InDE pursuit roles (editor/viewer). Push and PR events
feed into innovator_profiles for Pillar 1/2 signal strength. Admin UI allows review
and confirmation of github_unlinked flagged users. Sovereignty tests extended to
verify no outbound data flow from pursuit content to GitHub.

## New Files (v5.1b)

- app/models/pursuit_repo_link.py — PursuitRepoLink + GithubActivitySignal schemas
- app/connectors/github/pursuit_linker.py — PursuitRepoLinker service
- app/connectors/github/signal_ingester.py — GitHubSignalIngester for Pillar 1/2
- app/routers/pursuit_repo_links.py — Linkage CRUD API routes
- frontend/src/components/admin/GitHubUnlinkedReview.jsx — Admin confirmation UI
- docs/GITHUB_IDTFS_SIGNALS.md — Operational guide for IDTFS signals
- tests/test_pursuit_repo_links.py — 12 tests for pursuit-repo linkage
- tests/test_layer2_live.py — 7 tests for Layer 2 activation
- tests/test_signal_ingestion.py — 13 tests for signal ingestion
- tests/test_admin_ui_routes.py — 8 tests for admin UI routes

## New Files (v5.1a)

- app/connectors/github/rbac_bridge.py — GitHubRBACBridge service
- app/connectors/github/role_mapper.py — Translation tables and mapping logic
- app/connectors/github/sync_service.py — Initial sync + delta sync orchestration
- app/connectors/github/webhook_handlers.py — Live handlers (replaces stubs)
- app/models/github_sync_log.py — Sync audit trail collection
- app/api/v1/github_sync.py — RBAC sync API routes
- tests/test_rbac_bridge.py — 19 tests for RBAC bridge
- docs/GITHUB_RBAC_BRIDGE.md — Operational guide for org admins

## New Files (v5.1)

- app/connectors/__init__.py
- app/connectors/registry.py
- app/connectors/base.py
- app/connectors/crypto.py
- app/connectors/github/__init__.py
- app/connectors/github/app.py
- app/connectors/github/auth.py
- app/connectors/github/client.py
- app/connectors/github/webhooks.py
- app/connectors/github/events.py
- app/connectors/slack/__init__.py (stub)
- app/connectors/atlassian/__init__.py (stub)
- app/api/v1/connectors.py
- app/models/connector_installation.py
- app/models/webhook_event.py
- tests/test_connectors.py
- docs/CONNECTORS.md
- docs/GITHUB_APP_SETUP.md

## v5.0 Foundation (preserved)

- app/services/feature_gate.py
- app/middleware/deployment_context.py
- app/startup/mode_validator.py
- docs/DEPLOYMENT_MODE.md
- tests/test_linde_mode.py
- tests/test_cinde_mode.py
- tests/test_gii_portability.py

## v4.x Series (all preserved, all SHARED-mode modules)

- v4.0: Language & Terminology Transformation
- v4.1: Momentum Management Engine
- v4.2: Re-Entry & Async Re-Engagement
- v4.3: Visual Identity / Depth Frame
- v4.4: IML Momentum Pattern Intelligence
- v4.5: Engagement Engine (health card, cohort, pathway, milestones)
- v4.6: Outcome Formulator
- v4.7: Thesis Engine (ITD)
- v4.8: Projection Engine
- v4.9: Export Engine
- v4.10: Innovation Resource Canvas (IRC)

## Mode Gate: SHARED vs CINDE-only

SHARED (active in both modes):
  ODICM, MME, Re-Entry, Re-Engagement, Visual Identity, IML Pattern,
  Engagement Engine, Outcome Formulator, ITD, Projection, Export, IRC,
  TIM, Language Sovereignty, GII Identity, IKF Federation Client,
  License Middleware

CINDE-only (dormant in LINDE, active in CINDE):
  Org Service, Membership Manager, RBAC Middleware, Team Scaffolding,
  IDTFS, Activity Stream, Portfolio Dashboard, Convergence Protocol,
  SOC 2 Audit, **Enterprise Connectors (v5.1)**

## IDTFS GitHub Activation (v5.1b)

- Pursuit-Repo Linkage: explicit 1:N linking with primary designation
- Layer 2 Live Activation: GitHub repo roles sync to InDE pursuit roles
- Pillar 1/2 Signal Ingestion: push, PR, team events → innovator_profiles
- Admin Confirmation UI: review github_unlinked users before removal
- Extended Sovereignty: no import path from connectors to pursuit content/coaching

### Collections Added
- pursuit_repo_links: Links pursuits to GitHub repositories
- github_activity_signals: Append-only activity signals (push, PR, team)

### Signal Types
- push_commit: Commit activity from push events
- pr_opened, pr_merged, pr_reviewed: Pull request lifecycle
- team_added, team_removed: Team membership changes

## GitHub RBAC Bridge (v5.1a)

- GitHubRBACBridge: translates GitHub org/repo roles to InDE two-layer RBAC
- GitHubRoleMapper: org roles (owner/member/collaborator) and repo roles (admin/maintain/write/triage/read)
- Human floor enforcement: effective_role = max(github_derived, human_set)
- Removal advisory: github_unlinked flag set, human admin must confirm removal
- Two-layer independence: org_role and pursuit_role remain independent under sync
- Sovereignty invariant: GitHub data flows IN only, no coaching/pursuit data flows OUT
- Initial sync at installation: full org roster mapped on connector.installed
- Webhook-driven delta sync: live handlers for membership, organization, team_add

## Connector Framework (v5.1)

- ConnectorRegistry: pluggable architecture for enterprise integrations
- BaseConnector: abstract interface for all future connectors
- GitHubAppConnector: full OAuth installation flow with AES-256 token encryption
- Webhook ingestion: signature-verified, idempotent, payload-not-stored
- Slack and Atlassian stub slots reserved for future builds

## Modules NOT Touched

All v4.x modules are integration targets only — no modifications to
existing module files except additive wiring at startup.
