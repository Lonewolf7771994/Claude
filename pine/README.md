# Pine Script strategies

## `xauusd-trend-pullback.pine`

A TradingView **strategy** (not an indicator) for gold. Because it is a strategy it
executes on the chart: entries, exits, the equity curve and the full trade list appear
in the Strategy Tester once it is added.

### Loading it

1. Open the XAUUSD chart on TradingView and set the timeframe to **15m**.
2. Pine Editor → paste the file → **Save**, then **Add to chart**.
3. Open the **Strategy Tester** tab to see the trades.

### The timeframe lock

Trades are taken on one timeframe only — 15m by default. On any other timeframe the
strategy places no orders and prints a notice on the chart. This is deliberate: a
pullback system tuned for 15m produces a meaningless backtest on the daily, and the
lock stops that number from being read by accident. Change it with the
*Take trades only on* input, or set it to `Any` to remove the lock.

### How it trades

| Stage | Rule |
|---|---|
| Trend | Close above (below) the 200 EMA, optionally confirmed by the same EMA on the 1H chart |
| Trigger | Price pulls back to touch the 20 EMA and closes back on the trend side of it |
| Confirmation | RSI(14) above 50 for longs, below 50 for shorts |
| Stop | 1.5 × ATR(14) from entry |
| Target | 3.0 × ATR(14) from entry — a 2:1 reward-to-risk |
| Break-even | Stop moves to entry once price has travelled 1R |
| Size | Derived from the stop distance so every trade risks 1% of equity |
| Session | 08:00–17:00 exchange time; the open trade is closed at session end |
| Throttle | At most three entries per day, one position at a time |

### Backtest honesty

Slippage defaults to 20 ticks, roughly a realistic gold spread, and commission is left
at zero — set your broker's commission in *Properties* before believing any result.
Signals evaluate on bar close (`process_orders_on_close = true`), so there is no
intrabar peeking, and the higher-timeframe series is requested with lookahead off.
Stops and targets are submitted on the same bar as the entry rather than the bar after,
so no bar is ever left unprotected.

Backtested performance is not a forecast. For research only — not financial advice.
