---
id: 2026-11-15-sonnet-default-and-manager-workers
status: implemented
prs: [57]
topic: claude
supersedes: [2026-11-12-injected-prompts-start-in-plan-mode]
---
# Sonnet by default; the manager plans, and starts workers

- **Decision:** `claude_model` defaults to `sonnet`; `opusplan` stays a choice in Settings. Injected prompts (`inject_prompt`, `write_prompt`, `claude_base(plan=True)`, the review/audit prints and the guard's review rule) start in plan mode only when the configured model is `opusplan` (`plans_first()`); otherwise they start normally. `~/.claude/settings.json`'s `model` is moved from `opusplan` to `sonnet` once (marker `claude-model-sonnet`; a later manual choice is left alone). The manager (the first row) plans with the user; after the user says yes to a piece of work in that conversation it runs `hyperbeam work NAME PROMPT_FILE`: tmux session `claude-NAME`, a fresh Claude with `WORKER.md` + the prompt, `HB_WORKER=1`, no services, one per project (it edits the folder the user's services run from). `hyperbeam wait` blocks until the Stop hook's state says finished and prints the report path; `hyperbeam close` ends only `claude-NAME`. At Stop with `HB_WORKER=1` the hook also writes `reports/<date-time>-<slug>.md` (task, final message, branch, commits, PR, transcript). The sidebar marks a project with a running worker (`»`); `claude-*` sessions are not projects.
- **Why:** planning moved to the manager conversation, and every project Claude started in plan mode and waited for an approval nobody could give a worker. **Workers are started only by the manager after the user said yes; hyperbeam never starts Claude work by itself** (the earlier rule, kept).
- **Rejected:** a worker per project session window (it would share the user's Claude state and dot: the worker has its own `HB_STATE` subfolder); several workers per project (two Claudes in one folder); `wait` polling the transcript (the Stop hook state already exists); `--continue` for workers (each task starts clean).
