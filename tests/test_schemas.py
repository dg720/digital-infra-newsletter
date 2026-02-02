"""Tests for Pydantic schemas."""

import pytest
from datetime import date, datetime

from src.schemas.evidence import EvidenceItem, EvidencePack, generate_evidence_id
from src.schemas.state import TimeWindow, NewsletterState, ParsedInput
from src.schemas.sections import SectionDraft, Bullet, ReviewScore, FixPlan, FixAction
from src.constants import Vertical


class TestEvidenceItem:
    """Tests for EvidenceItem schema."""
    
    def test_create_evidence_item(self):
        """Test creating a basic evidence item."""
        item = EvidenceItem(
            source_type="web",
            source_name="tavily",
            url="https://example.com/article",
            title="Test Article",
            text="This is test content.",
        )
        
        assert item.source_type == "web"
        assert item.source_name == "tavily"
        assert item.evidence_id.startswith("ev_")
        assert item.reliability == "medium"  # Default
        assert isinstance(item.retrieved_at, datetime)
    
    def test_evidence_id_generation(self):
        """Test that evidence IDs are unique."""
        id1 = generate_evidence_id()
        id2 = generate_evidence_id()
        
        assert id1 != id2
        assert id1.startswith("ev_")
        assert len(id1) == 11  # ev_ + 8 hex chars


class TestEvidencePack:
    """Tests for EvidencePack schema."""
    
    def test_create_evidence_pack(self):
        """Test creating an evidence pack."""
        pack = EvidencePack(section_id="data_centers")
        
        assert pack.section_id == "data_centers"
        assert len(pack.items) == 0
    
    def test_add_item(self):
        """Test adding items to evidence pack."""
        pack = EvidencePack(section_id="data_centers")
        item = EvidenceItem(
            source_type="web",
            source_name="tavily",
            title="Test",
        )
        
        pack.add_item(item)
        
        assert len(pack.items) == 1
        assert pack.items[0].title == "Test"
    
    def test_get_item_by_id(self):
        """Test retrieving item by ID."""
        pack = EvidencePack(section_id="data_centers")
        item = EvidenceItem(
            source_type="web",
            source_name="tavily",
            title="Test",
        )
        pack.add_item(item)
        
        retrieved = pack.get_item_by_id(item.evidence_id)
        
        assert retrieved is not None
        assert retrieved.title == "Test"
    
    def test_get_evidence_ids(self):
        """Test getting all evidence IDs."""
        pack = EvidencePack(section_id="data_centers")
        item1 = EvidenceItem(source_type="web", source_name="tavily")
        item2 = EvidenceItem(source_type="news", source_name="newspaper3k")
        pack.add_item(item1)
        pack.add_item(item2)
        
        ids = pack.get_evidence_ids()
        
        assert len(ids) == 2
        assert item1.evidence_id in ids
        assert item2.evidence_id in ids


class TestTimeWindow:
    """Tests for TimeWindow schema."""
    
    def test_create_time_window(self):
        """Test creating a time window."""
        tw = TimeWindow(
            start=date(2026, 1, 26),
            end=date(2026, 2, 2),
        )
        
        assert tw.start == date(2026, 1, 26)
        assert tw.end == date(2026, 2, 2)
    
    def test_days_calculation(self):
        """Test days calculation."""
        tw = TimeWindow(
            start=date(2026, 1, 26),
            end=date(2026, 2, 2),
        )
        
        assert tw.days() == 7


class TestSectionDraft:
    """Tests for SectionDraft schema."""
    
    def test_create_section_draft(self):
        """Test creating a section draft."""
        draft = SectionDraft(
            section_id="data_centers",
            big_picture="This is the big picture paragraph about data centers.",
            big_picture_evidence_ids=["ev_001", "ev_002"],
            bullets=[
                Bullet(text="Equinix expands", evidence_ids=["ev_001"], player_referenced="Equinix"),
            ],
        )
        
        assert draft.section_id == "data_centers"
        assert len(draft.bullets) == 1
    
    def test_to_markdown(self):
        """Test markdown generation."""
        draft = SectionDraft(
            section_id="data_centers",
            big_picture="Big picture text.",
            big_picture_evidence_ids=["ev_001"],
            bullets=[
                Bullet(text="Bullet one", evidence_ids=["ev_002"]),
            ],
        )
        
        md = draft.to_markdown()
        
        assert "Big picture text." in md
        assert "[evidence: ev_001]" in md
        assert "- Bullet one [evidence: ev_002]" in md


class TestReviewScore:
    """Tests for ReviewScore schema."""
    
    def test_passes_threshold(self):
        """Test threshold checking."""
        passing = ReviewScore(
            grounding=4,
            clarity=4,
            newsworthiness=3,
            balance=3,
            voice_fit=4,
        )
        
        failing = ReviewScore(
            grounding=3,
            clarity=4,
            newsworthiness=3,
            balance=3,
            voice_fit=4,
        )
        
        assert passing.passes_threshold() is True
        assert failing.passes_threshold() is False
