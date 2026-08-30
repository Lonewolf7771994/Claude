# Linking a downloaded MCP bridge from PowerShell (Windows)

You downloaded an MCP bridge into `%USERPROFILE%\Downloads`. This folder has a script that
wires it into Claude for you, plus the manual commands in case you'd rather do it by hand.

## The quick way

Open **PowerShell** (no admin needed) and run:

```powershell
cd $HOME\Downloads
# allow the script to run in this window only
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# point it at wherever you saved this repo
& "<path-to-repo>\mcp-bridge\Link-McpBridge.ps1"
```

With no arguments it scans `Downloads` for the bridge, figures out how to launch it,
sends it a real MCP `initialize` handshake to confirm it works, and registers it with
Claude Code. Useful switches:

```powershell
# name it yourself and register with Claude Code *and* Claude Desktop
.\Link-McpBridge.ps1 -Path "$HOME\Downloads\mcp-bridge.js" -Name mcp-bridge -Target both

# the bridge needs an API key or token
.\Link-McpBridge.ps1 -EnvVar @{ BRIDGE_TOKEN = 'abc123'; API_KEY = 'sk-...' }

# see exactly what it would do, change nothing
.\Link-McpBridge.ps1 -DryRun
```

| Switch | Meaning |
| --- | --- |
| `-Path` | The downloaded file or folder. Omit to auto-detect in `Downloads`. |
| `-Name` | Server name. Defaults to a slug of the file name. |
| `-Target` | `claude-code` (default), `claude-desktop`, or `both`. |
| `-Scope` | Claude Code scope: `user` (default, all projects), `local`, or `project`. |
| `-EnvVar` | Hashtable of environment variables for the server. |
| `-InstallTo` | Where a `.zip` gets unpacked. Default `$HOME\.mcp-servers\<name>`. |
| `-SkipTest` | Skip the MCP handshake check. |
| `-DryRun` | Print the plan, change nothing. |

It handles `.js` / `.mjs` / `.cjs` (node), `.py` (python), `.jar` (java), `.exe`, `.ps1`,
`.zip` (unpacks, then detects), and a folder (reads `package.json`, or finds `server.py` /
`index.js` / `dist/index.js`). For a node project without `node_modules` it runs `npm install` first.

Re-running is safe: the Claude Code entry is removed and re-added, and the Claude Desktop
config is backed up to `claude_desktop_config.json.<timestamp>.bak` before each write.

## Doing it by hand

### Claude Code

`claude mcp add` takes the launch command after a `--` separator:

```powershell
# a JavaScript bridge
claude mcp add mcp-bridge -s user -- node "$HOME\Downloads\mcp-bridge.js"

# a Python bridge
claude mcp add mcp-bridge -s user -- python "$HOME\Downloads\mcp_bridge.py"

# a standalone .exe
claude mcp add mcp-bridge -s user -- "$HOME\Downloads\mcp-bridge.exe"

# an npm-published bridge -- on native Windows it must be wrapped in cmd /c
claude mcp add mcp-bridge -s user -- cmd /c npx -y some-mcp-bridge

# with environment variables
claude mcp add mcp-bridge -s user -e API_KEY=sk-... -- node "$HOME\Downloads\mcp-bridge.js"

# a hosted bridge that speaks HTTP or SSE instead of stdio
claude mcp add --transport http mcp-bridge https://example.com/mcp
```

Scopes: `-s user` makes it available in every project, `-s local` (the default) is just this
project for you, `-s project` writes `.mcp.json` and is shared with the repo.

Then check it:

```powershell
claude mcp list
claude mcp get mcp-bridge
claude mcp remove mcp-bridge -s user   # to undo
```

Inside a Claude Code session, `/mcp` shows connection status and lets you authenticate a
remote server.

### Claude Desktop

Claude Desktop reads a JSON file — there is no CLI:

```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

```json
{
  "mcpServers": {
    "mcp-bridge": {
      "command": "node",
      "args": ["C:\\Users\\you\\Downloads\\mcp-bridge.js"],
      "env": { "API_KEY": "sk-..." }
    }
  }
}
```

Backslashes must be doubled in JSON. Then quit Claude Desktop **completely** (system tray →
Quit, not just closing the window) and reopen it.

### If the file is a `.mcpb` (or older `.dxt`)

That's a packaged desktop extension, not a script — PowerShell can't register it. Double-click
it, or in Claude Desktop go to Settings → Extensions → Advanced settings → Install extension.

```powershell
explorer.exe /select,"$HOME\Downloads\your-bridge.mcpb"
```

## When it doesn't connect

| Symptom | Cause |
| --- | --- |
| `node`/`python` "not recognized" | Runtime missing, or PATH not refreshed — install it and open a **new** PowerShell window. |
| Server shows as `failed` in `claude mcp list` | Run the launch command by hand in PowerShell; the error prints to the console. |
| Works in `cmd` but not from Claude | Use absolute paths everywhere; Claude doesn't launch it from your current directory. |
| `npx` bridge never starts on Windows | It needs the `cmd /c` wrapper shown above. |
| Connects, then drops | The bridge is writing logs to stdout. MCP stdio needs stdout to carry only JSON-RPC — logs belong on stderr. |
| Desktop still doesn't see it | It wasn't fully quit, or the JSON is invalid: `Get-Content "$env:APPDATA\Claude\claude_desktop_config.json" \| ConvertFrom-Json`. |

To watch what a bridge actually does, run it directly and paste in a handshake:

```powershell
node "$HOME\Downloads\mcp-bridge.js"
```
then paste one line and press Enter:
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"manual","version":"1.0"}}}
```
A healthy server replies with a single JSON line containing `"result"`.
