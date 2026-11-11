# Rules for every project managed by hyperbeam
- Personal prototype: build the simplest thing that works for what was asked. No unrequested
  features, abstractions, versioning, or "future-proofing". If something more seems needed,
  say so in one line and ask.
- Security is light: repos are public by default. Gitignore only real secrets (.env, keys,
  tokens) and list them in PRIVATE.md with how to get them back. Never print secret values.
- Never commit steno-*.txt (personal dictation notes).
- Testing: ALL testing runs in the lab, including unit tests and headless browser suites. Never run test
  servers, kills or GUI apps as the user. Use `hyperbeam lab run`. Never touch the user's tmux sessions.
- Give `hyperbeam lab run` a short `--why`. The lab shares the machine's network: use free ports (bind port 0,
  or `$LAB_PORT_MIN`-`$LAB_PORT_MAX`), never 3100+ project ports. Docker-based tests are not run in the lab;
  list them as an exception. The lab is shared with other projects: stop only your own runs
  (`hyperbeam lab stop`); never run `hyperbeam lab reset` (user only).
- Branch from an up-to-date main (`git fetch` first). Never stack a PR on another PR.
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
