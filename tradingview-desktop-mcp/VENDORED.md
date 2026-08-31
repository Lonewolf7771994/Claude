# Provenance

This directory is a vendored copy of **tradesdontlie/tradingview-mcp**
(<https://github.com/tradesdontlie/tradingview-mcp>), package version 1.0.0,
MCP server version 2.0.0. Licensed MIT — see [LICENSE](LICENSE), copyright
tradesdontlie.

Imported from the uploaded `tradingview-mcp-main` archive, unmodified except:

- `.github/` (upstream CI workflow) was dropped so it does not run in this repo.

Not affiliated with, endorsed by, or associated with TradingView Inc. It drives a
TradingView Desktop app already running on your own machine over Chrome DevTools
Protocol, and requires a valid TradingView subscription.

## What it needs to work

- TradingView Desktop installed and launched with `--remote-debugging-port=9222`
  (`scripts/launch_tv_debug.bat` on Windows, `scripts/launch_tv_debug_mac.sh`,
  `scripts/launch_tv_debug_linux.sh`), or call the `tv_launch` tool.
- `npm install` in this directory (`@modelcontextprotocol/sdk`,
  `chrome-remote-interface`). `node_modules/` is gitignored.
- Host/port overrides: `TV_CDP_HOST` (default `127.0.0.1`), `TV_CDP_PORT`
  (default `9222`).

Without a live TradingView on that port every tool returns
`CDP connection failed` — the server still starts and lists its tools, it just
has nothing to talk to. That is the expected result on a machine that is not
running TradingView Desktop, including a remote Claude Code container.

## Verified

Handshake over stdio (`initialize` → `tools/list`) succeeds and advertises
**84 tools**; stdout carries only JSON-RPC, the disclaimer banner goes to stderr.
`tv_health_check` returns the documented "TradingView is not running with CDP
enabled" error when nothing is listening on 9222.
