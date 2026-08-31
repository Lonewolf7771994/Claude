# Claude

Trading tooling for Claude — MCP servers and the scripts that connect them.

Both servers in this repo are registered in [`.mcp.json`](.mcp.json), so a Claude
Code session started in this directory picks them up (approve them once when
Claude asks). To link them outside this repo, see the commands under each server.

## [`tradingview-mcp/`](tradingview-mcp) — TradingView MCP server

TradingView charts plus real market data, over MCP stdio, zero dependencies.
Charts come from TradingView's official widget; prices come from Crypto.com
(keyless) and Alpha Vantage. Six tools: quotes, candles, order-book depth,
EMA/RSI/ATR/VWAP/MACD analysis, chart links and embeds.

```bash
claude mcp add tradingview -s user -e ALPHAVANTAGE_API_KEY=your_key -- node tradingview-mcp/server.js
```

## [`tradingview-desktop-mcp/`](tradingview-desktop-mcp) — TradingView Desktop bridge

Vendored copy of [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)
(MIT — see [VENDORED.md](tradingview-desktop-mcp/VENDORED.md)). Drives the
TradingView Desktop app running on *your* machine over Chrome DevTools Protocol:
84 tools for reading chart state, Pine Script development, drawings, alerts,
replay, multi-pane layouts and screenshots — plus a `tv` CLI mirroring every tool.

Needs a TradingView subscription, the Desktop app launched with
`--remote-debugging-port=9222`, and `npm install` inside the directory. Every
tool errors with `CDP connection failed` until that app is running.

```bash
cd tradingview-desktop-mcp && npm install && cd ..
claude mcp add tradingview-desktop -s user -- node "$PWD/tradingview-desktop-mcp/src/server.js"
```

```powershell
# Windows
cd tradingview-desktop-mcp; npm install; cd ..
claude mcp add tradingview-desktop -s user -- node "$PWD\tradingview-desktop-mcp\src\server.js"
.\tradingview-desktop-mcp\scripts\launch_tv_debug.bat
```

## [`mcp-bridge/`](mcp-bridge) — PowerShell linker

Registers any downloaded MCP bridge with Claude Code and Claude Desktop on
Windows. Detects the file type, verifies the server with a real MCP handshake,
then writes the config.

```powershell
.\mcp-bridge\Link-McpBridge.ps1
# or point it straight at the vendored bridge above -- name the server file, not the
# folder: that package's `bin` is the `tv` CLI, which does not speak MCP stdio
.\mcp-bridge\Link-McpBridge.ps1 -Path .\tradingview-desktop-mcp\src\server.js -Name tradingview-desktop -Target both
```

---

Charts: https://www.tradingview.com/
