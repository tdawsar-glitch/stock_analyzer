"""
Stock Analyzer Engine
=====================
Main analysis engine that combines all components.
Produces comprehensive stock analysis reports.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

try:
    # Package (recommended): python -m stock_analyzer.main
    from .config import (
        RSI_OVERSOLD,
        RSI_OVERBOUGHT,
        ADX_STRONG_TREND,
        ATR_STOP_MULTIPLIER,
        ACCOUNT_SIZE,
        MAX_RISK_PER_TRADE,
        MAX_POSITION_SIZE,
        STOCK_SECTORS,
        SECTOR_ETFS,
    )
    from .data.fetcher import (
        fetch_stock_data,
        fetch_market_data,
        fetch_sector_data,
        get_stock_info,
        get_earnings_date,
        get_options_activity,
    )
    from .strategy.indicators import (
        calculate_all_indicators,
        calculate_volume_analysis,
        identify_support_resistance,
    )
except ImportError:
    # Script fallback: python stock_analyzer/analyzer.py
    from config import (
        RSI_OVERSOLD,
        RSI_OVERBOUGHT,
        ADX_STRONG_TREND,
        ATR_STOP_MULTIPLIER,
        ACCOUNT_SIZE,
        MAX_RISK_PER_TRADE,
        MAX_POSITION_SIZE,
        STOCK_SECTORS,
        SECTOR_ETFS,
    )
    from data.fetcher import (
        fetch_stock_data,
        fetch_market_data,
        fetch_sector_data,
        get_stock_info,
        get_earnings_date,
        get_options_activity,
    )
    from strategy.indicators import (
        calculate_all_indicators,
        calculate_volume_analysis,
        identify_support_resistance,
    )


class StockAnalyzer:
    """
    Comprehensive stock analysis engine.
    Evaluates trend, momentum, volume, volatility, and market context.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.df = None
        self.market_df = None
        self.sector_df = None
        self.info = None
        self.analysis = {}
        
    def load_data(self):
        """Load all required data."""
        print(f"\n{'='*60}")
        print(f"  ANALYZING: {self.symbol}")
        print(f"{'='*60}\n")
        
        # Stock data
        self.df = fetch_stock_data(self.symbol)
        if self.df is None:
            raise ValueError(f"Could not load data for {self.symbol}")
        
        # Calculate indicators
        self.df = calculate_all_indicators(self.df)
        
        # Market data
        print("\nLoading market context...")
        self.market_df = fetch_market_data()
        if self.market_df is not None:
            self.market_df = calculate_all_indicators(self.market_df)
        
        # Sector data
        self.sector_df = fetch_sector_data(self.symbol)
        if self.sector_df is not None:
            self.sector_df = calculate_all_indicators(self.sector_df)
        
        # Stock info
        self.info = get_stock_info(self.symbol)
        
        return self
    
    def analyze_trend(self) -> dict:
        """Analyze trend across multiple timeframes."""
        df = self.df
        current_price = df['Close'].iloc[-1]
        
        # MA positions
        ma20 = df['MA20'].iloc[-1]
        ma50 = df['MA50'].iloc[-1]
        ma100 = df['MA100'].iloc[-1]
        ma200 = df['MA200'].iloc[-1]
        
        # Trend determination
        short_trend = "BULLISH" if current_price > ma20 else "BEARISH"
        medium_trend = "BULLISH" if current_price > ma50 else "BEARISH"
        long_trend = "BULLISH" if current_price > ma200 else "BEARISH"
        
        # Golden/Death cross
        golden_cross = ma50 > ma200
        
        # Price structure (higher highs, higher lows)
        recent_highs = df['High'].tail(20)
        recent_lows = df['Low'].tail(20)
        
        hh = recent_highs.iloc[-1] > recent_highs.iloc[-10]  # Higher high
        hl = recent_lows.iloc[-1] > recent_lows.iloc[-10]   # Higher low
        structure = "UPTREND" if (hh and hl) else "DOWNTREND" if (not hh and not hl) else "CONSOLIDATION"
        
        # ADX trend strength
        adx = df['ADX'].iloc[-1]
        trend_strength = "STRONG" if adx > ADX_STRONG_TREND else "WEAK"
        
        # Overall trend score (-100 to +100)
        trend_score = 0
        trend_score += 25 if short_trend == "BULLISH" else -25
        trend_score += 25 if medium_trend == "BULLISH" else -25
        trend_score += 25 if long_trend == "BULLISH" else -25
        trend_score += 25 if golden_cross else -25
        
        return {
            "current_price": round(current_price, 2),
            "short_term": {"trend": short_trend, "ma": round(ma20, 2)},
            "medium_term": {"trend": medium_trend, "ma": round(ma50, 2)},
            "long_term": {"trend": long_trend, "ma": round(ma200, 2)},
            "golden_cross": golden_cross,
            "price_structure": structure,
            "adx": round(adx, 1) if not np.isnan(adx) else None,
            "trend_strength": trend_strength,
            "trend_score": trend_score
        }
    
    def analyze_momentum(self) -> dict:
        """Analyze momentum indicators."""
        df = self.df
        
        rsi = df['RSI'].iloc[-1]
        macd = df['MACD'].iloc[-1]
        macd_signal = df['MACD_Signal'].iloc[-1]
        macd_hist = df['MACD_Hist'].iloc[-1]
        momentum = df['Momentum'].iloc[-1]
        
        # RSI interpretation
        if rsi > RSI_OVERBOUGHT:
            rsi_status = "OVERBOUGHT"
        elif rsi < RSI_OVERSOLD:
            rsi_status = "OVERSOLD"
        else:
            rsi_status = "NEUTRAL"
        
        # MACD interpretation
        macd_bullish = macd > macd_signal
        macd_cross = "BULLISH CROSSOVER" if macd_bullish and df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2] else \
                     "BEARISH CROSSOVER" if not macd_bullish and df['MACD'].iloc[-2] >= df['MACD_Signal'].iloc[-2] else \
                     "BULLISH" if macd_bullish else "BEARISH"
        
        # Momentum score
        momentum_score = 0
        momentum_score += 33 if rsi_status != "OVERBOUGHT" else -33
        momentum_score += 33 if macd_bullish else -33
        momentum_score += 34 if momentum > 0 else -34
        
        return {
            "rsi": round(rsi, 1),
            "rsi_status": rsi_status,
            "macd": round(macd, 3),
            "macd_signal": round(macd_signal, 3),
            "macd_histogram": round(macd_hist, 3),
            "macd_status": macd_cross,
            "momentum_6m": round(momentum, 1),
            "momentum_score": momentum_score
        }
    
    def analyze_volatility(self) -> dict:
        """Analyze volatility metrics."""
        df = self.df
        current_price = df['Close'].iloc[-1]
        
        atr = df['ATR'].iloc[-1]
        atr_percent = (atr / current_price) * 100
        
        bb_upper = df['BB_Upper'].iloc[-1]
        bb_lower = df['BB_Lower'].iloc[-1]
        bb_percent = df['BB_Percent'].iloc[-1]
        bb_width = (bb_upper - bb_lower) / df['BB_Middle'].iloc[-1] * 100
        
        # Volatility interpretation
        if bb_percent > 0.8:
            bb_position = "NEAR UPPER BAND (potentially overbought)"
        elif bb_percent < 0.2:
            bb_position = "NEAR LOWER BAND (potentially oversold)"
        else:
            bb_position = "MIDDLE OF BANDS"
        
        # Squeeze detection (low volatility, potential breakout)
        avg_bb_width = ((df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100).tail(50).mean()
        squeeze = bb_width < avg_bb_width * 0.75
        
        return {
            "atr": round(atr, 2),
            "atr_percent": round(atr_percent, 2),
            "bollinger_upper": round(bb_upper, 2),
            "bollinger_lower": round(bb_lower, 2),
            "bollinger_position": bb_position,
            "bollinger_percent_b": round(bb_percent, 2),
            "bollinger_width": round(bb_width, 2),
            "squeeze_detected": squeeze
        }
    
    def analyze_market_context(self) -> dict:
        """Analyze broader market and sector conditions."""
        result = {
            "market_trend": "UNKNOWN",
            "sector_trend": "UNKNOWN",
            "relative_strength": "UNKNOWN"
        }
        
        if self.market_df is not None:
            spy_price = self.market_df['Close'].iloc[-1]
            spy_ma50 = self.market_df['MA50'].iloc[-1]
            spy_ma200 = self.market_df['MA200'].iloc[-1]
            
            result["market_trend"] = "BULLISH" if spy_price > spy_ma50 > spy_ma200 else \
                                     "BEARISH" if spy_price < spy_ma50 < spy_ma200 else "MIXED"
            result["spy_above_50ma"] = spy_price > spy_ma50
            result["spy_above_200ma"] = spy_price > spy_ma200
        
        if self.sector_df is not None:
            sector_price = self.sector_df['Close'].iloc[-1]
            sector_ma50 = self.sector_df['MA50'].iloc[-1]
            
            result["sector_trend"] = "BULLISH" if sector_price > sector_ma50 else "BEARISH"
            
            # Relative strength vs sector
            stock_perf = (self.df['Close'].iloc[-1] / self.df['Close'].iloc[-20] - 1) * 100
            sector_perf = (sector_price / self.sector_df['Close'].iloc[-20] - 1) * 100
            
            result["stock_20d_perf"] = round(stock_perf, 2)
            result["sector_20d_perf"] = round(sector_perf, 2)
            result["relative_strength"] = "OUTPERFORMING" if stock_perf > sector_perf else "UNDERPERFORMING"
        
        return result
    
    def calculate_position_sizing(self) -> dict:
        """
        Calculate position size based on risk management rules.
        From Carver's Systematic Trading approach.
        """
        current_price = self.df['Close'].iloc[-1]
        atr = self.df['ATR'].iloc[-1]
        
        # Stop loss based on ATR
        stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
        risk_per_share = current_price - stop_loss
        
        # Max loss per trade (2% of account)
        max_loss = ACCOUNT_SIZE * MAX_RISK_PER_TRADE
        
        # Position size based on risk
        shares_by_risk = int(max_loss / risk_per_share)
        
        # Max position size (25% of account)
        max_position_value = ACCOUNT_SIZE * MAX_POSITION_SIZE
        shares_by_max = int(max_position_value / current_price)
        
        # Take the smaller of the two
        recommended_shares = min(shares_by_risk, shares_by_max)
        position_value = recommended_shares * current_price
        
        return {
            "current_price": round(current_price, 2),
            "stop_loss": round(stop_loss, 2),
            "risk_per_share": round(risk_per_share, 2),
            "recommended_shares": recommended_shares,
            "position_value": round(position_value, 2),
            "percent_of_account": round(position_value / ACCOUNT_SIZE * 100, 1),
            "max_loss_if_stopped": round(recommended_shares * risk_per_share, 2)
        }
    
    def calculate_targets(self) -> dict:
        """Calculate price targets based on risk/reward."""
        current_price = self.df['Close'].iloc[-1]
        atr = self.df['ATR'].iloc[-1]
        stop_loss = current_price - (atr * ATR_STOP_MULTIPLIER)
        risk = current_price - stop_loss
        
        # Targets at 2:1 and 3:1 risk/reward
        target_1 = current_price + (risk * 2)
        target_2 = current_price + (risk * 3)
        
        # Support/resistance levels
        levels = identify_support_resistance(self.df)
        
        return {
            "entry_zone": f"${round(current_price * 0.98, 2)} - ${round(current_price, 2)}",
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "risk_reward_1": "1:2",
            "risk_reward_2": "1:3",
            "support_levels": [round(s, 2) for s in levels["support"][:3]],
            "resistance_levels": [round(r, 2) for r in levels["resistance"][:3]],
            "distance_to_52w_high": f"{levels['distance_to_52w_high']}%",
            "distance_to_52w_low": f"{levels['distance_to_52w_low']}%"
        }
    
    def generate_signal(self) -> dict:
        """
        Generate trading signal based on all analysis.
        Returns BUY, SELL, WAIT, or specific conditions.
        """
        trend = self.analysis.get('trend', {})
        momentum = self.analysis.get('momentum', {})
        volatility = self.analysis.get('volatility', {})
        market = self.analysis.get('market_context', {})
        
        # Scoring system
        score = 0
        reasons = []
        warnings = []
        
        # Trend factors (40% weight)
        if trend.get('trend_score', 0) > 50:
            score += 40
            reasons.append("Strong uptrend across timeframes")
        elif trend.get('trend_score', 0) > 0:
            score += 20
            reasons.append("Moderate uptrend")
        elif trend.get('trend_score', 0) < -50:
            score -= 40
            warnings.append("Strong downtrend - avoid buying")
        
        # Momentum factors (30% weight)
        if momentum.get('momentum_score', 0) > 50:
            score += 30
            reasons.append("Strong momentum")
        elif momentum.get('rsi_status') == "OVERSOLD":
            score += 15
            reasons.append("RSI oversold - potential bounce")
        elif momentum.get('rsi_status') == "OVERBOUGHT":
            score -= 15
            warnings.append("RSI overbought - wait for pullback")
        
        if "BULLISH CROSSOVER" in momentum.get('macd_status', ''):
            score += 15
            reasons.append("Recent MACD bullish crossover")
        
        # Market context (20% weight)
        if market.get('market_trend') == "BULLISH":
            score += 15
            reasons.append("Market trend is bullish")
        elif market.get('market_trend') == "BEARISH":
            score -= 20
            warnings.append("Market trend is bearish - higher risk")
        
        if market.get('relative_strength') == "OUTPERFORMING":
            score += 10
            reasons.append("Outperforming sector")
        
        # Volatility (10% weight)
        if volatility.get('squeeze_detected'):
            score += 10
            reasons.append("Volatility squeeze - potential breakout")
        
        # Generate signal
        if score >= 60:
            signal = "BUY"
            action = "Consider entering position"
        elif score >= 30:
            signal = "BUY ON PULLBACK"
            action = "Wait for pullback to support or MA"
        elif score <= -30:
            signal = "AVOID"
            action = "Conditions unfavorable"
        else:
            signal = "WAIT"
            action = "Monitor for better setup"
        
        return {
            "signal": signal,
            "action": action,
            "score": score,
            "confidence": "HIGH" if abs(score) > 60 else "MEDIUM" if abs(score) > 30 else "LOW",
            "reasons": reasons,
            "warnings": warnings
        }
    
    def run_full_analysis(self) -> dict:
        """Run complete analysis and return all results."""
        self.load_data()
        
        print("\n📊 Running analysis...")
        
        self.analysis = {
            "symbol": self.symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stock_info": self.info,
            "earnings": get_earnings_date(self.symbol),
            "options_activity": get_options_activity(self.symbol),
            "trend": self.analyze_trend(),
            "momentum": self.analyze_momentum(),
            "volatility": self.analyze_volatility(),
            "volume": calculate_volume_analysis(self.df),
            "market_context": self.analyze_market_context(),
            "position_sizing": self.calculate_position_sizing(),
            "targets": self.calculate_targets(),
        }
        
        self.analysis["signal"] = self.generate_signal()
        
        return self.analysis
    
    def print_report(self):
        """Print formatted analysis report."""
        a = self.analysis
        
        print(f"\n{'═'*70}")
        print(f"  STOCK ANALYSIS REPORT: {a['symbol']}")
        print(f"  {a['stock_info'].get('name', a['symbol'])}")
        print(f"  Generated: {a['timestamp']}")
        print(f"{'═'*70}")
        
        # Price & Trend
        print(f"\n{'─'*70}")
        print("  TREND ANALYSIS")
        print(f"{'─'*70}")
        t = a['trend']
        print(f"  Current Price:     ${t['current_price']}")
        print(f"  Short-term (20MA): {t['short_term']['trend']:8} (MA: ${t['short_term']['ma']})")
        print(f"  Medium-term (50MA):{t['medium_term']['trend']:8} (MA: ${t['medium_term']['ma']})")
        print(f"  Long-term (200MA): {t['long_term']['trend']:8} (MA: ${t['long_term']['ma']})")
        print(f"  Price Structure:   {t['price_structure']}")
        print(f"  Golden Cross:      {'Yes ✓' if t['golden_cross'] else 'No'}")
        print(f"  ADX:               {t['adx']} ({t['trend_strength']} trend)")
        
        # Momentum
        print(f"\n{'─'*70}")
        print("  MOMENTUM")
        print(f"{'─'*70}")
        m = a['momentum']
        print(f"  RSI (14):          {m['rsi']} ({m['rsi_status']})")
        print(f"  MACD:              {m['macd_status']}")
        print(f"  6-Month Momentum:  {m['momentum_6m']}%")
        
        # Volume
        print(f"\n{'─'*70}")
        print("  VOLUME")
        print(f"{'─'*70}")
        v = a['volume']
        print(f"  Current vs Avg:    {v['volume_ratio']}x average")
        print(f"  Volume Trend:      {v['volume_trend']}")
        print(f"  Flow:              {v['accumulation_distribution']}")
        
        # Volatility
        print(f"\n{'─'*70}")
        print("  VOLATILITY")
        print(f"{'─'*70}")
        vol = a['volatility']
        print(f"  ATR (14):          ${vol['atr']} ({vol['atr_percent']}%)")
        print(f"  Bollinger:         {vol['bollinger_position']}")
        print(f"  Squeeze:           {'Yes - potential breakout!' if vol['squeeze_detected'] else 'No'}")
        
        # Market Context
        print(f"\n{'─'*70}")
        print("  MARKET CONTEXT")
        print(f"{'─'*70}")
        mc = a['market_context']
        print(f"  Market (SPY):      {mc.get('market_trend', 'N/A')}")
        print(f"  Sector:            {mc.get('sector_trend', 'N/A')}")
        print(f"  Relative Strength: {mc.get('relative_strength', 'N/A')}")
        
        # Earnings & Options
        print(f"\n{'─'*70}")
        print("  ADDITIONAL SIGNALS")
        print(f"{'─'*70}")
        e = a['earnings']
        print(f"  Next Earnings:     {e['date']}", end="")
        if e.get('warning'):
            print(" ⚠️  WITHIN 2 WEEKS!")
        else:
            print("")
        
        opt = a['options_activity']
        if opt.get('available'):
            print(f"  Options Sentiment: {opt['sentiment']} (P/C ratio: {opt['put_call_ratio']})")
        
        # Signal
        print(f"\n{'═'*70}")
        print("  SIGNAL & RECOMMENDATION")
        print(f"{'═'*70}")
        sig = a['signal']
        print(f"  Signal:            {sig['signal']}")
        print(f"  Confidence:        {sig['confidence']} (Score: {sig['score']}/100)")
        print(f"  Action:            {sig['action']}")
        
        if sig['reasons']:
            print(f"\n  ✓ Bullish Factors:")
            for r in sig['reasons']:
                print(f"    • {r}")
        
        if sig['warnings']:
            print(f"\n  ⚠ Warnings:")
            for w in sig['warnings']:
                print(f"    • {w}")
        
        # Position Sizing
        print(f"\n{'─'*70}")
        print("  POSITION SIZING (Based on $3,000 account)")
        print(f"{'─'*70}")
        ps = a['position_sizing']
        print(f"  Recommended Shares: {ps['recommended_shares']}")
        print(f"  Position Value:     ${ps['position_value']} ({ps['percent_of_account']}% of account)")
        print(f"  Stop Loss:          ${ps['stop_loss']}")
        print(f"  Max Loss if Stopped: ${ps['max_loss_if_stopped']}")
        
        # Targets
        print(f"\n{'─'*70}")
        print("  TRADE SETUP")
        print(f"{'─'*70}")
        tgt = a['targets']
        print(f"  Entry Zone:        {tgt['entry_zone']}")
        print(f"  Stop Loss:         ${tgt['stop_loss']}")
        print(f"  Target 1 (2:1):    ${tgt['target_1']}")
        print(f"  Target 2 (3:1):    ${tgt['target_2']}")
        print(f"  Support:           {tgt['support_levels']}")
        print(f"  Resistance:        {tgt['resistance_levels']}")
        
        print(f"\n{'═'*70}")
        print("  END OF REPORT")
        print(f"{'═'*70}\n")


def analyze(symbol: str) -> dict:
    """
    Quick function to analyze a stock.
    
    Usage:
        from stock_analyzer.analyzer import analyze
        result = analyze("NVDA")
    """
    analyzer = StockAnalyzer(symbol)
    result = analyzer.run_full_analysis()
    analyzer.print_report()
    return result


# Run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = input("Enter stock symbol: ").strip().upper()
    
    analyze(symbol)
