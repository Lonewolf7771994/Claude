# Claude

Trade
https://www.tradingview.com/

## Ruflo + GitHub connectors

This repo is wired up for [Ruflo](https://github.com/ruvnet/ruflo) (`ruflo` on npm),
an agent meta-harness for Claude Code, with the GitHub MCP server registered
alongside it as a connector.

Both are declared in [`.mcp.json`](.mcp.json) and enabled in
[`.claude/settings.json`](.claude/settings.json), so Claude Code picks them up
automatically when you open this repo.

| Server        | Type  | How it runs                          |
| ------------- | ----- | ------------------------------------ |
| `claude-flow` | stdio | `npx -y ruflo@latest mcp start` (59 tools) |
| `github`      | http  | `https://api.githubcopilot.com/mcp/` |

### Setup

1. **GitHub token** — the GitHub server authenticates with a personal access
   token read from the environment (nothing secret is stored in this repo):

   ```bash
   export GITHUB_PERSONAL_ACCESS_TOKEN=<your-token>
   ```

   Create one at https://github.com/settings/personal-access-tokens with access
   to the repos you want Claude to reach.

2. **Start Claude Code** in this directory and approve the two servers when
   prompted. Check they came up with:

   ```bash
   claude mcp list
   ```

Ruflo needs no install step of its own — `npx` fetches it on first launch.
To pin it globally instead: `npm install -g ruflo@latest`.

### What's committed

`npx ruflo@latest init` has already been run here, so the full scaffold is in
the repo:

| Path                    | Contents                                  |
| ----------------------- | ----------------------------------------- |
| `CLAUDE.md`             | Swarm guidance and coordination rules     |
| `.claude/skills/`       | 30 skills                                 |
| `.claude/commands/`     | 16 command groups (sparc, swarm, github…) |
| `.claude/agents/`       | 17 agent definitions                      |
| `.claude/helpers/`      | Hook handler scripts                      |
| `.claude-flow/`         | V3 runtime config (`config.yaml`)         |
| `.agents/skills/ruflo/` | Core skill, discoverable by other agents  |

`.claude/settings.json` enables 7 hook types (PreToolUse, PostToolUse,
UserPromptSubmit, SessionStart and others) that shell out to
`.claude/helpers/hook-handler.cjs` on tool calls — that is how Ruflo routes
tasks and learns in the background. Delete the `hooks` block if you'd rather
run without it.

Runtime state (`.claude-flow/data/`, `logs/`, `sessions/`) is gitignored.

To re-run or extend the install:

```bash
npx ruflo@latest init --force        # regenerate the scaffold
npx ruflo@latest daemon start        # background workers
npx ruflo@latest swarm init          # initialize a swarm
npx skills add ruvnet/ruflo --all    # all 267 plugin skills
```

### Optional: Claude Code plugins

A lighter path — slash commands and agent definitions, no workspace files:

```
/plugin marketplace add ruvnet/ruflo
/plugin install ruflo-core@ruflo
/plugin install ruflo-swarm@ruflo
```

Note that plugin tools are namespaced `mcp__plugin_ruflo-core_ruflo__*` rather
than the bare tool names the CLI track uses.

### If the remote GitHub server is blocked

Some networks block `api.githubcopilot.com`. Swap the `github` entry in
`.mcp.json` for the local server instead:

```json
"github": {
  "command": "docker",
  "args": ["run", "-i", "--rm",
           "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
           "ghcr.io/github/github-mcp-server"]
}
```
