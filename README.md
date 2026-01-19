# Stock Analyzer

A comprehensive stock analysis tool for US equities. Evaluates potential entry points using multi-factor analysis.

## Features

- **Trend Analysis**: 20/50/100/200 MA, price structure, ADX
- **Momentum**: RSI, MACD, 6-month momentum
- **Volume**: Accumulation/distribution, volume trends
- **Volatility**: ATR, Bollinger Bands, squeeze detection
- **Market Context**: SPY trend, sector comparison, relative strength
- **Options Activity**: Put/call ratio sentiment
- **Earnings Warning**: Alert when earnings within 2 weeks
- **Position Sizing**: Risk-based sizing for $3,000 account
- **Trade Setup**: Entry zone, stop loss, targets with R:R

## Installation

```bash
# 1. Navigate to the project folder
cd stock_analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the Streamlit app
streamlit run streamlit_app.py
```

## Usage

### Streamlit (Browser)
```bash
streamlit run streamlit_app.py
```

### In Python Code
```python
from analyzer import analyze

# Get full analysis
result = analyze("NVDA")

# Access specific data
print(result['signal'])           # Trading signal
print(result['trend'])            # Trend analysis
print(result['position_sizing'])  # Position size recommendation
```

## Configuration

Edit `config.py` to customize:

```python
# Your account size
ACCOUNT_SIZE = 3000

# Risk per trade (2% = 0.02)
MAX_RISK_PER_TRADE = 0.02

# Maximum positions
MAX_POSITIONS = 5
```

## Project Structure

```
stock_analyzer/
├── streamlit_app.py     # Streamlit UI
├── main.py              # CLI entry point (optional)
├── analyzer.py          # Main analysis engine
├── config.py            # Configuration settings
├── requirements.txt     # Dependencies
├── data/
│   └── fetcher.py       # Data retrieval
└── strategy/
    └── indicators.py    # Technical indicators
```

## Based On

- Ernest Chan - *Quantitative Trading*
- Andreas Clenow - *Stocks on the Move*
- Robert Carver - *Systematic Trading*

## Disclaimer

Educational purposes only. Not financial advice.
