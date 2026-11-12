---
id: 2026-11-12-lab-setup-is-the-users
status: implemented
prs: [46]
topic: lab
---
# The lab's setup is the user's; no lab inside the lab; error messages state facts

- **Decision:** agents never run `lab/setup.sh`, `remove.sh` or `podman-setup.sh` and never use sudo (except `sudo -n -l`); the guard blocks them. A lab command (`tool`, `lab`, `shot`, `NAME test`) inside `hyperbeam lab run` is blocked by the guard, and `lab_ready` refuses it when `HB_LAB=1`. The lab's error messages say what failed and that the setup is the user's; none says to run the setup script. When the lab fails, an agent checks read-only (`lab status`, `id hblab`, `df /srv/hblab`, the end of lab-runs.jsonl), reports, and asks. CLAUDE.md and RULES.md say so.
- **Why:** on 2026-11-12 an agent wrapped `hyperbeam tool decisions check` in `hyperbeam lab run`. Inside the lab hblab has no sudo, so the check printed "sudo may not run commands as hblab ... run setup.sh again", and the agent told the user to rerun a root script on a machine that was fine (100G image, hblab, sudoers rule and podman set up the night before). The setup scripts change /etc, the user's mounts and accounts, so they must not be suggested on the strength of an error.
- **Rejected:** letting hblab sudo to itself (it would widen the lab user for a mistake of the caller); only fixing the message (the next wrong call would find another way to look broken); asking agents to read the setup script before suggesting it (the script is not the problem).
