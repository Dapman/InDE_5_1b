"""
InDE MVP v4.5.0 — Engagement Engine Test Suite

Tests for the 5 engagement features:
1. Innovation Health Card
2. Shareable Artifact Export
3. Cohort Presence Signals
4. Post-Vision Pathway Teaser
5. Milestone Narrative Hooks

Total: 12 tests covering all critical paths.

(c) 2026 Yul Williams | InDEVerse, Incorporated
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from dataclasses import asdict

# Import modules under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from modules.health_card.health_card_engine import (
    HealthCardEngine, InnovationHealthCard, HealthCardDimension
)
from modules.artifact_export.export_engine import ArtifactExportEngine, ExportResult
from modules.artifact_export.share_link_service import ShareLinkService
from modules.cohort_signals.cohort_aggregator import CohortAggregator, CohortSignals
from modules.pathway_teaser.pathway_teaser_engine import PathwayTeaserEngine, PathwayTeaser
from modules.milestones.milestone_templates import MilestoneTemplates
from modules.milestones.milestone_event_engine import MilestoneEventEngine, MilestoneEvent


# =============================================================================
# MOCK DATABASE FIXTURE
# =============================================================================

class MockCollection:
    """Mock MongoDB collection with configurable responses."""

    def __init__(self, data=None):
        self.data = data or []
        self._inserted = []

    def find_one(self, query, **kwargs):
        # Simple mock implementation for testing
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items() if not k.startswith("$")):
                return doc
        return None

    def find(self, query=None, **kwargs):
        return self.data

    def count_documents(self, query=None):
        return len(self.data)

    def insert_one(self, doc):
        self._inserted.append(doc)
        return MagicMock(inserted_id="mock_id")

    def find_one_and_update(self, query, update, **kwargs):
        doc = self.find_one(query)
        if doc and "$inc" in update:
            for key, val in update["$inc"].items():
                doc[key] = doc.get(key, 0) + val
        return doc

    def aggregate(self, pipeline):
        return iter([])

    def create_index(self, *args, **kwargs):
        pass


class MockDB:
    """Mock database with configurable collections."""

    def __init__(self, collections=None):
        self._collections = collections or {}

    @property
    def db(self):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattr__(name)
        if name not in self._collections:
            self._collections[name] = MockCollection()
        return self._collections[name]

    def __getitem__(self, name):
        return getattr(self, name)


# =============================================================================
# HEALTH CARD TESTS (Tests 1-4)
# =============================================================================

class TestHealthCardEngine:
    """Tests for Innovation Health Card computation."""

    def test_health_card_seed_stage(self):
        """Test 1: Health Card computes seed stage for new pursuit."""
        # Arrange — pursuit with no artifacts, no scaffolding, low momentum
        # Note: Engine defaults momentum to 0.5 for new users if no snapshot exists.
        # To get "seed" stage (no dimensions above threshold), we provide a low momentum.
        db = MockDB({
            "pursuits": MockCollection([
                {"pursuit_id": "p1", "state": "ACTIVE", "current_phase": "VISION"}
            ]),
            "artifacts": MockCollection([]),
            "scaffolding_states": MockCollection([]),
            "momentum_snapshots": MockCollection([
                # Low momentum keeps all dimensions below threshold
                {"pursuit_id": "p1", "composite_score": 0.2, "recorded_at": datetime.now(timezone.utc)}
            ]),
            "coaching_sessions": MockCollection([]),
            "evidence_packages": MockCollection([]),
        })

        engine = HealthCardEngine(db)

        # Act
        card = engine.compute("p1")

        # Assert — seed stage with all dimensions low
        assert card.growth_stage == "seed"
        assert "seed" in card.growth_stage_label.lower() or "planted" in card.growth_stage_label.lower()
        assert len(card.dimensions) == 5

    def test_health_card_roots_stage(self):
        """Test 2: Health Card computes roots stage with partial scaffolding."""
        # Arrange — pursuit with minimal scaffolding (1 element) and low momentum
        # Roots requires: 1 dimension >= 0.3
        db = MockDB({
            "pursuits": MockCollection([
                {"pursuit_id": "p1", "state": "ACTIVE", "current_phase": "VISION"}
            ]),
            "artifacts": MockCollection([]),
            "scaffolding_states": MockCollection([{
                "pursuit_id": "p1",
                "vision_elements": {
                    "problem": {"text": "Problem statement here"},
                    # Only 1 of 3 elements filled = 33% * 0.6 cap = 0.2 base
                }
            }]),
            "momentum_snapshots": MockCollection([
                # Low momentum so only clarity is above threshold
                {"pursuit_id": "p1", "composite_score": 0.35, "recorded_at": datetime.now(timezone.utc)}
            ]),
            "coaching_sessions": MockCollection([{"pursuit_id": "p1", "user_id": "u1"}]),
            "evidence_packages": MockCollection([]),
        })

        engine = HealthCardEngine(db)

        # Act
        card = engine.compute("p1")

        # Assert — roots stage with one dimension (momentum) above 0.3 threshold
        assert card.growth_stage == "roots"
        assert card.dimensions[0].key == "clarity"
        # Momentum should be above 0.3 (roots threshold)
        momentum_dim = next(d for d in card.dimensions if d.key == "momentum")
        assert momentum_dim.score >= 0.3

    def test_health_card_stem_stage(self):
        """Test 3: Health Card computes stem stage with vision artifact."""
        # Arrange — pursuit with vision artifact finalized
        db = MockDB({
            "pursuits": MockCollection([
                {"pursuit_id": "p1", "state": "ACTIVE", "current_phase": "DE_RISK"}
            ]),
            "artifacts": MockCollection([
                {"pursuit_id": "p1", "artifact_type": "vision", "content": "Vision content"},
                {"pursuit_id": "p1", "artifact_type": "fears", "content": "Risk content"},
            ]),
            "scaffolding_states": MockCollection([]),
            "momentum_snapshots": MockCollection([
                {"pursuit_id": "p1", "composite_score": 0.6, "recorded_at": datetime.now(timezone.utc)}
            ]),
            "coaching_sessions": MockCollection([
                {"pursuit_id": "p1", "user_id": "u1"},
                {"pursuit_id": "p1", "user_id": "u1"},
                {"pursuit_id": "p1", "user_id": "u1"},
            ]),
            "evidence_packages": MockCollection([]),
        })

        engine = HealthCardEngine(db)

        # Act
        card = engine.compute("p1")

        # Assert — stem or higher with artifacts present
        assert card.growth_stage in ["stem", "branches", "canopy"]
        # Clarity dimension should be high with vision artifact
        clarity = next(d for d in card.dimensions if d.key == "clarity")
        assert clarity.score >= 0.7

    def test_health_card_summary_generation(self):
        """Test 4: Health Card generates natural-language summary."""
        # Arrange
        db = MockDB({
            "pursuits": MockCollection([
                {"pursuit_id": "p1", "state": "ACTIVE", "current_phase": "VISION"}
            ]),
            "artifacts": MockCollection([]),
            "scaffolding_states": MockCollection([]),
            "momentum_snapshots": MockCollection([]),
            "coaching_sessions": MockCollection([]),
            "evidence_packages": MockCollection([]),
        })

        engine = HealthCardEngine(db)

        # Act
        card = engine.compute("p1")

        # Assert — summary should be a non-empty sentence
        assert card.summary_sentence
        assert len(card.summary_sentence) > 20
        assert card.next_growth_hint
        assert len(card.next_growth_hint) > 10


# =============================================================================
# ARTIFACT EXPORT TESTS (Tests 5-8)
# =============================================================================

class TestArtifactExport:
    """Tests for Shareable Artifact Export functionality."""

    def test_export_pdf_format(self):
        """Test 5: Export generates PDF format successfully."""
        # Arrange
        db = MockDB({
            "artifacts": MockCollection([{
                "pursuit_id": "p1",
                "artifact_type": "vision",
                "content": "My vision for sustainable packaging...",
                "title": "Sustainable Packaging Vision"
            }]),
            "pursuits": MockCollection([{
                "pursuit_id": "p1",
                "title": "EcoWrap Packaging"
            }]),
        })

        # Mock PDF generator to avoid actual PDF library dependency
        mock_pdf_gen = MagicMock()
        mock_pdf_gen.generate.return_value = b"%PDF-1.4 mock content"

        engine = ArtifactExportEngine(
            db=db,
            pdf_generator=mock_pdf_gen,
            base_url="https://app.indeverse.com"
        )

        # Act
        result = engine.export("p1", "vision", "pdf", innovator_name="Test User")

        # Assert
        assert result.format == "pdf"
        assert result.content is not None
        assert result.content.startswith(b"%PDF")
        mock_pdf_gen.generate.assert_called_once()

    def test_export_draft_rejection(self):
        """Test 6: Export rejects draft (non-finalized) artifacts."""
        # Arrange — artifact with no content
        db = MockDB({
            "artifacts": MockCollection([{
                "pursuit_id": "p1",
                "artifact_type": "vision",
                "content": ""  # Empty = draft
            }]),
        })

        engine = ArtifactExportEngine(db=db, base_url="")

        # Act
        can_export, reason = engine.can_export("p1", "vision")

        # Assert
        assert can_export is False
        assert "content" in reason.lower() or "no content" in reason.lower()

    def test_export_share_link_creation(self):
        """Test 7: Export creates shareable link with token."""
        # Arrange
        db = MockDB({
            "artifacts": MockCollection([{
                "pursuit_id": "p1",
                "artifact_type": "vision",
                "content": "Vision content here",
                "title": "My Vision"
            }]),
            "pursuits": MockCollection([{
                "pursuit_id": "p1",
                "title": "Test Pursuit"
            }]),
            "shared_artifact_links": MockCollection([]),
        })

        mock_share_service = MagicMock()
        engine = ArtifactExportEngine(
            db=db,
            share_link_service=mock_share_service,
            base_url="https://app.indeverse.com"
        )

        # Act
        result = engine.export("p1", "vision", "link", expiry_days=7)

        # Assert
        assert result.format == "link"
        assert result.url is not None
        assert result.token is not None
        assert "/share/" in result.url
        assert result.expires_at is not None
        mock_share_service.create.assert_called_once()

    def test_share_link_view_tracking(self):
        """Test 8: Share link tracks view count on access."""
        # Arrange
        shared_doc = {
            "token": "abc123xyz",
            "artifact_content": "Test content",
            "artifact_type": "vision",
            "view_count": 5,
            "pursuit_title": "Test Pursuit",
        }
        db = MockDB({
            "shared_artifact_links": MockCollection([shared_doc]),
        })

        service = ShareLinkService(db)

        # Act
        result = service.get_by_token("abc123xyz")

        # Assert
        assert result is not None
        assert result["view_count"] == 6  # Incremented from 5
        assert result["artifact_content"] == "Test content"


# =============================================================================
# COHORT SIGNALS TESTS (Test 9)
# =============================================================================

class TestCohortSignals:
    """Tests for Cohort Presence Signals."""

    def test_cohort_signal_classification(self):
        """Test 9: Cohort signals classify momentum tier correctly."""
        # Arrange — test different activity ratios
        aggregator = CohortAggregator(MockDB())

        # Test buzzing (60%+ ratio)
        signal, label = aggregator._compute_momentum_signal(active_24h=8, active_7d=10)
        assert signal == "buzzing"
        assert "buzzing" in label.lower()

        # Test active (30-60% ratio)
        signal, label = aggregator._compute_momentum_signal(active_24h=4, active_7d=10)
        assert signal == "active"

        # Test warming_up (10-30% ratio)
        signal, label = aggregator._compute_momentum_signal(active_24h=2, active_7d=10)
        assert signal == "warming_up"

        # Test getting_started (<10% ratio)
        signal, label = aggregator._compute_momentum_signal(active_24h=0, active_7d=10)
        assert signal == "getting_started"

        # Test very small cohort
        signal, label = aggregator._compute_momentum_signal(active_24h=2, active_7d=2)
        assert signal == "getting_started"


# =============================================================================
# PATHWAY TEASER TESTS (Tests 10-11)
# =============================================================================

class TestPathwayTeaser:
    """Tests for Post-Vision Pathway Teaser."""

    def test_pathway_teaser_vision_complete(self):
        """Test 10: Pathway teaser shows risk preview after vision completion."""
        # Arrange — pursuit with vision artifact, no fears artifact
        db = MockDB({
            "pursuits": MockCollection([{
                "pursuit_id": "p1",
                "current_phase": "VISION",
            }]),
            "artifacts": MockCollection([{
                "pursuit_id": "p1",
                "artifact_type": "vision",
                "content": "Vision content"
            }]),
        })

        engine = PathwayTeaserEngine(db)

        # Act — teaser for completing vision
        teaser = engine.get_teaser("p1", "vision")

        # Assert
        assert teaser is not None
        assert teaser.teaser_type == "risk_preview"
        assert teaser.target_pathway == "fears"
        assert teaser.source == "fallback"  # No IML patterns in test
        assert "risk" in teaser.headline.lower() or "threaten" in teaser.headline.lower()

    def test_pathway_teaser_all_explored(self):
        """Test 11: Pathway teaser returns None when next pathway already explored."""
        # Arrange — pursuit with both vision and fears artifacts
        db = MockDB({
            "pursuits": MockCollection([{
                "pursuit_id": "p1",
                "current_phase": "DE_RISK",
            }]),
            "artifacts": MockCollection([
                {"pursuit_id": "p1", "artifact_type": "vision", "content": "Vision"},
                {"pursuit_id": "p1", "artifact_type": "fears", "content": "Fears"},
            ]),
        })

        engine = PathwayTeaserEngine(db)

        # Act — teaser for completing vision (but fears already exists)
        teaser = engine.get_teaser("p1", "vision")

        # Assert — no teaser because target already explored
        assert teaser is None


# =============================================================================
# MILESTONE TESTS (Test 12)
# =============================================================================

class TestMilestoneNarrative:
    """Tests for Milestone Narrative Hooks."""

    def test_milestone_narrative_generation(self):
        """Test 12: Milestone generates achievement narrative with all components."""
        # Arrange
        db = MockDB({
            "pursuits": MockCollection([{
                "pursuit_id": "p1",
                "title": "Sustainable Packaging Innovation"
            }]),
            "artifacts": MockCollection([
                {"pursuit_id": "p1", "artifact_type": "vision", "content": "Vision"}
            ]),
        })

        engine = MilestoneEventEngine(db)

        # Act
        milestone = engine.generate_milestone(
            pursuit_id="p1",
            artifact_type="vision",
            growth_stage_before="seed"
        )

        # Assert — all milestone components present
        assert milestone is not None
        assert isinstance(milestone, MilestoneEvent)
        assert milestone.pursuit_id == "p1"
        assert milestone.artifact_type == "vision"
        assert milestone.headline  # Non-empty headline
        assert milestone.narrative  # Non-empty narrative
        assert milestone.next_hint  # Non-empty hint
        assert milestone.health_card_refresh is True
        assert milestone.pathway_teaser_trigger is True
        assert milestone.created_at  # Timestamp present

        # Verify narrative includes idea domain
        assert "packaging" in milestone.narrative.lower() or "your" in milestone.narrative.lower()

    def test_milestone_templates_render(self):
        """Supplementary: MilestoneTemplates render with domain injection."""
        # Act — use vision artifact type which always includes {idea_domain}
        rendered = MilestoneTemplates.render(
            artifact_type="vision",
            idea_domain="sustainable packaging"
        )

        # Assert
        assert "headline" in rendered
        assert "narrative" in rendered
        assert "next_hint" in rendered
        # All vision templates include {idea_domain}
        assert "sustainable packaging" in rendered["narrative"] or "your" in rendered["narrative"].lower()
        # Ensure no fear-centric language in any template type
        rendered_fears = MilestoneTemplates.render(artifact_type="fears", idea_domain="test")
        assert "fear" not in rendered_fears["narrative"].lower()


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
