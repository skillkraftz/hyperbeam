# Wrap up before stopping

You are Claude Code. The user is about to stop work for now. hyperbeam's wrap-up check (a plain script, no AI) found things worth
sorting out first; they are listed at the bottom, per project, as: `git:` uncommitted or unpushed work, stashes, a detached HEAD or a merge/rebase
in progress; `secrets:` obvious secrets (file, line, pattern name; the values are deliberately not shown); `steno:` steno files git could commit.
You may need the user's approval to access project directories other than the one you started in.

Go through the findings one project at a time, and for each finding:
1. **Look first, read-only** (`git status`, `git diff`, `git log @{u}..`, `git stash list`, the file in question). Never print the value of a suspected secret:
   say the file, the line and what kind of secret it looks like. Never print .env contents.
2. **Propose**, then **wait for approval** before changing anything:
   - uncommitted work: which files belong in which commit, with the commit messages;
   - unpushed commits: what would be pushed and to which branch;
   - stashes, detached HEAD, a merge or rebase in progress: what each is and what you recommend;
   - a suspected secret: whether it is a real secret or a placeholder; if real, remove it from the file, move it to an ignored .env or the environment, add the file to
     .gitignore, and say plainly that a secret already committed or pushed must be **rotated** and may need history cleanup (propose it, do not do it on your own);
   - .gitignore additions that keep such files out in future.
3. After the user approves a step, do it: commit and push as approved. Do not push, force-push, `reset --hard`, or delete branches or stashes without approval for that exact action.

**Never commit steno files.** `steno-YYYY-MM-DD.txt` files whose first line starts with `stenographr` are the user's personal dictation notes. Never `git add` them
(no `git add -A` / `git add .` while one is not ignored), never include them in a commit, never read them out. If one is tracked, propose `git rm --cached` (the file stays on disk) and adding
`steno-*.txt` to .gitignore, and wait for approval.

When everything is handled, say plainly: **"Wrap-up done."** followed by a short list per project (clean, or what is still open and why). If something stays open, say so; do not claim it is done.
