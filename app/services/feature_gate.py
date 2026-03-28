"""
FeatureGate — Deployment mode capability control.
InDE v5.1b.0 — The Convergence Build

Initialized once at startup from DEPLOYMENT_MODE env var.
All module startup checks read from this singleton.
Never import settings inside a request handler to check mode —
use request.state.feature_gate instead (injected by DeploymentContext middleware).
"""
from enum import Enum
from functools import lru_cache
import os


class DeploymentMode(str, Enum):
    LINDE = "LINDE"   # Individual innovator — default
    CINDE = "CINDE"   # Enterprise / corporate


class FeatureGate:
    def __init__(self, mode: DeploymentMode):
        self.mode = mode
        self._cinde = (mode == DeploymentMode.CINDE)

    # ── CInDE-only gates ─────────────────────────────────────────────────────
    @property
    def org_entity_active(self) -> bool:       return self._cinde
    @property
    def team_formation_active(self) -> bool:   return self._cinde
    @property
    def idtfs_active(self) -> bool:            return self._cinde
    @property
    def portfolio_active(self) -> bool:        return self._cinde
    @property
    def enterprise_connectors(self) -> bool:   return self._cinde  # v5.1

    @property
    def connectors_registry_active(self) -> bool:
        """True only when enterprise_connectors is True AND all required env vars are present."""
        if not self.enterprise_connectors:
            return False
        # Check required GitHub App env vars
        required_vars = [
            "GITHUB_APP_ID",
            "GITHUB_APP_PRIVATE_KEY_PATH",
            "GITHUB_APP_CLIENT_ID",
            "GITHUB_APP_CLIENT_SECRET",
            "GITHUB_APP_WEBHOOK_SECRET",
            "CONNECTOR_ENCRYPTION_KEY",
        ]
        for var in required_vars:
            if not os.getenv(var):
                return False
        return True
    @property
    def soc2_audit_active(self) -> bool:       return self._cinde
    @property
    def rbac_active(self) -> bool:             return self._cinde
    @property
    def activity_stream_active(self) -> bool:  return self._cinde
    @property
    def convergence_protocol_active(self) -> bool: return self._cinde

    # ── SHARED gates (always True) ────────────────────────────────────────────
    @property
    def coaching_active(self) -> bool:         return True
    @property
    def outcome_intelligence_active(self) -> bool: return True
    @property
    def momentum_active(self) -> bool:         return True
    @property
    def irc_active(self) -> bool:              return True
    @property
    def gii_active(self) -> bool:              return True
    @property
    def license_active(self) -> bool:          return True

    def __repr__(self):
        return f"FeatureGate(mode={self.mode.value})"


@lru_cache(maxsize=1)
def get_feature_gate() -> FeatureGate:
    raw = os.getenv("DEPLOYMENT_MODE", "LINDE").upper().strip()
    try:
        mode = DeploymentMode(raw)
    except ValueError:
        raise ValueError(
            f"Invalid DEPLOYMENT_MODE='{raw}'. "
            f"Allowed values: LINDE, CINDE"
        )
    return FeatureGate(mode)
