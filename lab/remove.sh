#!/bin/bash
# Undo lab/setup.sh: stop hblab's processes, unmount, delete the image, the fstab line, the sudo rule and the user.
# Run with:   sudo bash lab/remove.sh        (xvfb and rsync stay installed: `sudo apt remove xvfb` if you want it gone)
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo:  sudo bash $0"; exit 1; }
IMG=/var/lib/hyperbeam-lab.img; MNT=/srv/hblab

id hblab >/dev/null 2>&1 && { pkill -KILL -u hblab || true; sleep 1; }       # by user id: only hblab's own processes
mountpoint -q "$MNT" && umount "$MNT"
sed -i "\|^$IMG |d" /etc/fstab && systemctl daemon-reload
rm -f /etc/sudoers.d/hyperbeam-lab "$IMG"
id hblab >/dev/null 2>&1 && userdel hblab
rmdir "$MNT" 2>/dev/null || true
[ -e /etc/hyperbeam-lab.uv ] && rm -f /usr/local/bin/uv /etc/hyperbeam-lab.uv     # only the copy setup.sh made
[ -e /etc/hyperbeam-lab.pnpm ] && rm -f /usr/local/bin/pnpm /etc/hyperbeam-lab.pnpm     # only the shim setup.sh made
[ -e /etc/hyperbeam-lab.podman ] && rm -f /etc/hyperbeam-lab.podman     # podman itself stays installed (sudo apt remove podman uidmap passt); hblab's id ranges go with the user
rm -f /tmp/.X11-unix/X99 /tmp/.X99-lock
echo "lab removed (a backup of the old fstab is /etc/fstab.hyperbeam-lab.bak)"
