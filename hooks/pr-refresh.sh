#!/bin/sh
# PostToolUse hook on Bash (installed by `hyperbeam update`, see prs_command): after `gh pr create|merge|close` refresh hyperbeam's PR list in the background, so the
# sidebar's Merge button is right at once. Reads the hook input (JSON) on stdin: the new PR's number is the /pull/N in the tool output; merged or closed
# numbers come from the command. Does nothing outside hyperbeam sessions.
[ -n "$HB_PROJECT" ] || exit 0
in=$(cat)
case "$in" in *"gh pr create"*|*"gh pr merge"*|*"gh pr close"*) ;; *) exit 0;; esac
new=$(printf %s "$in" | grep -o 'pull/[0-9]*' | cut -d/ -f2 | sort -un | tr '\n' ' ')
gone=$(printf %s "$in" | grep -o 'gh pr \(merge\|close\) [0-9]*' | grep -o '[0-9]*$' | sort -un | tr '\n' ' ')
hyperbeam refresh-prs "$HB_PROJECT" $new ${gone:+--gone $gone} >/dev/null 2>&1 &
exit 0
