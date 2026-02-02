"""Article fetch and parse tool using newspaper3k."""

from datetime import datetime
from typing import Optional
from langchain_core.tools import tool

from ..schemas.evidence import EvidenceItem


def fetch_article(url: str) -> Optional[EvidenceItem]:
    """
    Fetch and parse an article from a URL using newspaper3k.
    
    Args:
        url: The article URL to fetch and parse.
    
    Returns:
        EvidenceItem with cleaned text, title, authors, and publish date.
        Returns None if the article cannot be fetched/parsed.
    """
    from newspaper import Article
    
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        # Extract publish date
        publish_date = None
        if article.publish_date:
            publish_date = article.publish_date.isoformat()
        
        # Build evidence item
        item = EvidenceItem(
            source_type="news",
            source_name="newspaper3k",
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
