# Tools

Small, single-purpose scripts that replace repeated multi-step lab work, built from the daily lab digest (`hyperbeam lab digest --today`).
**Rule for every agent: before multi-step lab work, check this list (`hyperbeam tool --list`) for a tool that does it, and use it
(`hyperbeam tool NAME [ARGS]`) instead of redoing the steps.** Tools run in the lab, in the current project's synced copy; each has a test
(`hyperbeam tool --test NAME`). The sidebar runs every tool's test once a day (the first start) and a failing one turns the hyperbeam row red;
the digest shows how often each tool was used, how often it failed, and work it replaces that was done by hand.

A tool lives in `tools/<name>/<name>` with `tools/<name>/test`. New ones come from the digest, proposed by Claude and approved by the user
(TOOLS_PROPOSE.md). One line each: **name** - usage - the work it replaces.

## Tools
- **test-timing** - `hyperbeam tool test-timing "npx vitest run --maxWorkers=1" "npx vitest run"` - timing test runs by hand: prints wall time, average cores busy and exit code per command, so a suite stuck on 1 core of 20 shows at once (Go)
