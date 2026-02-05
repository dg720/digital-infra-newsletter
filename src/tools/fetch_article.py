"""Article fetch and parse tool using newspaper4k."""

from datetime import datetime
import re
from typing import Optional
from langchain_core.tools import tool

from ..schemas.evidence import EvidenceItem


def fetch_article(url: str) -> Optional[EvidenceItem]:
    """
    Fetch and parse an article from a URL using newspaper4k.
    
    Args:
        url: The article URL to fetch and parse.
    
    Returns:
        EvidenceItem with cleaned text, title, authors, and publish date.
        Returns None if the article cannot be fetched/parsed.
    """
    import newspaper
    
    try:
        article = newspaper.article(url)
        
        # Extract publish date
        publish_date = None
        publish_date = _normalize_publish_date(getattr(article, "publish_date", None))
        if not publish_date and getattr(article, "html", None):
            publish_date = _extract_publish_date_from_html(article.html)
        
        # Build evidence item
        item = EvidenceItem(
            source_type="news",
            source_name="newspaper4k",
            retrieved_at=datetime.utcnow(),
            url=url,
            title=article.title,
            text=article.text[:5000] if article.text else None,  # Limit text length
            data={
                "authors": article.authors,
                "publish_date": publish_date,
                "top_image": article.top_image,
                "keywords": article.keywords if hasattr(article, 'keywords') else [],
            },
            reliability=_assess_article_reliability(url, article),
            tags=["full_article"],
        )
        
        return item
        
    except Exception as e:
        print(f"Error fetching article {url}: {e}")
        return None


def _assess_article_reliability(url: str, article) -> str:
    """Assess article reliability based on source and content quality."""
    high_reliability_domains = [
        "reuters.com",
        "bloomberg.com",
        "ft.com",
        "wsj.com",
        "datacenterknowledge.com",
        "datacenterdynamics.com",
        "capacitymedia.com",
    ]
    
    url_lower = url.lower()
    
    # Check domain
    for domain in high_reliability_domains:
        if domain in url_lower:
            return "high"
    
    # Check content quality indicators
    if article.text and len(article.text) > 500 and article.authors:
        return "medium"
    
    return "low"


def extract_publish_date_newspaper4k(url: str) -> Optional[str]:
    """Extract publish date using newspaper4k for a URL."""
    try:
        import newspaper
        article = newspaper.article(url)
        publish_date = _normalize_publish_date(getattr(article, "publish_date", None))
        if not publish_date and getattr(article, "html", None):
            publish_date = _extract_publish_date_from_html(article.html)
        return publish_date
    except Exception as exc:
        print(f"Error extracting publish date for {url}: {exc}")
        return None


def _normalize_publish_date(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


def _extract_publish_date_from_html(html: str) -> Optional[str]:
    """Extract explicit publish date strings from raw HTML."""
    month_names = (
        "January|February|March|April|May|June|July|August|September|October|November|December|"
        "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    )
    patterns = [
        (rf"(Published|Updated|Written|Posted|Date|On|Last\\s+updated|Last\\s+modified)\\s*[:\\-]?\\s*({month_names})\\s+(\\d{{1,2}})(?:st|nd|rd|th)?,\\s*(20\\d{{2}})\\s*\\d{{0,2}}:?\\d{{0,2}}", "mdy_prefix"),
        (rf"(Published|Updated|Written|Posted|Date|On|Last\\s+updated|Last\\s+modified)\\s*[:\\-]?\\s*(\\d{{1,2}})(?:st|nd|rd|th)?\\s+({month_names})\\s+(20\\d{{2}})\\s*\\d{{0,2}}:?\\d{{0,2}}", "dmy_prefix"),
        (rf"\\b({month_names})\\s+(\\d{{1,2}})(?:st|nd|rd|th)?,\\s*(20\\d{{2}})\\b", "mdy"),
        (rf"\\b({month_names})\\s+(\\d{{1,2}})(?:st|nd|rd|th)?\\s+(20\\d{{2}})\\b", "mdy"),
        (rf"\\b(\\d{{1,2}})(?:st|nd|rd|th)?\\s+({month_names})\\s+(20\\d{{2}})\\b", "dmy"),
    ]
    for pattern, order in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if not match:
            continue
        parts = match.groups()
        if order == "mdy":
            month, day, year = parts[0], parts[1], parts[2]
        elif order == "mdy_prefix":
            month, day, year = parts[1], parts[2], parts[3]
        elif order == "dmy_prefix":
            day, month, year = parts[1], parts[2], parts[3]
        else:
            day, month, year = parts[0], parts[1], parts[2]
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                parsed = datetime.strptime(f"{day} {month} {year}", fmt)
                return parsed.date().isoformat()
            except ValueError:
                continue
    return None


@tool
def fetch_article_tool(url: str) -> Optional[dict]:
    """
    Fetch and parse a full article from a URL.
    
    Use this tool to get the complete text of an article when you need more
    detail than the search snippet provides. Good for verifying claims and
    extracting specific quotes or data points.
    
    Args:
        url: The full URL of the article to fetch.
    
    Returns:
        Evidence item with full article text, title, authors, and publish date.
        Returns None if the article cannot be fetched.
    """
    item = fetch_article(url)
    if item:
        return item.model_dump()
    return None
