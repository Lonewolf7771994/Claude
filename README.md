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

### Live desk — gold and Bitcoin

`charts/hard-money-desk.html` — gold and Bitcoin on 15-minute and 4-hour candles,
with supply and demand zones drawn from 4-hour swing structure. Data comes from the
Crypto.com Exchange public feed, captured 2026-08-22 01:12 UTC.

Gold is priced through **PAXG** (Pax Gold), a token redeemable for one fine troy ounce
of London Good Delivery bullion, so the quote is dollars per ounce and trades around
the clock — much closer to XAUUSD than the GLD share price used in `gold-tape.html`.
The two agree: PAXG at 4,593.31 against GLD's 415.26 implies 0.0904 oz of gold per GLD
share, which matches the fund's actual bullion backing.

The feed returns 50 candles per request, so the 15-minute chart spans about 12 hours
and the 4-hour chart about 8 days. That is why the moving averages are EMA 9 and 21
rather than the 50/200 pair used on the daily chart. Source bars and the build script
are in `charts/data/live/`.
