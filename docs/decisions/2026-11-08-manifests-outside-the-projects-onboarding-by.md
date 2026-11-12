---
id: 2026-11-08-manifests-outside-the-projects-onboarding-by
status: implemented
prs: [1, 2, 3]
topic: unsorted
---
# Manifests outside the projects; onboarding by Claude

- **Decision:** a project's manifest (`projects/<name>.toml`: ordered services, ready checks, fixed port, env) lives in this repo, not in the project. There is no heuristic drafting: Claude investigates, proposes the manifest and waits for approval (ONBOARDING.md). Manifests are committed straight to main.
- **Why:** the user does not want hyperbeam files in other repos; heuristics guessed wrong, Claude reads the project.
