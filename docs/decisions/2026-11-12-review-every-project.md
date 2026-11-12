---
id: 2026-11-12-review-every-project
status: implemented
prs: [51]
topic: review
---
# Every onboarded project is in the review loop: counted from onboarding, shown on Open, a Review button

- **Decision:** a project with no `docs/reviews/` record counts merged PRs from its onboarding (the fingerprint date: the last commit of the default branch at that time, else the root commit). The first review writes the record and the normal count follows. The note ("N of 5 PRs since onboarding", "review due ...") is part of the start check, so Open prints it; the Project screen has a **Review** button that starts the review now; Done keeps offering it once a day. A project never onboarded is in no loop.
- **Why:** the review pass was meant for every project, but `reviews_due` returned nothing without a record, so only hyperbeam (the only project with one) was ever counted or offered a review. Onboarding is the moment hyperbeam starts managing a project, so it is the natural zero.
- **Rejected:** counting from today for every project (loses what was merged since onboarding); a starting review of the whole history on first Open (too big, and not what the loop is for); offering only at Done (the user works in a project for days before Done).
