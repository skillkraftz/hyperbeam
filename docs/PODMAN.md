# Docker in the lab: rootless podman (investigation)

**Status: waiting for the user to run `sudo bash lab/podman-setup.sh` once.** Nothing is installed or changed before that.

## Why
The lab user `hblab` must not be in the `docker` group (that is root on this machine, and would let a test touch the user's real containers and files).
Projects whose services need Docker (algoviewz-platform: `pnpm supabase:start` = the Supabase CLI = Docker; plantlab's compose files) cannot test in the lab today: they are listed as an exception in their CLAUDE.md. Rootless podman runs containers as `hblab` with a private range of user ids, inside the lab disk, and cannot see the user's Docker containers or images.

## Known (checked 2026-11-11)
- podman is not installed (apt has 5.7.0); `hblab` has no `/etc/subuid` range (the user has `andy:100000:65536`); `/usr/bin/docker` is the only runtime.
- `lab/podman-setup.sh` installs podman + uidmap + passt, gives hblab 200000-265535 (no overlap), and writes hblab's containers.conf (cgroupfs, file events, pasta networking: no systemd session needed). `lab/remove.sh` undoes the config.

## To test after the script (as hblab, `hyperbeam lab run --why ...`)
1. `podman info --format {{.Host.Security.Rootless}}` is true; `podman run --rm docker.io/library/hello-world`.
2. A compose file from a real project (`podman compose up -d` / `docker-compose` with `DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock`), published ports only from `$LAB_PORT_MIN`-`$LAB_PORT_MAX`.
3. The Supabase CLI (`pnpm supabase:start` in algoviewz-platform) against the podman socket: the likely sticking point (it expects the Docker API, volumes and a few privileged-looking mounts).
4. hblab cannot see the user's containers (`podman ps -a` empty; the user's `docker ps` unchanged).
5. Disk: image storage lives in `/srv/hblab/.local/share/containers`; note the size after step 3 (the lab disk is fixed-size).

## Decision gate
- **Works:** Docker-based tests move from "exception" to supported in the lab; CLAUDE.md Lab section and RULES.md lose the exception; the projects' CLAUDE.md exception lines are removed by Align.
- **Works with a workaround** (for example only plain compose, not the Supabase CLI): document exactly what runs, keep the rest as an exception.
- **Does not work:** the alternative is a libvirt/virsh VM: its own Docker, network and credentials, snapshot/revert (matches "undo a wrong iteration"). Costs: disk and RAM for a VM image, a sync step, and **no GPU** (passthrough of the only NVIDIA card is not realistic). Decide then.

## Results
(not run yet)
