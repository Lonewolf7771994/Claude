# Claude

Trading tooling for Claude — MCP servers and the scripts that connect them.

## [`tradingview-mcp/`](tradingview-mcp) — TradingView MCP server

TradingView charts plus real market data, over MCP stdio, zero dependencies.
Charts come from TradingView's official widget; prices come from Crypto.com
(keyless) and Alpha Vantage. Six tools: quotes, candles, order-book depth,
EMA/RSI/ATR/VWAP/MACD analysis, chart links and embeds.

```bash
claude mcp add tradingview -s user -e ALPHAVANTAGE_API_KEY=your_key -- node tradingview-mcp/server.js
```

## [`mcp-bridge/`](mcp-bridge) — PowerShell linker

Registers any downloaded MCP bridge with Claude Code and Claude Desktop on
Windows. Detects the file type, verifies the server with a real MCP handshake,
then writes the config.

```powershell
.\mcp-bridge\Link-McpBridge.ps1
```

---

Charts: https://www.tradingview.com/
