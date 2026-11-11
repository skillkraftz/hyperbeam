#!/bin/bash
# hyperbeam lab: a user `hblab` whose home is a disk image, so agent tests can't touch your processes or your /home.
# Run once, as yourself, with sudo:   sudo bash lab/setup.sh [SIZE]      (SIZE defaults to 10G)
# Safe to run again (every step checks first). `sudo bash lab/remove.sh` undoes all of it.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run it with sudo:  sudo bash $0 [SIZE]"; exit 1; }
WHO="${SUDO_USER:-}"                      # the human who gets the right to run commands as hblab
[[ "$WHO" =~ ^[a-z_][a-z0-9_-]*$ && "$WHO" != root ]] || { echo "run it with sudo from your own account (SUDO_USER is '$WHO')"; exit 1; }
SIZE="${1:-10G}"
IMG=/var/lib/hyperbeam-lab.img            # on the root partition, not /home
MNT=/srv/hblab                            # hblab's home
SUDOERS=/etc/sudoers.d/hyperbeam-lab

# 1. The virtual display for GUI tests (Xvfb), only if missing.
command -v Xvfb >/dev/null || apt-get install -y xvfb

# 2. The disk image: a fixed-size file (space reserved now, so tests can never fill your disk), formatted ext4.
if [ ! -e "$IMG" ]; then
  fallocate -l "$SIZE" "$IMG" || truncate -s "$SIZE" "$IMG"
  mkfs.ext4 -q -F -L hblab "$IMG"
  chmod 600 "$IMG"
fi

# 3. Mount it at /srv/hblab now and at every boot (nofail: a missing image never blocks booting).
mkdir -p "$MNT"
if ! grep -qs "^$IMG " /etc/fstab; then
  cp -n /etc/fstab /etc/fstab.hyperbeam-lab.bak
  echo "$IMG $MNT ext4 loop,noatime,nofail 0 2" >> /etc/fstab
  systemctl daemon-reload
fi
mountpoint -q "$MNT" || mount "$MNT"

# 4. The user hblab: a system account, home on the image, no password. It is a different uid from yours,
#    so nothing it runs (not even `kill -9 -1`) can signal your processes.
id hblab >/dev/null 2>&1 || useradd --system --user-group --home-dir "$MNT" --no-create-home --shell /bin/bash hblab
chown hblab:hblab "$MNT"; chmod 750 "$MNT"

# 5. uv for hblab (it can't read your ~/.local/bin): a copy in /usr/local/bin, only if there isn't one.
if [ ! -e /usr/local/bin/uv ] && [ -x "$(getent passwd "$WHO" | cut -d: -f6)/.local/bin/uv" ]; then
  install -m755 "$(getent passwd "$WHO" | cut -d: -f6)/.local/bin/uv" /usr/local/bin/uv && touch /etc/hyperbeam-lab.uv
fi

# 6. sudo rule: you may run commands as hblab (and only as hblab, never as root), without a password. Checked with visudo before it is installed.
tmp="$(mktemp)"; echo "$WHO ALL=(hblab) NOPASSWD: ALL" > "$tmp"
visudo -c -q -f "$tmp" || { rm -f "$tmp"; echo "the sudoers rule did not validate; nothing installed"; exit 1; }
install -m440 -o root -g root "$tmp" "$SUDOERS"; rm -f "$tmp"
visudo -c -q

H="$(getent passwd "$WHO" | cut -d: -f6)"
[ $(( 0$(stat -c %a "$H") & 5 )) -ne 0 ] && echo "note: $H is readable by other users (mode $(stat -c %a "$H")); to keep hblab out: chmod 750 $H"
echo "lab ready: $MNT ($SIZE image $IMG). Try:  hyperbeam lab status"
