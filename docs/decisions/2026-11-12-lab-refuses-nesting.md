---
id: 2026-11-12-lab-refuses-nesting
status: implemented
prs: [46, 53]
supersedes: [2026-11-12-lab-setup-is-the-users]
topic: lab
---
# The lab's setup is the user's; the lab refuses nesting itself; error messages state facts

- **Decision:** agents never run `lab/setup.sh`, `remove.sh` or `podman-setup.sh` and never use sudo (except `sudo -n -l`); the guard blocks them. The lab's error messages say what failed and that the setup is the user's; none says to run the setup script. When the lab fails, an agent checks read-only (`lab status`, `id hblab`, `df /srv/hblab`, the end of lab-runs.jsonl), reports, and asks. A lab command (`tool`, `shot`, `NAME test`, `lab run|status|stop|reset`) inside `hyperbeam lab run` is refused **by the lab**, not the guard: everything a lab run starts has `HB_LAB=1`, and `lab_ready` and `cmd_tool` print `LAB_NESTED` (what happened, that nothing needs changing, what to do) and exit 2. The guard has no nesting rule.
- **Why:** on 2026-11-12 an agent wrapped `hyperbeam tool decisions check` in `hyperbeam lab run`; inside the lab hblab has no sudo, so the check printed a sudo error and the agent told the user to rerun a root script on a machine that was fine. PR #46 fixed it twice: a clear refusal in the lab and a guard rule that searched the command's text. The second copy fired on file contents, PR bodies and edit scripts that merely mentioned the words (five false blocks in one day) while the lab's refusal, at the moment of the real mistake, already did the job. One check, in the place where the mistake happens.
- **Rejected:** a smarter guard rule that parses the real commands (still a second copy of a check the lab makes); letting hblab sudo to itself (widens the lab user for a mistake of the caller); asking agents to read the setup script before suggesting it (the script is not the problem).
