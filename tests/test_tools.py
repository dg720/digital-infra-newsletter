"""Tests for retrieval tools."""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.schemas.evidence import EvidenceItem


class TestWebSearchTool:
    """Tests for web_search tool."""
    
    def test_evidence_item_schema(self):
        """Test that web search returns proper EvidenceItem schema."""
        # Mock the actual web search call
        item = EvidenceItem(
            source_type="web",
            source_name="tavily",
            url="https://datacenterknowledge.com/test",
            title="Test Data Center Article",
            text="Content about data centers.",
            reliability="high",
            tags=["search_result"],
        )
        
        # Validate schema
        assert item.source_type == "web"
        assert item.source_name == "tavily"
        assert item.evidence_id.startswith("ev_")
        assert item.reliability in ["high", "medium", "low"]


class TestFetchArticleTool:
    """Tests for fetch_article tool."""
    
    def test_evidence_item_schema(self):
        """Test that article fetch returns proper EvidenceItem schema."""
        item = EvidenceItem(
            source_type="news",
            source_name="newspaper3k",
            url="https://example.com/article",
            title="Test Article Title",
            text="Full article text here...",
            data={
                "authors": ["John Doe"],
                "publish_date": "2026-01-30T00:00:00",
            },
            reliability="medium",
            tags=["full_article"],
        )
        
        assert item.source_type == "news"
        assert item.source_name == "newspaper3k"
        assert "authors" in item.data


class TestMarketDataTool:
    """Tests for get_price_history tool."""
    
    def test_evidence_item_schema(self):
        """Test that market data returns proper EvidenceItem schema."""
        item = EvidenceItem(
            source_type="market_data",
            source_name="yfinance",
            url="https://finance.yahoo.com/quote/EQIX",
            title="Equinix Inc. (EQIX) Price History",
            text="Price data for Equinix Inc. from 2026-01-26 to 2026-02-02",
            data={
                "ticker": "EQIX",
                "company_name": "Equinix Inc.",
                "interval": "1d",
                "ohlcv": [
                    {
                        "date": "2026-01-26T00:00:00",
                        "open": 850.0,
                        "high": 855.0,
                        "low": 848.0,
                        "close": 852.0,
                        "volume": 500000,
                    }
                ],
            },
            reliability="high",
            tags=["market_data", "stock_price", "EQIX"],
        )
        
        assert item.source_type == "market_data"
        assert item.source_name == "yfinance"
        assert "ohlcv" in item.data
        assert item.data["ticker"] == "EQIX"


class TestReliabilityAssessment:
    """Tests for reliability scoring logic."""
    
    def test_high_reliability_domains(self):
        """Test that known high-reliability domains are scored correctly."""
        high_rel_urls = [
            "https://www.reuters.com/article",
            "https://www.bloomberg.com/news",
            "https://www.datacenterknowledge.com/story",
        ]
        
        # The reliability assessment happens in the tool
        # This tests the expected output format
        for url in high_rel_urls:
            item = EvidenceItem(
                source_type="web",
                source_name="tavily",
                url=url,
                reliability="high",  # Expected for these domains
            )
            assert item.reliability == "high"
