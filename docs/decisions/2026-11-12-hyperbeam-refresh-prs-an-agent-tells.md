---
id: 2026-11-12-hyperbeam-refresh-prs-an-agent-tells
status: implemented
prs: [39]
topic: unsorted
---
# `hyperbeam refresh-prs`: an agent tells the sidebar about a new PR

- **Decision:** a plain command `hyperbeam refresh-prs [PROJECT] [NUMBER...] [--gone N...]` fetches the project's open PRs, writes the PR cache and signals the menus (SIGUSR2) to read it at once; the sidebar also reads the cache every 5 seconds. PR numbers given are looked up one by one (`gh pr view`). A PostToolUse hook on Bash runs it after any `gh pr create|merge|close`, so no agent has to remember. `install_hooks` also recognises its state hooks again (they had piled up to 26 copies).
- **Why:** the Merge button waited up to 6 minutes for the 5-minute cache, and Claude opens PRs in the background. `gh pr list --author` lags a few seconds behind a new PR, so a plain refresh right after `gh pr create` would miss it.
- **Rejected:** a lab tool (tools run as the lab user, which has no gh login); a 60-second TTL for running projects (more gh calls, still up to a minute late); a hook on `gh pr create` (gh has none).
