#!/usr/bin/env python3
"""
Stock Analyzer - Main Entry Point
=================================

A comprehensive stock analysis tool that evaluates:
- Trend (multiple timeframes)
- Momentum (RSI, MACD)
- Volume (accumulation/distribution)
- Volatility (ATR, Bollinger Bands)
- Market Context (SPY, sector)
- Options Activity (sentiment)
- Earnings Date Warning

Usage:
    python main.py              # Interactive mode
    python main.py NVDA         # Analyze specific stock
    python main.py AAPL MSFT    # Analyze multiple stocks

Author: Built with guidance from:
    - Ernest Chan (Quantitative Trading)
    - Marcos López de Prado (ML for Finance)
    - Andreas Clenow (Stocks on the Move)
    - Robert Carver (Systematic Trading)
"""

import sys
from .analyzer import StockAnalyzer, analyze


def main():
    # Best-effort: ensure stdout can emit UTF-8 (Windows defaults can be non-UTF8)
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    banner_utf8 = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    STOCK ANALYZER v1.0                       ║
    ║                                                              ║
    ║  Comprehensive technical analysis for US equities            ║
    ║  Account Size: $3,000 | Max Risk: 2% per trade              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    banner_ascii = """
    +--------------------------------------------------------------+
    |                    STOCK ANALYZER v1.0                       |
    |                                                              |
    |  Comprehensive technical analysis for US equities            |
    |  Account Size: $3,000 | Max Risk: 2% per trade              |
    +--------------------------------------------------------------+
    """

    try:
        print(banner_utf8)
    except UnicodeEncodeError:
        print(banner_ascii)
    
    # Get symbols from command line or input
    if len(sys.argv) > 1:
        symbols = [s.upper() for s in sys.argv[1:]]
    else:
        user_input = input("Enter stock symbol(s) separated by space: ").strip()
        symbols = [s.upper() for s in user_input.split()]
    
    if not symbols:
        print("No symbols provided. Exiting.")
        return
    
    # Analyze each symbol
    results = {}
    for symbol in symbols:
        try:
            results[symbol] = analyze(symbol)
        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {e}")
    
    # Summary if multiple stocks
    if len(results) > 1:
        print("\n" + "="*70)
        print("  SUMMARY: All Analyzed Stocks")
        print("="*70)
        print(f"  {'Symbol':<8} {'Price':>10} {'Signal':<15} {'Score':>8} {'Confidence':<10}")
        print("-"*70)
        
        for symbol, data in results.items():
            sig = data['signal']
            trend = data['trend']
            print(f"  {symbol:<8} ${trend['current_price']:>9.2f} {sig['signal']:<15} {sig['score']:>8} {sig['confidence']:<10}")
        
        print("="*70)
    
    return results


if __name__ == "__main__":
    main()
