"""Web search tool using Tavily API."""

from datetime import datetime
from typing import List, Optional
from langchain_core.tools import tool

from ..schemas.evidence import EvidenceItem
from ..config import get_settings


def web_search(
    query: str,
    max_results: int = 10,
    time_window_days: Optional[int] = None,
) -> List[EvidenceItem]:
    """
    Search the web using Tavily API.
    
    Args:
        query: The search string.
        max_results: Maximum number of results to return.
        time_window_days: Optional filter for recent results (in days).
    
    Returns:
        List of EvidenceItem objects with search results.
    """
    from tavily import TavilyClient
    
    settings = get_settings()
    client = TavilyClient(api_key=settings.tavily_api_key)
    
    # Build search parameters
    search_params = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_raw_content": False,
    }
    
    # Add time filter if specified
    if time_window_days:
        search_params["days"] = time_window_days
    
    try:
        response = client.search(**search_params)
        results = response.get("results", [])
    except Exception as e:
        # Return empty list on error - let the agent handle
        print(f"Tavily search error: {e}")
        return []
    
    evidence_items = []
    for result in results:
        item = EvidenceItem(
            source_type="web",
            source_name="tavily",
            retrieved_at=datetime.utcnow(),
            url=result.get("url"),
            title=result.get("title"),
            text=result.get("content"),
            reliability=_assess_reliability(result.get("url", "")),
            tags=["search_result"],
        )
        evidence_items.append(item)
    
    return evidence_items


def _assess_reliability(url: str) -> str:
    """Assess reliability based on source domain."""
    high_reliability_domains = [
        "reuters.com",
        "bloomberg.com",
        "ft.com",
        "wsj.com",
        "datacenterknowledge.com",
        "datacenterdynamics.com",
        "capacitymedia.com",
        "fiercetelecom.com",
        "lightreading.com",
    ]
    
    medium_reliability_domains = [
        "techcrunch.com",
        "zdnet.com",
        "theregister.com",
        "arstechnica.com",
    ]
    
    url_lower = url.lower()
    
    for domain in high_reliability_domains:
        if domain in url_lower:
            return "high"
    
    for domain in medium_reliability_domains:
        if domain in url_lower:
            return "medium"
    
    return "medium"


@tool
def web_search_tool(
    query: str,
    max_results: int = 10,
    time_window_days: Optional[int] = None,
) -> List[dict]:
    """
    Search the web for relevant information using Tavily.
    
    Use this tool to find news articles, company announcements, and industry
    updates related to digital infrastructure (data centers, fibre, towers).
    
    Args:
        query: Search query string. Be specific and include relevant keywords.
        max_results: Maximum number of results (default 10).
        time_window_days: Only return results from the last N days (optional).
    
    Returns:
        List of evidence items with title, url, text snippet, and reliability.
    """
    items = web_search(query, max_results, time_window_days)
    return [item.model_dump() for item in items]
