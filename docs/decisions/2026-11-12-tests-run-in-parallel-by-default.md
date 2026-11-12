---
id: 2026-11-12-tests-run-in-parallel-by-default
status: implemented
prs: [34]
topic: lab
---
# Tests run in parallel by default; no lab CPU limits

- **Decision:** RULES.md: tests use the runner's automatic worker count, a single-worker config needs a reason in CLAUDE.md, and a change to the test setup reports the suite's time. ALIGN.md: onboarding times the suite and flags pinned worker counts; a suite still over ~2 minutes splits into a fast `test` and a slow script run before a PR.
- **Why:** projects ran tests on 1 core of 20, and dotwork's e2e takes minutes. The lab sets no CPU or memory limits, so the slowness is the projects' own configs.
- **Rejected:** a lab CPU/RAM cap or exported worker hints (adds machinery while nothing limits the lab today); an interactive "unit or e2e?" prompt in `test` (the Test button and agents run it unattended).
