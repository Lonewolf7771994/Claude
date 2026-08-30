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

| Server  | Type  | How it runs                     |
| ------- | ----- | ------------------------------- |
| `ruflo` | stdio | `npx -y ruflo@latest mcp start` |
| `github`| http  | `https://api.githubcopilot.com/mcp/` |

### Setup

1. **GitHub token** — the GitHub server authenticates with a personal access
   token read from the environment (nothing secret is stored in this repo):

   ```bash
   export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
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

### Optional: the full Ruflo scaffold

The config above gives you Ruflo's MCP tools. The CLI install additionally
generates agents, hooks, skills and a daemon into your workspace:

```bash
npx ruflo@latest init wizard   # interactive
npx ruflo@latest init          # non-interactive
```

That writes `.claude/`, `.claude-flow/`, `CLAUDE.md` and helper files. The
generated runtime state is gitignored here; commit whatever parts of the
scaffold you want tracked.

### Optional: Claude Code plugins

A lighter path — slash commands and agent definitions, no workspace files:

```
/plugin marketplace add ruvnet/ruflo
/plugin install ruflo-core@ruflo
/plugin install ruflo-swarm@ruflo
```

Note that plugin tools are namespaced `mcp__plugin_ruflo-core_ruflo__*` rather
than the bare tool names the CLI track uses.
