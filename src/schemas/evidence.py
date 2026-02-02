"""Evidence schemas - EvidenceItem and EvidencePack models."""

from datetime import datetime
from typing import Optional, List, Any, Literal
from pydantic import BaseModel, Field
import uuid


def generate_evidence_id() -> str:
    """Generate a unique evidence ID."""
    return f"ev_{uuid.uuid4().hex[:8]}"


class EvidenceItem(BaseModel):
    """A single piece of evidence from a retrieval tool."""
    
    evidence_id: str = Field(default_factory=generate_evidence_id)
    source_type: Literal["web", "news", "market_data"] = Field(
        description="Type of source: web, news, or market_data"
    )
    source_name: Literal["tavily", "newspaper3k", "yfinance"] = Field(
        description="Name of the tool that retrieved this evidence"
    )
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO-8601 timestamp of when the evidence was retrieved"
    )
    url: Optional[str] = Field(default=None, description="URL of the source if applicable")
    title: Optional[str] = Field(default=None, description="Title of the source if available")
    text: Optional[str] = Field(default=None, description="Cleaned text content")
    data: Optional[Any] = Field(default=None, description="Structured payload (e.g., OHLCV data)")
    reliability: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Reliability assessment of the source"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Optional tags for categorization"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EvidencePack(BaseModel):
    """Collection of evidence items for a section."""
    
    section_id: str = Field(description="ID of the section this evidence belongs to")
    items: List[EvidenceItem] = Field(
        default_factory=list,
        description="List of evidence items"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_item(self, item: EvidenceItem) -> None:
        """Add an evidence item to the pack."""
        self.items.append(item)
    
    def get_item_by_id(self, evidence_id: str) -> Optional[EvidenceItem]:
        """Retrieve an evidence item by its ID."""
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item
        return None
    
    def get_evidence_ids(self) -> List[str]:
        """Get all evidence IDs in this pack."""
        return [item.evidence_id for item in self.items]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
