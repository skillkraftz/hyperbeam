---
id: 2026-11-15-no-automatic-prompts
status: implemented
prs: []
topic: work-loop
supersedes: [2026-11-09-beam-in-beam-out-saved-layouts, 2026-11-11-loud-problems-red-only-when-rare]
---
# hyperbeam never sends Claude a prompt by itself

- **Decision:** Starting a session types plain `claude --continue ... || claude` and nothing else. A service that fails or is slow makes the dot red (a finding) and writes `.hyperbeam/notes/YYYY-MM-DD-services.md` (the result and the last lines of its window); a project without a manifest is the same as any other. Gone: the red-problem popup and `_problem`, the `on_problem` setting (ignored in old configs), `cmd_entered`'s prompt logic (the tmux hook only refreshes the status segment now), `RECOVER.md`, `investigate_prompt`/`investigate_window`, the Fix button and `hyperbeam fix`, the Onboard button and key, the start check's "Start Claude to sort it out?" question. `ONBOARDING.md` and `ALIGN.md` stay as worker task files the manager sends (`hyperbeam work NAME ~/.local/lib/hyperbeam/ONBOARDING.md`, then `.../ALIGN.md`); they are written as worker tasks (no waiting for approval: the user's yes came first, ambiguity is settled and noted in the report/PR). The daily tool check and a failing tool test are a quiet note on the hyperbeam row, never a dot. The only prompt hyperbeam still types is the Update button's, after a click.
- **Why:** the manager sends work after the user's yes; a slow service must not start Claude on ONBOARDING + ALIGN, a popup that comes back on every session switch is noise, and a flaky tool test must not turn the hyperbeam row red.
- **Rejected:** keeping Onboard as a button that only writes the prompt into a file (the manager already sends the two files with `hyperbeam work`); keeping the popup as "once per problem" (the red dot and `kk` already show it).
