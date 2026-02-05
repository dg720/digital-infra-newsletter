"""API schemas - request and response models for FastAPI endpoints."""

from typing import Optional, Dict
from pydantic import BaseModel, Field

from .state import TimeWindow


class GenerateRequest(BaseModel):
    """Request body for POST /newsletter/generate."""
    
    prompt: Optional[str] = Field(
        default=None,
        description="Optional natural language description (legacy)."
    )
    time_window: Optional[TimeWindow] = Field(
        default=None,
        description="Explicit time window for coverage."
    )
    region_focus: Optional[str] = Field(
        default=None,
        description="Geographic focus (e.g. 'UK', 'EU', 'US', or comma-separated)."
    )
    voice_profile: Optional[str] = Field(
        default=None,
        description="Desired tone/voice. Defaults to expert_operator."
    )
    style_prompt: Optional[str] = Field(
        default=None,
        description="Additional style instructions."
    )
    verticals: Optional[list[str]] = Field(
        default=None,
        description="Optional list of vertical IDs to include (e.g. data_centers)"
    )
    search_provider: Optional[str] = Field(
        default=None,
        description="Search provider to use: openai (default) or tavily"
    )
    strict_date_filtering: Optional[bool] = Field(
        default=None,
        description="If true, require explicit publish dates within time window."
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


class SourceOverride(BaseModel):
    """Source override for manual inclusion/exclusion."""

    url: str = Field(description="Source URL")
    title: Optional[str] = Field(default=None, description="Optional source title")
    publish_date: Optional[str] = Field(default=None, description="Optional publish date")
    include: bool = Field(default=True, description="Whether to include this source")


class UpdateSourcesRequest(BaseModel):
    """Request body for POST /newsletter/{newsletter_id}/update-sources."""

    section_id: str = Field(
        description="Section to update: data_centers, connectivity_fibre, or towers_wireless"
    )
    sources: list[SourceOverride] = Field(
        default_factory=list,
        description="All sources with include toggles"
    )
    add_urls: Optional[list[str]] = Field(
        default=None,
        description="Additional URLs to fetch and include"
    )


class UpdateSourcesResponse(BaseModel):
    """Response for POST /newsletter/{newsletter_id}/update-sources."""

    newsletter_id: str
    section_id: str
    status: str = Field(default="updated")


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
