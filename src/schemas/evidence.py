"""Evidence schemas - EvidenceItem and EvidencePack models."""

from datetime import datetime
from typing import Optional, List, Any, Literal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
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
    source_name: Literal["tavily", "openai_web_search", "newspaper3k", "newspaper4k", "yfinance", "manual_override"] = Field(
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
        """Add an evidence item to the pack with basic deduping."""
        if item.url:
            item_key = _normalize_url(item.url)
            for existing in self.items:
                if existing.url and _normalize_url(existing.url) == item_key:
                    return
        else:
            title_key = (item.title or "").strip().lower()
            if title_key:
                for existing in self.items:
                    if not existing.url and (existing.title or "").strip().lower() == title_key:
                        return
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


def _normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        query_params = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
            and k.lower() not in {"ref", "ref_src", "source", "fbclid", "gclid", "mc_cid", "mc_eid"}
        ]
        clean_query = urlencode(query_params, doseq=True)
        netloc = parsed.netloc.lower()
        scheme = parsed.scheme.lower()
        return urlunparse((scheme, netloc, parsed.path.rstrip("/"), "", clean_query, ""))
    except Exception:
        return url
