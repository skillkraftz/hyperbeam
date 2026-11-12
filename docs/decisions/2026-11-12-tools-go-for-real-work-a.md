---
id: 2026-11-12-tools-go-for-real-work-a
status: implemented
prs: [35]
topic: unsorted
---
# Tools: Go for real work, a daily check, usage and bypass in the digest

- **Decision:** tools that do real work are written in Go (`tools/<name>/main.go`, built by `hyperbeam tool` when the source changes; the binary is gitignored); bash/python only for glue. The sidebar runs every tool's test once a day and turns the hyperbeam row red for a failing one. The digest shows per tool how often it was used and failed, and how often its work (`tools/<name>/replaces`) was done by hand. First tool: `test-timing` (wall time and cores busy per command).
- **Why:** tools are amortised over many runs, so a build step is cheap and a compiled tool is faster; a tool that silently breaks gets routed around by agents, which the user wants to see at the start of the day, not discover later.
- **Rejected:** bash/python-only tools (the old rule); Rust (not installed, Go is); building inside the lab (`tools/` is re-synced with `--delete` before every run, so the binary would be rebuilt each time).
