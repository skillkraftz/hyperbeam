---
id: 2026-11-15-simplify-guard
status: implemented
prs: []
topic: guard
---
# The guard parses commands instead of matching words

- **Decision:** `guard.py` has one tokenizer (`parse`: shlex, split at `; & | ( )`, backtick and newline, heredoc bodies dropped, quoted strings single words, `bash -c` and `$(...)` looked into), one reducer (`head`: command word and args without VAR=x and wrappers) and one rule table tested per command. Kill is one rule (command word kill/pkill/killall); `hyperbeam lab run|tool|shot` commands are skipped. Same blocks and messages as before.
- **Why:** word matching blocked harmless text (a heredoc writing notes that mention "terminal recordings", a commit message with pkill); kill was checked three ways; the lab already refuses most of it.
- **Rejected:** regexes over the whole line (the cause of the false positives); dropping rules (each one prevents a past incident).
