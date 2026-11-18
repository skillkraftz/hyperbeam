---
id: 2026-11-18-update-runs-own-update
status: implemented
topic: verbs
prs: []
---

# `NAME update` runs the project's own update and measures from the last recorded commit

## Decision
`verb_update` (hb/verbs.py) pulls as before, then, if the project has its own `update` (manifest `[commands]`, package.json script, Makefile target), runs it whenever any file changed; a failure says so and returns 1. Without one, today's behaviour (install only if a lockfile changed). Changes are measured from the commit stored in `<project data>/updated-commit` (written after a successful update or install), else Merge's `since`, else the HEAD before the pull. Services are restarted as before.

## Why
daybeam (`uv tool install` plus a systemd service, Makefile `update`) kept running old code after Merge: the lockfile check skipped the project's own update, and a pull by the manager before `update` made "what changed" empty.

## Rejected
- Always measuring from the pre-pull HEAD: misses changes someone else already pulled.
- Running the project's update on every call: slow and noisy when nothing changed.
