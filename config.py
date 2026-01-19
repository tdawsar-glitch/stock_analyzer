"""
Stock Analyzer Configuration
============================
Central configuration for the trading system.
Adjust these values to match your trading style.
"""

# ============================================================
# ANALYSIS PARAMETERS
# ============================================================

# Moving Averages
MA_SHORT = 20
MA_MEDIUM = 50
MA_LONG = 100
MA_VERY_LONG = 200

# Momentum
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MOMENTUM_PERIOD = 125  # ~6 months, from Clenow's book

# Volatility
ATR_PERIOD = 14
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# Volume
VOLUME_MA_PERIOD = 20

# ADX (Trend Strength)
ADX_PERIOD = 14
ADX_STRONG_TREND = 25

# ============================================================
# RISK MANAGEMENT (from Carver's Systematic Trading)
# ============================================================

# Position Sizing
ACCOUNT_SIZE = 3000  # Your capital in USD
MAX_RISK_PER_TRADE = 0.02  # 2% max loss per trade
MAX_POSITIONS = 5  # Maximum concurrent positions
MAX_POSITION_SIZE = 0.25  # Max 25% in single stock

# Stop Loss
ATR_STOP_MULTIPLIER = 1.5  # Stop loss = 1.5 x ATR below entry

# ============================================================
# MARKET CONTEXT
# ============================================================

MARKET_ETF = "SPY"  # S&P 500 ETF for market trend

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials", 
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services"
}

# Stock to Sector mapping (expandable)
STOCK_SECTORS = {
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "GOOGL": "XLC", "AMZN": "XLY",
    "META": "XLC", "TSLA": "XLY", "JPM": "XLF", "V": "XLK", "JNJ": "XLV",
    "WMT": "XLP", "PG": "XLP", "XOM": "XLE", "CVX": "XLE", "BAC": "XLF",
    "HD": "XLY", "KO": "XLP", "PFE": "XLV", "DIS": "XLC", "NFLX": "XLC",
    "AMD": "XLK", "INTC": "XLK", "CRM": "XLK", "ORCL": "XLK", "CSCO": "XLK",
    "PLTR": "XLK", "SOFI": "XLF", "NIO": "XLY", "RIVN": "XLY", "COIN": "XLF"
}

# ============================================================
# DATA SETTINGS
# ============================================================

DATA_PERIOD = "2y"  # Fetch 2 years of data
DATA_INTERVAL = "1d"  # Daily data
