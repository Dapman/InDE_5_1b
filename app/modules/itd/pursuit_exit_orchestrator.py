"""
InDE MVP v5.1b.0 - Pursuit Exit Orchestrator

Manages the Four-Phase Pursuit Exit Experience:

Phase 1: RETROSPECTIVE
- Guided reflection on the journey
- Capture key learnings, outcomes, methodology assessment
- Uses existing RetrospectiveOrchestrator

Phase 2: ITD_PREVIEW
- Generate Innovation Thesis Document
- Preview layers for innovator review
- Allow regeneration requests

Phase 3: ARTIFACT_PACKAGING
- Package all pursuit artifacts
- Generate exportable bundle
- Include ITD as primary document

Phase 4: TRANSITION_GUIDANCE
- Provide next steps recommendations
- Offer IKF contribution opportunity
- Close the pursuit loop

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

logger = logging.getLogger("inde.itd.exit_orchestrator")


# =============================================================================
# EXIT PHASE ENUM
# =============================================================================

class ExitPhase(str, Enum):
    """The four phases of pursuit exit."""
    RETROSPECTIVE = "retrospective"
    ITD_PREVIEW = "itd_preview"
    ARTIFACT_PACKAGING = "artifact_packaging"
    TRANSITION_GUIDANCE = "transition_guidance"
    COMPLETED = "completed"


# =============================================================================
# EXIT SESSION STATE
# =============================================================================

class ExitSessionState:
    """
    State container for a pursuit exit session.

    Tracks progress through the four phases.
    """

    def __init__(
        self,
        pursuit_id: str,
        user_id: str,
    ):
        self.session_id = str(uuid.uuid4())
        self.pursuit_id = pursuit_id
        self.user_id = user_id
        self.current_phase = ExitPhase.RETROSPECTIVE
        self.phase_history: List[Dict] = []
        self.retrospective_id: Optional[str] = None
        self.itd_id: Optional[str] = None
        self.package_id: Optional[str] = None
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None

    def advance_phase(self) -> bool:
        """
        Advance to the next phase.

        Returns:
            True if advanced, False if already at final phase
        """
        phase_order = [
            ExitPhase.RETROSPECTIVE,
            ExitPhase.ITD_PREVIEW,
            ExitPhase.ARTIFACT_PACKAGING,
            ExitPhase.TRANSITION_GUIDANCE,
            ExitPhase.COMPLETED,
        ]

        current_idx = phase_order.index(self.current_phase)
        if current_idx >= len(phase_order) - 1:
            return False

        # Record history
        self.phase_history.append({
            "phase": self.current_phase.value,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        # Advance
        self.current_phase = phase_order[current_idx + 1]

        if self.current_phase == ExitPhase.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)

        return True

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/API response."""
        return {
            "session_id": self.session_id,
            "pursuit_id": self.pursuit_id,
            "user_id": self.user_id,
            "current_phase": self.current_phase.value,
            "phase_history": self.phase_history,
            "retrospective_id": self.retrospective_id,
            "itd_id": self.itd_id,
            "package_id": self.package_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# =============================================================================
# PURSUIT EXIT ORCHESTRATOR
# =============================================================================

class PursuitExitOrchestrator:
    """
    Orchestrates the Four-Phase Pursuit Exit Experience.

    Coordinates retrospective, ITD generation, artifact packaging,
    and transition guidance into a cohesive exit flow.
    """

    def __init__(
        self,
        db,
        itd_engine=None,
        retrospective_orchestrator=None,
        export_engine=None,
        telemetry_fn: Callable = None,
    ):
        """
        Initialize PursuitExitOrchestrator.

        Args:
            db: Database instance
            itd_engine: ITDCompositionEngine instance
            retrospective_orchestrator: RetrospectiveOrchestrator instance
            export_engine: ArtifactExportEngine instance (optional)
            telemetry_fn: Telemetry tracking function (optional)
        """
        self.db = db
        self.itd_engine = itd_engine
        self.retrospective_orchestrator = retrospective_orchestrator
        self.export_engine = export_engine
        self.telemetry_fn = telemetry_fn or (lambda *args, **kwargs: None)

        # Active sessions (could be moved to Redis for distributed)
        self._sessions: Dict[str, ExitSessionState] = {}

    def start_exit(self, pursuit_id: str, user_id: str) -> ExitSessionState:
        """
        Start a new exit session for a pursuit.

        Args:
            pursuit_id: The pursuit entering exit
            user_id: The user owning the pursuit

        Returns:
            ExitSessionState for tracking progress
        """
        logger.info(f"[ExitOrchestrator] Starting exit session for pursuit: {pursuit_id}")

        # Create new session
        session = ExitSessionState(pursuit_id, user_id)
        self._sessions[session.session_id] = session

        # Store in database
        self._save_session(session)

        # Track telemetry
        self.telemetry_fn("itd.exit_started", pursuit_id, {
            "session_id": session.session_id,
        })

        return session

    def get_session(self, session_id: str) -> Optional[ExitSessionState]:
        """Get an exit session by ID."""
        return self._sessions.get(session_id) or self._load_session(session_id)

    def get_session_for_pursuit(self, pursuit_id: str) -> Optional[ExitSessionState]:
        """Get active exit session for a pursuit."""
        # Check in-memory first
        for session in self._sessions.values():
            if session.pursuit_id == pursuit_id and session.current_phase != ExitPhase.COMPLETED:
                return session

        # Check database
        return self._load_session_for_pursuit(pursuit_id)

    def process_phase(
        self,
        session_id: str,
        phase_data: Dict = None,
    ) -> Dict:
        """
        Process the current phase and optionally advance.

        Args:
            session_id: Exit session ID
            phase_data: Optional data for phase processing

        Returns:
            Phase result with next steps
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        phase = session.current_phase
        logger.info(f"[ExitOrchestrator] Processing phase {phase.value} for session {session_id}")

        # Handle each phase
        if phase == ExitPhase.RETROSPECTIVE:
            return self._process_retrospective(session, phase_data)
        elif phase == ExitPhase.ITD_PREVIEW:
            return self._process_itd_preview(session, phase_data)
        elif phase == ExitPhase.ARTIFACT_PACKAGING:
            return self._process_packaging(session, phase_data)
        elif phase == ExitPhase.TRANSITION_GUIDANCE:
            return self._process_transition(session, phase_data)
        else:
            return {"status": "completed", "session": session.to_dict()}

    def _process_retrospective(
        self,
        session: ExitSessionState,
        data: Dict = None,
    ) -> Dict:
        """
        Process the retrospective phase.

        If retrospective_id is provided, validate and advance.
        Otherwise, return instructions to complete retrospective.
        """
        if data and data.get("retrospective_id"):
            # Retrospective completed
            session.retrospective_id = data["retrospective_id"]
            session.advance_phase()
            self._save_session(session)

            self.telemetry_fn("itd.phase_completed", session.pursuit_id, {
                "phase": "retrospective",
                "session_id": session.session_id,
            })

            return {
                "status": "phase_completed",
                "completed_phase": "retrospective",
                "next_phase": session.current_phase.value,
                "session": session.to_dict(),
            }

        return {
            "status": "in_progress",
            "current_phase": "retrospective",
            "instructions": "Complete the guided retrospective conversation to proceed.",
            "session": session.to_dict(),
        }

    def _process_itd_preview(
        self,
        session: ExitSessionState,
        data: Dict = None,
    ) -> Dict:
        """
        Process the ITD preview phase.

        Generates ITD if not done, otherwise returns preview.
        """
        # Check if ITD already generated
        if session.itd_id:
            itd = self.itd_engine.get_itd(session.pursuit_id) if self.itd_engine else None

            if data and data.get("approved"):
                # ITD approved, advance
                session.advance_phase()
                self._save_session(session)

                self.telemetry_fn("itd.phase_completed", session.pursuit_id, {
                    "phase": "itd_preview",
                    "session_id": session.session_id,
                })

                return {
                    "status": "phase_completed",
                    "completed_phase": "itd_preview",
                    "next_phase": session.current_phase.value,
                    "session": session.to_dict(),
                }

            return {
                "status": "preview_ready",
                "current_phase": "itd_preview",
                "itd_id": session.itd_id,
                "itd_summary": self._get_itd_summary(itd) if itd else None,
                "instructions": "Review your Innovation Thesis Document and approve to proceed.",
                "session": session.to_dict(),
            }

        # Generate ITD
        if not self.itd_engine:
            logger.warning("[ExitOrchestrator] No ITD engine configured")
            # Skip ITD phase
            session.advance_phase()
            self._save_session(session)
            return {
                "status": "phase_skipped",
                "reason": "ITD engine not available",
                "next_phase": session.current_phase.value,
                "session": session.to_dict(),
            }

        # Get retrospective data
        retro_data = self._get_retrospective_data(session.retrospective_id)

        # Generate ITD
        itd = self.itd_engine.generate(
            pursuit_id=session.pursuit_id,
            retrospective_data=retro_data,
        )

        session.itd_id = itd.itd_id
        self._save_session(session)

        return {
            "status": "itd_generated",
            "current_phase": "itd_preview",
            "itd_id": itd.itd_id,
            "itd_status": itd.status.value,
            "layers_completed": itd.layers_completed,
            "instructions": "Your Innovation Thesis Document has been generated. Review and approve.",
            "session": session.to_dict(),
        }

    def _process_packaging(
        self,
        session: ExitSessionState,
        data: Dict = None,
    ) -> Dict:
        """
        Process the artifact packaging phase.

        v4.9: Now includes coach-assisted export discovery, offering
        intelligent export suggestions based on ITD and outcome readiness.
        """
        if data and data.get("package_id"):
            # Package already created, advance
            session.package_id = data["package_id"]
            session.advance_phase()
            self._save_session(session)

            self.telemetry_fn("itd.phase_completed", session.pursuit_id, {
                "phase": "artifact_packaging",
                "session_id": session.session_id,
            })

            return {
                "status": "phase_completed",
                "completed_phase": "artifact_packaging",
                "next_phase": session.current_phase.value,
                "session": session.to_dict(),
            }

        # v4.9: Get export discovery suggestions
        export_discovery = self._get_export_discovery(session.pursuit_id)

        # Generate package
        package_id = str(uuid.uuid4())
        package_info = {
            "package_id": package_id,
            "pursuit_id": session.pursuit_id,
            "itd_id": session.itd_id,
            "contents": [
                "innovation_thesis_document",
                "vision_artifact",
                "concerns_artifact",
                "hypothesis_artifacts",
                "retrospective_artifact",
            ],
            "export_suggestions": export_discovery.get("suggestions", [])[:3],  # Top 3
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store package metadata
        if self.db:
            self.db.db.pursuit_packages.insert_one(package_info)

        session.package_id = package_id
        session.advance_phase()
        self._save_session(session)

        return {
            "status": "package_created",
            "completed_phase": "artifact_packaging",
            "package_id": package_id,
            "next_phase": session.current_phase.value,
            "export_discovery": export_discovery,  # v4.9: Include export suggestions
            "session": session.to_dict(),
        }

    def _get_export_discovery(self, pursuit_id: str) -> Dict:
        """
        Get export discovery suggestions for Phase 3.

        v4.9: Uses ExportCoachBridge to provide intelligent export
        recommendations based on ITD and outcome readiness.
        """
        try:
            from modules.export_engine import get_export_discovery_for_phase3

            return get_export_discovery_for_phase3(
                pursuit_id=pursuit_id,
                db=self.db,
                template_registry=getattr(self, 'template_registry', None),
                style_engine=getattr(self, 'style_engine', None),
            )
        except Exception as e:
            logger.warning(f"[ExitOrchestrator] Export discovery failed: {e}")
            return {
                "pursuit_id": pursuit_id,
                "suggestions": [],
                "coach_introduction": "Export options are being prepared.",
                "coach_closing": "Check back soon for export recommendations.",
            }

    def _process_transition(
        self,
        session: ExitSessionState,
        data: Dict = None,
    ) -> Dict:
        """
        Process the transition guidance phase.

        Provides next steps and closes the exit flow.
        """
        if data and data.get("acknowledged"):
            # Transition acknowledged, complete
            session.advance_phase()
            self._save_session(session)

            self.telemetry_fn("itd.exit_completed", session.pursuit_id, {
                "session_id": session.session_id,
            })

            return {
                "status": "exit_completed",
                "completed_phase": "transition_guidance",
                "session": session.to_dict(),
            }

        # Generate transition guidance
        guidance = self._generate_transition_guidance(session)

        return {
            "status": "guidance_ready",
            "current_phase": "transition_guidance",
            "guidance": guidance,
            "instructions": "Review your next steps and acknowledge to complete the exit.",
            "session": session.to_dict(),
        }

    def _get_itd_summary(self, itd) -> Dict:
        """Get a summary of ITD for preview."""
        if not itd:
            return {}

        return {
            "thesis_preview": itd.thesis_statement.thesis_text[:200] + "..." if itd.thesis_statement else "",
            "narrative_acts": len(itd.narrative_arc.acts) if itd.narrative_arc else 0,
            "coaching_moments": len(itd.coachs_perspective.moments) if itd.coachs_perspective else 0,
            "quality_score": None,  # Could calculate with assembler
        }

    def _get_retrospective_data(self, retrospective_id: str) -> Dict:
        """Get retrospective data for ITD generation."""
        if not self.db or not retrospective_id:
            return {}

        try:
            retro = self.db.db.retrospectives.find_one({
                "retrospective_id": retrospective_id
            })
            if retro:
                artifact = retro.get("artifact", {})
                return {
                    "key_learnings": artifact.get("key_learnings", []),
                    "outcome_reflection": artifact.get("outcome_reflection", ""),
                    "surprise_factors": artifact.get("surprise_factors", []),
                    "future_recommendations": artifact.get("future_recommendations", []),
                }
        except Exception as e:
            logger.error(f"[ExitOrchestrator] Error fetching retrospective: {e}")

        return {}

    def _generate_transition_guidance(self, session: ExitSessionState) -> Dict:
        """Generate transition guidance for the innovator."""
        return {
            "next_steps": [
                "Share your Innovation Thesis Document with stakeholders",
                "Consider contributing patterns to the Innovation Knowledge Federation",
                "Apply learnings to future innovation pursuits",
            ],
            "resources": [
                {"title": "Export Your Artifacts", "action": "export"},
                {"title": "Start New Pursuit", "action": "new_pursuit"},
                {"title": "View Learning Library", "action": "learning_library"},
            ],
            "closing_message": (
                "Congratulations on completing your innovation journey! "
                "Your learnings and insights have been captured for future reference."
            ),
        }

    def _save_session(self, session: ExitSessionState):
        """Save session to database."""
        if not self.db:
            return

        try:
            self.db.db.exit_sessions.replace_one(
                {"session_id": session.session_id},
                session.to_dict(),
                upsert=True
            )
        except Exception as e:
            logger.error(f"[ExitOrchestrator] Error saving session: {e}")

    def _load_session(self, session_id: str) -> Optional[ExitSessionState]:
        """Load session from database."""
        if not self.db:
            return None

        try:
            doc = self.db.db.exit_sessions.find_one({"session_id": session_id})
            if doc:
                session = ExitSessionState(doc["pursuit_id"], doc["user_id"])
                session.session_id = doc["session_id"]
                session.current_phase = ExitPhase(doc["current_phase"])
                session.phase_history = doc.get("phase_history", [])
                session.retrospective_id = doc.get("retrospective_id")
                session.itd_id = doc.get("itd_id")
                session.package_id = doc.get("package_id")
                self._sessions[session_id] = session
                return session
        except Exception as e:
            logger.error(f"[ExitOrchestrator] Error loading session: {e}")

        return None

    def _load_session_for_pursuit(self, pursuit_id: str) -> Optional[ExitSessionState]:
        """Load active session for a pursuit."""
        if not self.db:
            return None

        try:
            doc = self.db.db.exit_sessions.find_one({
                "pursuit_id": pursuit_id,
                "current_phase": {"$ne": "completed"}
            })
            if doc:
                return self._load_session(doc["session_id"])
        except Exception as e:
            logger.error(f"[ExitOrchestrator] Error loading session for pursuit: {e}")

        return None
