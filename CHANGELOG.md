# InDE MVP Changelog

## [5.1b.0] — 2026-03-28 "The GitHub RBAC Bridge"

### Series
InDE v5.1a — The GitHub RBAC Bridge. Implements live synchronization of
GitHub organization roles to InDE's two-layer RBAC model. Replaces v5.1
webhook stub handlers with real implementations that create and update
InDE memberships based on GitHub organization membership.

### Added

**GitHub RBAC Bridge — app/connectors/github/rbac_bridge.py**
- `GitHubRBACBridge` class translating GitHub roles to InDE RBAC
- `initial_sync()` method for full org member synchronization
- `handle_membership_event()` for webhook-driven membership updates
- `handle_organization_event()` for org rename and member changes
- `handle_team_add_event()` capturing team signals for v5.1b IDTFS
- `apply_human_override()` for admin role floor setting
- Result dataclasses: `InitialSyncResult`, `MembershipSyncResult`, `TeamSyncResult`, `OrgSyncResult`, `OverrideResult`

**GitHub Role Mapper — app/connectors/github/role_mapper.py**
- `GitHubRoleMapper` class with org and repo role translation
- `GITHUB_ORG_ROLE_TO_INDE` mapping table (owner→org_admin, member→org_member, etc.)
- `GITHUB_REPO_ROLE_TO_INDE_PURSUIT` mapping table (admin→editor, NOT owner)
- `compute_effective_role()` with human floor enforcement
- Role hierarchy: `org_viewer < org_member < org_admin`

**GitHub Sync Service — app/connectors/github/sync_service.py**
- `GitHubSyncService` orchestrating sync operations
- `trigger_initial_sync()` with background task management
- `run_initial_sync()` executing the sync
- `get_sync_status()` returning current sync state
- `is_sync_in_progress()` preventing concurrent syncs
- `SyncStatus` dataclass for status tracking

**Live Webhook Handlers — app/connectors/github/webhook_handlers.py**
- `handle_membership()` with RBAC bridge integration
- `handle_organization()` routing member events
- `handle_team()` logging for v5.1b IDTFS
- `handle_team_add()` capturing team membership signals
- `handle_repository()` logging for v5.1b pursuit linking
- `handle_installation()` triggering initial sync on install

**GitHub Sync Log Model — app/models/github_sync_log.py**
- `GithubSyncLog` dataclass for audit entries
- Index definitions with 90-day TTL
- `MEMBERSHIP_GITHUB_SYNC_FIELDS` documentation
- `ensure_github_sync_indexes()` startup function

**New API Routes — app/api/connectors.py**
- `GET /api/v1/connectors/github/sync/status` — Sync status
- `POST /api/v1/connectors/github/sync/trigger` — Manual sync (202)
- `GET /api/v1/connectors/github/sync/log` — Paginated sync log
- `GET /api/v1/connectors/github/members` — Members with sync info
- `GET /api/v1/connectors/github/members/{id}/role` — Member role details
- `POST /api/v1/connectors/github/members/{id}/role` — Set human override

### Design Invariants

**Human Floor Rule**
```
effective_role = max(github_derived_role, human_set_role)
```
- GitHub sync can elevate but never demote below admin-set floor
- `human_floor_applied=True` in sync log when floor prevents demotion

**Removal Advisory Pattern**
- Removed GitHub members get `github_unlinked=True` flag
- Membership document NOT deleted — admin must confirm
- Prevents accidental data loss from GitHub org changes

**Two-Layer Independence**
- Org role and pursuit role are independent
- `org_admin` can have `viewer` access to a specific pursuit
- GitHub repo `admin` maps to pursuit `editor`, never `owner`

**Sovereignty Invariant**
- GitHub data flows IN only
- Bridge has no import path to coaching, maturity, fear, or pursuit content
- Verified by `test_sovereignty_no_outbound_data`

### New MongoDB Collections

**github_sync_log**
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

**github_sync_status**
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

### Membership Collection Extensions

New fields added to existing `memberships` documents:
- `github_login` — GitHub username
- `github_org_role` — Raw GitHub role
- `github_derived_role` — Computed InDE role from GitHub
- `github_synced_at` — Last sync timestamp
- `github_unlinked` — True if removed from GitHub
- `github_unlinked_at` — When unlink was detected
- `human_set_role` — Admin-set role floor
- `human_set_at` — When floor was set
- `human_set_by` — Who set the floor
- `effective_role` — max(github_derived, human_set)

### Tests

- **tests/test_rbac_bridge.py**: 19 tests for RBAC bridge
  - TestRoleMapper (5 tests): Role mapping validation
  - TestRBACBridge (3 tests): Bridge logic
  - TestWebhookHandlers (3 tests): Handler behavior
  - TestTwoLayerRBAC (1 test): Layer independence
  - TestSyncRoutes (4 tests): API route behavior
  - TestSovereignty (1 test): Import boundary verification
  - TestLINDERegression (1 test): Mode regression
  - TestConnectorRegression (1 test): v5.1.0 suite verification

### Documentation

- **docs/CONNECTORS.md**: Connector registry, webhook security, RBAC Bridge section
- **docs/GITHUB_RBAC_BRIDGE.md**: Operations guide for org admins

### Architecture

- **CINDE-only**: All sync features gated by `enterprise_connectors`
- **LINDE unchanged**: Zero impact on individual innovator deployments
- **v5.1.0 compatible**: All 17 connector tests pass unmodified
- **v5.1b ready**: Team and repository events captured for IDTFS activation

### Known Limitations (v5.1a)

1. Team events captured but not mapped to pursuits (v5.1b: IDTFS)
2. Repository events logged but not linked to pursuits (v5.1b)
3. No scheduled re-sync (use manual trigger or rely on webhooks)
4. Single GitHub org per InDE org

---

## [5.1.0] — 2026-03-28 "The GitHub Connector Build"

### Series
InDE v5.1 — The GitHub Connector Build. Introduces the Enterprise Connector
Framework with GitHub App OAuth integration for CINDE deployments. Enables
organization-level authentication, webhook ingestion, and membership data
synchronization from external services.

### Added

