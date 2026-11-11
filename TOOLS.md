# Tools

Small, single-purpose scripts that replace repeated multi-step lab work, built from the daily lab digest (`hyperbeam lab digest --today`).
**Rule for every agent: before multi-step lab work, check this list (`hyperbeam tool --list`) for a tool that does it, and use it
(`hyperbeam tool NAME [ARGS]`) instead of redoing the steps.** Tools run in the lab, in the current project's synced copy; each has a test
(`hyperbeam tool --test NAME`), and the digest runs them all and flags a failing one.

A tool lives in `tools/<name>/<name>` with `tools/<name>/test`. New ones come from the digest, proposed by Claude and approved by the user
(TOOLS_PROPOSE.md). One line each: **name** - usage - the work it replaces.

## Tools
(none yet)
