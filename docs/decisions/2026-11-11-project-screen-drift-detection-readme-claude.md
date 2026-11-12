---
id: 2026-11-11-project-screen-drift-detection-readme-claude
status: implemented
prs: [22]
topic: ui
---
# Project screen, drift detection, README, Claude's default model

- **Decision:** a Project screen (modal, keys `i`/`j`, the Project (j) button) shows one project at a glance with its actions (Onboard, Edit manifest, Copy context/report, Info window, Mark as onboarded). Drift is detected without tokens: a fingerprint of the run-defining parts of the project (script names and commands, dependency names, compose services/images/ports, Makefile targets, .env.example variable names; not versions or lockfiles) is stored when the manifest is written or confirmed, compared on Open and Refresh, and a difference is a quiet note, never red. README.md, RULES.md "Working with the user" and IDEAS.md (also in the Copy context bundle) hold what a new chat was missing: the why, how the user works, the roadmap. `hyperbeam _hooks` sets Claude's global model to `opusplan`, once.
- **Why:** the repo is the memory, and a new chat reading the bundle was missing the purpose of hyperbeam and the roadmap. Drift is what makes a manifest wrong silently; a fingerprint finds it for free, Onboard fixes it.
- **Rejected:** a red drift alert (it is not an emergency); fingerprinting versions or lockfiles (noise on every install); resetting the model on every `_hooks` run (it would fight a manual `/model` choice); a YAML dependency for compose files (three facts are read by indentation instead).
