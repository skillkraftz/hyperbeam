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
# rsync keeps one synced copy of each project in the lab (hyperbeam lab run).
command -v rsync >/dev/null || apt-get install -y rsync

# 2. The disk image (to change the size later: sudo bash lab/remove.sh, then sudo bash lab/setup.sh NEWSIZE; the lab's contents are rebuilt by the next runs): a fixed-size file (space reserved now, so tests can never fill your disk), formatted ext4.
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

# 4b. GPU: the DRI nodes (/dev/dri/*) belong to the groups video and render, so hblab joins them if they exist. The NVIDIA nodes (/dev/nvidia*)
#     are world-writable here already, so CUDA works for hblab without any group; nvidia-smi sees every process's VRAM, and the card is shared
#     with your desktop, so GPU runs compete with your work. Docker stays out: the docker group is root, so hblab is kept out of it.
for g in video render; do
  if getent group "$g" >/dev/null && ! id -nG hblab | tr ' ' '\n' | grep -qx "$g"; then usermod -aG "$g" hblab; fi
done
id -nG hblab | tr ' ' '\n' | grep -qx docker && gpasswd -d hblab docker >/dev/null
if command -v nvidia-smi >/dev/null; then
  echo "note: GPU: hblab is in $(id -nG hblab | sed 's/^hblab //') ; /dev/nvidia* mode: $(stat -c %a /dev/nvidia0 2>/dev/null || echo none)."
  echo "      A GPU run shares the card and its VRAM with your desktop (Kdenlive, ...). stenographr's tests are offline (fake nvidia-smi); its [gpu] extra"
  echo "      downloads ~1.6 GB of CUDA wheels into the lab disk, so only run real GPU transcription in the lab on purpose."
fi

# 5. uv for hblab (it can't read your ~/.local/bin): a copy in /usr/local/bin, only if there isn't one.
if [ ! -e /usr/local/bin/uv ] && [ -x "$(getent passwd "$WHO" | cut -d: -f6)/.local/bin/uv" ]; then
  install -m755 "$(getent passwd "$WHO" | cut -d: -f6)/.local/bin/uv" /usr/local/bin/uv && touch /etc/hyperbeam-lab.uv
fi

# 5b. pnpm: `hyperbeam lab run` installs it once with npm into the lab disk (/srv/hblab/cache/tools). The corepack shim an earlier version of this script
#     made can't run pnpm 12 (corepack 0.24 looks for bin/pnpm.cjs, which pnpm 12 doesn't ship): remove it, only if this script made it.
if [ -e /etc/hyperbeam-lab.pnpm ]; then rm -f /usr/local/bin/pnpm /etc/hyperbeam-lab.pnpm; fi

# 6. sudo rule: you may run commands as hblab (and only as hblab, never as root), without a password. Checked with visudo before it is installed.
tmp="$(mktemp)"; echo "$WHO ALL=(hblab) NOPASSWD: ALL" > "$tmp"
visudo -c -q -f "$tmp" || { rm -f "$tmp"; echo "the sudoers rule did not validate; nothing installed"; exit 1; }
install -m440 -o root -g root "$tmp" "$SUDOERS"; rm -f "$tmp"
visudo -c -q

H="$(getent passwd "$WHO" | cut -d: -f6)"
[ $(( 0$(stat -c %a "$H") & 5 )) -ne 0 ] && echo "note: $H is readable by other users (mode $(stat -c %a "$H")); to keep hblab out: chmod 750 $H"
echo "lab ready: $MNT ($SIZE image $IMG). Try:  hyperbeam lab status"
