# How hyperbeam works (the map)

One page to check against what you meant. The walk through it, part by part, is `docs/DESIGN.md`; every detail is in `docs/REFERENCE.md`; the why is in `docs/decisions/`.
Marked **[gap]** = known difference between what was intended and what is built. **[planned]** = not built yet (see the end).

## The picture

```
 HOTKEY ─> sidebar window (kitty: menu left | tmux right)
            ├─ hyperbeam row (always first) = session "hyperbeam"
            │     home: Claude in ~/projects/hyperbeam + shell   layout saved, restored after a reboot
            │     menu: the menu again (phone / SSH)
            └─ project row ── Open ──┐
                                     ▼
          saved layout? ──> restored without asking: windows, panes, their programs
                │
          services start in order ─> start check (git, crash) ─> shell runs kk
                │                    failed service? → red dot + a note, nothing sent to Claude
                ▼
          Claude starts: continues its last conversation (fresh if none), no question
                ▼
          WORK: you + Claude (sonnet) on a branch → PR
                │   lab runs every test, guard blocks dangerous commands
                │   dots: blue = waits for you, cyan = working; PR badge in the row
                ▼
          Merge (button): every open PR, oldest first, stops at a conflict → the project's `update` runs
                ▼
          Stop (one project): wrap-up check → clean: stop / not: stop anyway or cancel
          Done (whole day):  wrap-up check on every project touched → all clean: stop their sessions / else list what is unclean

 Background: minute recheck (dots, notes: drift, stale docs, context size), PR poll,
 usage line (5h / week), daily tool check, layout save every 5 min (every session, the hyperbeam one too).
```

## Which prompt runs where

| Prompt | When | What Claude does |
|---|---|---|
| ONBOARDING.md | the manager sends it (`hyperbeam work NAME ~/.local/lib/hyperbeam/ONBOARDING.md`) after your yes | reads the project, starts it, writes and commits the manifest |
| ALIGN.md | the manager sends it the same way | compares the project with RULES.md, makes the changes in a PR |

hyperbeam never sends a prompt by itself.

Every injected prompt starts in plan mode (Opus plans, Sonnet builds).

## Planned (not built; each PR updates this page)
1. ~~Layouts come back whole~~ (built: the hyperbeam session is saved too; panes remember their program and start it again; no "Restore?" question).
2. ~~Work loop, step 1~~ (built, then cut: Open continues the last conversation; the manager plans and starts workers).
3. Later: a "presentable" check at the end of the day, the phone view, the sidebar redesign.
