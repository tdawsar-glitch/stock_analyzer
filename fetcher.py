"""
Data Fetcher Module
===================
Handles all data retrieval from Yahoo Finance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import sys
sys.path.append('..')
try:
    from ..config import DATA_PERIOD, DATA_INTERVAL, MARKET_ETF, SECTOR_ETFS, STOCK_SECTORS
except ImportError:
    from config import DATA_PERIOD, DATA_INTERVAL, MARKET_ETF, SECTOR_ETFS, STOCK_SECTORS


def fetch_stock_data(symbol: str, period: str = DATA_PERIOD) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a stock.
    
    Parameters:
        symbol: Stock ticker (e.g., 'AAPL')
        period: How far back ('1y', '2y', '5y')
    
    Returns:
        DataFrame with Open, High, Low, Close, Volume
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=DATA_INTERVAL)
        
        if df.empty:
            print(f"⚠️  No data found for {symbol}")
            return None
        
        df.index = pd.to_datetime(df.index)
        df = df.dropna()
        print(f"✓ Loaded {len(df)} days for {symbol}")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return None


def fetch_market_data() -> pd.DataFrame:
    """Fetch SPY data for market context."""
    return fetch_stock_data(MARKET_ETF)


def fetch_sector_data(symbol: str) -> pd.DataFrame:
    """Fetch the sector ETF data for a given stock."""
    sector_etf = STOCK_SECTORS.get(symbol.upper())
    if sector_etf:
        sector_name = SECTOR_ETFS.get(sector_etf, "Unknown")
        print(f"📊 {symbol} sector: {sector_name} ({sector_etf})")
        return fetch_stock_data(sector_etf)
    return None


def get_stock_info(symbol: str) -> dict:
    """Get fundamental info about a stock."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "name": info.get("longName", symbol),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "avg_volume": info.get("averageVolume", 0),
            "beta": info.get("beta", 1)
        }
    except Exception as e:
        print(f"❌ Error getting info: {e}")
        return {"name": symbol}


def get_earnings_date(symbol: str) -> dict:
    """Get next earnings date and days until."""
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar
        
        if calendar is not None and len(calendar) > 0:
            # Handle different calendar formats
            if isinstance(calendar, pd.DataFrame):
                earnings_date = calendar.iloc[0, 0] if not calendar.empty else None
            else:
                earnings_date = calendar.get('Earnings Date', [None])[0]
            
            if earnings_date:
                if isinstance(earnings_date, str):
                    earnings_date = pd.to_datetime(earnings_date)
                days_until = (earnings_date - datetime.now()).days
                return {
                    "date": earnings_date.strftime('%Y-%m-%d'),
                    "days_until": days_until,
                    "warning": days_until <= 14
                }
        
        return {"date": "Unknown", "days_until": None, "warning": False}
        
    except:
        return {"date": "Unknown", "days_until": None, "warning": False}


def get_options_activity(symbol: str) -> dict:
    """
    Get options activity for sentiment analysis.
    High put/call ratio = bearish sentiment
    Low put/call ratio = bullish sentiment
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        
        if not expirations:
            return {"available": False}
        
        # Get nearest expiration
        opt_chain = ticker.option_chain(expirations[0])
        calls, puts = opt_chain.calls, opt_chain.puts
        
        call_vol = calls['volume'].sum()
        put_vol = puts['volume'].sum()
        call_oi = calls['openInterest'].sum()
        put_oi = puts['openInterest'].sum()
        
        pc_ratio = put_vol / call_vol if call_vol > 0 else 0
        
        # Determine sentiment
        if pc_ratio > 1.2:
            sentiment = "BEARISH"
        elif pc_ratio < 0.7:
            sentiment = "BULLISH"
        else:
            sentiment = "NEUTRAL"
        
        return {
            "available": True,
            "expiration": expirations[0],
            "call_volume": int(call_vol),
            "put_volume": int(put_vol),
            "put_call_ratio": round(pc_ratio, 2),
            "sentiment": sentiment
        }
        
    except Exception as e:
        return {"available": False}
