# PRIVATE.md

Things .gitignore keeps out of this public repo. One line each: where it lives, how to get it back.

Nothing is ignored in practice yet. The patterns below are guards for later.

- `.env`, `.env.*` (except `.env.example`): would live in this directory on the laptop. Recreate by hand from the service's own dashboard; never copy from another project.
- `*.pem`, `*.key`, `*.token`, `*secret*`, `id_*`, `credentials*`: would live in ~/.ssh or the service dashboard. Regenerate there.
- `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `*.log`, `*.swp`, `.DS_Store`: local junk. Rebuilt by the tools.

Not stored here by design: per-project manifests (kept outside the project repos, location decided in a later prompt).
