---
id: 2026-11-16-lean-workers
status: implemented
topic: work-loop
prs: []
---

# Workers start without MCP servers, plugins and skills

## Decision
`hyperbeam work` starts Claude with `worker_flags()`: `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`, `--disable-slash-commands`, and `--settings` switching off every plugin enabled in the user's `~/.claude/settings.json`. The user's own sessions and the manager are unchanged. `WORKER.md` adds three habits: Edit/Write instead of python/sed rewrites, a flaky test is rerun at most twice then reported, no `sleep`.

## Why
The skill listing, deferred tools and MCP text were ~18k tokens of start context that every call re-reads; workers use none of it.

## Rejected
An `--agents` override (the agent list came from plugins, so it goes with them); `--bare` (it skips hooks, which workers need).
