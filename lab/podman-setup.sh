#!/bin/bash
# hyperbeam lab: rootless podman for the user hblab, so Docker-style tests can run in the lab WITHOUT giving hblab the docker group (which is root).
# Run once, as yourself, with sudo (after lab/setup.sh):   sudo bash lab/podman-setup.sh
# Safe to run again. `sudo bash lab/remove.sh` undoes the config (podman and its packages stay installed: `sudo apt remove podman uidmap passt`).
# What it changes: installs podman, uidmap and passt (apt) if missing; gives hblab a private range of user ids (/etc/subuid, /etc/subgid, a range that
# does not overlap yours); writes hblab's containers.conf (no systemd needed: cgroupfs, file events). Containers then run as hblab, inside the lab disk,
# and cannot see your Docker containers or images.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo:  sudo bash $0"; exit 1; }
id hblab >/dev/null 2>&1 || { echo "the lab user hblab does not exist: run  sudo bash $(dirname "$0")/setup.sh  first"; exit 1; }
MNT=/srv/hblab
mountpoint -q "$MNT" || { echo "$MNT is not mounted: run setup.sh again"; exit 1; }

command -v podman >/dev/null || apt-get install -y podman uidmap passt
command -v newuidmap >/dev/null || apt-get install -y uidmap

# a private range of 65536 ids for hblab's containers (yours starts at 100000; this one does not overlap it)
grep -q '^hblab:' /etc/subuid || usermod --add-subuids 200000-265535 hblab
grep -q '^hblab:' /etc/subgid || usermod --add-subgids 200000-265535 hblab

# hblab is a system user without a systemd session: tell podman not to need one
install -d -o hblab -g hblab -m 700 "$MNT/.config" "$MNT/.config/containers"
if [ ! -e "$MNT/.config/containers/containers.conf" ]; then
  cat > "$MNT/.config/containers/containers.conf" <<'EOF'
[engine]
cgroup_manager = "cgroupfs"
events_logger = "file"
[containers]
netns = "pasta"
EOF
  chown hblab:hblab "$MNT/.config/containers/containers.conf"
fi
touch /etc/hyperbeam-lab.podman
echo "podman ready for hblab. Check:  hyperbeam lab run --why 'podman check' 'podman info --format {{.Host.Security.Rootless}}'"
