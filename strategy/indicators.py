"""
Technical Indicators Module
===========================
All technical analysis calculations.
Based on methods from Chan, Clenow, and Carver.
"""

import pandas as pd
import numpy as np
import sys

from config import (
    MA_SHORT,
    MA_MEDIUM,
    MA_LONG,
    MA_VERY_LONG,
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    ATR_PERIOD,
    BOLLINGER_PERIOD,
    BOLLINGER_STD,
    VOLUME_MA_PERIOD,
    ADX_PERIOD,
    MOMENTUM_PERIOD,
)


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all moving averages."""
    df = df.copy()
    df['MA20'] = df['Close'].rolling(window=MA_SHORT).mean()
    df['MA50'] = df['Close'].rolling(window=MA_MEDIUM).mean()
    df['MA100'] = df['Close'].rolling(window=MA_LONG).mean()
    df['MA200'] = df['Close'].rolling(window=MA_VERY_LONG).mean()
    return df


def calculate_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.Series:
    """
    Calculate Relative Strength Index.
    RSI > 70 = overbought, RSI < 30 = oversold
    """
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(df: pd.DataFrame) -> tuple:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    Returns: (macd_line, signal_line, histogram)
    """
    exp1 = df['Close'].ewm(span=MACD_FAST, adjust=False).mean()
    exp2 = df['Close'].ewm(span=MACD_SLOW, adjust=False).mean()
    
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """
    Calculate Average True Range (volatility measure).
    Used for stop loss placement and position sizing.
    """
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_bollinger_bands(df: pd.DataFrame) -> tuple:
    """
    Calculate Bollinger Bands.
    Returns: (upper_band, middle_band, lower_band, %B)
    """
    middle = df['Close'].rolling(window=BOLLINGER_PERIOD).mean()
    std = df['Close'].rolling(window=BOLLINGER_PERIOD).std()
    
    upper = middle + (std * BOLLINGER_STD)
    lower = middle - (std * BOLLINGER_STD)
    
    # %B shows where price is within the bands (0 = lower, 1 = upper)
    percent_b = (df['Close'] - lower) / (upper - lower)
    
    return upper, middle, lower, percent_b


def calculate_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.Series:
    """
    Calculate ADX (Average Directional Index).
    ADX > 25 = strong trend, ADX < 20 = weak/no trend
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()
    
    tr = calculate_atr(df, 1) * 1  # True range (not averaged)
    
    plus_di = 100 * (plus_dm.rolling(period).mean() / tr.rolling(period).mean())
    minus_di = 100 * (minus_dm.rolling(period).mean() / tr.rolling(period).mean())
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx


def calculate_momentum(df: pd.DataFrame, period: int = MOMENTUM_PERIOD) -> pd.Series:
    """
    Calculate momentum (rate of change).
    From Clenow's momentum ranking approach.
    """
    return (df['Close'] / df['Close'].shift(period) - 1) * 100


def calculate_volume_analysis(df: pd.DataFrame) -> dict:
    """
    Analyze volume patterns.
    Returns volume metrics and accumulation/distribution signals.
    """
    df = df.copy()
    
    # Volume moving average
    vol_ma = df['Volume'].rolling(window=VOLUME_MA_PERIOD).mean()
    current_vol = df['Volume'].iloc[-1]
    avg_vol = vol_ma.iloc[-1]
    
    # Volume ratio
    vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
    
    # Recent volume trend (last 10 days vs previous 10)
    recent_avg = df['Volume'].tail(10).mean()
    prior_avg = df['Volume'].iloc[-20:-10].mean()
    vol_trend = "INCREASING" if recent_avg > prior_avg * 1.1 else \
                "DECREASING" if recent_avg < prior_avg * 0.9 else "STABLE"
    
    # Accumulation/Distribution approximation
    # Positive = accumulation (buying), Negative = distribution (selling)
    clv = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
    clv = clv.fillna(0)
    ad = (clv * df['Volume']).cumsum()
    ad_trend = "ACCUMULATION" if ad.iloc[-1] > ad.iloc[-20] else "DISTRIBUTION"
    
    return {
        "current_volume": int(current_vol),
        "avg_volume": int(avg_vol),
        "volume_ratio": round(vol_ratio, 2),
        "volume_trend": vol_trend,
        "accumulation_distribution": ad_trend
    }


def identify_support_resistance(df: pd.DataFrame, window: int = 20) -> dict:
    """
    Identify key support and resistance levels.
    Uses swing highs/lows from recent price action.
    """
    highs = df['High'].tail(100)
    lows = df['Low'].tail(100)
    current_price = df['Close'].iloc[-1]
    
    # Find local maxima and minima
    resistance_levels = []
    support_levels = []
    
    for i in range(window, len(highs) - window):
        # Check for swing high
        if highs.iloc[i] == highs.iloc[i-window:i+window].max():
            resistance_levels.append(highs.iloc[i])
        # Check for swing low
        if lows.iloc[i] == lows.iloc[i-window:i+window].min():
            support_levels.append(lows.iloc[i])
    
    # Filter to nearby levels
    resistance_levels = sorted([r for r in resistance_levels if r > current_price])[:3]
    support_levels = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]
    
    # Add 52-week high/low
    high_52w = df['High'].tail(252).max()
    low_52w = df['Low'].tail(252).min()
    
    return {
        "resistance": resistance_levels,
        "support": support_levels,
        "52w_high": round(high_52w, 2),
        "52w_low": round(low_52w, 2),
        "distance_to_52w_high": round((high_52w - current_price) / current_price * 100, 1),
        "distance_to_52w_low": round((current_price - low_52w) / current_price * 100, 1)
    }


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators and add to dataframe.
    """
    df = calculate_moving_averages(df)
    df['RSI'] = calculate_rsi(df)
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df)
    df['ATR'] = calculate_atr(df)
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'], df['BB_Percent'] = calculate_bollinger_bands(df)
    df['ADX'] = calculate_adx(df)
    df['Momentum'] = calculate_momentum(df)
    
    return df
