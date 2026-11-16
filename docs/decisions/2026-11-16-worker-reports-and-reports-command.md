---
id: 2026-11-16-worker-reports-and-reports-command
status: implemented
topic: workers
prs: []
---

## Decision
A worker run has one report: its name has seconds and is kept in `started.json`, so later Stops (after `send`) rewrite it and the earlier final messages move to an "Earlier rounds" section. Commits are those on branches the worker created or moved (refs recorded at start, compared at Stop). `hyperbeam reports` lists the reports with tokens, calls, active minutes and lab seconds, and a total. The old `hyperbeam report` is now `hyperbeam copy-last` (button "Copy last").

## Why
The manager reads reports to decide what is next and the user wants to see what a stretch of work cost. Minute-resolution names overwrote, every Stop wrote a report, and `git log --all --since` listed other people's merges.

## Rejected
- Filtering commits by author: a worker commits as the user. Refs at start say exactly what moved.
- Deleting the stray test report from `update`: it would be a one-off hack in the code for one file.
