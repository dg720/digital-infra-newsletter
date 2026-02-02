"""State schemas - LangGraph state object and time window."""

from datetime import date, datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
import uuid

from ..constants import Vertical, DEFAULT_VOICE_PROFILE, DEFAULT_EVIDENCE_BUDGET, DEFAULT_MAX_REVIEW_ROUNDS


def generate_run_id() -> str:
    """Generate a unique run ID with timestamp."""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    return f"newsletter_{timestamp}_{uuid.uuid4().hex[:6]}"


class TimeWindow(BaseModel):
    """Time window for newsletter coverage."""
    
    start: date = Field(description="Start date of the time window")
    end: date = Field(description="End date of the time window")
    
    def days(self) -> int:
        """Return the number of days in the window."""
        return (self.end - self.start).days


class ParsedInput(BaseModel):
    """Structured fields parsed from natural language input."""
    
    time_window: TimeWindow = Field(description="Parsed time window")
    verticals: List[Vertical] = Field(
        default_factory=lambda: list(Vertical),
        description="Which verticals to include"
    )
    voice_profile: str = Field(
        default=DEFAULT_VOICE_PROFILE,
        description="Desired voice/tone for the newsletter"
    )
    region_focus: Optional[str] = Field(
        default=None,
        description="Optional region filter (e.g., 'UK', 'EU', 'US')"
    )
    style_prompt: Optional[str] = Field(
        default=None,
        description="Freeform tone/style override"
    )


class NewsletterArtifacts(BaseModel):
    """Container for all artifacts produced during newsletter generation."""
    
    evidence_packs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence packs per section"
    )
    drafts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Section drafts"
    )
    reviews: Dict[str, List[Any]] = Field(
        default_factory=dict,
        description="Review rounds per section"
    )
    final_sections: Dict[str, Any] = Field(
        default_factory=dict,
        description="Final approved sections"
    )


class NewsletterState(BaseModel):
    """Main state object for the LangGraph workflow."""
    
    # Run identification
    run_id: str = Field(default_factory=generate_run_id)
    mode: Literal["generate_issue", "update_section"] = Field(
        default="generate_issue",
        description="Workflow mode"
    )
    
    # Parsed input fields
    time_window: TimeWindow
    verticals: List[Vertical] = Field(default_factory=lambda: list(Vertical))
    voice_profile: str = Field(default=DEFAULT_VOICE_PROFILE)
    region_focus: Optional[str] = Field(default=None)
    style_prompt: Optional[str] = Field(default=None)
    
    # Configuration
    comps: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Major players per vertical"
    )
    evidence_budgets: Dict[str, int] = Field(
        default_factory=dict,
        description="Tool call budget per vertical"
    )
    max_review_rounds: int = Field(default=DEFAULT_MAX_REVIEW_ROUNDS)
    
    # Workflow state
    current_review_round: int = Field(default=0)
    sections_to_fix: List[str] = Field(default_factory=list)
    
    # Artifacts
    artifacts: NewsletterArtifacts = Field(default_factory=NewsletterArtifacts)
    
    # Metadata
    original_prompt: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_versions: Dict[str, str] = Field(default_factory=dict)
    
    # For update_section mode
    target_section_id: Optional[str] = Field(default=None)
    update_instruction: Optional[str] = Field(default=None)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
