# Audit the whole project

You are Claude Code in plan mode, a fresh session started for an audit. A review looks at the PRs merged since the last one; this looks at **everything**:
what the project does, where it has gaps, and where code, decisions or docs have grown faster than they were cleaned up (duplicated checks, two ways of doing one thing,
leftovers of earlier approaches, docs that say the same thing in several places and have drifted, tests that guard nothing). The aim is ideas in, good code out, saving
tokens without poor code. The facts and a snapshot (CLAUDE.md, decisions index, IDEAS.md, last review, recent history, what the previous session last said) are at the
bottom. You have no chat history; read what you need, and use subagents for broad reading.

The audit has five steps. **Nothing is changed in the project before step 4, and step 4 starts only after the user has triaged the findings in step 2.**

## Step 1: Read and list (plan mode, read-only)
Read in this order: README.md, CLAUDE.md, docs/DESIGN.md and docs/SYSTEM.md (if there), the decisions index and any decision that looks contradicted, IDEAS.md, then the
code area by area (follow the layout in CLAUDE.md), the tests, and the prompts and hooks. For each area write down what it does in one line, then look for:
- **Redundancy**: the same check or rule in two places; two helpers for one job; stacked layers that parse or decide the same thing in different ways.
- **Leftovers**: code, flags, files or docs of an approach that was replaced; decisions still `implemented` that a later one replaced.
- **Contradictions and drift**: docs that disagree with each other or with the code; numbers and names that changed.
- **Bugs and gaps**: behaviour that cannot do what the docs promise; a case nothing handles; state that is written and never read.
- **Missing tests**: anything checked only by hand, or tests that pass on the code they should guard against.
- **Too big or unclear**: a function or file nobody can hold in their head; a document that repeats another one.
Write each finding as: an id (A1, A2...), area, where (file and function or line), what and why it is a problem, kind (one of the above), size (S: minutes, M: one small PR, L: several),
what it depends on, and your recommendation (fix, defer with a reason, or accept as it is). Also list **"Looked at and fine"**, so the next audit does not look again.
Put the findings in your plan, grouped by area, and call ExitPlanMode. Do not start fixing.

## Step 2: Triage with the user
Go through the groups with the user (AskUserQuestion, a few questions each with your recommended default): for each finding, **fix now**, **defer** (it goes to IDEAS.md `## Open` with the reason) or
**accept** (it stays as it is; the reason is written down). Record the decisions. Ask only where the choice is the user's: take the obvious one and say so otherwise.

## Step 3: Write the findings down
On a branch from an up-to-date main, write `docs/audits/YYYY-MM-DD.md`: front matter (`through:` the commit audited, `findings:` the count), the findings with their status (`open`,
`fixed in PR #N`, `deferred`, `accepted: why`), and "Looked at and fine". Add the deferred ones to IDEAS.md. Open a docs-only PR `Audit: findings and triage`. Do not merge it.

## Step 4: Fix, in small PRs
Group the "fix now" findings by area and order them by what depends on what. One branch and one PR at a time, each from an up-to-date main (never stack a PR on a PR), each small enough
to review: the change, tests in the lab, a decision record in the same PR (superseding and collapsing the ones it replaces; `hyperbeam tool decisions check` must pass), the docs it touches
(README, CLAUDE.md, docs/REFERENCE.md, docs/DESIGN.md, docs/SYSTEM.md), and the findings' status in the audit file. Prefer deleting and simplifying over adding. No new features. Tell the user
which PR is next when one is merged; the user merges.

## Step 5: Close
The audit is done when every finding is `fixed`, `deferred` (in IDEAS.md) or `accepted` (with the reason) and the user says so. Then, in one last small PR: write the review record
`docs/reviews/YYYY-MM-DD.md` (`through:` the last merge commit it covered, `prs:` the audit's PRs, what was refactored, which docs were updated, which decisions were superseded, what was left alone),
regenerate the decisions index (`hyperbeam tool decisions index > docs/DECISIONS.md`), move the audit item in IDEAS.md to Done, and report: what was found, fixed, deferred and accepted.
End with the words **"Audit done."**
