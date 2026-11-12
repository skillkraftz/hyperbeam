#!/bin/bash
# Install hyperbeam: a clone of main at ~/.local/lib/hyperbeam (the app you run; never edit it), `hyperbeam` and the tmux conf linked to it, the Claude hooks
# (the guard) pointed at it. Safe to run again: it fast-forwards the clone. Work on hyperbeam in its dev folder (~/projects/hyperbeam), on branches.
set -euo pipefail
src="$(cd "$(dirname "$0")" && pwd)"
lib="${HB_LIB:-$HOME/.local/lib/hyperbeam}"
bin="${HB_BIN:-$HOME/.local/bin}"
conf="${HB_TMUXCONF:-$HOME/.config/tmux/hyperbeam.conf}"
origin="${HB_ORIGIN:-$(git -C "$src" remote get-url origin)}"
if [ -d "$lib/.git" ]; then
  git -C "$lib" fetch -q origin
  git -C "$lib" checkout -q main
  git -C "$lib" merge -q --ff-only origin/main
else
  mkdir -p "$(dirname "$lib")"
  git clone -q "$origin" "$lib"
fi
mkdir -p "$bin" "$(dirname "$conf")"
ln -sfn "$lib/hyperbeam" "$bin/hyperbeam"
ln -sfn "$lib/hyperbeam.conf" "$conf"
uv run --quiet --script "$lib/hyperbeam" _hooks
echo "hyperbeam installed: $lib ($(git -C "$lib" log --oneline -1))"
echo "Now restart the hyperbeam session so it runs from there (close the sidebar window and run: hyperbeam)."
