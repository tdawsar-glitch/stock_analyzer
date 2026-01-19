"""Streamlit UI for the Stock Analyzer."""
from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from analyzer import StockAnalyzer


st.set_page_config(page_title="Stock Analyzer", layout="wide")


@st.cache_data(ttl=3600, show_spinner=False)
def run_analysis(symbol: str) -> dict:
    analyzer = StockAnalyzer(symbol, verbose=False)
    return analyzer.run_full_analysis()


def parse_symbols(raw: str) -> List[str]:
    tokens = [token.strip().upper() for token in raw.replace(",", " ").split()]
    return [token for token in tokens if token]


st.title("📈 Stock Analyzer")
st.write(
    "Run multi-factor analysis for US equities. "
    "Enter one or more tickers separated by spaces or commas."
)

with st.form("analysis-form"):
    symbols_input = st.text_input("Symbols", placeholder="AAPL MSFT NVDA")
    submitted = st.form_submit_button("Analyze")

if submitted:
    symbols = parse_symbols(symbols_input)
    if not symbols:
        st.error("Please enter at least one stock symbol.")
    else:
        results = {}
        errors = {}
        with st.spinner("Fetching market data and running analysis..."):
            for symbol in symbols:
                try:
                    results[symbol] = run_analysis(symbol)
                except Exception as exc:
                    errors[symbol] = str(exc)

        if errors:
            for symbol, message in errors.items():
                st.warning(f"{symbol}: {message}")

        if results:
            summary_rows = []
            for symbol, data in results.items():
                trend = data["trend"]
                signal = data["signal"]
                summary_rows.append(
                    {
                        "Symbol": symbol,
                        "Price": trend["current_price"],
                        "Signal": signal["signal"],
                        "Score": signal["score"],
                        "Confidence": signal["confidence"],
                    }
                )

            st.subheader("Summary")
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

            for symbol, data in results.items():
                info = data["stock_info"]
                trend = data["trend"]
                momentum = data["momentum"]
                volatility = data["volatility"]
                volume = data["volume"]
                market = data["market_context"]
                signal = data["signal"]
                earnings = data["earnings"]
                options = data["options_activity"]
                targets = data["targets"]
                sizing = data["position_sizing"]

                with st.expander(f"{symbol} — {info.get('name', symbol)}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Price", f"${trend['current_price']}")
                    col2.metric("Signal", signal["signal"])
                    col3.metric("Confidence", signal["confidence"])

                    st.markdown("### Trend")
                    trend_cols = st.columns(4)
                    trend_cols[0].metric("Short (20MA)", trend["short_term"]["trend"])
                    trend_cols[1].metric("Medium (50MA)", trend["medium_term"]["trend"])
                    trend_cols[2].metric("Long (200MA)", trend["long_term"]["trend"])
                    trend_cols[3].metric("ADX", f"{trend['adx']} ({trend['trend_strength']})")

                    st.markdown("### Momentum")
                    mom_cols = st.columns(3)
                    mom_cols[0].metric("RSI", f"{momentum['rsi']} ({momentum['rsi_status']})")
                    mom_cols[1].metric("MACD", momentum["macd_status"])
                    mom_cols[2].metric("6M Momentum", f"{momentum['momentum_6m']}%")

                    st.markdown("### Volume & Volatility")
                    vv_cols = st.columns(4)
                    vv_cols[0].metric("Volume Ratio", f"{volume['volume_ratio']}x")
                    vv_cols[1].metric("Volume Trend", volume["volume_trend"])
                    vv_cols[2].metric("ATR", f"${volatility['atr']} ({volatility['atr_percent']}%)")
                    vv_cols[3].metric("Bollinger", volatility["bollinger_position"])

                    st.markdown("### Market Context")
                    mc_cols = st.columns(3)
                    mc_cols[0].metric("Market", market.get("market_trend", "N/A"))
                    mc_cols[1].metric("Sector", market.get("sector_trend", "N/A"))
                    mc_cols[2].metric("Relative Strength", market.get("relative_strength", "N/A"))

                    st.markdown("### Signals")
                    st.write(f"**Action:** {signal['action']}")
                    if signal["reasons"]:
                        st.success("Bullish Factors")
                        for reason in signal["reasons"]:
                            st.write(f"- {reason}")
                    if signal["warnings"]:
                        st.warning("Warnings")
                        for warning in signal["warnings"]:
                            st.write(f"- {warning}")

                    st.markdown("### Earnings & Options")
                    st.write(
                        f"Next Earnings: {earnings['date']} "
                        f"({'⚠️ within 2 weeks' if earnings.get('warning') else 'no immediate risk'})"
                    )
                    if options.get("available"):
                        st.write(
                            "Options Sentiment: "
                            f"{options['sentiment']} (P/C {options['put_call_ratio']})"
                        )

                    st.markdown("### Position Sizing & Targets")
                    sizing_cols = st.columns(3)
                    sizing_cols[0].metric("Recommended Shares", sizing["recommended_shares"])
                    sizing_cols[1].metric("Position Value", f"${sizing['position_value']}")
                    sizing_cols[2].metric("Stop Loss", f"${sizing['stop_loss']}")

                    target_cols = st.columns(3)
                    target_cols[0].metric("Entry Zone", targets["entry_zone"])
                    target_cols[1].metric("Target 1", f"${targets['target_1']}")
                    target_cols[2].metric("Target 2", f"${targets['target_2']}")

                    st.write(f"Support: {targets['support_levels']}")
                    st.write(f"Resistance: {targets['resistance_levels']}")
