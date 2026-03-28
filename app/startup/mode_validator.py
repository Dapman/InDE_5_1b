"""
Startup validator — checks required env vars per deployment mode.
Called once from app/main.py lifespan before any routes are served.
"""
import os
import logging
from pathlib import Path
from services.feature_gate import get_feature_gate, DeploymentMode

logger = logging.getLogger("inde.startup")


def validate_deployment_mode():
    gate = get_feature_gate()

    if gate.mode == DeploymentMode.CINDE:
        required = {
            "ORG_ID_SEED": "Required for bootstrap organization initialization in CINDE mode",
        }
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise EnvironmentError(
                f"DEPLOYMENT_MODE=CINDE requires missing env vars: "
                + ", ".join(f"{k} ({required[k]})" for k in missing)
            )

        # v5.1: Validate Enterprise Connectors env vars (optional but warn if missing)
        _validate_connector_env_vars()

    # Shared validation (both modes)
    # App can use direct API keys OR the LLM gateway
    has_direct_provider = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OLLAMA_BASE_URL")
    has_gateway = os.getenv("LLM_GATEWAY_URL")

    if not has_direct_provider and not has_gateway:
        raise EnvironmentError(
            "At least one LLM provider must be configured: "
            "ANTHROPIC_API_KEY, OLLAMA_BASE_URL, or LLM_GATEWAY_URL"
        )

    print(f"[startup] DeploymentMode={gate.mode.value} validated ✓")


def _validate_connector_env_vars():
    """
    Validate GitHub App environment variables for enterprise connectors.
    Logs CRITICAL warning if any are missing - connectors will be disabled but app continues.
    """
    connector_vars = {
        "GITHUB_APP_ID": "GitHub App ID from settings page",
        "GITHUB_APP_PRIVATE_KEY_PATH": "Path to GitHub App private key (.pem)",
        "GITHUB_APP_CLIENT_ID": "GitHub App OAuth client ID",
        "GITHUB_APP_CLIENT_SECRET": "GitHub App OAuth client secret",
        "GITHUB_APP_WEBHOOK_SECRET": "Secret for webhook signature verification",
        "CONNECTOR_ENCRYPTION_KEY": "AES-256 key for encrypting stored tokens (32 bytes hex)",
    }

    missing = []
    for var, desc in connector_vars.items():
        value = os.getenv(var)
        if not value:
            missing.append(f"{var} ({desc})")

    # Special validation for private key path
    pem_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
    if pem_path:
        if not Path(pem_path).exists():
            logger.critical(f"GITHUB_APP_PRIVATE_KEY_PATH file not found: {pem_path}")
            missing.append(f"GITHUB_APP_PRIVATE_KEY_PATH file not found")

    # Special validation for encryption key length
    enc_key = os.getenv("CONNECTOR_ENCRYPTION_KEY")
    if enc_key:
        try:
            key_bytes = bytes.fromhex(enc_key)
            if len(key_bytes) != 32:
                logger.critical(f"CONNECTOR_ENCRYPTION_KEY must be 32 bytes (64 hex chars), got {len(key_bytes)} bytes")
                missing.append("CONNECTOR_ENCRYPTION_KEY wrong length")
        except ValueError:
            logger.critical("CONNECTOR_ENCRYPTION_KEY must be valid hex string")
            missing.append("CONNECTOR_ENCRYPTION_KEY invalid hex")

    if missing:
        logger.critical(
            f"Enterprise Connectors DISABLED - missing configuration:\n  - "
            + "\n  - ".join(missing)
        )
        logger.critical("Set these env vars to enable GitHub connector integration")
    else:
        logger.info("Enterprise Connector configuration validated ✓")
