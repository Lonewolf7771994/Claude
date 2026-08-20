# Claude
Trade
https://www.tradingview.com/

## Charts

`charts/gold-tape.html` — a self-contained daily candlestick chart of gold, viewed
through GLD (SPDR Gold Shares), covering 365 sessions to 20 Aug 2026. Candles use the
hollow-up / filled-down convention, overlaid with SMA 50, SMA 200 and Bollinger bands,
plus an RSI(14) panel, a crosshair readout and a full session table. No build step and
no external dependencies — open the file in a browser.

Spot XAUUSD is not available from the connected market-data feed, which carries listed
equities and ETFs rather than FX or metals, so GLD stands in as the gold proxy. Levels
are quoted in GLD share terms, not dollars per ounce.

Source data is in `charts/data/gld-daily.csv` (date, open, high, low, close, volume).
`charts/data/indicators.js` recomputes the SMA, Bollinger, RSI and ATR series from it;
the values reconcile with the data provider's own indicator snapshot at the matching bar.
