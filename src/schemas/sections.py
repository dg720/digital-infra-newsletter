"""Section schemas - drafts, reviews, and fix plans."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Bullet(BaseModel):
    """A single bullet point in a section."""
    
    text: str = Field(description="The bullet text content")
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Evidence IDs supporting this bullet"
    )
    player_referenced: Optional[str] = Field(
        default=None,
        description="Name of the major player referenced, if any"
    )


class SectionDraft(BaseModel):
    """Draft of a newsletter section."""
    
    section_id: str = Field(description="Section identifier (vertical name)")
    big_picture: str = Field(
        description="Big picture paragraph (~80-140 words)"
    )
    big_picture_evidence_ids: List[str] = Field(
        default_factory=list,
        description="Evidence IDs supporting the big picture paragraph"
    )
    bullets: List[Bullet] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5 one-line bullets"
    )
    risk_flags: List[str] = Field(
        default_factory=list,
        description="Uncertainties or missing context"
    )
    
    def to_markdown(self) -> str:
        """Convert section to markdown format."""
        # Format evidence citations for big picture
        bp_citations = ", ".join(self.big_picture_evidence_ids)
        
        lines = [
            self.big_picture + f" [evidence: {bp_citations}]",
            "",
            "**Major player updates**",
        ]
        
        for bullet in self.bullets:
            citations = ", ".join(bullet.evidence_ids)
            lines.append(f"- {bullet.text} [evidence: {citations}]")
        
        return "\n".join(lines)


class ReviewScore(BaseModel):
    """Review rubric scores (0-5 per criterion)."""
    
    grounding: int = Field(ge=0, le=5, description="How well claims are supported by evidence")
    clarity: int = Field(ge=0, le=5, description="Conciseness and comprehensibility")
    newsworthiness: int = Field(ge=0, le=5, description="Timeliness and importance")
    balance: int = Field(ge=0, le=5, description="Avoids hype, includes caveats")
    voice_fit: int = Field(ge=0, le=5, description="Matches requested voice/tone")
    
    def passes_threshold(self, grounding_min: int = 4, clarity_min: int = 4) -> bool:
        """Check if the review passes minimum thresholds."""
        return self.grounding >= grounding_min and self.clarity >= clarity_min


class FixAction(BaseModel):
    """A specific action to fix an issue."""
    
    action_type: Literal["fetch_source", "rewrite", "add_citation", "clarify", "adjust_tone"]
    description: str = Field(description="What needs to be done")
    target: Optional[str] = Field(
        default=None,
        description="Specific target (e.g., bullet index, paragraph)"
    )
    suggested_tool: Optional[str] = Field(
        default=None,
        description="Suggested tool to use (e.g., web_search, fetch_article)"
    )
    suggested_query: Optional[str] = Field(
        default=None,
        description="Suggested search query if applicable"
    )


class FixPlan(BaseModel):
    """Plan to fix issues identified in review."""
    
    section_id: str = Field(description="Target section to fix")
    target_agent: str = Field(description="Agent responsible for fixes")
    issues: List[str] = Field(description="List of identified issues")
    actions: List[FixAction] = Field(
        default_factory=list,
        description="Specific actions to take"
    )
    blocking: bool = Field(
        default=False,
        description="Whether these issues block acceptance"
    )


class ReviewResult(BaseModel):
    """Complete review result for a section."""
    
    section_id: str
    review_round: int
    scores: ReviewScore
    issues: List[str] = Field(default_factory=list)
    fix_plan: Optional[FixPlan] = Field(default=None)
    accepted: bool = Field(default=False)
    notes: Optional[str] = Field(default=None)
