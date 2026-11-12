---
id: 2026-11-11-cheaper-context-fitting-modals-verify-opens
status: implemented
prs: [27]
topic: unsorted
---
# Cheaper context, fitting modals, verify opens the PR, Docker in the lab

- **Decision:** hyperbeam's CLAUDE.md is cut from 66 KB to 8 KB (the rules, a map and the command list); the detail lives in `docs/REFERENCE.md`, read on demand and never imported. `hyperbeam context --size` shows what each part costs. Modals fit the screen and stack their buttons, Settings labels are short enough for 35 columns. `hyperbeam verify merge` opens the throwaway PR itself so the user only clicks Merge; `ignore_owners` in the user config takes an owner (algoviewz) out of the badge, Merge and verify. Rootless podman works in the lab through two shims (`podman`, `docker`) with one stable runtime dir under /tmp; compose with host networking works, compose's own networks need a user dbus (open).
- **Why:** in a 5-hour window ending at the usage limit there were 642 requests, 0.8M output tokens and 128M cache-read tokens: the cost is context size times requests, and CLAUDE.md is in every request. The two 35-column bugs hid buttons the user needs. verify had pushed work onto the user that the agent used to do.
- **Rejected:** `@docs/REFERENCE.md` in CLAUDE.md (it would load it again); a per-run podman runtime dir (breaks the second run); giving hblab the docker group; a systemd user session for hblab before a project needs it.
