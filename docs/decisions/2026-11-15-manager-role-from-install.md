---
id: 2026-11-15-manager-role-from-install
status: implemented
prs: []
topic: manager
---
# The manager's role ships with hyperbeam; ~/manager is the user's notes

- **Decision:** `manager_cmd` starts Claude with `--append-system-prompt-file <installed hyperbeam>/manager/CLAUDE.md`, so the role is read at every start and a Merge + update changes it. `ensure_manager_dir` no longer copies `manager/CLAUDE.md`; once, it removes a `~/manager/CLAUDE.md` that is a full copy of the role (same first line); a file the user wrote is left alone. The notes (`now.md`, `hyperbeam.md`, `projects/`, `inbox/`, `outbox/`) are never touched and committing stays with the manager.
- **Why:** the copy was made once and never updated, so every role change (PR #57's Workers section) needed a hand copy and it had already drifted.
- **Rejected:** an `@` import in ~/manager/CLAUDE.md (a file outside the folder needs an approval prompt and leaves a stub to migrate); overwriting the copy on update (would clobber user edits).
