"""API schemas - request and response models for FastAPI endpoints."""

from typing import Optional, Dict
from pydantic import BaseModel, Field

from .state import TimeWindow


class GenerateRequest(BaseModel):
    """Request body for POST /newsletter/generate."""
    
    prompt: str = Field(
        description="Natural language describing timeframe, region focus, voice, etc."
    )
    verticals: Optional[list[str]] = Field(
        default=None,
        description="Optional list of vertical IDs to include (e.g. data_centers)"
    )
    max_review_rounds: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum number of review iterations"
    )
    active_players: Optional[Dict[str, list]] = Field(
        default=None,
        description="Optional map of vertical to list of active player names"
    )


class GenerateResponse(BaseModel):
    """Response for POST /newsletter/generate."""
    
    newsletter_id: str = Field(description="Unique identifier for the generated newsletter")
    paths: Dict[str, str] = Field(
        description="Paths to generated artifacts"
    )
    status: str = Field(default="completed")


class UpdateSectionRequest(BaseModel):
    """Request body for POST /newsletter/{newsletter_id}/update-section."""
    
    section_id: str = Field(
        description="Section to update: data_centers, connectivity_fibre, or towers_wireless"
    )
    instruction: str = Field(
        description="Natural language describing how to modify the section"
    )
    time_window: Optional[TimeWindow] = Field(
        default=None,
        description="Optional new time window; uses original if omitted"
    )


class UpdateSectionResponse(BaseModel):
    """Response for POST /newsletter/{newsletter_id}/update-section."""
    
    newsletter_id: str
    section_id: str
    paths: Optional[Dict[str, str]] = Field(default=None, description="Paths to updated artifacts")
    status: str = Field(default="completed")


class NewsletterMetadata(BaseModel):
    """Metadata stored in meta.json for each newsletter issue."""
    
    newsletter_id: str
    original_prompt: str
    time_window: TimeWindow
    voice_profile: str
    region_focus: Optional[str] = None
    style_prompt: Optional[str] = None
    verticals_included: list[str]
    model_versions: Dict[str, str]
    created_at: str
    total_review_rounds: int
