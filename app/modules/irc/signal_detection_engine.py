"""
InDE MVP v5.1b.0 - IRC Signal Detection Engine

Primary Deliverable A: Detects resource-relevant language in coaching turns
across five signal families. Uses a two-stage pipeline:
1. Pattern pre-filter (fast regex scan, <5ms latency target)
2. LLM extraction (150 tokens max, only on positive pre-filter)

Signal Families:
- IDENTIFICATION: "we would need", "this requires", "I'll need"
- AVAILABILITY: "assuming we have", "not sure we can get"
- COST: "budget-wise", "what that runs", "investment"
- TIMING: "won't need until", "only during testing"
- UNCERTAINTY: "hopefully", "I think we can", "question mark"

2026 Yul Williams | InDEVerse, Incorporated
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("inde.irc.signal_detection")


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class ResourceSignalFamily(str, Enum):
    """Signal families for resource detection."""
    IDENTIFICATION = "IDENTIFICATION"   # "we would need", "this requires", "I'll need"
    AVAILABILITY = "AVAILABILITY"       # "assuming we have", "not sure we can get"
    COST = "COST"                       # "budget-wise", "I wonder what that runs"
    TIMING = "TIMING"                   # "won't need until", "only during testing"
    UNCERTAINTY = "UNCERTAINTY"         # "I think we can", "hopefully", "question mark"


@dataclass
class ResourceSignal:
    """Detected resource signal from a coaching turn."""
    family: ResourceSignalFamily
    raw_text: str                           # The span of text that triggered detection
    turn_id: str                            # Coaching session turn ID
    pursuit_id: str
    detected_at: str                        # ISO 8601
    confidence: float                       # 0.0–1.0
    candidate_resource_name: Optional[str]  # LLM-extracted resource name if discernible
    candidate_category: Optional[str]       # Preliminary category classification
    uncertainty_flag: bool                  # True if signal carries hedging language
    matched_families: List[ResourceSignalFamily] = field(default_factory=list)


# =============================================================================
# SIGNAL PATTERN VOCABULARY
# =============================================================================

SIGNAL_PATTERNS: Dict[ResourceSignalFamily, List[str]] = {
    ResourceSignalFamily.IDENTIFICATION: [
        r"\bwe('d| would)? need\b",
        r"\bthis requires?\b",
        r"\bwill need\b",
        r"\bsomeone with\b",
        r"\baccess to\b",
        r"\bhave to get\b",
        r"\brequires? (a |an |the )?\w+",
        r"\bwe('ll)? have to\b",
        r"\bneed (a |an |the )?\w+ (to|for|in order)\b",
        r"\bgoing to need\b",
        r"\bneed someone\b",
        r"\bneed expertise\b",
        r"\bneed help with\b",
        r"\bwho can\b",
        r"\bspecialist\b",
        r"\bcontractor\b",
        r"\bequipment\b",
        r"\btool(s|ing)?\b",
        r"\bsoftware\b",
        r"\bplatform\b",
        r"\binfrastructure\b",
        r"\bdeveloper\b",
        r"\bengineer\b",
        r"\bdesigner\b",
        r"\bconsultant\b",
    ],
    ResourceSignalFamily.AVAILABILITY: [
        r"\bassuming we have\b",
        r"\bpending approval\b",
        r"\bnot sure we can\b",
        r"\bthat depends on\b",
        r"\bnot certain we have\b",
        r"\bif we can get\b",
        r"\bstill (need to )?sort(ing)? out\b",
        r"\bquestion mark\b",
        r"\bdon't have yet\b",
        r"\bwould need to find\b",
        r"\bwould need to secure\b",
        r"\blooking for\b",
        r"\bstill searching\b",
        r"\bneed to arrange\b",
        r"\bwaiting on\b",
        r"\bpending\b",
        r"\bin discussion\b",
        r"\bnegotiating\b",
    ],
    ResourceSignalFamily.COST: [
        r"\bbudget[\s-]?wise\b",
        r"\bgoing to be expensive\b",
        r"\bwhat (that |it )?runs?\b",
        r"\bhave to pay\b",
        r"\bnot cheap\b",
        r"\bcost(s)? (a lot|money|us)\b",
        r"\bafford\b",
        r"\bfunding\b",
        r"\binvestment\b",
        r"\bcapital\b",
        r"\bprice\b",
        r"\bspend\b",
        r"\bexpense\b",
        r"\bsalary\b",
        r"\brate\b",
        r"\bfees?\b",
        r"\bquote\b",
        r"\bestimate\b",
        r"\b\$\d+\b",
        r"\bthousand\b",
        r"\bmillion\b",
    ],
    ResourceSignalFamily.TIMING: [
        r"\bwon't need (that |it )?(until|till)\b",
        r"\bonly during\b",
        r"\bupfront before\b",
        r"\bthat comes later\b",
        r"\bnot (yet|right now)\b",
        r"\bin the \w+ phase\b",
        r"\bafter we\b",
        r"\bbefore we can\b",
        r"\bonce we have\b",
        r"\bwhen we get to\b",
        r"\bearly stage\b",
        r"\blater stage\b",
        r"\binitially\b",
        r"\beventually\b",
        r"\bdown the road\b",
        r"\bfirst we need\b",
    ],
    ResourceSignalFamily.UNCERTAINTY: [
        r"\bI think we can\b",
        r"\bhopefully\b",
        r"\bstill figuring\b",
        r"\bTBD\b",
        r"\bnot sure\b",
        r"\bI'm not certain\b",
        r"\bwe might be able to\b",
        r"\bif everything works out\b",
        r"\bmaybe\b",
        r"\bpossibly\b",
        r"\bprobably\b",
        r"\bmight need\b",
        r"\bcould need\b",
        r"\bnot clear\b",
        r"\bunclear\b",
        r"\bopen question\b",
        r"\bstill exploring\b",
        r"\bworking through\b",
    ],
}

# Compile patterns for performance
COMPILED_PATTERNS: Dict[ResourceSignalFamily, List[re.Pattern]] = {
    family: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for family, patterns in SIGNAL_PATTERNS.items()
}


# =============================================================================
# SIGNAL DETECTION ENGINE
# =============================================================================

class IRCSignalDetectionEngine:
    """
    Two-stage resource signal detection pipeline.

    Stage 1: Pattern pre-filter (fast, no LLM)
    Stage 2: LLM extraction (only on positive pre-filter)
    """

    def __init__(self, llm_client=None):
        """
        Initialize the signal detection engine.

        Args:
            llm_client: Optional LLM client for extraction. If None, signals
                       are detected but not enriched with LLM extraction.
        """
        self.llm_client = llm_client
        self._confidence_threshold = 0.65  # Minimum for MDS response injection

    async def detect(
        self,
        text: str,
        turn_id: str,
        pursuit_id: str,
        coaching_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ResourceSignal]:
        """
        Detect resource signals in text using the two-stage pipeline.

        Args:
            text: The coaching turn text to analyze
            turn_id: The coaching turn ID
            pursuit_id: The pursuit ID
            coaching_context: Optional context for LLM extraction

        Returns:
            ResourceSignal if detected with confidence >= threshold, else None
        """
        if not text or len(text.strip()) < 10:
            return None

        # Stage 1: Pattern pre-filter
        matched_families, matched_text = self._pattern_prefilter(text)

        if not matched_families:
            logger.debug(f"[IRCSignal] No resource signal patterns in turn {turn_id}")
            return None

        logger.info(
            f"[IRCSignal] Pre-filter hit: {[f.value for f in matched_families]} "
            f"in turn {turn_id}"
        )

        # Stage 2: LLM extraction (if client available)
        candidate_name = None
        candidate_category = None
        confidence = 0.7  # Base confidence from pattern match
        uncertainty_flag = ResourceSignalFamily.UNCERTAINTY in matched_families

        if self.llm_client:
            extraction = await self._llm_extract(
                text, matched_families, coaching_context
            )
            if extraction:
                candidate_name = extraction.get("resource_name")
                candidate_category = extraction.get("category")
                confidence = extraction.get("confidence", confidence)
                uncertainty_flag = extraction.get("uncertainty_flag", uncertainty_flag)

        # Build signal
        primary_family = self._select_primary_family(matched_families)

        signal = ResourceSignal(
            family=primary_family,
            raw_text=matched_text[:500],  # Truncate for storage
            turn_id=turn_id,
            pursuit_id=pursuit_id,
            detected_at=datetime.now(timezone.utc).isoformat(),
            confidence=confidence,
            candidate_resource_name=candidate_name,
            candidate_category=candidate_category,
            uncertainty_flag=uncertainty_flag,
            matched_families=matched_families,
        )

        # Only return if above confidence threshold
        if signal.confidence >= self._confidence_threshold:
            logger.info(
                f"[IRCSignal] Signal detected: {signal.family.value} "
                f"(confidence={signal.confidence:.2f}) for '{candidate_name}'"
            )
            return signal

        logger.debug(
            f"[IRCSignal] Signal below threshold: {signal.confidence:.2f} < "
            f"{self._confidence_threshold}"
        )
        return None

    def _pattern_prefilter(self, text: str) -> Tuple[List[ResourceSignalFamily], str]:
        """
        Fast pattern-based pre-filter for resource signals.

        Returns:
            Tuple of (matched families, matched text span)
        """
        matched_families = []
        matched_spans = []

        for family, patterns in COMPILED_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    matched_families.append(family)
                    matched_spans.append(match.group())
                    break  # One match per family is sufficient

        # Get context around first match
        matched_text = text
        if matched_spans:
            # Find first match position and extract surrounding context
            first_span = matched_spans[0]
            pos = text.lower().find(first_span.lower())
            if pos >= 0:
                start = max(0, pos - 50)
                end = min(len(text), pos + len(first_span) + 100)
                matched_text = text[start:end]

        return matched_families, matched_text

    def _select_primary_family(
        self, families: List[ResourceSignalFamily]
    ) -> ResourceSignalFamily:
        """
        Select the primary signal family when multiple are detected.

        Priority order: IDENTIFICATION > COST > AVAILABILITY > TIMING > UNCERTAINTY
        """
        priority = [
            ResourceSignalFamily.IDENTIFICATION,
            ResourceSignalFamily.COST,
            ResourceSignalFamily.AVAILABILITY,
            ResourceSignalFamily.TIMING,
            ResourceSignalFamily.UNCERTAINTY,
        ]

        for family in priority:
            if family in families:
                return family

        return families[0] if families else ResourceSignalFamily.IDENTIFICATION

    async def _llm_extract(
        self,
        text: str,
        matched_families: List[ResourceSignalFamily],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to extract resource details from the signal text.

        Returns dict with: resource_name, category, confidence, uncertainty_flag
        """
        if not self.llm_client:
            return None

        try:
            from .irc_llm_client import IRCLLMClient

            if not isinstance(self.llm_client, IRCLLMClient):
                logger.warning("[IRCSignal] LLM client is not IRCLLMClient")
                return None

            return await self.llm_client.extract_resource_signal(
                text=text,
                matched_families=[f.value for f in matched_families],
                context=context,
            )

        except ImportError:
            logger.warning("[IRCSignal] IRCLLMClient not available")
            return None
        except Exception as e:
            logger.error(f"[IRCSignal] LLM extraction error: {e}")
            return None

    def detect_sync(
        self,
        text: str,
        turn_id: str,
        pursuit_id: str,
    ) -> Optional[ResourceSignal]:
        """
        Synchronous detection for non-async contexts.
        Only performs pattern pre-filter (no LLM extraction).
        """
        if not text or len(text.strip()) < 10:
            return None

        matched_families, matched_text = self._pattern_prefilter(text)

        if not matched_families:
            return None

        primary_family = self._select_primary_family(matched_families)
        uncertainty_flag = ResourceSignalFamily.UNCERTAINTY in matched_families

        return ResourceSignal(
            family=primary_family,
            raw_text=matched_text[:500],
            turn_id=turn_id,
            pursuit_id=pursuit_id,
            detected_at=datetime.now(timezone.utc).isoformat(),
            confidence=0.70,  # Pattern-only confidence
            candidate_resource_name=None,
            candidate_category=None,
            uncertainty_flag=uncertainty_flag,
            matched_families=matched_families,
        )


# =============================================================================
# MDS INTEGRATION
# =============================================================================

def get_resource_signal_moment_definition():
    """
    Returns the MDS Moment Definition for RESOURCE_SIGNAL.

    This is called by the coaching pipeline to register the IRC signal
    detection with the Moment Detection System.
    """
    return {
        "moment_type": "RESOURCE_SIGNAL",
        "priority": 5,           # Standard priority — below safety/emotional, above celebration
        "cooldown_turns": 0,     # No cooldown — every resource signal warrants response
        "description": "Conversational turn contains resource-relevant language",
    }
