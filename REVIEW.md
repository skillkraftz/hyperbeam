# Review the work since the last review

You are Claude Code in the project's session, in plan mode. A number of PRs were merged since the last review (the facts are at the bottom: the PRs with the
files each changed, decision records added, the ideas lists, and the last review record). Fast work layers up: this is the pass that checks it as a whole
and fixes it in **one** cleanup PR, so the next session starts from something simple and correct.

## 1. Look (read-only), then propose
Read the diff of what was merged (`git diff <since>..origin/main`, the files named below), the project's CLAUDE.md and README, and the decision records. Look for:
- **Duplicated or grown code**: the same thing done twice, functions whose parameters keep growing, two mechanisms doing one job.
- **Hacks**: state passed between functions by stuffing it into a dict, fragile strings (a program inside a quoted string), dead code, leftovers of an earlier approach.
- **Missing tests**: anything that was only checked by a throwaway script. Persist those checks as real tests in the project's test folder and make sure
  `hyperbeam NAME test` runs them in the lab.
- **Docs that no longer match the code**: README, CLAUDE.md, docs/REFERENCE.md and anything else the refactor touches; screenshots that changed.
- **Decisions that replaced each other**: set `status: superseded` on the old record with `collapsed_into` (a decision id) and/or `code` (where it now lives),
  and `supersedes` on the new one; give `topic: unsorted` records a topic. `hyperbeam tool decisions check` must pass.
- **IDEAS.md**: items that are done but still in `## Open` (move them to `## Done` with the PR number and decision id); new ideas that came up (add to Open).

Write the proposal as a short list: what you found (file and line), what you would change, and which docs you would update. Prefer deleting and simplifying
over adding. Say what you would leave alone and why. **Then stop and wait for approval.** Nothing is changed before that.

## 2. After approval
Work on a branch from an up-to-date main, in the project's own folder (a git worktree only if the checkout has other work). Make exactly the approved changes.
Test in the lab (`hyperbeam lab run --why ...`; see the project's CLAUDE.md for the test command). Then:
1. Write the review record `docs/reviews/YYYY-MM-DD.md`, front matter `through:` (the last merge commit this review covered, short hash), `prs:` (the numbers),
   `refactored:` / `docs_updated:` / `decisions_superseded:` (what changed, one line each), then a few lines of prose.
2. Regenerate the decisions index: `hyperbeam tool decisions index > docs/DECISIONS.md`.
3. Open one PR titled `Review: PRs #A to #B` whose description lists the same, with a manual test checklist. Do not merge it.
4. Report: branch, PR URL, what changed, what you tested, what is untested. End with the words **"Review done."** once the PR is open.
