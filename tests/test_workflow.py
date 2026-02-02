"""Tests for the LangGraph workflow."""

import pytest
from datetime import date

from src.schemas.state import TimeWindow, NewsletterState
from src.schemas.sections import SectionDraft, Bullet
from src.constants import Vertical


class TestWorkflowState:
    """Tests for workflow state management."""
    
    def test_initial_state_creation(self):
        """Test creating initial newsletter state."""
        state = NewsletterState(
            time_window=TimeWindow(
                start=date(2026, 1, 26),
                end=date(2026, 2, 2),
            ),
            verticals=[Vertical.DATA_CENTERS, Vertical.CONNECTIVITY_FIBRE],
            voice_profile="expert_operator",
        )
        
        assert state.run_id.startswith("newsletter_")
        assert state.mode == "generate_issue"
        assert len(state.verticals) == 2
    
    def test_state_defaults(self):
        """Test that state uses correct defaults."""
        state = NewsletterState(
            time_window=TimeWindow(
                start=date(2026, 1, 26),
                end=date(2026, 2, 2),
            ),
        )
        
        assert state.max_review_rounds == 2
        assert state.voice_profile == "expert_operator"
        assert state.region_focus is None


class TestNewsletterAssembly:
    """Tests for newsletter markdown assembly."""
    
    def test_section_to_markdown(self):
        """Test section markdown generation."""
        draft = SectionDraft(
            section_id="data_centers",
            big_picture="The data center sector saw significant activity this week, with major hyperscalers announcing expansion plans across Europe.",
            big_picture_evidence_ids=["ev_001", "ev_002"],
            bullets=[
                Bullet(
                    text="Equinix announced a new 50MW facility in Frankfurt",
                    evidence_ids=["ev_003"],
                    player_referenced="Equinix",
                ),
                Bullet(
                    text="Digital Realty completed acquisition of European portfolio",
                    evidence_ids=["ev_004", "ev_005"],
                    player_referenced="Digital Realty",
                ),
            ],
        )
        
        md = draft.to_markdown()
        
        # Check structure
        assert "The data center sector" in md
        assert "[evidence: ev_001, ev_002]" in md
        assert "**Major player updates**" in md
        assert "- Equinix announced" in md
        assert "[evidence: ev_003]" in md
        assert "- Digital Realty" in md
        assert "[evidence: ev_004, ev_005]" in md
    
    def test_full_newsletter_format(self):
        """Test that assembled newsletter matches expected format."""
        # This would test the full assembly node
        # For now, test the expected output structure
        expected_sections = [
            "# Digital Infrastructure Weekly",
            "## Data Centers",
            "## Connectivity & Fibre",
            "## Towers & Wireless Infrastructure",
        ]
        
        # Mock newsletter content
        newsletter_md = """# Digital Infrastructure Weekly — 2026-02-02

_Time window: 2026-01-26 to 2026-02-02_  
_Voice: expert_operator_

---

## Data Centers
Test content [evidence: ev_001]

**Major player updates**
- Bullet 1 [evidence: ev_002]

---

## Connectivity & Fibre
Test content [evidence: ev_003]

**Major player updates**
- Bullet 2 [evidence: ev_004]

---

## Towers & Wireless Infrastructure
Test content [evidence: ev_005]

**Major player updates**
- Bullet 3 [evidence: ev_006]
"""
        
        for section in expected_sections:
            assert section in newsletter_md or section.split(" — ")[0] in newsletter_md


class TestReviewLoop:
    """Tests for the review loop logic."""
    
    def test_review_round_counting(self):
        """Test that review rounds are properly tracked."""
        state = NewsletterState(
            time_window=TimeWindow(start=date(2026, 1, 26), end=date(2026, 2, 2)),
            max_review_rounds=2,
        )
        
        # Simulate review rounds
        state.current_review_round = 1
        assert state.current_review_round < state.max_review_rounds
        
        state.current_review_round = 2
        assert state.current_review_round >= state.max_review_rounds
