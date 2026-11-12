---
id: 2026-11-11-loud-problems-red-only-when-rare
status: implemented
prs: [14]
topic: ui
---
# Loud problems, red only when rare

- **Decision:** the dot is red only for a down service, secrets in unpushed commits, or a stuck merge with conflicts; everything else is a quiet note. Red shows a popup on entry (or sends RECOVER.md with `on_problem = "auto"`).
- **Why:** problems must not be missed, but constant red teaches the user to ignore it.
