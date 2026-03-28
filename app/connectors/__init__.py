"""
InDE MVP v5.1b.0 - Enterprise Connectors Module

This module provides the pluggable enterprise connector framework.
All connector logic is CINDE-only, gated by feature_gate.enterprise_connectors.
"""

from .registry import ConnectorRegistry, connector_registry
from .base import BaseConnector, ConnectorMeta, ConnectorInstallation, ConnectorHealth

__all__ = [
    'ConnectorRegistry',
    'connector_registry',
    'BaseConnector',
    'ConnectorMeta',
    'ConnectorInstallation',
    'ConnectorHealth',
]
