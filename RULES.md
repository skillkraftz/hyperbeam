# Rules for every project managed by hyperbeam
- Personal prototype: build the simplest thing that works for what was asked. No unrequested
  features, abstractions, versioning, or "future-proofing". If something more seems needed,
  say so in one line and ask.
- Security is light: repos are public by default. Gitignore only real secrets (.env, keys,
  tokens) and list them in PRIVATE.md with how to get them back. Never print secret values.
- Never commit steno-*.txt (personal dictation notes).
- Testing: ALL testing runs in the lab, including unit tests and headless browser suites. Never run test
  servers, kills or GUI apps as the user. Use `hyperbeam lab run`. Never touch the user's tmux sessions.
- Tests use the machine (20 cores, 64 GB): run them in parallel by default (the runner's automatic worker count: Playwright and vitest
  defaults, `pytest -n auto`). A config pinned to 1 worker needs a reason in CLAUDE.md. When you change the test setup, say how long the suite took.
- Give `hyperbeam lab run` a short `--why`. The lab shares the machine's network: use free ports (bind port 0,
  or `$LAB_PORT_MIN`-`$LAB_PORT_MAX`), never 3100+ project ports. Docker-based tests are not run in the lab;
  list them as an exception. The lab is shared with other projects: stop only your own runs
  (`hyperbeam lab stop`); never run `hyperbeam lab reset` (user only).
- Before multi-step lab work, check TOOLS.md (`hyperbeam tool --list`) for a tool that does it, and use it
  (`hyperbeam tool NAME`) instead of redoing the steps.
- Branch from an up-to-date main (`git fetch` first). Never stack a PR on another PR.
- After `gh pr create` (and after a merge or close) run `hyperbeam refresh-prs NUMBER` (the PR number; no number after a merge): the sidebar's
  Merge button then shows within seconds instead of minutes.
- Work on a branch per task. Commit, push, open a PR. End the PR description with a short
  manual test checklist. Don't merge unless the user says so.
- If you change user-facing behaviour, update the README in the same PR.
- Final message: branch, PR URL, what changed, what you tested and how, what's untested, what
  the user should test.
- Notes about problems the user must handle (e.g. a leaked key and how to rotate it) go in
  .hyperbeam/notes/<date>-<topic>.md.
- Keep CLAUDE.md describing how the project works now (setup, run, test, layout). Update it
  in the same PR as any change to those.
- Record design decisions in docs/DECISIONS.md, newest first: date, decision, why, what was
  rejected. Create the file if missing. Update it in the same PR as the decision.
- Exceptions to these rules are allowed only in the project's CLAUDE.md, in a section `## Exceptions to
  hyperbeam rules` that lists each exception and why, approved by the user. Otherwise the project follows
  this file; if the project's CLAUDE.md disagrees, the project is brought in line (see ALIGN.md).
- Manual test checklists use real, runnable commands. No placeholders (no `...`, no `<name>`).
- Never run `git worktree remove --force` or delete a worktree that has uncommitted changes. Commit or stash
  first.

## Working with the user
- The user often dictates: messages are long and loose. Extract the intent and follow his actual
  design. Read the existing docs before proposing. Don't invent structure, UI flows or strict
  rules.
- Keep answers direct. Ask at most a few questions, each with a recommended default.
- He runs commands literally: no placeholders.
- He works mostly by mouse and voice (RSI): prefer visible buttons over keys to memorize.
- He is on a Claude Pro plan with 5-hour limits. Be economical: read what you need, prefer
  existing scripts and tools over long exploration, don't re-run expensive suites without a
  reason.
- Planning happens in plan mode (opusplan: Opus plans, Sonnet implements).
- Every project provides the same verbs: `install`, `update`, `test`, `version`, `help` (and `restart` for its services), run as `hyperbeam NAME VERB`.
  hyperbeam supplies defaults from what is in the folder (pnpm/npm/uv/pip/cargo); when the default doesn't fit, add the real thing (a package.json script,
  a Makefile target, or `[commands]` in the manifest) in the same PR. A prototype that is becoming a project gets these first.
- Build it conforming: anything you build as a CLI or app has, from the first commit, `--version`, `help`, and a documented `update` and `install`
  path; a web app answers `/version` (or shows its version in the footer). The project has a command named after itself, or a package.json
  script / Makefile target / `[commands]` entry, answering the standard verbs above. Keep it the simplest thing that works. New project:
  `hyperbeam new NAME --cli|--web` starts from this skeleton.
