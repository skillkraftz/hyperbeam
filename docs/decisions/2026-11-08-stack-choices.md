---
id: 2026-11-08-stack-choices
status: implemented
prs: [1, 2]
topic: unsorted
---
# Stack choices

- **Decision:** one uv script with Textual declared inline; Claude Code is the default agent; one tmux session per project; fixed ports per project through tmux session env (no direnv); the app runs on the host, backing services through docker compose.
- **Why:** a personal prototype: simplest thing that works, nothing to install.
- **Rejected:** a packaged app; direnv; containerizing every app.
