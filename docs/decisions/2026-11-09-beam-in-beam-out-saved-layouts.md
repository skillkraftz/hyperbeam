---
id: 2026-11-09-beam-in-beam-out-saved-layouts
status: implemented
prs: [8, 9]
topic: unsorted
---
# Beam in / beam out: saved layouts, start check, wrap-up check, Done

- **Decision:** layouts are saved per project and restored on Open (asked); a start check and a wrap-up check report git state and obvious secrets (file, line, pattern, never the value); Claude is started to fix things only when the user says yes. Stop and Done run the wrap-up check first.
- **Why:** sessions end by crash or reboot, and work gets left uncommitted or unpushed.
