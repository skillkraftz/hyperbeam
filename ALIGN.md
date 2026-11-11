# Align a project with hyperbeam

hyperbeam is the system; projects are brought in line with it, they do not override it. A project may differ from RULES.md **only** where its
CLAUDE.md has a section `## Exceptions to hyperbeam rules` that lists each exception and why, approved by the user.
You are Claude Code in the project's directory. Read `.hyperbeam/RULES.md` (or ~/projects/hyperbeam/RULES.md) first. The project's real state is
in the "Alignment facts" at the bottom of this prompt; check anything else yourself (read-only: `gh`, `git`, the files). Never print secret values.

## 1. Compare
Compare the project's CLAUDE.md, README and docs/ against RULES.md **and against the real repo state**:
- **Stale or wrong claims**: anything a doc says that the repo contradicts. Example: CLAUDE.md says the repo is not public but `gh` says it is
  public (check the facts; the lines that claim public/private are listed).
- **Rules**: does CLAUDE.md import `@.hyperbeam/RULES.md`? Does it say anything that conflicts with a rule (branch/PR workflow, testing, secrets,
  steno files, README upkeep, final report)? Is there a PRIVATE.md for the real secrets, and does .gitignore cover exactly those?
- **Docs layout**: CLAUDE.md = how the project works now (setup, run, test, layout); docs/DECISIONS.md = design decisions (newest first: date,
  decision, why, what was rejected). Does DECISIONS.md exist? Is any decision text elsewhere?
- **Existing doc structures** (for example docs/product-model.md, ADR folders, SPEC.md, design notes): say what each is, and propose how it fits.
  Options: keep it as is and link it from CLAUDE.md; split what is a decision (dated, with a why) into DECISIONS.md and leave the rest; or move it.
  Do not pick for the user: give a recommendation and the alternative, one line each.
- **Tests**: how they run; which need Docker (those cannot run in the lab: propose listing them as an exception, with the reason), which need a browser
  or a GPU, which start servers (they must use a free port or the lab range `$LAB_PORT_MIN`-`$LAB_PORT_MAX`, never a project port 3100+).
- **Hygiene**: steno files ignored, `.hyperbeam` not committed, README matches how the project behaves now.

## 2. Propose, then wait
Write the proposal as a list. Each difference gets: what you found (with file:line), and either
- **change the project** (what you would edit), or
- **record an exception** (draft the line for `## Exceptions to hyperbeam rules`: the rule, what the project does instead, and the reason).
Mark the ones where the user must decide (for example how an existing decisions doc relates to DECISIONS.md). Show the list and **stop and wait for approval.**
Nothing is changed before that.

## 3. After approval
Work in a worktree on a branch (`git fetch` first, branch from up-to-date main, never stack): `git worktree add -b align ~/.cache/hyperbeam-work/<project>-align main`
(the project's own rules win if they say otherwise and the user approved that). Make exactly the approved changes, including the `@.hyperbeam/RULES.md`
import and the Exceptions section if any. Test in the lab (`hyperbeam lab run --why ...`), commit, push, open a PR with a manual test checklist, remove the
worktree, and report: branch, PR URL, what changed, what you could not do. Do not merge.
