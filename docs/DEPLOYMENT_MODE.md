# InDE v5.0 Deployment Mode Reference

**Version:** 5.0.0 — "The Convergence Build"
**Last Updated:** March 2026

## Overview

InDE v5.0 introduces the **Deployment Mode Architecture** — a single unified codebase
that serves both individual innovators (LInDE) and enterprise organizations (CInDE).

The deployment mode is controlled by a single environment variable: `DEPLOYMENT_MODE`

## Deployment Modes

### LINDE (Local InDE) — Individual Innovator Mode

**Default mode.** Designed for solo innovators working on personal pursuits.

```bash
DEPLOYMENT_MODE=LINDE
```

**Active Features:**
- Full coaching experience (ODICM)
- All v4.x modules (Momentum, IRC, ITD, Export, Projection, Outcome)
- GII identity (INDIVIDUAL binding)
- IKF federation client
- License validation
- TIM (Temporal Intelligence Manager)

**Dormant Features:**
- Organization service
- Team scaffolding / IDTFS
- Portfolio dashboard (org-level)
- Activity stream
- RBAC / governance
- SOC 2 audit pipeline
- Convergence protocol

**Enterprise Routes:**
Return `404 Not Found` — the enterprise surface does not exist in LINDE mode.

### CINDE (Corporate InDE) — Enterprise Mode

Designed for organizations with multiple innovators and team collaboration.

```bash
DEPLOYMENT_MODE=CINDE
ORG_ID_SEED=your-bootstrap-org-seed
```

**Required Environment Variables:**
- `ORG_ID_SEED`: Seed string for bootstrap organization initialization

**Active Features:**
All LINDE features PLUS:
- Organization service
- Team scaffolding / IDTFS (6-pillar expertise matching)
- Portfolio dashboard (9-panel enterprise intelligence)
- Activity stream (v4.x event wiring)
- RBAC middleware (custom roles, policy-based access)
- SOC 2 audit pipeline
- Convergence protocol
- GII org binding

## Startup Sequence

### LINDE Mode Startup
```
[startup] DeploymentMode=LINDE validated ✓
Starting InDE v5.0.0 - The Convergence Build
...
InDE API ready to accept requests
```

### CINDE Mode Startup
```
[startup] DeploymentMode=CINDE validated ✓
Starting InDE v5.0.0 - The Convergence Build
RBAC policy cache warmed
IDTFS indexes verified
Audit log writable
[startup] CInDE mode initialized ✓
InDE API ready to accept requests
```

## FeatureGate Properties

The FeatureGate singleton controls capability activation.

| Property | LINDE | CINDE |
|----------|-------|-------|
| `org_entity_active` | False | True |
| `team_formation_active` | False | True |
| `idtfs_active` | False | True |
| `portfolio_active` | False | True |
| `soc2_audit_active` | False | True |
| `rbac_active` | False | True |
| `activity_stream_active` | False | True |
| `convergence_protocol_active` | False | True |
| `coaching_active` | True | True |
| `outcome_intelligence_active` | True | True |
| `momentum_active` | True | True |
| `irc_active` | True | True |
| `gii_active` | True | True |
| `license_active` | True | True |

## GII Portability

GII (Global Innovator Identifier) is portable across deployment modes.

### LInDE to CInDE Transition
```python
from gii.manager import GIIManager

manager = GIIManager(db)
manager.onboard_to_cinde(user_id, org_id)
```
- GII remains unchanged
- Binding changes from INDIVIDUAL to ORGANIZATION
- Transition recorded in binding_history

### CInDE to LInDE Transition
```python
manager.dissolve_binding(user_id)
```
- GII remains unchanged
- Binding reverts to INDIVIDUAL
- Personal pursuits remain accessible
- Org-shared pursuits become read-only

### Data Isolation Verification
```python
isolation = manager.verify_data_isolation(user_id, former_org_id)
# Returns: {gii_isolated, personal_pursuits_accessible, isolation_verified}
```

## Health Endpoint

The `/health` endpoint includes deployment mode:

```json
{
  "status": "healthy",
  "version": "5.0.0",
  "deployment_mode": "LINDE",
  "redis": {"connected": true}
}
```

## Docker Compose

### LINDE Mode
```yaml
services:
  inde-app:
    environment:
      DEPLOYMENT_MODE: LINDE
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

### CINDE Mode
```yaml
services:
  inde-app:
    environment:
      DEPLOYMENT_MODE: CINDE
      ORG_ID_SEED: ${ORG_ID_SEED}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
```

## Migration Notes

### From v4.x (single mode)
1. Set `DEPLOYMENT_MODE=LINDE` (default behavior)
2. Existing users continue with INDIVIDUAL GII binding
3. No database migration required

### Enterprise Activation
1. Set `DEPLOYMENT_MODE=CINDE`
2. Provide `ORG_ID_SEED` for bootstrap organization
3. Existing GIIs can be bound to org via `onboard_to_cinde()`

## Testing

Run dual-mode certification tests:

```bash
# LINDE mode tests
DEPLOYMENT_MODE=LINDE pytest tests/test_linde_mode.py -v

# CINDE mode tests
DEPLOYMENT_MODE=CINDE ORG_ID_SEED=test-org pytest tests/test_cinde_mode.py -v

# GII portability tests
DEPLOYMENT_MODE=CINDE ORG_ID_SEED=test-org pytest tests/test_gii_portability.py -v
```

## Files Reference

**New Files (v5.0):**
- `app/services/feature_gate.py` — Deployment mode capability control
- `app/middleware/deployment_context.py` — Request context middleware
- `app/startup/mode_validator.py` — Startup validation
- `docs/DEPLOYMENT_MODE.md` — This document
- `tests/test_linde_mode.py` — LInDE certification tests
- `tests/test_cinde_mode.py` — CInDE certification tests
- `tests/test_gii_portability.py` — GII portability tests

---

**InDE v5.0.0 — The Convergence Build**
2026 Yul Williams | InDEVerse, Incorporated