**Enterprise Connector Framework — app/connectors/**
- `ConnectorRegistry` singleton for pluggable connector management
- `BaseConnector` abstract class defining connector interface
- Token encryption with AES-256-GCM via `CONNECTOR_ENCRYPTION_KEY`
- Support for active connectors and stub connectors (coming soon)

**GitHub App Connector — app/connectors/github/**
- Full OAuth App installation flow with state management
- JWT-based authentication for GitHub App API
- Installation access token exchange and encrypted storage
- Health check via GitHub API with status reporting
- Webhook event routing and handler registration

**Webhook Ingestion System**
- HMAC-SHA256 signature verification for webhook security
- Idempotent processing via delivery_id unique index
- Payload hash storage (raw payload never stored)
- Background task processing for sub-500ms webhook response
- Event handlers: membership, organization, team, team_add, repository

**Connector API Routes — app/api/connectors.py**
- `GET /api/v1/connectors/` — List available connectors and status
- `GET /api/v1/connectors/{slug}/status` — Health for installed connector
- `POST /api/v1/connectors/{slug}/install` — Initiate OAuth flow (admin only)
- `GET /api/v1/connectors/{slug}/callback` — OAuth callback handler
- `DELETE /api/v1/connectors/{slug}/uninstall` — Revoke installation (admin only)
- `GET /api/v1/connectors/{slug}/events` — Recent webhook events (admin only)
- `POST /api/v1/webhooks/github` — Webhook receiver (signature verified)

**Connector Stubs**
- Slack connector stub (`app/connectors/slack/`)
- Atlassian connector stub (`app/connectors/atlassian/`)

**Feature Gate Extensions — app/services/feature_gate.py**
- `enterprise_connectors` property: True in CINDE mode
- `connectors_registry_active` property: True when all env vars present

**Startup Validation — app/startup/mode_validator.py**
- GitHub App environment variable validation in CINDE mode
- Connector encryption key requirement enforcement

### New MongoDB Collections

**connector_installations**
```javascript
{
  org_id: "org-123",
  connector_slug: "github",
  status: "ACTIVE",           // ACTIVE | SUSPENDED | UNINSTALLED
  installed_at: ISODate(),
  installed_by: "user-456",
  github_installation_id: 12345678,
  github_org_login: "myorg",
  github_access_token_enc: "base64...",  // AES-256-GCM encrypted
  github_token_expires_at: ISODate()
}
```

**webhook_events**
```javascript
{
  delivery_id: "abc-123-def",     // Unique per provider
  org_id: "org-123",
  connector_slug: "github",
  event_type: "membership",
  payload_hash: "sha256...",      // NOT the payload itself
  received_at: ISODate(),
  processed: true,
  processing_result: "SUCCESS"
}
```

**connector_oauth_states**
```javascript
{
  state: "random-64-char-hex",
  org_id: "org-123",
  admin_user_id: "user-456",
  expires_at: ISODate(),     // +10 minutes
  used: false
}
```

### New Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_APP_ID` | CINDE | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY_PATH` | CINDE | Path to PEM private key |
| `GITHUB_APP_CLIENT_ID` | CINDE | OAuth client ID |
| `GITHUB_APP_CLIENT_SECRET` | CINDE | OAuth client secret |
| `GITHUB_APP_WEBHOOK_SECRET` | CINDE | Webhook signing secret |
| `CONNECTOR_ENCRYPTION_KEY` | CINDE | 64-char hex for AES-256-GCM |

### Tests

- **tests/test_connectors.py**: 17 tests for connector framework
  - LINDE mode returns 404 for connector routes
  - CINDE mode enables connector routes
  - Connector registry operations
  - OAuth state generation and storage
  - Token encryption roundtrip
  - Webhook signature verification
  - Webhook idempotency
  - Installation permissions (admin only)
  - Health check states

### Documentation

- **docs/CONNECTORS.md**: Connector registry pattern, webhook security, installation flow
- **docs/GITHUB_APP_SETUP.md**: Step-by-step GitHub App creation guide

### Architecture

- **CINDE-only**: All connector features gated by `enterprise_connectors`
- **LINDE unchanged**: Zero impact on individual innovator deployments
- **No new containers**: Connectors are modules within inde-app
- **Security model**: OAuth state single-use, webhook signatures, encrypted tokens

### Known Limitations

1. GitHub only — Slack and Atlassian are stubs
2. Single installation per org
3. No automatic token refresh
4. No webhook retry on failure
5. No rate limiting on webhook receiver
6. No admin UI for connector management (API only)

---

## [5.0.0] — 2026-03-28 "The Convergence Build"

### Series
InDE v5.0 — The Convergence Build. A unified codebase that serves both individual
innovators (LInDE) and enterprise organizations (CInDE) via a single deployment
mode environment variable. Zero feature duplication, zero code branching. One
codebase, two deployment contexts.

### Added

**Deployment Mode Architecture**
- `DEPLOYMENT_MODE` environment variable: `LINDE` (default) or `CINDE`
- Single entry point with capability activation based on mode
- Enterprise routes return 404 in LINDE mode (dormant, not absent)
- Shared capabilities active in both modes (coaching, momentum, IRC, ITD, etc.)

**FeatureGate Service — app/services/feature_gate.py**
- Central singleton controlling all capability activation
- Mode-specific property gates:
  - LINDE-only: All v4.x modules, coaching, GII (INDIVIDUAL binding)
  - CINDE-only: org_entity, team_formation, idtfs, portfolio, soc2_audit, rbac, activity_stream, convergence_protocol
- `get_feature_gate()` with lru_cache for consistent access

**Deployment Context Middleware — app/middleware/deployment_context.py**
- Attaches FeatureGate to request state
- Blocks CINDE-only route prefixes in LINDE mode with 404 response
- Zero performance impact for allowed routes

**Startup Mode Validator — app/startup/mode_validator.py**
- Validates `DEPLOYMENT_MODE` environment variable at startup
- Enforces `ORG_ID_SEED` requirement for CINDE mode
- Clear error messages for misconfiguration

**CInDE Mode Activation Sequence (main.py)**
- RBAC policy cache warmup
- IDTFS index verification
- Audit log writable check
- Conditional enterprise router registration

**GII Portability Protocol (v5.0)**
- `onboard_to_cinde(user_id, org_id)`: Bind existing GII to organization
- `dissolve_binding(user_id)`: Revert to INDIVIDUAL binding
- `get_binding_type(user_id)`: Query current binding state
- `verify_data_isolation(user_id, org_id)`: Transition verification
- Binding history tracked for audit compliance
- GII remains unchanged across mode transitions

**ODICM Transition Context — app/coaching/odicm_extensions.py**
- `org_context` field for CInDE team intelligence
- `transition_context` field for mode transition awareness
- `_build_org_context()`: Assembles team gaps and composition guidance
- `_build_transition_context()`: Detects recent mode transitions

**Activity Stream Consumer — app/events/consumer_registry.py**
- CInDE-only consumer wiring v4.x events to activity feed
- IRC_UPDATE, EXPORT_COMPLETED, ITD_GENERATED, OUTCOME_RECORDED events

**V4X_INTELLIGENCE Panel — app/portfolio/dashboard.py**
- New PanelType.V4X_INTELLIGENCE for portfolio dashboard
- Aggregates IRC, Export, ITD, and Outcome metrics
- `_generate_v4x_intelligence()` method for panel content

**Team Formation Helpers — app/discovery/formation.py**
- `get_team_gaps(pursuit_id)`: Returns team coverage gaps

**RBAC Warmup — app/middleware/rbac.py**
- `warm_rbac_cache()`: Pre-populates role permission cache at startup

**IDTFS Index Verification — app/discovery/idtfs.py**
- `verify_idtfs_indexes(database)`: Validates expertise matching indexes

**Audit Verification — app/events/audit.py**
- `verify_audit_writable()`: Confirms audit log is writable

### Modified

- **main.py**: Added deployment mode startup sequence, conditional router registration
- **app/core/config.py**: VERSION updated to 5.0.0
- **.env.example**: Added DEPLOYMENT_MODE documentation

### Tests

- **tests/test_linde_mode.py**: 15 tests for LINDE certification
  - Health endpoint returns LINDE mode
  - Enterprise gates disabled
  - Shared gates enabled
  - Enterprise routes return 404
  - Coaching, momentum, IRC active

- **tests/test_cinde_mode.py**: 15 tests for CINDE certification
  - Health endpoint returns CINDE mode
  - All enterprise gates enabled
  - Shared gates enabled
  - RBAC cache warmup
  - Portfolio V4X panel generation

- **tests/test_gii_portability.py**: 17 tests for GII portability
  - GII format validation (v3.1 and v3.16)
  - onboard_to_cinde binding
  - dissolve_binding reversion
  - Binding history tracking
  - Data isolation verification
  - Transition context in ODICM

### Documentation

- **docs/DEPLOYMENT_MODE.md**: Comprehensive deployment mode reference
  - Mode comparison table
  - FeatureGate property reference
  - Startup sequence examples
  - GII portability usage
  - Docker Compose examples
  - Migration notes

### Architecture

- **FeatureGate Properties**:
  | Property | LINDE | CINDE |
  |----------|-------|-------|
  | org_entity_active | False | True |
  | team_formation_active | False | True |
  | idtfs_active | False | True |
  | portfolio_active | False | True |
  | soc2_audit_active | False | True |
  | rbac_active | False | True |
  | activity_stream_active | False | True |
  | convergence_protocol_active | False | True |
  | coaching_active | True | True |
  | outcome_intelligence_active | True | True |
  | momentum_active | True | True |
  | irc_active | True | True |
  | gii_active | True | True |
  | license_active | True | True |

- **GII Binding Types**: INDIVIDUAL (LInDE) | ORGANIZATION (CInDE)
- **GII Portability**: GII survives mode transitions, only binding changes

### Deployment

```bash
# LINDE Mode (default - individual innovators)
DEPLOYMENT_MODE=LINDE

# CINDE Mode (enterprise organizations)
DEPLOYMENT_MODE=CINDE
ORG_ID_SEED=your-bootstrap-org-seed
```

---

## [4.10.0] — 2026-03-27 "The Resource Intelligence Engine"

### Series
InDE v4.x — Outcome Intelligence & Resource Intelligence Extension.
v4.10 adds the Innovation Resource Canvas (IRC) module — conversational
resource intelligence that accumulates across the pursuit lifecycle and
synthesizes into a structured canvas at a coached Consolidation Moment.

### Added
**IRC Signal Detection Engine — app/modules/irc/signal_detection_engine.py**
- ResourceSignalFamily: 5 signal families (IDENTIFICATION, AVAILABILITY,
  COST, TIMING, UNCERTAINTY)
- Pattern pre-filter: Fast regex scan (<5ms latency target)
- LLM extraction: 150-token resource extraction on positive pre-filter
- MDS registration: RESOURCE_SIGNAL Moment Type

**Resource Entry Manager — app/modules/irc/resource_entry_manager.py**
- ResourceCategory: 5 categories (HUMAN_CAPITAL, CAPITAL_EQUIPMENT,
  DATA_AND_IP, SERVICES, FINANCIAL)
- AvailabilityStatus: 4 states (SECURED, IN_DISCUSSION, UNRESOLVED, UNKNOWN)
- Fuzzy name deduplication (80% Jaccard similarity threshold)
- Phase alignment tracking (PITCH, DE_RISK, DEPLOY, ACROSS_ALL)

**Consolidation Engine — app/modules/irc/consolidation_engine.py**
- ConsolidationTriggerEvaluator: Signal density + pause point detection
- CanvasComputer: Derived canvas metrics (completeness, cost totals)
- MDS registration: IRC_CONSOLIDATION Moment Type
- Session-based cooldown (5 sessions) and decline memory (3 sessions)

**IRC Coach Bridge — app/modules/irc/irc_coach_bridge.py**
- Walk-through state machine: OFFER → PITCH → DERISK → DEPLOY → SYNTHESIS
- Language Sovereignty compliant coaching scripts
- Phase approach nudges for unresolved resources

**IRC LLM Client — app/modules/irc/irc_llm_client.py**
- Language Sovereignty post-validation with 2-retry correction
- Prohibited term sanitization fallback
- Resource extraction, coaching probe, and synthesis generation

**IRC Prompt Library — app/modules/irc/irc_prompt_library.py**
- 7 prompt templates with embedded Language Sovereignty instructions
- Probe templates for each signal family

**TIM Integration — app/modules/irc/tim_integration.py**
- notify_resource_update: Fire-and-forget TIM events
- get_upcoming_phase_resource_gaps: Phase readiness queries

**ITD Integration — app/modules/irc/itd_integration.py**
- get_itd_layer2_resource_data: Resource landscape for ITD Layer 2
- get_itd_layer5_resource_patterns: IML pattern queries
- get_itd_layer6_resource_projection: Forward projection data

**IML Integration — app/modules/irc/iml_integration.py**
- contribute_resource_pattern: resource_snapshot pattern type
- query_similar_resource_patterns: Archetype-filtered queries
- IKF eligibility checking (practice pursuits excluded)

**Export Integration — app/modules/irc/export_integration.py**
- get_export_resource_data: Formatted resource data for exports
- get_resource_appendix: Markdown/HTML/text appendix rendering

**IRC API — app/api/irc.py**
- GET /pursuits/{id}/irc/resources: List resource entries
- GET /pursuits/{id}/irc/resources/{rid}: Get single resource
- PATCH /pursuits/{id}/irc/resources/{rid}: Update resource
- GET /pursuits/{id}/irc/canvas: Get IRC canvas
- POST /pursuits/{id}/irc/consolidate: Trigger consolidation
- GET /pursuits/{id}/irc/status: Status indicator data

**Frontend Components — frontend/src/components/irc/**
- IRCStatusIndicator: Sidebar status display
- ResourceEntryCard: Resource display (compact and expanded views)
- CanvasDisplayPanel: Full canvas with phase/category views

### Modified
- evidence_architecture_compiler.py: Optional IRC resource_landscape data source
- export_template_registry.py: irc_integration flag, updated investment_readiness
  and gate_review_package templates
- itd_schemas.py: EvidenceArchitectureLayer.resource_landscape field
- database/indexes.py: resource_entries and irc_canvases indexes
- shared/display_labels.py: "At Risk" → "Needs Guidance" (Language Sovereignty fix)
- main.py: IRC router registration

### New MongoDB Collections
- resource_entries: .resource artifacts
- irc_canvases: Consolidated canvas artifacts

### Display Labels
- 5 category labels (People & Expertise, Tools & Equipment, etc.)
- 4 availability labels (In Place, Being Arranged, Still Open, Not Yet Explored)
- 4 confidence labels, 4 duration labels, 4 criticality labels, 4 phase labels

### Tests
- test_irc.py: Signal detection, display labels, Language Sovereignty,
  resource entry, consolidation, API models, integration tests

---

## [4.8.0] — 2026-03-26 "The Projection Engine"

### Series
InDE v4.x — Outcome Intelligence. v4.8 completes the 6-layer ITD architecture
by implementing the two forward-facing intelligence layers that transform the
Innovation Thesis Document from a retrospective artifact into a launchpad document.

### Added
**Forward Projection Engine — app/modules/projection/**
- TrajectoryAnalyzer: Structural similarity scoring across 4 dimensions
- HorizonGenerator: 90/180/365-day pattern extraction from trajectory dataset
- ForwardProjectionEngine: ITD Layer 6 - actionable trajectory guidance

**Pattern Connections Compiler**
- ConnectionMapBuilder: 4 connection types (WITHIN_PURSUIT, CROSS_PURSUIT,
  CROSS_DOMAIN, FEDERATION)
- PatternConnectionsCompiler: ITD Layer 5 - IML/IKF influence map

**Methodology Transparency Layer**
- Experience-level gate: EXPERT and ADVANCED only
- Analytical methodology descriptions — no branded framework names
- Returns None for ineligible levels (never blocks ITD composition)

**ITD Living Preview — app/modules/itd_preview/**
- LayerReadinessAssessor: 6-layer readiness scoring from pursuit data
- ITDPreviewEngine: Real-time layer readiness during active pursuits
- Preview API endpoints for innovators and admin summary

**ProjectionLLMClient**
- Language Sovereignty validation with methodology-name prohibition
- 2-retry correction prompt injection on violations

### Modified
- itd_composition_engine.py: Layer 5 & 6 now resolve via ITDLayerResolver
- itd_assembler.py: methodology_transparency field added
- itd_schemas.py: Layers 5 & 6 renamed to pattern_connections and forward_projection

### Architecture
- New module: app/modules/projection/ (9 files)
- New module: app/modules/itd_preview/ (4 files)
- 5 new REST endpoints for projection and preview
- 7 new telemetry events
- 4 new Display Label Registry categories (34 entries)

---

## [4.7.0] — 2026-03-26 "The Thesis Engine"

### Series
InDE v4.x — Momentum Management. v4.7 introduces the ITD Composition Engine,
transforming pursuit artifacts into Innovation Thesis Documents — structured
narratives that tell the story of an innovation journey.

### Added
**ITD Composition Engine — app/modules/itd/**
- 6-layer document architecture: Thesis Statement, Evidence Architecture,
  Narrative Arc, Coach's Perspective, Metrics Dashboard (placeholder),
  Future Pathways (placeholder)
- Thesis Statement Generator: Synthesizes vision, concerns, and archetype
- Evidence Architecture Compiler: Confidence trajectory + pivot record
- Narrative Arc Generator: Archetype-structured story in 5 acts
- Coach's Perspective Curator: Top coaching moments with thematic quotes
- ITD Assembler: Composes layers into final document
- ITD Composition Engine: Orchestrates generation with event bus

**Four-Phase Pursuit Exit Experience**
- Phase 1: Retrospective (existing flow)
- Phase 2: ITD Preview
- Phase 3: Artifact Packaging
- Phase 4: Transition Guidance
- PursuitExitOrchestrator: Manages phase progression

**Dynamic SILR Replacement**
- SILR generator delegates to ITD engine for pursuit_type=innovation
- Practice pursuits retain legacy SILR behavior

**Coached Retrospective Integration**
- Retrospective answers mapped to ITD layers
- Journey highlights feed Narrative Arc
- Key learnings feed Coach's Perspective

### Architecture
- MongoDB collection: innovation_thesis_documents
- 5 new REST endpoints under /api/v1/pursuits/{id}/itd
- 5 telemetry events: itd.generation_started, itd.layer_completed, etc.
- 4 Display Label Registry categories

---

## [4.4.1] — 2026-03-17 "Innovation Vitals"

### Series
InDE v4.x — Momentum Management. v4.4.1 adds the Innovation Vitals panel to
Admin Diagnostics, enabling real-time behavioral analysis of beta testers.

### Added
**Innovation Vitals Panel — Admin Diagnostics**
- New "Innovator Vitals" tab as first tab in Diagnostics panel
- Per-user behavioral intelligence aggregation from existing MongoDB collections
- Engagement status classification: ENGAGED, EXPLORING, AT RISK, DORMANT, NEW
- Summary bar with status counts and color indicators
- Sortable table with columns: Innovator, Experience, Pursuits, Phase, Artifacts, Sessions, Status
- Expandable row details: Last Login, Session Duration, Member Since
- Status and experience level filter dropdowns
- Client-side search by name or email
- CSV export of current filtered view
- Auto-refresh every 120 seconds

**Backend Aggregation Endpoint**
- GET /api/system/diagnostics/innovator-vitals (admin-only)
- InnovatorVitalsService class for efficient MongoDB aggregation
- Response envelope with users array, summary counts, and warnings

### Architecture
- New module: app/modules/diagnostics/innovator_vitals.py
- New component: frontend/src/components/admin/InnovatorVitalsTab.jsx
- Zero changes to coaching logic (ODICM, scaffolding, IML, RVE)
- Read-only queries against existing collections

---

## [4.4.0] — 2026-03-XX "The Learning Engine"

### Series
InDE v4.x — Momentum Management. v4.4 closes the intelligence loop opened by the
entire v4.x series: momentum signals accumulated across pursuits become cross-innovator
patterns. The IML learns what keeps innovators moving forward. The coach adapts.

### Added
[filled in at end of build]

### Architecture
- GitHub: https://github.com/Dapman/InDE_4_4
- Deployment: Local development only
- v3.16.0 beta testing continues unaffected
- InDE_4_3 preserved at ~/InDE_4_3 — not modified

---

## [4.2.0] — 2026-03-15 "The Depth Frame"

### Series
InDE v4.x — Momentum Management. v4.2 extends momentum management beyond
session boundaries with depth-framed re-entry and async re-engagement.

### Added
**Momentum-Aware Re-Entry System — app/modules/reentry/**
- Personalized coach opening turns for returning users based on last
  session's momentum state and gap duration
- Depth-framed context assembly from session history
- Re-entry opening library with pursuit-specific templates

**Async Re-Engagement System — app/modules/reengagement/**
- Lightweight outreach (48-72h) for innovators who haven't returned
- Coach-voiced pursuit-specific question delivery
- Re-engagement tracking and analytics

### Changed
- ODICM first-turn detection extended to support re-entry context injection
- Admin diagnostics extended with re-engagement metrics

---

## [4.1.0] — 2026-03-14 "The Momentum Engine"

### Series
InDE v4.x — Momentum Management. v4.1 introduces the Momentum Management
Engine (MME) — the intelligence layer that makes the v4.0 bridge context-aware,
pursuit-specific, and dynamically adaptive to each innovator's conversational
energy.

### Added
**Momentum Management Engine — app/momentum/**

signal_collectors.py:
- MomentumSignals dataclass: 4 dimensions (response_specificity, conversational_lean,
  temporal_commitment, idea_ownership), each 0.0–1.0
- ResponseSpecificityCollector: word count + precision/vagueness pattern scoring
- ConversationalLeanCollector: forward energy vs. closure language detection
- TemporalCommitmentCollector: future action reference detection
- IdeaOwnershipCollector: possessive/active vs. distancing/passive framing
- collect_signals(): unified entry point for all four collectors

momentum_engine.py:
- SessionMomentumState: live per-session state (turn_count, signal_history, composite_score, tier)
- MomentumSnapshot: persistence dataclass for session exit
- MomentumManagementEngine: per-session intelligence module
  - process_turn(): signal extraction + rolling-window composite update
  - Rolling window: 5 turns, recency-discounted (10% discount per position back)
  - Composite weights: specificity 0.30, lean 0.25, commitment 0.25, ownership 0.20
  - Tier thresholds: HIGH >=0.70, MEDIUM >=0.45, LOW >=0.25, CRITICAL >=0.0
  - _build_context(): tier-differentiated coaching guidance for ODICM injection
  - snapshot(): session exit capture

bridge_library.py:
- BRIDGE_LIBRARY: vision x 4 tiers, fear x 4 tiers, validation x 4 tiers, _fallback x 4 tiers
- {idea_domain}, {idea_summary}, {user_name}, {persona} placeholders
- All templates are questions (end with '?') — no methodology terminology

bridge_selector.py:
- BridgeSelector: replaces v4.0 random momentum_bridge_generator()
- Tier-aware selection (HIGH tier -> advance bridges, CRITICAL tier -> reconnection bridges)
- Pursuit context injection with graceful fallback for missing values
- Recently-used deduplication (last 3 bridges)

momentum_persistence.py:
- MomentumPersistence: MongoDB persistence service
- save_snapshot() -> momentum_snapshots collection (90-day TTL index)
- contribute_iml_pattern() -> iml_patterns collection (momentum_trajectory type)
- get_momentum_summary() -> per-pursuit health aggregation

### Changed
**ODICM Turn Pipeline:**
- MME instantiated at session creation, snapshotted at session end
- process_turn() called on every innovator message
- COACHING TONE GUIDANCE block prepended to ODICM system prompt each turn
- Artifact completion bridge upgraded: BridgeSelector replaces random selection
- Bridge now momentum-tier-aware and pursuit-context-parameterized

**Coaching Convergence Protocol:**
- check_convergence() accepts optional momentum_context
- HIGH tier: convergence threshold lowered by 0.05
- LOW tier: threshold raised by 0.08 / CRITICAL: raised by 0.15
- Backward compatible — no change when momentum_context is None

**Admin Telemetry (DiagnosticsAggregator):**
- momentum_health section added: total_sessions, avg_momentum_score,
  tier_distribution, bridge_delivery_rate, bridge_response_rate,
  post_vision_exit_rate (the primary v4.x success metric)

### Architecture
- New collection: momentum_snapshots (90-day TTL, indexed by pursuit_id, gii_id)
- New IML pattern type: momentum_trajectory (written at pursuit terminal states)
- GitHub: https://github.com/Dapman/InDE_4_1 (fresh history from v4.0.0 baseline)
- Deployment: Local development only
- v3.16.0 beta testing continues unaffected on InDEVerse-1
- InDE_4 (v4.0.0) preserved at ~/InDE_4 — not modified

### What Claude Code Must NOT Change
- Display Label Registry and all v4.0 language changes (complete — do not touch)
- Navigation labels, onboarding flow copy (complete from v4.0)
- 5-container Docker architecture
- All v3.16 / v4.0 API contracts
- IKF, federation, GII, RBAC, audit logging
- Any active Digital Ocean configuration or v3.16 deployment

---

## [4.0.0] — 2026-03-14 "The Coherence Build"

### Series
v4.0 begins the Momentum Management series. It is a coherence build —
zero new features, zero functional regression. Only what the innovator
reads changes.

### Changed

- **Display Label Registry Extended** (`app/shared/display_labels.py`)
  - 7 new categories: `workflow_step`, `artifact_panel`, `pursuit_state_display`,
    `onboarding_path`, `innovator_role`, `depth_progress`, `re_engagement`
  - New methods: `get_workflow_step()`, `get_pursuit_state()`
  - Novice suppression for `methodology_selection` step

- **Frontend Navigation Labels** (innovator-facing goal vocabulary)
  - `CoachMessage.jsx`: "Fear Extraction" → "Protecting Your Idea"
  - `ChatHeader.jsx`: All mode labels updated to goal vocabulary
  - `CommandPalette.jsx`: Commands use action-oriented language
  - `ChatInput.jsx`: Placeholders reframed as questions
  - `ScaffoldingPanel.jsx`: "Fears & Risks" → "Risks & Protections"
  - `ArtifactsPanel.jsx`: Group labels use innovator vocabulary
  - `artifactParser.js`, `print.js`: Artifact titles reframed

- **Coaching Language Adapters** (`app/coaching/methodology_archetypes.py`)
  - Added `MOMENTUM_BRIDGES` templates for session close/re-engagement
  - New methods: `get_session_close_message()`, `get_re_engagement_message()`,
    `get_depth_acknowledgment()`

- **Momentum Telemetry** (`app/services/telemetry.py`)
  - 8 new momentum events: `session_opened`, `session_closed`, `re_engaged`,
    `long_gap_return`, `depth_advanced`, `depth_acknowledged`, `bridge_shown`,
    `context_restored`
  - Helper function `track_momentum()` for standardized event properties

### Architecture
- GitHub: InDE_4 repository (fresh history from v3.16.0 baseline)
- Deployment: Local development only — no Digital Ocean in v4.x series
- v3.16.0 beta testing continues unaffected on InDEVerse-1

### Verification
- All modified Python files pass syntax validation
- No "Fear Extraction" or "Vision Formulator" terminology remains in user-facing code
- Display Label Registry: 38 categories, 199 labels registered

---

## v3.16.0 — Production Trust (March 2026)

**Release Date:** 2026-03-08

A production-readiness release focused on establishing trust through secure communications, reliable email delivery, innovator identity, and operational observability.

### Added

- **HTTPS via Let's Encrypt**: Automatic SSL certificate provisioning and renewal
  - Nginx reverse proxy with Certbot integration
  - Auto-renewal cron job for certificates
  - HTTP to HTTPS redirect for all traffic

- **Transactional Email Service**: SendGrid/SMTP integration for reliable email delivery
  - Password reset emails with secure tokens
  - Welcome emails for new user registration
  - Configurable email templates with InDE branding

- **Global Innovator Identifier (GII)**: Automatic assignment at registration
  - Unique GII format: `GII-XXXXXXXX` (8-character alphanumeric)
  - Stored in user profile, displayed in settings
  - Foundation for cross-pursuit analytics

- **Behavioral Telemetry**: GII-keyed event tracking for product analytics
  - Session start/end events with duration
  - Feature usage events (coaching, artifacts, retrospectives)
  - Non-PII event schema with GII correlation

### Fixed

- **Deployment Baseline**: Codified all Digital Ocean deployment fixes
  - WebSocket authentication using `decode_token` (not `verify_token`)
  - UUID generation fallback for non-HTTPS contexts
  - CRLF line ending validation in `.env` files
  - Environment variable persistence across container restarts
  - `.editorconfig` enforcing LF line endings

### Technical Details

- Added `scripts/validate_env.sh` for pre-deployment environment validation
- Added `scripts/migrate_v315_data.sh` for data migration from v3.15
- MongoDB data migration archive support for seamless upgrades

---

## v3.15.0 — First User Ready (March 2026)

**Release Date:** 2026-03-06

A user experience and resilience release focused on ensuring an external user can successfully complete onboarding, understand the workspace without guidance, and have robust coaching sessions even when the LLM has intermittent issues.

### Added

- **Onboarding Gap Remediation**: All CRITICAL and HIGH findings from the v3.14 audit implemented and verified
  - All 5 onboarding screens behave as specified
  - All 4 completion criteria now tracked correctly

- **Guided Discovery Layer**: Lightweight ambient guidance for first-time users
  - `HelpTooltip` components on all 5 workspace zone headers
  - `HintCard` components in empty zones for first-time users
  - `GettingStartedChecklist` widget in workspace sidebar
  - Discovery state persisted in user profile

- **API Rate Limiting**: Per-user and per-IP rate limiting middleware
  - Per-user coaching limit (default 30 requests/minute)
  - Per-IP authentication limit (default 10 attempts/5 minutes)
  - Sliding window implementation, no Redis dependency

- **LLM Resilience**: Retry logic and timeout handling for coaching endpoint
  - 3-attempt retry with exponential backoff (2s → 4s → 8s)
  - 30-second client-side timeout indicator with cancel option
  - Human-readable error messages for all failure scenarios

- **Error Recovery**: React ErrorBoundary wrapping all workspace zones
  - Zone-specific fallback cards with refresh button
  - Frontend errors logged to diagnostics error buffer
  - Global exception handler for user-friendly 500 messages

- **Discovery API Endpoints**:
  - `GET /api/v1/user/discovery` - Returns discovery state
  - `POST /api/v1/user/discovery/dismiss` - Persists hint dismissal
  - `POST /api/v1/user/discovery/reset` - Resets all dismissed hints
  - `POST /api/v1/errors/client` - Receives frontend error reports

### New Environment Variables (all optional with safe defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `INDE_COACHING_RATE_LIMIT` | 30 | Per-user coaching rate limit (requests/minute) |
| `INDE_AUTH_RATE_LIMIT` | 10 | Per-IP auth attempt limit |
| `INDE_AUTH_RATE_LIMIT_WINDOW` | 300 | Auth rate limit window (seconds) |

### New Files

```
app/middleware/
└── rate_limiting.py              # Sliding window rate limiter

app/api/
├── user_discovery.py             # User discovery state API
└── client_errors.py              # Frontend error logging

frontend/src/components/
├── discovery/
│   ├── GettingStartedChecklist.jsx
│   ├── HintCard.jsx
│   └── HelpTooltip.jsx
└── common/
    └── ErrorBoundary.jsx

frontend/src/api/
└── discovery.js                  # Discovery API client
```

### Changed

- Users collection: `discovery` subdocument added (additive, no migration required)
- All coaching endpoint error messages updated to user-friendly language
- Frontend error reports now appear in diagnostics error buffer

---

## v3.14.0 — Operational Readiness (March 2026)

**Release Date:** 2026-03-05

An operational readiness release that adds system health monitoring, onboarding completeness tracking, and backup automation for self-hosted deployments.

### Added

- **In-App Diagnostics Panel**: Admin-only system health dashboard at `/diagnostics`
  - Real-time error counts by severity (ERROR, WARNING, CRITICAL)
  - Onboarding funnel visualization with completion rates
  - System health status monitoring
  - Recent error log table with filtering
  - Auto-refresh every 30 seconds

- **Onboarding Completeness Audit**: Funnel metrics tracking four completion criteria
  - `vision_artifact_created` - First vision artifact
  - `fear_identified` - First fears artifact
  - `methodology_selected` - Methodology guidance engagement
  - `iml_pattern_engaged` - IKF pattern surfaced

- **Error Buffer**: Thread-safe circular buffer for application error events
  - In-memory storage (never persisted)
  - 100-entry capacity
  - Severity-level filtering

- **Backup & Restore Scripts**: MongoDB backup automation
  - `scripts/backup.sh` - Timestamped archive creation with compression
  - `scripts/restore.sh` - Archive restoration with safety prompts
  - Configurable retention (default 30 days)
  - Authentication support

### New Files

```
app/modules/diagnostics/
├── __init__.py
├── error_buffer.py          # Thread-safe error ring buffer
├── aggregator.py            # Health metric aggregation
└── onboarding_metrics.py    # Onboarding funnel service

app/migrations/
└── v314_operational.py      # Collection & index creation

scripts/
├── backup.sh                # MongoDB backup automation
└── restore.sh               # Archive restoration

frontend/src/pages/
└── DiagnosticsPage.jsx      # Admin diagnostics panel

ONBOARDING_AUDIT.md          # Instrumentation documentation
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/system/diagnostics` | System diagnostics aggregation (admin) |
| GET | `/api/system/diagnostics/onboarding` | Onboarding funnel stats (admin) |
| GET | `/api/system/diagnostics/errors` | Recent error entries (admin) |

### Schema Changes

**New collection: `onboarding_metrics`**
- `user_id`: User identifier
- `started_at`: Session start timestamp
- `completed_at`: Completion timestamp (null if incomplete)
- `criteria`: Object with four boolean completion flags
- `screen_reached`: Integer (1-5) for funnel stage
- `duration_seconds`: Time to completion

**New indexes:**
- `onboarding_metrics_user_started`: (user_id, started_at DESC)
- `onboarding_metrics_started`: (started_at DESC)

### Changed

- Global exception handler now records errors to diagnostics buffer
- LeftSidebar navigation shows Diagnostics link for admin users

### Technical Notes

- Diagnostics panel requires `role: "admin"`
- All instrumentation wrapped in try/catch for graceful degradation
- Migration runs automatically on startup (idempotent)
- No breaking changes to existing APIs

---

## v3.13.0 — Innovator Experience Polish (March 2026)

**Release Date:** 2026-03-05

A workspace quality-of-life release that makes InDE feel like a thoughtfully designed environment. Archiving keeps the workspace clean, search makes history useful, export makes work portable, and notification preferences make the platform respectful of attention.

### Added

- **Pursuit Archiving**: Move any pursuit out of the active workspace while preserving all data. Archived pursuits are stored separately and can be restored at any time.
- **Pursuit Restoration**: Return an archived pursuit to the active workspace with a single action.
- **Archived Pursuits View**: Dedicated list showing all archived pursuits with restore functionality.
- **Coaching Conversation Search**: Full-text search across session history within a pursuit, with 3-turn context window around each match. Uses MongoDB text indexes for performance.
- **Pursuit Export Packaging**: Download a complete pursuit as a ZIP file containing conversations, vision artifacts, fear register, milestone timeline, and export manifest.
- **Notification Preferences**: UI and API for controlling activity feed visibility, mention alerts, state change notifications, contribution alerts, and polling interval.
- **MongoDB Text Index**: Full-text search index on conversation_history collection.
- **Compound Archive Index**: Optimized queries for archived/active pursuit filtering.

### New Files

```
app/
├── modules/
│   ├── pursuit/
│   │   ├── __init__.py
│   │   ├── archive.py          # Archive/restore service
│   │   └── export.py           # ZIP export generation
│   └── search/
│       ├── __init__.py
│       └── conversation_search.py  # Full-text search
└── migrations/
    └── v313_experience_polish.py   # Add archive fields

frontend/src/components/
├── pursuit/
│   ├── ArchiveButton.jsx        # Archive/restore button
│   └── ArchivedPursuitsList.jsx # Archived pursuits panel
├── search/
│   └── ConversationSearch.jsx   # Inline search UI
├── export/
│   └── ExportButton.jsx         # Export download button
└── settings/
    └── NotificationPreferences.jsx  # Notification settings
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pursuits/{id}/archive` | Archive a pursuit |
| POST | `/api/pursuits/{id}/restore` | Restore an archived pursuit |
| GET | `/api/pursuits/archived/list` | List archived pursuits |
| GET | `/api/pursuits/{id}/export` | Download pursuit as ZIP |
| GET | `/api/coaching/{id}/search?q=` | Search conversation history |
| GET | `/api/account/notification-preferences` | Get notification settings |
| PUT | `/api/account/notification-preferences` | Update notification settings |

### Changed

- Active pursuit list queries now exclude archived pursuits by default
- Pursuit model: added `is_archived` (bool, default false) and `archived_at` fields
- List pursuits endpoint accepts `include_archived` query parameter

### Architecture

- Export packages generated on-demand in memory — not persisted server-side
- Conversation search scoped per-pursuit — cross-pursuit search is a future enhancement
- Notification preferences stored within existing user.preferences object — no schema migration required

---

## v3.12.0 — Innovator Trust & Completeness (March 2026)

**Release Date:** 2026-03-05

A trust-building release that delivers essential account management features expected by modern SaaS users: password reset, session management, and GDPR-compliant account deletion with a 14-day cooling-off period.

### Added

- **Password Reset Flow**: Secure, time-limited, single-use tokens with email delivery (graceful degradation when SMTP not configured)
- **Session Management**: View and terminate active sessions from Settings page; see device type, IP address, and login time
- **Account Deletion**: Two-phase deletion with 14-day grace period; email confirmation with cancellation link; GDPR/CCPA compliant data removal
- **Email Service**: SMTP integration for transactional emails with graceful degradation; supports password reset and deletion confirmation
- **Admin Password Reset Link**: Endpoint for self-hosted deployments to generate reset links without SMTP

### New Files

```
app/
├── services/
│   ├── __init__.py
│   └── email_service.py      # SMTP email with graceful degradation
├── modules/
│   └── account/
│       ├── __init__.py
│       ├── deletion.py       # Two-phase account deletion
│       └── password_reset.py # Secure token-based reset
├── api/account.py            # Account management endpoints
└── migrations/
    └── v312_account_trust.py # Add status/deletion fields to users

frontend/src/
├── pages/
│   ├── ForgotPasswordPage.jsx
│   ├── ResetPasswordPage.jsx
│   └── CancelDeletionPage.jsx
└── components/settings/
    ├── SessionManagement.jsx
    ├── PasswordChange.jsx
    └── AccountDeletion.jsx
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/account/forgot-password` | Request password reset email |
| POST | `/api/account/reset-password` | Reset password with token |
| POST | `/api/account/validate-reset-token` | Check token validity |
| GET | `/api/account/password-reset-status` | Check if SMTP configured |
| GET | `/api/account/sessions` | List active sessions |
| DELETE | `/api/account/sessions/{id}` | Terminate specific session |
| DELETE | `/api/account/sessions` | Terminate all sessions |
| PUT | `/api/account/change-password` | Change password (authenticated) |
| POST | `/api/account/request-deletion` | Initiate account deletion |
| GET | `/api/account/cancel-deletion` | Cancel pending deletion |
| GET | `/api/account/deletion-status` | Check deletion status |
| POST | `/api/account/admin/users/{id}/reset-link` | Admin: generate reset link |

### Schema Changes

**users collection:**
- `status`: "active" | "deactivated" | "deleted"
- `deletion_requested_at`: ISO timestamp
- `deletion_scheduled_for`: ISO timestamp (14 days after request)
- `deletion_cancellation_token`: cryptographic token for email link
- `deleted_at`: ISO timestamp when fully deleted

**New collection: `password_reset_tokens`**
- `token_hash`: SHA-256 hash (never store plaintext)
- `user_id`: reference to user
- `expires_at`: datetime with TTL index (auto-delete expired tokens)
- `used`: boolean (single-use enforcement)

### Security Features

- Password reset tokens SHA-256 hashed before storage
- Tokens expire after 60 minutes (configurable)
- Single-use enforcement: tokens invalidated after consumption
- All sessions revoked on password change or reset
- Account deletion requires email confirmation before processing
- 14-day cooling-off period with cancellation option
- Background job processes scheduled deletions hourly

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| SMTP_HOST | - | SMTP server hostname |
| SMTP_PORT | 587 | SMTP server port |
| SMTP_USERNAME | - | SMTP auth username |
| SMTP_PASSWORD | - | SMTP auth password |
| SMTP_FROM_ADDRESS | noreply@indeverse.com | Sender email |
| SMTP_FROM_NAME | InDE Innovation Platform | Sender name |
| SMTP_USE_TLS | true | Use STARTTLS |
| APP_BASE_URL | http://localhost:5173 | Base URL for email links |
| PASSWORD_RESET_TOKEN_EXPIRY_MINUTES | 60 | Token expiry time |
| ACCOUNT_DELETION_COOLING_OFF_DAYS | 14 | Grace period before deletion |

---

## v3.11.0 — Timeline Housekeeping & Closure (March 2026)

**Release Date:** 2026-03-05

A deliberate, scoped housekeeping build that completes and formally closes the timeline module workstream. This release adds performance indexes and team permission enforcement while retiring timeline management features that are outside InDE's coaching scope.

### Added

- **MongoDB Compound Indexes (TD-015)**: Query performance indexes on `pursuit_milestones`, `temporal_events`, and `time_allocations` collections for sustained performance as data grows
- **Team Milestone Permissions (TD-014)**: Only pursuit creators can change milestone dates, types, or delete milestones in team pursuits
- **`created_by_user_id` Field**: New milestone field tracking who created each milestone; backfilled from pursuit ownership for existing records
- **`app/database/indexes.py`**: Centralized index management module, called at startup
- **`app/scaffolding/permissions.py`**: Milestone permission enforcement utilities
- **`GET /timeline/{id}/milestone-permissions`**: New endpoint for UI to check edit permissions

### Changed

- Milestone mutation API routes now enforce creator-only permission for structural changes in team pursuits
- Milestone extraction sets `created_by_user_id` from session context
- Timeline panel shows "Locked" indicator for non-creators in team pursuits
- Inconsistency resolution buttons hidden for non-creators

### Architecture

Timeline enhancement workstream formally closed. The timeline module (v3.9 extraction, v3.10 integrity, v3.11 housekeeping) is complete. The following TD items are retired:

| TD | Description | Retirement Rationale |
|----|-------------|---------------------|
| TD-003 | Missing Milestone Detection | Project scheduling, not coaching |
| TD-004 | Compression Risk Scoring | PM risk management, not coaching |
| TD-007 | Dependency Tracking | Critical path analysis out of scope |
| TD-008 | Timeline Branching/Scenarios | PM scenario planning out of scope |
| TD-009 | Calendar Sync | Stakeholder calendar mgmt out of scope |
| TD-010 | Evidence Collection | Compliance tooling out of scope |
| TD-011 | Scaffolding Modulation by Deadline | Calendar pressure corrupts coaching quality |
| TD-012 | RVE Trigger from Milestones | RVE already triggered by conversation |
| TD-013 | Estimation Accuracy Tracking | Performance management out of scope |
| TD-016 | Natural Language Milestone Updates | Ambiguity risk in coaching context |

**Principle**: InDE captures timeline information because it reveals innovator intent and commitment. InDE does not manage timelines.

### Files Modified

```
app/
├── database/
│   ├── __init__.py         # New module
│   └── indexes.py          # New: index management
├── scaffolding/
│   ├── permissions.py      # New: permission enforcement
│   ├── engine.py           # Pass user_id to extractor
│   └── timeline_extractor.py # Add created_by_user_id
├── api/timeline.py         # Permission checks on mutations
├── main.py                 # Startup index + migration calls
└── migrations/
    └── v311_milestone_permissions.py  # New migration

frontend/
├── src/api/pursuits.js     # getMilestonePermissions API
└── src/components/panels/TimelinePanel.jsx  # Permission-aware UI
```

---

## v3.9.1 — User Provider Selection (February 2026)

**Release Date:** 2026-02-28

Adds user-facing AI provider selection to Settings, allowing users to choose between Cloud (Premium), Local (Cost-Free), or Auto provider routing with transparent cost vs quality tradeoffs.

### AI Provider Preference UI

New Settings section available to all users:

- **Provider Options**: Auto (Recommended), Cloud (Premium), Local (Cost-Free)
- **Cost/Quality Transparency**: Each option shows quality tier and cost indicator
- **Availability Status**: Real-time provider availability display
- **Fallback Warnings**: Notification when preferred provider is unavailable

### Backend Provider Preference Support

- **`get_provider_by_preference()`**: New registry method for preference-aware selection
- **`preferred_provider` Parameter**: Added to LLM Gateway `/llm/chat` endpoint
- **User Preference Storage**: Persisted in `users.preferences.llm_provider`
- **Coaching Integration**: User preference passed through entire coaching flow

### New Endpoints

- **`GET /system/llm/user-providers`**: Returns provider options and user's saved preference
- Accessible to all authenticated users (not admin-only)

### Files Modified

```
llm-gateway/
├── provider_registry.py      # Added get_provider_by_preference()
└── main.py                   # Added preferred_provider to LLMChatRequest

app/
├── api/system.py             # Added /llm/user-providers endpoint
├── api/coaching.py           # Pass user preference to engine
├── core/llm_interface.py     # Pass preferred_provider to gateway
└── scaffolding/engine.py     # Added set/get_llm_preference methods

frontend/
├── src/api/system.js         # Added getUserProviders, updateLlmPreference
└── src/pages/SettingsPage.jsx # Added AI Provider section
```

---

## v3.9.0 — Air-Gapped Intelligence (February 2026)

**Release Date:** 2026-02-28

The Air-Gapped Intelligence release enables InDE to operate without cloud connectivity by supporting local LLM inference via Ollama. Organizations with strict data sovereignty requirements can now run InDE entirely on-premises with no API calls to external services.

### Provider Registry Architecture

New LLM abstraction layer with automatic failover:

- **Provider Chain**: Configuration-driven provider ordering
- **Automatic Failover**: Primary unavailable → next provider in chain
- **Quality Tier Detection**: Automatic classification based on model capabilities
  - PREMIUM: Claude (full ODICM capabilities)
  - STANDARD: 70B+ parameter local models
  - BASIC: 7B-13B parameter local models
- **Failover Event Logging**: Redis Streams integration for observability

### Ollama Integration

Full support for local LLM inference via Ollama:

- **REST API Adapter**: `/api/chat` and `/api/generate` support
- **Model Metadata Detection**: Parameter count, context window, quantization
- **Quality Tier Assignment**: Based on model parameter count
- **Streaming Support**: SSE-compatible streaming for real-time coaching

### ODICM Prompt Calibration Layer

Quality-tier-aware prompt adaptation:

- **Premium Tier**: Full ODICM prompts, 3000 token system prompts
- **Standard Tier**: Compressed prompts, simplified reasoning chains
- **Basic Tier**: Numbered directives, explicit structure, 800 token limit
- **Methodology Keywords Preserved**: Critical coaching concepts maintained

### Docker Compose Deployment Modes

Three deployment configurations:

- **Standard** (`docker-compose.yml`): Claude API (default)
- **Air-Gapped** (`docker-compose.ollama.yml`): Ollama only
- **Hybrid** (`docker-compose.hybrid.yml`): Claude primary, Ollama failover

### Admin Panel Provider Status UI

New settings panel for administrators:

- Provider chain visualization with availability status
- Quality tier badges per provider
- Failover history timeline
- Air-gapped mode indicator

### LLM Gateway Enhancements

- **Provider Status Endpoints**: `/api/v1/providers`, `/api/v1/providers/quality-tier`
- **Failover Events Endpoint**: `/api/v1/providers/failover-events`
- **Environment Configuration**: `LLM_PROVIDER`, `LLM_PROVIDER_CHAIN`, `OLLAMA_MODEL`

### Technical Changes

- Version updated to 3.9.0 in all services
- New modules: `provider_registry.py`, `prompt_calibration.py`
- New provider: `ollama_provider.py`
- 2 new Docker Compose overlays
- Integration tests for provider architecture

### Files Added

```
llm-gateway/
├── provider_registry.py      # Provider chain management
├── providers/
│   ├── base_provider.py      # Abstract provider interface
│   ├── claude_provider.py    # Refactored Claude adapter
│   └── ollama_provider.py    # Ollama REST API adapter
└── tests/
    ├── conftest.py
    └── test_v39_providers.py

app/coaching/
└── prompt_calibration.py     # Quality-tier prompt adaptation

docker-compose.ollama.yml     # Air-gapped deployment
docker-compose.hybrid.yml     # Hybrid failover deployment

tests/
└── test_v39_airgapped.py     # Integration tests
```

### Migration Notes

- Existing v3.8 deployments continue to work unchanged (default: Claude only)
- For air-gapped deployment:
  1. Install Ollama on host system
  2. Pull model: `ollama pull llama3`
  3. Use `docker-compose.ollama.yml` overlay
- For hybrid failover: Use `docker-compose.hybrid.yml` overlay
- No database migrations required

---

## v3.8.0 — Commercial Launch Infrastructure (February 2026)

**Release Date:** 2026-02-27

The Commercial Launch Infrastructure release transforms InDE from an internal prototype into a deployable, licensable product. This release adds enterprise licensing, production deployment tooling, and customer onboarding infrastructure.

### License Validation Service (`inde-license`)

New microservice for license key management and entitlement enforcement:

- **License Key Format**: `INDE-{TIER}-{CUSTOMER_ID}-{CHECKSUM}` with CRC32 validation
- **Three License Tiers**: Professional (PRO), Enterprise (ENT), Federated (FED)
- **Grace Period State Machine**: 30-day tolerance with progressive warnings
  - Days 1-7: GRACE_QUIET (silent grace)
  - Days 8-21: GRACE_VISIBLE (warnings appear)
  - Days 22-30: GRACE_URGENT (prominent warnings)
  - Day 31+: EXPIRED (read-only mode)
- **Seat Counting**: MongoDB-based active user tracking with compliance checks
- **Offline Support**: HMAC-SHA256 signed license files for air-gapped deployments
- **Simulation Mode**: Local development without license.indeverse.com connection
- **FastAPI Endpoints**: `/health`, `/api/v1/validate`, `/api/v1/status`, `/api/v1/activate`, `/api/v1/seats`
- **74 unit tests** covering all license service modules

### Production Deployment Infrastructure

- **`deployment/docker-compose.production.yml`**: 6-service orchestration with:
  - Health checks with startup/interval/timeout configuration
  - Resource limits (CPU, memory) per container
  - Log rotation (10 files, 10MB each)
  - Volume mounts for data persistence
  - Network isolation for security
- **`deployment/.env.template`**: Documented environment configuration
- **`deployment/start.sh`**: Linux/macOS startup script with prereq checks
- **`deployment/start.ps1`**: Windows PowerShell startup script
- **`deployment/DEPLOYMENT.md`**: Comprehensive deployment guide

### First-Run Setup Wizard

6-step React wizard (`/setup`) for customer onboarding:

1. **License Activation**: Enter license key, validate with license service
2. **Organization Setup**: Create organization name and slug
3. **Admin Account**: Create first administrator with email/password
4. **API Key Configuration**: BYOK Anthropic API key entry and validation
5. **System Verification**: Health check for all InDE services
6. **Setup Complete**: Summary and launch button

Components: `SetupWizard.jsx`, `LicenseActivation.jsx`, `OrganizationSetup.jsx`, `AdminAccount.jsx`, `ApiKeyConfig.jsx`, `SystemCheck.jsx`, `SetupComplete.jsx`

### BYOK API Key Management

LLM Gateway enhancements for Bring-Your-Own-Key support:

- **`GET /api/v1/validate-key`**: Test currently configured API key
- **`POST /api/v1/validate-key`**: Test a provided key without configuring
- **`POST /api/v1/configure`**: Runtime key configuration (no restart required)
- API key validation via actual Anthropic API call
- Key stored in memory only (never persisted to disk)
- Health endpoint shows key configuration status

### License Status in Admin Panel

Settings page (`/settings`) enhancements for administrators:

- License status banner with state indicator (Active, Grace, Expired)
- Days remaining counter during grace periods
- License tier and seat usage display
- Enabled features list
- Refresh button for real-time status check

### Backend License Integration

- **`app/middleware/license.py`**: Request filtering middleware
  - Validates license on each request
  - Enforces read-only mode when expired
  - Excludes health/setup endpoints from validation
- **`app/api/system.py`**: Extended with license endpoints
  - `GET /api/system/license`: Full license status
  - `GET /api/system/first-run`: Check if setup wizard needed
  - `POST /api/system/setup-complete`: Mark setup as done

### Technical Changes

- Version updated to 3.8.0 in `app/core/config.py` and `frontend/package.json`
- LLM Gateway version updated to 3.8.0
- Settings page version display updated to 3.8.0
- Main `docker-compose.yml` includes license service

### Files Added

```
license-service/
├── models.py           # Pydantic models for license data
├── config.py           # Service configuration
├── key_generator.py    # License key generation/validation
├── crypto.py           # HMAC-SHA256 signing
├── grace_period.py     # Grace period state machine
├── seat_counter.py     # MongoDB seat counting
├── offline_validator.py # Offline license validation
├── entitlement_manager.py # Core license logic
├── main.py             # FastAPI application
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container definition
└── tests/              # 74 unit tests

deployment/
├── docker-compose.production.yml
├── .env.template
├── start.sh
├── start.ps1
└── DEPLOYMENT.md

frontend/src/pages/setup/
├── SetupWizard.jsx
└── steps/
    ├── index.js
    ├── LicenseActivation.jsx
    ├── OrganizationSetup.jsx
    ├── AdminAccount.jsx
    ├── ApiKeyConfig.jsx
    ├── SystemCheck.jsx
    └── SetupComplete.jsx

app/middleware/
└── license.py
```

### Migration Notes

- Existing v3.7.4 deployments need a license key to continue operating
- Contact InDEVerse sales for license activation
- Setup wizard runs automatically on first deployment
- API key must be configured during setup or via environment variable

---

## v3.7.4.4 - Integration, Polish & Gradio Retirement

**Release Date:** 2026-02-20

### Returning User Experience
- Context detection algorithm: resume pursuit, portfolio overview, welcome screen, expert minimal
- WelcomePage for zero-pursuit users with capability overview cards
- User API module for session state and preferences
- Context-aware routing after authentication

### Adaptive Complexity
- Four UI complexity tiers: guided, standard, streamlined, minimal
- Experience level auto-detection from innovator maturity model
- AdaptiveVisibility component for conditional rendering
- Complexity preferences stored in uiStore with auto-detect toggle

### Backend Cleanup
- **Pydantic v2 migration**: All `class Config` converted to `model_config = ConfigDict(...)`
- **datetime.utcnow() cleanup**: All instances replaced with `datetime.now(timezone.utc)`
- Zero Pydantic deprecation warnings
- Zero deprecated datetime calls

### Gradio Retirement
- Removed Gradio UI files: `chat_interface.py`, `auth_interface.py`, `portfolio_dashboard.py`, `v34_extensions.py`
- Kept `analytics_visualizations.py` (matplotlib-based, used by reports)
- Updated `run_inde.py` to FastAPI-only mode
- FastAPI serves React production build as static files
- Single frontend: React 18 with Vite
- Updated app/ui/__init__.py to export only visualization utilities

### Static File Serving
- React build served from `frontend/dist/` via FastAPI
- Catch-all route for client-side routing (React Router)
- API routes, WebSocket, and docs routes excluded from catch-all
- Development: Vite dev server on port 5173 with proxy to FastAPI

### v3.7.4 UI Overhaul Complete
The Gradio-to-React migration is finished. InDE is now served by a
professional React 18 frontend consuming the unchanged FastAPI backend.
Five sub-builds (v3.7.4.0 through v3.7.4.4) transformed InDE from a
prototyping UI into a production-grade Innovation Development Environment.

### Technical Notes
- Bundle size: 1,001 KB JS, 70 KB CSS
- Context detection runs once after authentication
- Complexity tier affects sidebar default states and tooltip visibility
- Static file serving only active when `frontend/dist/` exists

---

## v3.7.4.3 - Intelligence, Analytics & EMS

**Release Date:** 2026-02-20

### Intelligence Panel (Right Sidebar)
- IML pattern suggestion cards with similarity badges and feedback actions (Apply, Explore, Dismiss)
- Cross-pollination insight cards with domain distance indicators and transfer probability
- Learning velocity metrics with sparkline trend visualization
- Biomimicry insights section (visible on TRIZ pursuits)
- Apply-to-chat action sends pattern context to coaching conversation

### Portfolio Dashboard (Full Page)
- Pursuit grid/list view toggle with filtering by status, methodology, health zone
- Methodology distribution donut chart (CSS-based, no external dependencies)
- Cross-pursuit pattern insights from IML
- Aggregate metric cards: active pursuits, success rate, average health, learning velocity
- Route: `/portfolio` with Briefcase icon in left sidebar

### Organization Portfolio (Full Page, Enterprise)
- Org-level aggregated analytics across all innovators
- Methodology effectiveness comparison chart (grouped bars)
- Innovation pipeline Kanban visualization (Discovery → Development → Validation → Complete)
- Learning velocity trends with industry benchmark comparison
- Team performance breakdown cards
- Route: `/org/portfolio` (visible only for enterprise users)

### IKF Federation Panels (Right Sidebar)
- **Federation Status Panel**: Connection state with human-friendly labels (Display Labels applied)
  - Incoming pattern feed with type badges and confidence indicators
  - Global benchmark comparisons with visual bars
  - Trust network relationships with sharing level indicators
- **Contribution Panel**: Queue management with review interface
  - Side-by-side preview (original vs. generalized) before sharing
  - Approve/Decline workflow with optional notes
  - Contribution history tracking
- All internal identifiers pass through Display Labels — zero schema leakage

### EMS Visual Suite
- **EMS Sidebar Tab**: Observation status indicator, inference ready notifications
- **EMS Page** (`/ems`): Full dashboard with inference results and published archetypes
  - Phase cards with confidence badges (stars: HIGH ★★★, MODERATE ★★☆, LOW ★☆☆)
  - Comparison preview against existing archetypes
  - Published methodology cards with visibility management and evolution checking
- **Review Session Interface** (`/ems/review/:sessionId`): The Crown Jewel
  - Split-screen layout: 60% visual review + 40% coaching chat
  - Draggable phase cards with inline rename (double-click)
  - Interactive activity chips: click to toggle optional/required, × to remove, + to add
  - Process flow visualization (SVG, updates in real-time as phases reorder)
  - Split-screen comparison view against existing archetypes
  - Naming panel with coach-suggested names and principles
  - Visibility selector with descriptive labels (Personal, Team, Organization, InDEVerse)
  - Publish confirmation modal with methodology summary
  - Coaching chat alongside visual review — both paths converge through Review Session API

### New Infrastructure
- 3 API client modules: `intelligence.js`, `portfolio.js`, `federation.js`
- 2 Zustand stores: `intelligenceStore.js`, `emsStore.js`
- 4 new right sidebar tabs: Intelligence, Federation, Contributions, EMS
- 3 new page routes: `/portfolio`, `/org/portfolio`, `/ems/review/:sessionId`
- Left sidebar nav entries: Portfolio, Org Portfolio (enterprise)

### Right Sidebar Tab Count (10 total)
- Scaffolding (v3.7.4.2)
- Artifacts (v3.7.4.2)
- Health (v3.7.4.2)
- Timeline (v3.7.4.2)
- Convergence (v3.7.4.2)
- Team (v3.7.4.2)
- **Intelligence** (v3.7.4.3, NEW)
- **Federation** (v3.7.4.3, NEW)
- **Contributions** (v3.7.4.3, NEW)
- **EMS** (v3.7.4.3, NEW)

### Technical Notes
- Bundle size: 997 KB JS (+86 KB from v3.7.4.2)
- CSS bundle: 70 KB (+2 KB)
- All visualizations use CSS or simple SVG — no heavy charting libraries added
- Display Labels applied throughout new panels — verified zero internal identifier exposure

### Coming in v3.7.4.4
- @Mention autocomplete in chat input
- Full artifact editor pages
- Gradio retirement

---

## v3.7.4.2 - Innovation Workspace Panels

**Release Date:** 2026-02-20

### Right Sidebar Panel System
- Tabbed panel container with adaptive tab visibility
- Notification dots for data changes on inactive tabs
- Panel-to-chat context triggers ("Ask coach" buttons)
- Panel tab persistence across pursuit switches
- Mobile bottom sheet access for panels
- Tablet overlay toggle

### Scaffolding Tracker Panel
- 40-element completion visualization grouped by 6 categories:
  - Vision (6 elements): Problem statement, solution concept, value proposition, target user, desired outcome, current situation
  - Market (7 elements): Competitive landscape, differentiation, business model, revenue model, go-to-market, market timing, adoption barriers
  - Technical (5 elements): Technical feasibility, resource requirements, team capabilities, scalability constraints, cost structure
  - Risk (6 elements): Capability fears, timing fears, market fears, execution fears, risk tolerance, regulatory concerns
  - Validation (6 elements): Hypothesis statement, test plan, key metrics, validation criteria, learning goals, decision criteria
  - Strategy (7 elements): Constraints, assumptions, success metrics, timeline, partnerships, stakeholder alignment, exit strategy
- Overall progress bar with color transitions (red <40%, amber 40-70%, green >70%)
- Click-to-expand element detail with confidence badge, timestamps, attribution
- "Ask coach" button for empty elements to trigger coaching conversation
- Team attribution on shared pursuits

### Artifact Viewer Panel
- Artifacts grouped by type (Vision, Validation, Analysis, Reports, Methodology)
- Inline preview overlay with markdown/JSON rendering
- Version badges and history
- Creation/update timestamps

### Health Dashboard Panel
- Health score gauge with circular progress ring (0-100)
- Zone badge with color coding (Healthy/Caution/At Risk)
- CSS sparkline trend visualization (7-14 days history)
- 5-component breakdown bars (Velocity, Completeness, Engagement, Risk Balance, Time Health)
- Active risk cards with severity indicators and "Discuss" action

### TIM Timeline Panel
- Phase progress bar with proportional segments per phase
- Current phase highlighting with indicator marker
- Planned vs. actual duration comparison with over/under indicators
- Velocity metrics with status badge (Ahead/On Track/Behind)
- Maturity score display with progress bar

### Convergence Indicators Panel
- Phase display with distinct visual treatment:
  - EXPLORING: Blue tint, "Gathering information" guidance
  - CONSOLIDATING: Amber tint, "Narrowing focus" guidance
  - COMMITTED: Green tint, "Moving forward" guidance
- Transition criteria checklist with satisfied/unsatisfied indicators
- "Ready to Move On" action button with confirmation dialog
- Captured outcomes from previous convergence decisions

### Team Panels (Enterprise)
- Sub-tabbed interface: Roster, Activity, Gaps
- Team roster with roles, online status, contribution counts
- Activity stream with polling refresh
- Team gap analysis with coverage visualization
- Contribution balance bars per team member

### Mobile/Tablet Responsive Design
- Mobile (<768px): Bottom action bar with panel icons, bottom sheet panels (70% height)
- Tablet (768-1023px): Toggle overlay for right sidebar
- Desktop (>1024px): Persistent right sidebar

### New Utilities
- `dateUtils.js`: formatDistanceToNow, formatShortDate, formatFullDate, daysUntil, formatDuration
- Extended uiStore with panel state management (activePanelTab, panelNotifications, mobilePanelOpen)

### Technical Notes
- Bundle size: 900 KB JS (+58 KB from v3.7.4.1)
- CSS bundle: 65 KB (+3 KB)
- All panels use React Query with 30-second staleTime and refetchInterval
- No new external dependencies (CSS-only visualizations per spec)

### Coming in v3.7.4.3
- @Mention autocomplete in chat input
- Full artifact editor pages
- Advanced analytics visualizations

---

## v3.7.4.1 - Coaching Experience & Pursuit Management

**Release Date:** 2026-02-20

### Core Coaching Experience

This build delivers the heart of InDE — the real-time streaming coaching conversation. An innovator can now create a pursuit, choose a methodology, and have a coaching conversation through the React frontend.

#### Coaching Chat Interface
- **CoachMessage**: Markdown-rendered coach responses with mode badges
- **InnovatorMessage**: Right-aligned user messages with initials avatar
- **StreamingMessage**: Real-time streaming with blinking cursor indicator
- **MomentNotification**: 6 inline notification types (Teaching, Fear, Readiness, Health Warning, Portfolio, Experiment)
- **ChatHeader**: Mode indicator + health badge + phase display
- **ChatInput**: Auto-growing textarea with Cmd+Enter, mode-aware placeholders
- **ChatContainer**: Full orchestration — WebSocket, history, REST fallback

#### Pursuit Creation Wizard (NewPursuitPage)
- **Step 1**: Spark/problem description input
- **Step 2**: Archetype selection — 6 standard methodologies + emergent archetypes from EMS
  - Lean Startup 🔬, Design Thinking 🎨, Stage-Gate 🏗️, TRIZ 🧩, Blue Ocean 🌊, Freeform ✨
  - Emergent archetypes show ConfidenceBadge + "Discovered from practice" label
- **Step 3**: Optional time & commitment settings
- **Step 4**: Summary review and creation

#### Pursuit Explorer (LeftSidebar)
- React Query integration with 30-second polling
- Active pursuit highlighting with glow effect
- Archetype emojis and health dots per pursuit
- Completed/archived pursuits collapsible section
- Collapsed mode with icon-only view and tooltips

#### Dashboard Enhancement
- Portfolio overview with pursuit cards
- Quick stats: active/completed/total pursuits
- Empty state with onboarding for new users
- Click-to-navigate pursuit cards

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd+K | Open command palette |
| Cmd+1-9 | Switch to pursuit 1-9 |
| Cmd+N | New pursuit creation |
| Cmd+\ | Toggle left sidebar |
| Cmd+] | Toggle right sidebar |

### Command Palette Enhancements
- Dynamic pursuit switching with (current) indicator
- Coaching actions: Vision, Fear Extraction, Retrospective, Experiment
- Fuzzy search across all commands

### Coaching Mode Visual Treatment
- 6 distinct modes: coaching, vision, fear, retrospective, ems_review, crisis
- Top border accent color changes per mode
- Mode badge in chat header
- Crisis mode: red pulse animation

### Responsive Design
- Desktop (≥1024px): Full 5-zone layout
- Tablet (768-1023px): Auto-collapsed sidebar
- Mobile (<768px): Hidden sidebar, wider message bubbles (90%)

### New Dependencies
- `framer-motion`: Message animations and transitions

### Technical Notes
- Bundle size: 842 KB JS (+336 KB from v3.7.4.0 due to framer-motion)
- CSS bundle: 62 KB
- WebSocket streaming with exponential backoff reconnection
- REST fallback when WebSocket unavailable

### Coming in v3.7.4.2
- Innovation Workspace Panels
- Scaffolding tracker panel
- Artifacts preview panel
- Analytics charts

---

## v3.7.4.0 - UI Foundation: React + Design System

**Release Date:** 2026-02-19

### New Frontend Infrastructure

This build establishes the architectural foundation for InDE's modern React frontend. Every subsequent v3.7.4.x build constructs upon this foundation.

#### Core Technologies
- **React 18 + Vite**: Modern build tooling with hot module replacement
- **Tailwind CSS v3**: Utility-first styling with InDE design tokens
- **shadcn/ui**: Component library (Button, Input, Dialog, Command, etc.)
- **Zustand**: Lightweight state management
- **React Query**: Server state and caching
- **React Router v6**: Client-side routing

#### Design System - "InDE Forge"
- Comprehensive color system:
  - InDE brand palette (inde-50 through inde-950)
  - Surface colors for dark/light themes
  - Phase colors (Vision, Pitch, De-Risk, Build, Deploy)
  - Confidence tiers (High, Moderate, Low, Insufficient)
  - Health zones (Thriving, Healthy, Caution, At Risk, Critical)
- Typography: DM Sans (display), Source Sans 3 (body), JetBrains Mono (code)
- Spacing system with sidebar/topbar/statusbar presets
- Animation presets (fade-in, slide-in, shimmer)

#### 5-Zone Layout Shell
- Zone 1: TopBar with logo, pursuit dropdown, search, notifications, theme toggle
- Zone 2: LeftSidebar with pursuit list and navigation (collapsible)
- Zone 3: WorkCanvas with React Router Outlet
- Zone 4: RightSidebar intelligence panel (placeholder)
- Zone 5: StatusBar with connection status, phase, version
- Responsive breakpoints: Desktop (1024px+), Tablet (768px-1023px), Mobile (<768px)

#### API Client Layer
- Axios instance with auth interceptors
- API modules: auth, pursuits, coaching, artifacts, analytics, ems, ikf, system
- WebSocket client for coaching streaming with reconnection
- Display Label hook with infinite cache

#### State Management
- `authStore`: User authentication state
- `pursuitStore`: Active pursuit context and cache
- `uiStore`: Theme, panel states, command palette
- `coachingStore`: Messages, streaming, health

#### Router & Routes
- Protected routes inside AppShell
- Route stubs: Dashboard, Pursuit, Coaching, Artifacts, Analytics, EMS, IKF, Settings
- Functional LoginPage with form and demo login
- 404 NotFoundPage

#### Command Palette (Cmd+K)
- Fuzzy search across pursuits, actions, navigation
- Keyboard shortcuts:
  - Cmd+K: Open command palette
  - Cmd+\: Toggle left sidebar
  - Cmd+]: Toggle right sidebar
  - Escape: Close modals

#### Display Components
- ConfidenceBadge, PhaseBadge, HealthBadge
- DisplayLabel with hook integration
- LoadingSpinner, LoadingOverlay, LoadingPlaceholder

### Backend Additions
- GET /api/system/display-labels endpoint for frontend label caching
- `DisplayLabels.get_all_categories()` method

### Technical Notes
- Gradio remains functional in parallel on port 7860
- React dev server runs on port 5173
- Vite proxy forwards /api and /ws to FastAPI on port 8000
- Dark theme is the default experience

### Coming in v3.7.4.x
- v3.7.4.1: Coaching Chat Experience
- v3.7.4.2: Portfolio Dashboard & Pursuit Workspace
- v3.7.4.3: Intelligence Panels & Analytics
- v3.7.4.4: Final Polish & Gradio Retirement

---

## v3.7.3 - EMS Innovator Review Interface & Archetype Publisher

**Release Date:** 2026-02-19

### New Capabilities

- **Innovator Review Interface**: Coaching-assisted session to validate, refine, and name inferred methodologies
  - Phase-by-phase review with confidence indicators
  - Refinement tools: rename, reorder, add/remove, mark optional/required, merge, split
  - Comparison view against similar existing archetypes
  - Naming, description, and key principles capture

- **Archetype Publisher**: Commits approved methodologies to the Archetype Repository
  - Version 1.0 designation with provenance
  - Attribution metadata crediting the creator
  - Configurable visibility (Personal, Team, Organization, IKF-Shared)
  - Evolution tracking for methodology updates

- **Published Methodology Selection**: Emergent archetypes appear alongside established methodologies

- **IKF Integration**: Emergent methodologies shareable through federation with generalization

- **Distinctiveness Remediation**: True archetype-to-archetype similarity comparison (Audit I fix)

### EMS Pipeline Complete

The full EMS pipeline is now operational:

```
Observe freely -> Infer structure -> Review with innovator -> Publish methodology -> Select for future pursuits
```

### New Infrastructure

- `review_sessions` collection with 3 indexes
- 7 new EMS event types for review and publication workflow
- 13 new API endpoints (9 review + 4 archetype management)
- 25+ new Display Label entries across 4 categories:
  - `review_status`: INITIATED, IN_PROGRESS, APPROVED, REJECTED, ABANDONED
  - `refinement_action`: RENAMED_PHASE, REORDERED, ADDED_ACTIVITY, REMOVED_ACTIVITY, etc.
  - `methodology_visibility`: PERSONAL, TEAM, ORGANIZATION, IKF_SHARED
  - `archetype_version`: CURRENT, SUPERSEDED, EVOLVING

### UI Enhancements

- New "EMS" button in Quick Actions toolbar
- EMS Panel with three tabs:
  - My Methodologies: Published methodologies with visibility indicators
  - Discovered Patterns: Patterns awaiting review with similarity info
  - Review Session: Interactive coaching conversation interface

### API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ems/review/start/{innovator_id}` | POST | Start review session |
| `/api/ems/review/{session_id}/exchange` | POST | Coaching exchange |
| `/api/ems/review/{session_id}/status` | GET | Get review status |
| `/api/ems/review/{session_id}/name` | POST | Set methodology name |
| `/api/ems/review/{session_id}/visibility` | POST | Set visibility |
| `/api/ems/review/{session_id}/approve` | POST | Approve and publish |
| `/api/ems/review/{session_id}/reject` | POST | Reject pattern |
| `/api/ems/review/{session_id}/comparison` | GET | Compare to archetypes |
| `/api/ems/archetypes/mine` | GET | List published |
| `/api/ems/archetypes/{id}/visibility` | PUT | Update visibility |
| `/api/ems/archetypes/{id}/evolution-check` | GET | Check evolution |
| `/api/ems/archetypes/{id}/evolve` | POST | Trigger re-analysis |

### Breaking Changes

None.

### Dependencies

No new external dependencies.

---

## v3.7.2 - EMS Pattern Inference Engine & ADL Generator

**Release Date:** 2025-01-XX

### New Capabilities

- Pattern Inference Engine with 4 algorithms (sequence mining, phase clustering, transition detection, dependency analysis)
- ADL Generator producing full ADL 1.0 archetypes from inferred patterns
- Archetype similarity comparison for distinctiveness assessment

---

## v3.7.1 - EMS Process Observation Engine

**Release Date:** 2025-01-XX

### New Capabilities

- Process Observation Engine for behavior capture
- Observation types: tool invocation, artifact creation, phase transitions, decisions
- Signal weighting for external vs internal activities

---

## v3.7.0 - Display Label Registry

**Release Date:** 2025-01-XX

### New Capabilities

- Unified Display Label Registry for human-readable UI text
- Version-organized label categories
- Icon support for visual indicators
