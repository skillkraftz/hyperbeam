# Rules for every project managed by hyperbeam
- Personal prototype: build the simplest thing that works for what was asked. No unrequested
  features, abstractions, versioning, or "future-proofing". If something more seems needed,
  say so in one line and ask.
- Security is light: repos are public by default. Gitignore only real secrets (.env, keys,
  tokens) and list them in PRIVATE.md with how to get them back. Never print secret values.
- Never commit steno-*.txt (personal dictation notes).
- Testing: never run test servers, kills or GUI apps as the user. Use `hyperbeam lab run`.
  Never touch the user's tmux sessions.
- Work on a branch per task. Commit, push, open a PR. End the PR description with a short
  manual test checklist. Don't merge unless the user says so.
- If you change user-facing behaviour, update the README in the same PR.
- Final message: branch, PR URL, what changed, what you tested and how, what's untested, what
  the user should test.
- Notes about problems the user must handle (e.g. a leaked key and how to rotate it) go in
  .hyperbeam/notes/<date>-<topic>.md.
