# TradingView MCP

An MCP server that gives Claude TradingView charts **and** real market data, over stdio, with no npm dependencies.

## What this is honest about

TradingView publishes **charts**, not a public quote API. There is no official TradingView MCP
server and no public TradingView endpoint that returns prices. So this server splits the job:

| Layer | Source |
| --- | --- |
| Charts — deep links and embeds | TradingView's official advanced-chart widget |
| Crypto prices, candles, order book | **Crypto.com public API** — no key, no quota |
| Metals, energy, FX, equities | **Alpha Vantage** — needs `ALPHAVANTAGE_API_KEY` |

Nothing here scrapes TradingView and nothing invents a price. Every quote carries its `source`
and `as_of` so you can check where the number came from.

## Install

Requires Node 18+ (uses the built-in `fetch`). No `npm install` needed.

```bash
claude mcp add tradingview -s user -e ALPHAVANTAGE_API_KEY=your_key -- node /path/to/tradingview-mcp/server.js
claude mcp list
```

On Windows, or if you'd rather not type the path, use the linker in [`../mcp-bridge`](../mcp-bridge):

```powershell
.\Link-McpBridge.ps1 -Path "C:\path\to\tradingview-mcp\server.js" -Name tradingview `
  -Target both -EnvVar @{ ALPHAVANTAGE_API_KEY = 'your_key' }
```

Claude Desktop, by hand — `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["C:\\path\\to\\tradingview-mcp\\server.js"],
      "env": { "ALPHAVANTAGE_API_KEY": "your_key" }
    }
  }
}
```

The key is optional. Without it crypto still works completely; metals, energy, FX and equities
return a clear error telling you what's missing. Get a free one at
<https://www.alphavantage.co/support/#api-key> (free tier is 25 requests/day).

## Tools

| Tool | What it does |
| --- | --- |
| `tv_symbol` | Resolve `gold` / `btc` / `oil` / `NASDAQ:AAPL` to a TradingView symbol, chart URL and data feed |
| `tv_quote` | Live price with bid/ask, 24h range, change, source and timestamp |
| `tv_candles` | OHLCV candles — crypto `1m 5m 15m 30m 1h 4h 1d 1w`, Alpha Vantage `1m 5m 15m 30m 1h` |
| `tv_orderbook` | Live depth with bid/ask volume and resting-size imbalance (crypto only) |
| `tv_analysis` | EMA20/50, RSI14, ATR14, VWAP, MACD → bullish/bearish/sideways, every check shown |
| `tv_chart` | TradingView deep link + a self-contained HTML page embedding the official widget |

### Symbols

Presets: `XAUUSD` `XAGUSD` `USOIL` `UKOIL` `NATGAS` `BTCUSD` `ETHUSD` `SOLUSD` `XRPUSD`.
Aliases are generous — `gold`, `XAU`, `xau/usd`, `GC` all reach `XAUUSD`; `btc`, `bitcoin`,
`BTC/USD`, `btcusdt` all reach `BTCUSD`. Any other ticker is treated as an equity.

### Try it

> "What's BTC doing right now?" → `tv_quote`
> "Show me the 15m read on gold" → `tv_analysis`
> "Where's the resting size on BTC?" → `tv_orderbook`
> "Open an XAUUSD chart" → `tv_chart` with `save_to`

## How `tv_analysis` decides

Five checks vote +1, −1, or **0**: price vs EMA20, EMA20 vs EMA50, price vs VWAP, RSI vs its
45–55 neutral band, and MACD vs its signal. `score >= 2` is bullish, `<= -2` bearish, otherwise
sideways.

The zero vote is the important part. Two values that differ by less than a tenth of ATR are
**abstentions**, not evidence — otherwise a dead-flat tape produces a confident "bearish" from
noise in the last decimal. `votes_cast` tells you how many checks actually had something to say,
and every check reports its own `detail` so the reasoning is auditable rather than a black box.

This is descriptive only. No entry, stop-loss or take-profit is implied.

## Development

```bash
npm test        # 42 tests: indicators, feeds (mocked), symbol resolution, and the live MCP protocol
```

`test/protocol.test.js` spawns the real server and speaks JSON-RPC to it over stdio — the same
handshake a client performs — covering initialize, version negotiation, `tools/list`, tool
dispatch, failed calls, malformed input and stderr/stdout separation.

Layout:

```
server.js          MCP protocol, tool definitions and dispatch
lib/symbols.js     friendly name -> TradingView symbol + data feed
lib/sources.js     Crypto.com and Alpha Vantage clients (injectable fetch)
lib/indicators.js  EMA, SMA, RSI, ATR, VWAP, MACD, bias
lib/chart.js       TradingView links and widget HTML
```

## Notes

- `stdout` carries JSON-RPC only; all logging goes to `stderr`. A stray `console.log` in an MCP
  stdio server breaks the connection — that's the most common cause of a server that connects
  and immediately drops.
- Oil, Brent and natural gas are **daily settlement series** from Alpha Vantage, not intraday
  ticks. The response says so in a `note` field rather than pretending otherwise.
- Order book depth is crypto-only: no public venue publishes a consolidated book for spot gold
  or oil, so asking for one returns an error instead of a fabricated ladder.
