# Propose small tools from the lab digest

hyperbeam turned today's lab runs into a digest (below). Repeated multi-step lab work costs tokens and time every time an agent redoes it.
A tool is a small, single-purpose script that does that work in one command, with a test. You are Claude Code in the hyperbeam session.
Read RULES.md and TOOLS.md first (`hyperbeam tool --list`): do not propose what an existing tool already does.

## 1. Propose (at most 3)
From the digest's tool candidates, flaky commands and "where the time went" list, propose **at most 3** tools. Both lists are ordered by total time
(count x duration): start from the top, because six 15-minute runs cost more than one 45-minute run. For each:
- **The work it replaces**: the exact repeated commands or sequence, and how often it ran.
- **Its usage line**: `hyperbeam tool NAME [ARGS]`, with a real example.
- **What it saves**: time per run, and tokens (the output an agent no longer has to read, the steps it no longer has to plan). A tool must save real time or
  tokens on every use; one that saves milliseconds is not worth its upkeep.
Skip candidates that are not worth a tool (one-off, already one short command, or the repetition was a real fix-and-retry loop, not a pattern).
If nothing is worth a tool, say so in one line and stop. Then **stop and wait for approval**. Nothing is built before the user says which ones.

## 2. After approval
Work on a branch from an up-to-date main in hyperbeam's dev folder (`git fetch`, `git switch -c tools-<name> origin/main`); a git worktree only if the checkout has other work.
For each approved tool, create `tools/<name>/`:
- The language: **Go** for a tool that does real work (runs, measures, parses or waits on things): `tools/<name>/main.go` + `go.mod` + a `.gitignore`
  with `/<name>`; `hyperbeam tool` builds it when the source is newer than the binary (the build step is fine: it is paid once). bash or python3
  (stdlib only, `set -euo pipefail` for bash) only for thin glue around a few commands. It answers `--help` and `--version`.
- `tools/<name>/<name>`: the executable (built from Go, or the script). It runs in the lab as hblab, in the
  current project's synced copy (the working directory); `$HB_TOOLS` is the tools folder, `$HB_LAB=1`. It prints little: the result and, on failure,
  the few lines that explain it. Free ports only (`$LAB_PORT_MIN`-`$LAB_PORT_MAX` or port 0). It never touches the user's sessions or home.
- `tools/<name>/test`: an executable test that exits 0 on success. It must be self-contained (make its own scratch files under a temp dir).
- `tools/<name>/replaces` (optional): one regular expression per line matching the commands the tool replaces. The digest counts lab runs that match
  but did not go through the tool ("done by hand": agents bypassing it).
- one line in `TOOLS.md`: `- **name** - usage line - the work it replaces`.
Test each in the lab: `hyperbeam lab run --why "test tool NAME" -- hyperbeam tool --test NAME`, or run `bash tools/<name>/test` through `hyperbeam lab run`.
Commit, push, open a PR with a manual test checklist of real commands, and report: branch, PR URL, the tools, what they save, what is
untested. Do not merge. Add a decision record (docs/decisions/, see RULES.md) only if a real design decision was made.
