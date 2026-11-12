---
id: 2026-11-11-align-projects-to-the-system-the
status: implemented
prs: [19]
topic: unsorted
---
# Align projects to the system; the lab keeps synced copies and a run log

- **Decision:** projects follow RULES.md; a difference is allowed only as an approved entry in the project's `## Exceptions to hyperbeam rules`. Onboard runs the manifest step and then ALIGN.md (compare docs with the rules and the real repo, propose, wait, then change on a branch). All agent testing, including unit and headless browser suites, runs in the lab. Docker-based tests are not run there (docker group = root) and are listed as exceptions. The lab keeps one rsync-synced copy per project and its dependency caches; every `lab run` is logged (`--why`) to `lab-runs.jsonl`.
- **Why:** projects drift from the docs (a CLAUDE.md saying a public repo isn't public) and from each other; a lab that reinstalls everything each run is too slow to use for all testing; the log is the base for turning repeated lab work into small tools.
- **Rejected:** letting each project override the rules silently; Docker in the lab (root-equivalent); a network namespace for ports (needs privileges: `unshare -n` is denied), so the lab uses a port convention instead; copying `.git` and secrets into the lab.
