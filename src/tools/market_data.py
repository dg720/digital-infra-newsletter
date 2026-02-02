"""Market data tool using yfinance."""

from datetime import datetime, date
from typing import List, Literal, Optional
from langchain_core.tools import tool

from ..schemas.evidence import EvidenceItem


def get_price_history(
    tickers: List[str],
    start: date,
    end: date,
    interval: Literal["1d", "1h"] = "1d",
) -> List[EvidenceItem]:
    """
    Fetch OHLCV price history for given tickers using yfinance.
    
    Args:
        tickers: List of stock ticker symbols.
        start: Start date for price history.
        end: End date for price history.
        interval: Data interval - "1d" for daily or "1h" for hourly.
    
    Returns:
        List of EvidenceItem objects with structured OHLCV data.
    
    Note:
        This tool only retrieves raw data. It does not compute analytics.
        Agents should interpret price movements only based on the retrieved data.
    """
    import yfinance as yf
    
    evidence_items = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start, end=end, interval=interval)
            
            if hist.empty:
                continue
            
            # Convert to serializable format
            ohlcv_data = []
            for idx, row in hist.iterrows():
                ohlcv_data.append({
                    "date": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })
            
            # Get company info
            info = stock.info
            company_name = info.get("longName", ticker)
            
            item = EvidenceItem(
                source_type="market_data",
                source_name="yfinance",
                retrieved_at=datetime.utcnow(),
                url=f"https://finance.yahoo.com/quote/{ticker}",
                title=f"{company_name} ({ticker}) Price History",
                text=f"Price data for {company_name} from {start} to {end}",
                data={
                    "ticker": ticker,
                    "company_name": company_name,
                    "interval": interval,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "ohlcv": ohlcv_data,
                    "latest_close": ohlcv_data[-1]["close"] if ohlcv_data else None,
                    "first_close": ohlcv_data[0]["close"] if ohlcv_data else None,
                },
                reliability="high",  # Market data is factual
                tags=["market_data", "stock_price", ticker],
            )
            evidence_items.append(item)
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            continue
    
    return evidence_items


# Mapping of major players to their tickers (where publicly traded)
PLAYER_TICKERS = {
    # Data Centers
    "Equinix": "EQIX",
    "Digital Realty": "DLR",
    "CyrusOne": None,  # Acquired
    "QTS Data Centers": None,  # Acquired
    "NTT Global Data Centers": None,  # Part of NTT
    "Iron Mountain Data Centers": "IRM",
    "Switch": None,  # Acquired
    "STACK Infrastructure": None,  # Private
    "Google Cloud": "GOOGL",
    "Amazon Web Services (AWS)": "AMZN",
    
    # Connectivity & Fibre
    "Lumen Technologies": "LUMN",
    "Zayo": None,  # Private
    "Crown Castle Fiber": "CCI",
    "Colt Technology Services": None,  # Private
    "euNetworks": None,  # Private
    "CityFibre": None,  # Private
    "Openreach": "BT.A",  # BT Group
    "Telxius": None,  # Private
    "Sparkle (Telecom Italia Sparkle)": "TIT.MI",
    "Subsea7": "SUBC.OL",
    
    # Towers & Wireless
    "American Tower": "AMT",
    "Cellnex Telecom": "CLNX.MC",
    "Vantage Towers": "VTWR.DE",
    "SBA Communications": "SBAC",
    "IHS Towers": "IHS",
    "Indus Towers": "INDUSTOWER.NS",
    "Crown Castle": "CCI",
    "Phoenix Tower International": None,  # Private
    "Helios Towers": "HTWS.L",
    "DigitalBridge": "DBRG",
}


def get_ticker_for_player(player_name: str) -> Optional[str]:
    """Get the stock ticker for a major player if publicly traded."""
    return PLAYER_TICKERS.get(player_name)


@tool
def get_price_history_tool(
    tickers: List[str],
    start_date: str,
    end_date: str,
    interval: str = "1d",
) -> List[dict]:
    """
    Fetch stock price history for infrastructure company tickers.
    
    Use this tool to get OHLCV (Open, High, Low, Close, Volume) data for
    publicly traded digital infrastructure companies. Useful for understanding
    market sentiment and verifying price-related claims.
    
    NOTE: This tool only retrieves raw price data. Do not compute or claim
    analytics that aren't directly observable from the data.
    
    Args:
        tickers: List of stock ticker symbols (e.g., ["EQIX", "DLR", "AMT"]).
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        interval: Data interval - "1d" for daily or "1h" for hourly.
    
    Returns:
        List of evidence items with OHLCV data for each ticker.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    interval_typed: Literal["1d", "1h"] = "1d" if interval == "1d" else "1h"
    
    items = get_price_history(tickers, start, end, interval_typed)
    return [item.model_dump() for item in items]
