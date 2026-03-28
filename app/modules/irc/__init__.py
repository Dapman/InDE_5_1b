"""
IRC Module — v5.1b.0 "The Resource Intelligence Engine"

Implements the Innovation Resource Canvas: conversational resource
intelligence that accumulates across the pursuit lifecycle and synthesizes
into a structured canvas at a coached Consolidation Moment.

Architecture:
  Signal Detection Engine  -> detects resource signals in coaching turns
  Resource Entry Manager   -> creates/updates .resource artifacts
  Consolidation Engine     -> produces .irc canvas artifact
  IRC Coach Bridge         -> Language Sovereignty coaching interactions
  TIM Integration          -> phase-aligned resource feeds TIM
  ITD Integration          -> resource landscape for ITD Layer 2
  IML Integration          -> resource pattern learning and retrieval
  Export Integration       -> resource data for export templates

2026 Yul Williams | InDEVerse, Incorporated
"""

from .signal_detection_engine import IRCSignalDetectionEngine, ResourceSignal, ResourceSignalFamily
from .resource_entry_manager import ResourceEntryManager
from .consolidation_engine import IRCConsolidationEngine, ConsolidationTriggerEvaluator
from .irc_coach_bridge import IRCCoachBridge

__all__ = [
    "IRCSignalDetectionEngine",
    "ResourceSignal",
    "ResourceSignalFamily",
    "ResourceEntryManager",
    "IRCConsolidationEngine",
    "ConsolidationTriggerEvaluator",
    "IRCCoachBridge",
]
