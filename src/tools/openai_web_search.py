"""Web search tool using OpenAI's built-in web_search tool."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from openai import OpenAI

from ..config import get_settings
from ..schemas.evidence import EvidenceItem


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _iter_output_text_parts(response: Any):
    output_items = _get(response, "output", []) or []
    for item in output_items:
        content = _get(item, "content", []) or []
        for part in content:
            if _get(part, "type") == "output_text":
                yield part


def openai_web_search(
    query: str,
    max_results: int = 10,
    time_window_days: Optional[int] = None,
    model: Optional[str] = None,
) -> List[EvidenceItem]:
    """
    Search the web using OpenAI's web_search tool.

    Args:
        query: The search string.
        max_results: Maximum number of sources to return.
        time_window_days: Optional filter hint for recent results (in days).
        model: Optional model override for the web search request.

    Returns:
        List of EvidenceItem objects with URLs and titles from citations.
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = f"Find recent sources about: {query}."
    if time_window_days:
        prompt += f" Focus on sources from the last {time_window_days} days."
    prompt += " Provide a concise summary with citations."

    response = client.responses.create(
        model=model or settings.model_web_search,
        input=prompt,
        tools=[{"type": "web_search"}],
    )

    citations = []
    for part in _iter_output_text_parts(response):
        annotations = _get(part, "annotations", []) or []
        for annotation in annotations:
            if _get(annotation, "type") == "url_citation":
                url = _get(annotation, "url")
                title = _get(annotation, "title")
                if url:
                    citations.append((url, title))

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for url, title in citations:
        if url in seen:
            continue
        seen.add(url)
        unique.append((url, title))

    items = []
    for url, title in unique[:max_results]:
        items.append(EvidenceItem(
            source_type="web",
            source_name="openai_web_search",
            retrieved_at=datetime.utcnow(),
            url=url,
            title=title,
            text=None,
            reliability="medium",
            tags=["openai_web_search"],
        ))

    return items
