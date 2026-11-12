---
id: 2026-11-11-verify-command-sidebar-screenshots-rootless-podman
status: implemented
prs: [25]
topic: lab
---
# Verify command, sidebar screenshots, rootless podman

- **Decision:** GitHub features are assumed to work and are verified by the user with one command, `hyperbeam verify` (PASS/FAIL/YOU with the exact commands); the lab gets no GitHub credentials for now. Docker in the lab is investigated through rootless podman (no docker group, no root) behind one sudo script and a decision gate in docs/PODMAN.md, with a libvirt VM as the fallback. The sidebar is designed from pictures: `hyperbeam shot` renders the real menu in the lab at a chosen width (35 laptop, 42 phone) and brings the PNGs back; docs/UI.md records the constraints and what breaks at 35 columns, which starts the redesign phase earlier than planned.
- **Why:** the user will test GitHub personally, a fake gh already covers the logic, and a lab with credentials was the wrong thing to build first; Docker-based projects (algoviewz-platform) are the real blocker; the 35-column menu has hidden buttons and clipped modals that only show up when looked at.
- **Rejected:** giving hblab the docker group (root); a GitHub token in the lab before there is a need; guessing at widths without looking.
