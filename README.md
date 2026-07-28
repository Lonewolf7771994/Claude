# Claude
Trade
https://www.tradingview.com/

## Scalp Mode + Movement Engine Indicator

`scalp-movement-engine.pine` — a TradingView Pine Script (v6) overlay indicator.

**How to use:** open TradingView → Pine Editor → paste the contents of the file → "Add to chart".

**Features:**
- **Trading Mode** — `Scalp` (fast, reactive settings for 1m–15m charts) or `Standard` (smoother settings for higher timeframes).
- **Movement Engine** — scores how strongly price is moving (0–100) from three components: ATR-normalized velocity, candle range expansion, and volume participation.
- **Signals** — BUY/SELL arrows fire only when an impulse move (score above your threshold) aligns with the EMA trend and, optionally, a volume surge.
- **Visuals** — bars colored by movement strength, impulse-zone background highlighting, fast/slow EMAs.
- **Dashboard** — live panel showing mode, movement score, market state (IMPULSE / CHOP / NEUTRAL), trend, and volume ratio.
- **Alerts** — buy, sell, and impulse-start alert conditions.
