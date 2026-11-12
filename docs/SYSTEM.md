# How hyperbeam works (the map)

One page to check against what you meant. Details are in `docs/REFERENCE.md`; the why is in `docs/decisions/`.
Marked **[gap]** = known difference between what was intended and what is built. **[planned]** = not built yet (see the end).

## The picture

```
 HOTKEY ─> sidebar window (kitty: menu left | tmux right)
            ├─ hyperbeam row (always first) = session "hyperbeam"
            │     home: Claude in ~/projects/hyperbeam + shell   [gap] layout NOT saved: after a reboot it is rebuilt as the default
            │     menu: the menu again (phone / SSH)
            └─ project row ── Open ──┐
                                     ▼
          no manifest? ──yes──> Onboard: ONBOARDING.md + ALIGN.md (plan, wait for approval, PR)
                │no
          saved layout? ──> "Restore last layout?" yes: windows + claude --continue (other panes: empty shells)
                │
          services start in order ─> start check (git, crash) ─> shell runs kk
                │                    red problem? → offer RECOVER.md
                ▼
          WORK: you + Claude (opusplan) on a branch → PR      [gap] the conversation never ends by itself
                │   lab runs every test, guard blocks dangerous commands
                │   dots: blue = waits for you, cyan = working; PR badge in the row
                ▼
          Merge (button): every open PR, oldest first, stops at a conflict → the project's `update` runs
                ▼
          Stop (one project): wrap-up check → clean: stop / not: WRAPUP.md
          Done (whole day):  1. lab digest → maybe "propose tools" (TOOLS_PROPOSE.md)
                             2. review due (5 merges since the last record) [gap] only projects that already have a record
                                → fresh plan-mode Claude, REVIEW.md, one cleanup PR
                             3. wrap-up check on every project touched → stop their sessions

 Background: minute recheck (dots, notes: drift, stale docs, review count, context size), PR poll,
 usage line (5h / week), daily tool check, layout save every 5 min (project sessions only).
```

## Which prompt runs where

| Prompt | When | What Claude does |
|---|---|---|
| ONBOARDING.md | Open without a manifest, a service failed, or Onboard | reads the project, starts it, proposes the manifest, waits for approval |
| ALIGN.md | right after ONBOARDING | compares the project with RULES.md, proposes changes, waits, then a PR |
| RECOVER.md | Open finds a red problem and you say yes | diagnoses read-only, proposes, waits |
| WRAPUP.md | Stop/Done finds uncommitted work, secrets, steno files | sorts them out before stopping |
| TOOLS_PROPOSE.md | Done, when the lab digest has candidates | proposes up to 3 small tools, waits |
| REVIEW.md | Done offers it (or `hyperbeam review`) | fresh plan-mode Claude proposes ONE cleanup PR, then does it |

Every injected prompt starts in plan mode (Opus plans, Sonnet builds).

## The review loop today
- A project is "in the loop" only when it has `docs/reviews/<date>.md`; only hyperbeam has one. For every other project nothing is counted or offered.
- After `review_after` (5) merged PRs since the record's `through` commit: a quiet note on the row, a line in `hyperbeam context`, and the offer at Done (once a day).

## Planned (not built; each PR updates this page)
1. **Layouts come back whole**: the hyperbeam session is saved too; panes remember the program that ran in them (not just Claude) and it is started again; the "Restore?" question goes away.
2. **Every project is in the review loop**: no record yet = count from onboarding; the offer also appears on Open, and the Project screen gets a Review button.
3. **Work loop, step 1**: when a project's Claude starts, a choice: Continue last conversation / Fresh plan session (START.md: read the state, bring it to a good state, propose the next 1-3 items) / Review (when due). The same choice after a Merge finishes a task, so a conversation has an end.
4. Later: a "presentable" check at the end of the day, the phone view, the sidebar redesign.
