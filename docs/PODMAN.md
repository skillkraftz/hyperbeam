# Docker in the lab: rootless podman (investigation)

**Status (2026-11-11): installed (the user ran `lab/podman-setup.sh`) and investigated. Works for single containers and for compose with host networking; compose's own networks need one more step (see Results).**

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

## Results (lab runs on 2026-11-11; scripts were throwaway, the shims are in `lab_ensure_shims`)
| Test | Result |
|---|---|
| `podman info` as hblab | rootless true, overlay storage, netavark; harmless warning "Failed to add pause process to systemd sandbox cgroup" (hblab has no systemd user session) |
| `podman run hello-world` / alpine / nginx / redis, images pulled from docker.io | works; 65-105 MB of images in `/srv/hblab/.local/share/containers` |
| hblab sees the user's containers? | no (0), and `/var/run/docker.sock` is root:docker, mode 660: hblab cannot reach the real Docker |
| `podman run -p PORT:80` with the default runtime dir `/srv/hblab/rt/<id>` | **fails**: "pasta failed ... Couldn't open network namespace ... Permission denied". Cause (kernel log): Ubuntu's AppArmor profile for pasta only lets it open files under `/tmp/**` |
| the same with `XDG_RUNTIME_DIR` under `/tmp` | **works**: published port answers 200, outbound network works, the container's uid 0 is hblab |
| `podman run --network host` | works (the container shares the machine's network: use ports from `$LAB_PORT_MIN`-`$LAB_PORT_MAX`) |
| a runtime dir that **changes per run** | breaks the second run: podman keeps the first run's runtime dir in its state (`rootless-netns` pid file under a deleted dir). Fix: one stable dir, `/tmp/hblab-podman` |
| Docker API socket (`podman system service`) + `docker` CLI + `docker compose` v2 (installed plugin) | works: `docker version` answers podman 5.7.0 |
| `docker compose up` with **host networking** (`network_mode: host`, a named volume, a port from the lab range) | **works**: redis answered PONG, `down -v` leaves nothing |
| `docker compose up` with compose's **default network** (service-name DNS) | **fails**: "aardvark-dns failed to start: Failed to connect to user scope bus". netavark starts aardvark-dns through the user's systemd bus, which hblab (a system user) does not have |

## What the lab does now
`lab run` writes two shims into hblab's `~/.local/bin` (first on PATH): `podman` (runtime dir `/tmp/hblab-podman`) and `docker` (the same dir; starts `podman system service` there on first use and points `DOCKER_HOST` at it, so `docker ...` and `docker compose ...` work unchanged and cannot reach the real Docker). Containers are per user, not per run: they are shared between lab runs, and `docker compose down` / `podman rm -af` in a test cleans them up (a run's tagged processes are killed when it ends, which stops its containers).

## Decision
- **Supported now:** single containers (published ports from the lab range, volumes, outbound network) and compose files that use `network_mode: host`. A project's own CLAUDE.md can drop "Docker tests are not run in the lab" for those.
- **Open:** compose's default bridge network (services reaching each other by name). Candidate fix, **needs the user (sudo)**: `sudo loginctl enable-linger hblab` so hblab has a user systemd/dbus (then the shims would use `/run/user/997`). Untested: hblab is a system user (uid 997), which systemd may not give a user manager. Only worth doing when a project needs it: no current project does (algoviewz is set aside).
- **Fallback if that fails:** the libvirt/virsh VM (its own Docker, network and credentials, snapshot/revert; costs disk and RAM; no GPU).
